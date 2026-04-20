"""
recon.py - Phase 0: Network environment scanner
"""

import asyncio
import socket
import subprocess
import time
import httpx
import urllib.request
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from locales import t

@dataclass
class ReconResult:
    ssid: str
    bssid: str
    interface: str
    original_dns: list[str]
    dns_hijacked: bool
    doh_reachable: dict[str, bool]
    doh_latency: dict[str, float]
    port_443_open: bool
    mtu: int
    captive_portal: bool
    recommended_mode: str
    recommended_provider: str

PROVIDERS = {
    "quad9": "https://dns.quad9.net/dns-query",
    "cloudflare": "https://cloudflare-dns.com/dns-query",
    "adguard": "https://dns.adguard-dns.com/dns-query"
}

def get_wifi_interface() -> str:
    try:
        output = subprocess.check_output(["networksetup", "-listallhardwareports"], text=True)
        lines = output.split('\n')
        for i, line in enumerate(lines):
            if "Hardware Port: Wi-Fi" in line:
                if i + 1 < len(lines):
                    return lines[i+1].replace("Device:", "").strip()
    except Exception:
        pass
    return "en0"

def get_wifi_info() -> tuple[str, str]:
    try:
        airport_path = "/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport"
        output = subprocess.check_output([airport_path, "-I"], text=True)
        ssid, bssid = "", ""
        for line in output.split('\n'):
            line = line.strip()
            if line.startswith("SSID:"):
                ssid = line.split(":", 1)[1].strip()
            elif line.startswith("BSSID:"):
                bssid = line.split(":", 1)[1].strip()
        return ssid, bssid
    except Exception:
        return "", ""

def get_original_dns(interface: str) -> list[str]:
    try:
        output = subprocess.check_output(["networksetup", "-getdnsservers", interface], text=True).strip()
        if "There aren't any" in output or not output:
            return []
        return [line.strip() for line in output.split('\n') if line.strip()]
    except Exception:
        return []

def _check_dns_hijacked_proper(original_dns: list[str]) -> bool:
    query = b'\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x06whoami\x06akamai\x03net\x00\x00\x01\x00\x01'
    def resolve_raw(ip):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)
            sock.sendto(query, (ip, 53))
            data, _ = sock.recvfrom(512)
            sock.close()
            if data and len(data) >= 4:
                return data[-4:]
            return None
        except Exception:
            return None

    target_dns = "8.8.8.8" if not original_dns else original_dns[0]
    res_orig = resolve_raw(target_dns)
    res_quad9 = resolve_raw("9.9.9.9")

    if res_orig and res_quad9:
        if res_orig != res_quad9:
            return True
    return False

async def check_doh_provider(name: str, url: str) -> tuple[str, bool, float]:
    query_example = b'\x56\x78\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03com\x00\x00\x01\x00\x01'
    
    start_time = time.time()
    try:
        async with httpx.AsyncClient(http2=True) as client:
            resp = await client.post(
                url,
                headers={"Content-Type": "application/dns-message"},
                content=query_example,
                timeout=3.0
            )
            resp.raise_for_status()
            elapsed = (time.time() - start_time) * 1000
            if resp.content:
                return name, True, elapsed
    except Exception:
        pass
    return name, False, 0.0

def check_port_443() -> bool:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect(("1.1.1.1", 443))
        sock.close()
        return True
    except Exception:
        return False

def check_mtu() -> int:
    mtu_candidates = [1400, 1300, 1200]
    for size in mtu_candidates:
        try:
            out = subprocess.check_output(
                ["ping", "-c", "1", "-D", "-s", str(size), "-t", "1", "8.8.8.8"], 
                text=True, stderr=subprocess.STDOUT
            )
            if "frag needed" not in out and "1 packets received" in out:
                return size + 28
        except Exception:
            continue
    return 1500

def check_captive_portal() -> bool:
    try:
        req = urllib.request.Request("http://captive.apple.com/hotspot-detect.html")
        with urllib.request.urlopen(req, timeout=3.0) as response:
            body = response.read().decode('utf-8')
            if "Success" not in body:
                return True
            return False
    except Exception:
        return False

async def run_recon() -> ReconResult:
    interface = get_wifi_interface()
    ssid, bssid = get_wifi_info()

    original_dns = get_original_dns(interface)

    dns_hijacked = _check_dns_hijacked_proper(original_dns)
    
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        port_443_open_task = loop.run_in_executor(pool, check_port_443)
        mtu_task = loop.run_in_executor(pool, check_mtu)
        captive_portal_task = loop.run_in_executor(pool, check_captive_portal)

        port_443_open = await port_443_open_task
        mtu = await mtu_task
        captive_portal = await captive_portal_task

    doh_tasks = [check_doh_provider(name, url) for name, url in PROVIDERS.items()]
    doh_results = await asyncio.gather(*doh_tasks)

    doh_reachable = {}
    doh_latency = {}
    for name, rch, lat in doh_results:
        doh_reachable[name] = rch
        if rch:
            doh_latency[name] = lat

    recommended_mode = "passive"
    recommended_provider = "quad9"

    if not port_443_open:
        recommended_mode = "passive"
    elif any(doh_reachable.values()) and not dns_hijacked:
        recommended_mode = "standard"
        if doh_latency:
            recommended_provider = min(doh_latency, key=doh_latency.get)
    elif any(doh_reachable.values()) and dns_hijacked:
        recommended_mode = "obfuscated"
        if doh_latency:
            recommended_provider = min(doh_latency, key=doh_latency.get)
    else:
        recommended_mode = "passive"

    return ReconResult(
        ssid=ssid,
        bssid=bssid,
        interface=interface,
        original_dns=original_dns,
        dns_hijacked=dns_hijacked,
        doh_reachable=doh_reachable,
        doh_latency=doh_latency,
        port_443_open=port_443_open,
        mtu=mtu,
        captive_portal=captive_portal,
        recommended_mode=recommended_mode,
        recommended_provider=recommended_provider
    )

async def format_recon_report(r: ReconResult) -> str:
    parts = []
    parts.append(f"SSID: {r.ssid or 'Unknown'}")
    parts.append(f"DNS Hijack: {'Yes' if r.dns_hijacked else 'No'}")
    parts.append(f"Recommended Mode: {t('mode_' + r.recommended_mode)}")
    if r.recommended_mode != "passive" and r.recommended_provider:
        latency = r.doh_latency.get(r.recommended_provider, 0)
        parts.append(f"Best DoH: {r.recommended_provider.title()} ({latency:.0f}ms)")
    
    if r.captive_portal:
        parts.append("\n⚠️ Captive portal detected! Please log in via browser first.")
    if r.recommended_mode == "passive":
        parts.append(f"\n⚠️ {t('recon_doh_blocked')}")

    return "\n".join(parts)
