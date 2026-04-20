"""
network_manager.py - networksetup + pfctl wrappers (v2)

Fixes vs v1:
- pfctl: anchor(com.schoolnet) 사용 → 기존 시스템 방화벽 규칙 보존
  (v1: pfctl -ef - 는 전체 규칙 삭제, pfctl -F all 도 전체 삭제)
- pfctl rdr 규칙: lo0에만 적용 → DNS가 lo0를 통해 127.0.0.1로 들어오므로 유지,
  단 앵커 방식으로 시스템 pf 설정을 덮어쓰지 않음
- restore: SchoolNet-Optimized location 삭제 추가 (v1은 location 잔여물 남김)
- osascript 인자 구성: 셸 인젝션 방지를 위해 명령을 직접 osascript heredoc 방식 사용
- async 함수 내 subprocess → run_in_executor로 이벤트 루프 블로킹 방지
"""

import asyncio
import subprocess
import time
import logging
import httpx
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from recon import ReconResult, PROVIDERS
from settings import Settings

ANCHOR_NAME = "com.schoolnet"

@dataclass
class OptimizationResult:
    success:      bool
    mode:         str
    pfctl_active: bool
    dns_set:      bool
    error:        Optional[str]


def _shell_escape(s: str) -> str:
    """bash 내 단따옴표 이스케이프."""
    return s.replace("'", "'\\''")


def _run_as_admin(shell_script: str) -> tuple[bool, str]:
    """
    osascript로 관리자 권한 셸 스크립트 실행.
    heredoc 방식으로 따옴표 중첩 문제 회피.
    """
    # AppleScript: do shell script "..." 대신 quoted form 사용
    applescript = f'do shell script "{shell_script}" with administrator privileges'
    try:
        out = subprocess.check_output(
            ["osascript", "-e", applescript],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=30,
        )
        return True, out
    except subprocess.CalledProcessError as e:
        return False, e.output or ""
    except subprocess.TimeoutExpired:
        return False, "timeout"


def _build_optimize_script(interface: str, use_pfctl: bool) -> str:
    """최적화 적용 셸 스크립트 생성."""
    iface = _shell_escape(interface)
    lines = [
        # SchoolNet-Optimized location 없으면 생성
        'if ! networksetup -listlocations | grep -q "SchoolNet-Optimized"; then '
        'networksetup -createlocation "SchoolNet-Optimized" populate; fi',
        'networksetup -switchtolocation "SchoolNet-Optimized"',
        f'networksetup -setdnsservers {iface} 127.0.0.1',
    ]
    if use_pfctl:
        # [Fix] pfctl anchor 사용: 기존 시스템 pf 규칙 보존
        # -F all 대신 앵커별로 관리
        anchor_rule = (
            f'echo "rdr pass on lo0 proto udp from any to 127.0.0.1 port 53 -> 127.0.0.1 port 5353" '
            f'| pfctl -a {ANCHOR_NAME} -ef -'
        )
        lines.append(anchor_rule)
    lines.append("dscacheutil -flushcache && killall -HUP mDNSResponder")
    return " && ".join(lines)


def _build_restore_script(interface: str, original_dns: list[str]) -> str:
    """복원 셸 스크립트 생성."""
    iface = _shell_escape(interface)
    orig = [d for d in original_dns if d and d != "127.0.0.1"]

    lines = []
    if orig:
        dns_str = " ".join(_shell_escape(d) for d in orig)
        lines.append(f"networksetup -setdnsservers {iface} {dns_str}")
    else:
        lines.append(f"networksetup -setdnsservers {iface} empty")

    lines.append('networksetup -switchtolocation "Automatic"')

    # [Fix] pfctl anchor만 삭제 → 시스템 방화벽 규칙 보존
    lines.append(f"pfctl -a {ANCHOR_NAME} -F all 2>/dev/null || true")

    # [Fix] SchoolNet-Optimized location 삭제 (v1 잔여물 방지)
    lines.append(
        'networksetup -deletelocation "SchoolNet-Optimized" 2>/dev/null || true'
    )
    lines.append("dscacheutil -flushcache && killall -HUP mDNSResponder")
    return " && ".join(lines)


async def apply_optimization(recon: ReconResult, config: Settings) -> OptimizationResult:
    if recon.recommended_mode == "passive":
        return OptimizationResult(False, "passive", False, False, "DoH not reachable. Passive mode.")

    interface = recon.interface
    if not interface:
        return OptimizationResult(False, recon.recommended_mode, False, False, "No Wi-Fi interface found.")

    use_pfctl = recon.port_443_open

    script = _build_optimize_script(interface, use_pfctl)
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        success, out = await loop.run_in_executor(pool, _run_as_admin, script)

    if not success:
        # pfctl 실패만인 경우 DNS 전용으로 계속
        if use_pfctl and "pfctl" in out.lower():
            logging.warning("pfctl failed, continuing DNS-only mode.")
            return OptimizationResult(True, recon.recommended_mode, False, True,
                                      "pfctl error. DNS-only mode.")
        return OptimizationResult(False, recon.recommended_mode, False, False,
                                  f"Failed to apply: {out}")

    return OptimizationResult(True, recon.recommended_mode, use_pfctl, True, None)


async def restore_original(recon: ReconResult, config: Settings) -> bool:
    interface = recon.interface
    if not interface:
        return False

    script = _build_restore_script(interface, recon.original_dns)
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        success, out = await loop.run_in_executor(pool, _run_as_admin, script)

    if not success:
        logging.error(f"Restore failed: {out}")
    return success


def measure_latency(provider_url: str) -> float:
    """동기 latency 측정 (--test CLI 옵션용)."""
    query = b'\x56\x78\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03com\x00\x00\x01\x00\x01'
    start = time.time()
    try:
        with httpx.Client(http2=True, timeout=3.0) as client:
            client.post(
                provider_url,
                headers={"Content-Type": "application/dns-message"},
                content=query,
            )
        return (time.time() - start) * 1000
    except Exception:
        return 0.0


async def measure_latency_async(provider_url: str) -> float:
    """비동기 latency 측정 (GUI timer 콜백용 - UI 블로킹 방지)."""
    query = b'\x56\x78\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03com\x00\x00\x01\x00\x01'
    start = time.time()
    try:
        async with httpx.AsyncClient(http2=True, timeout=3.0) as client:
            await client.post(
                provider_url,
                headers={"Content-Type": "application/dns-message"},
                content=query,
            )
        return (time.time() - start) * 1000
    except Exception:
        return 0.0
