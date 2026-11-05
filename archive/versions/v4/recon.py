"""
recon.py - Phase 0: Network environment scanner (v4)

Fixes vs v2:
- _get_mtu(): ifconfig 파싱 들여쓰기 구조 오류 수정
- _check_dns_hijacked(): 각 DNS 쌍을 ThreadPoolExecutor로 병렬 실행
- DNS hijack detection: 여러 도메인 + 여러 레퍼런스 DNS 비교로 false-positive 감소
- MTU 탐지: macOS 호환 (-D 대신 networksetup -getMTU 우선 사용)
- 포트 체크: 단일 IP 편향 제거, 여러 엔드포인트 테스트
- _check_dns_hijacked를 executor로 실행해 이벤트 루프 블로킹 방지
"""

import asyncio
import socket
import subprocess
import time
import httpx
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
    "quad9":      "https://dns.quad9.net/dns-query",
    "cloudflare": "https://cloudflare-dns.com/dns-query",
    "adguard":    "https://dns.adguard-dns.com/dns-query",
}

# 하이재킹 감지용 레퍼런스 DNS (학교가 동시에 둘 다 제어하기 어려운 조합)
_REF_DNS_PAIRS = [
    ("9.9.9.9", "8.8.4.4"),   # Quad9 vs Google Secondary
    ("1.1.1.1", "8.8.8.8"),   # Cloudflare vs Google
]

# 여러 도메인으로 비교 → 한 도메인 캐시 차이에 의한 false positive 방지
_HIJACK_TEST_DOMAINS = [
    b'\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x06whoami\x06akamai\x03net\x00\x00\x01\x00\x01',
    b'\xab\xcd\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x0ccloudflare-dns\x03com\x00\x00\x01\x00\x01',
]


def get_wifi_interface() -> str:
    try:
        output = subprocess.check_output(
            ["networksetup", "-listallhardwareports"], text=True, timeout=5
        )
        lines = output.split('\n')
        for i, line in enumerate(lines):
            if "Hardware Port: Wi-Fi" in line and i + 1 < len(lines):
                return lines[i + 1].replace("Device:", "").strip()
    except Exception:
        pass
    return "en0"


def get_wifi_info() -> tuple[str, str]:
    try:
        airport_path = (
            "/System/Library/PrivateFrameworks/Apple80211.framework"
            "/Versions/Current/Resources/airport"
        )
        output = subprocess.check_output([airport_path, "-I"], text=True, timeout=5)
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
        output = subprocess.check_output(
            ["networksetup", "-getdnsservers", interface], text=True, timeout=5
        ).strip()
        if "There aren't any" in output or not output:
            return []
        return [line.strip() for line in output.split('\n') if line.strip()]
    except Exception:
        return []


from typing import Optional

def _resolve_raw(ip: str, query: bytes, timeout: float = 2.0) -> Optional[bytes]:
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(query, (ip, 53))
        data, _ = sock.recvfrom(512)
        if data and len(data) >= 12:
            return data[-4:]  # 마지막 4바이트: 응답 IP
        return None
    except Exception:
        return None
    finally:
        if sock:
            sock.close()


def _check_dns_hijacked(original_dns: list[str]) -> bool:
    """
    여러 레퍼런스 DNS 쌍으로 비교, 다수결로 판정.
    original_dns의 첫 번째 서버와 두 독립 레퍼런스가 모두 다를 때만 hijack으로 판정.
    """
    target = original_dns[0] if original_dns else "8.8.8.8"

    mismatch_votes = 0
    total_votes = 0

    for query in _HIJACK_TEST_DOMAINS:
        for ref_a, ref_b in _REF_DNS_PAIRS:
            res_target = _resolve_raw(target, query)
            res_ref_a  = _resolve_raw(ref_a, query)
            res_ref_b  = _resolve_raw(ref_b, query)

            if res_target and res_ref_a and res_ref_b:
                total_votes += 1
                # 두 레퍼런스가 동일한데 target이 다르면 하이재킹 의심
                if res_ref_a == res_ref_b and res_target != res_ref_a:
                    mismatch_votes += 1

    if total_votes == 0:
        return False
    # 과반수 이상 불일치 시 hijack
    return mismatch_votes > total_votes // 2


async def check_doh_provider(name: str, url: str) -> tuple[str, bool, float]:
    query = b'\x56\x78\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03com\x00\x00\x01\x00\x01'
    start = time.time()
    try:
        async with httpx.AsyncClient(http2=True, timeout=4.0) as client:
            resp = await client.post(
                url,
                headers={"Content-Type": "application/dns-message"},
                content=query,
            )
            resp.raise_for_status()
            if resp.content:
                return name, True, (time.time() - start) * 1000
    except Exception:
        pass
    return name, False, 0.0


def _check_port_443() -> bool:
    """여러 엔드포인트 중 하나라도 열려 있으면 True."""
    endpoints = [("1.1.1.1", 443), ("8.8.8.8", 443), ("9.9.9.9", 443)]
    for host, port in endpoints:
        sock = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect((host, port))
            return True
        except Exception:
            pass
        finally:
            if sock:
                sock.close()
    return False


def _get_mtu(interface: str) -> int:
    """
    macOS: networksetup -getMTU 우선 사용.
    실패 시 ifconfig 파싱, 그마저 실패 시 1500 반환.
    (v1의 ping -D 방식은 macOS에서 -D가 타임스탬프 플래그라 DF bit 설정 불가)
    """
    try:
        out = subprocess.check_output(
            ["networksetup", "-getMTU", interface], text=True, timeout=5
        )
        # 출력 예: "Active MTU: 1500 (Current Setting: 1500)"
        for token in out.split():
            if token.isdigit():
                val = int(token)
                if 576 <= val <= 9000:
                    return val
    except Exception:
        pass

    # [Fix v4] ifconfig 파싱 로직 수정 (v2의 들여쓰기 구조 오류 해결)
    try:
        out = subprocess.check_output(["ifconfig", interface], text=True, timeout=5)
        tokens = out.split()
        for i, tok in enumerate(tokens):
            if tok == "mtu" and i + 1 < len(tokens) and tokens[i + 1].isdigit():
                val = int(tokens[i + 1])
                if 576 <= val <= 9000:
                    return val
    except Exception:
        pass

    return 1500


def _check_captive_portal() -> bool:
    import urllib.request
    try:
        req = urllib.request.Request("http://captive.apple.com/hotspot-detect.html")
        with urllib.request.urlopen(req, timeout=3.0) as response:
            body = response.read().decode("utf-8")
            return "Success" not in body
    except Exception:
        return False


async def run_recon() -> ReconResult:
    interface = get_wifi_interface()
    ssid, bssid = get_wifi_info()
    original_dns = get_original_dns(interface)

    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=5) as pool:
        # 동기 블로킹 작업을 executor로 병렬 실행
        hijack_fut    = loop.run_in_executor(pool, _check_dns_hijacked, original_dns)
        port_443_fut  = loop.run_in_executor(pool, _check_port_443)
        mtu_fut       = loop.run_in_executor(pool, _get_mtu, interface)
        captive_fut   = loop.run_in_executor(pool, _check_captive_portal)

        doh_tasks = [check_doh_provider(n, u) for n, u in PROVIDERS.items()]
        doh_results_list = await asyncio.gather(*doh_tasks)

        dns_hijacked   = await hijack_fut
        port_443_open  = await port_443_fut
        mtu            = await mtu_fut
        captive_portal = await captive_fut

    doh_reachable: dict[str, bool]  = {}
    doh_latency:   dict[str, float] = {}
    for name, reachable, lat in doh_results_list:
        doh_reachable[name] = reachable
        if reachable:
            doh_latency[name] = lat

    # 모드 결정
    if not port_443_open:
        recommended_mode = "passive"
    elif any(doh_reachable.values()) and not dns_hijacked:
        recommended_mode = "standard"
    elif any(doh_reachable.values()) and dns_hijacked:
        recommended_mode = "obfuscated"
    else:
        recommended_mode = "passive"

    recommended_provider = (
        min(doh_latency, key=doh_latency.get) if doh_latency else "quad9"
    )

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
        recommended_provider=recommended_provider,
    )


def format_recon_report(r: ReconResult) -> str:
    parts = [
        f"SSID: {r.ssid or 'Unknown'}",
        f"DNS 하이재킹: {'감지됨' if r.dns_hijacked else '없음'}",
        f"권장 모드: {t('mode_' + r.recommended_mode)}",
    ]
    if r.recommended_mode != "passive" and r.recommended_provider:
        lat = r.doh_latency.get(r.recommended_provider, 0)
        parts.append(f"최적 DoH: {r.recommended_provider.title()} ({lat:.0f}ms)")

    if r.captive_portal:
        parts.append("\n⚠️ Captive portal 감지! 브라우저로 먼저 로그인하세요.")
    if r.recommended_mode == "passive":
        parts.append(f"\n⚠️ {t('recon_doh_blocked')}")

    return "\n".join(parts)
