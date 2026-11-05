"""
network_manager.py - networksetup + pfctl wrappers
"""

import subprocess
import time
import httpx
from dataclasses import dataclass
from typing import Optional

from recon import ReconResult
from settings import Settings

@dataclass
class OptimizationResult:
    success: bool
    mode: str
    pfctl_active: bool
    dns_set: bool
    error: Optional[str]

def _run_osascript(commands: list[str]) -> tuple[bool, str]:
    script = " && ".join(commands)
    script = script.replace('"', '\\"')
    try:
        out = subprocess.check_output(
            ['osascript', '-e', f'do shell script "{script}" with administrator privileges'],
            text=True, stderr=subprocess.STDOUT
        )
        return True, out
    except subprocess.CalledProcessError as e:
        return False, e.output

async def apply_optimization(recon: ReconResult, config: Settings) -> OptimizationResult:
    if recon.recommended_mode == "passive":
        return OptimizationResult(False, "passive", False, False, "DoH not reachable. Set to passive.")

    interface = recon.interface
    if not interface:
        return OptimizationResult(False, recon.recommended_mode, False, False, "No Wi-Fi interface.")

    commands = []
    
    commands.append('not_exist=$(networksetup -listlocations | grep "SchoolNet-Optimized" > /dev/null; echo $?); '
                    'if [ $not_exist -ne 0 ]; then networksetup -createlocation "SchoolNet-Optimized" populate; fi')
    commands.append('networksetup -switchtolocation "SchoolNet-Optimized"')

    commands.append(f'networksetup -setdnsservers {interface} 127.0.0.1')
    
    pfctl_active = False
    if recon.port_443_open and recon.recommended_mode != "passive":
        pf_rule = 'echo "rdr pass on lo0 proto udp from any to 127.0.0.1 port 53 -> 127.0.0.1 port 5353" | pfctl -ef -'
        commands.append(pf_rule)
        pfctl_active = True
        
    commands.append('dscacheutil -flushcache && killall -HUP mDNSResponder')

    success, out = _run_osascript(commands)
    
    if not success:
        if pfctl_active and "pfctl" in out.lower():
            return OptimizationResult(True, recon.recommended_mode, False, True, "pfctl error. Continuing DNS-only mode.")
        return OptimizationResult(False, recon.recommended_mode, False, False, f"Failed to apply settings: {out}")
        
    return OptimizationResult(True, recon.recommended_mode, pfctl_active, True, None)


async def restore_original(recon: ReconResult, config: Settings) -> bool:
    interface = recon.interface
    if not interface:
        return False

    orig = [dns for dns in recon.original_dns if dns and dns != "127.0.0.1"]
    
    commands = []
    
    if not orig:
        commands.append(f'networksetup -setdnsservers {interface} empty')
    else:
        dns_str = " ".join(orig)
        commands.append(f'networksetup -setdnsservers {interface} {dns_str}')

    commands.append('networksetup -switchtolocation "Automatic"')

    commands.append('pfctl -F all')

    commands.append('dscacheutil -flushcache && killall -HUP mDNSResponder')

    success, _ = _run_osascript(commands)
    return success

def measure_latency(provider_url: str) -> float:
    query_example = b'\x56\x78\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03com\x00\x00\x01\x00\x01'
    start = time.time()
    try:
        import httpx
        with httpx.Client(http2=True, timeout=3.0) as client:
            client.post(
                provider_url,
                headers={"Content-Type": "application/dns-message"},
                content=query_example
            )
        elapsed = (time.time() - start) * 1000
        return elapsed
    except Exception:
        return 0.0
