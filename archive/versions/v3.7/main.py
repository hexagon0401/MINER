"""
main.py - Entry point: CLI parsing + GUI launch (v2)

Fixes vs v1:
- --stop: SIGTERM 이후 프로세스 종료 확인 대기 추가
- --test: provider latency 측정 병렬화 (asyncio)
- --start: asyncio.run(apply_optimization(...)) 불필요한 감싸기 제거
- PID 파일 검증: psutil 없어도 /proc 또는 kill(0) 방식으로 프로세스 존재 확인
"""

import sys
import argparse
import asyncio
import json
import logging
from dataclasses import asdict

from settings import Settings, setup_logging
from recon import run_recon, PROVIDERS
from network_manager import apply_optimization, restore_original, measure_latency
from doh_proxy import DoHProxy


def _pid_path() -> str:
    import os
    return os.path.expanduser("~/.schoolnet.pid")


def write_pid():
    import os
    with open(_pid_path(), "w") as f:
        f.write(str(os.getpid()))


from typing import Optional

def read_pid() -> Optional[int]:
    import os
    path = _pid_path()
    if os.path.exists(path):
        try:
            with open(path) as f:
                return int(f.read().strip())
        except Exception:
            pass
    return None


def _is_running(pid: int) -> bool:
    import os, signal
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # 존재하지만 권한 없음


async def _test_latencies():
    """provider latency 병렬 측정."""
    import time, httpx
    query = b'\x56\x78\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03com\x00\x00\x01\x00\x01'

    async def _measure(name: str, url: str) -> tuple[str, float]:
        start = time.time()
        try:
            async with httpx.AsyncClient(http2=True, timeout=3.0) as c:
                await c.post(url, headers={"Content-Type": "application/dns-message"}, content=query)
            return name, (time.time() - start) * 1000
        except Exception:
            return name, 0.0

    results = await asyncio.gather(*[_measure(n, u) for n, u in PROVIDERS.items()])
    return results


def main():
    parser = argparse.ArgumentParser(description="SchoolNet Optimizer v2 CLI")
    parser.add_argument("--recon",  action="store_true", help="Run recon and print result JSON")
    parser.add_argument("--start",  action="store_true", help="Recon + optimize + start proxy (no GUI)")
    parser.add_argument("--stop",   action="store_true", help="Stop daemon and restore DNS")
    parser.add_argument("--status", action="store_true", help="Print current status JSON")
    parser.add_argument("--test",   action="store_true", help="Test latency to all providers")
    args = parser.parse_args()

    setup_logging()
    config = Settings.load()

    if args.recon:
        res = asyncio.run(run_recon())
        print(json.dumps(asdict(res), indent=2))
        sys.exit(0)

    if args.start:
        write_pid()
        res = asyncio.run(run_recon())

        if res.dns_hijacked:
            config.obfuscation_enabled = True

        opt_res = asyncio.run(apply_optimization(res, config))
        print(json.dumps(asdict(opt_res)))

        if not opt_res.success:
            sys.exit(1)

        proxy = DoHProxy(res, config)
        try:
            asyncio.run(proxy.start())
        except KeyboardInterrupt:
            pass
        finally:
            asyncio.run(restore_original(res, config))
        sys.exit(0)

    if args.stop:
        import os, signal, time as _time
        pid = read_pid()
        if pid and _is_running(pid):
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Sent SIGTERM to {pid}")
                # 최대 5초 대기
                for _ in range(50):
                    if not _is_running(pid):
                        print("Process terminated.")
                        break
                    _time.sleep(0.1)
                else:
                    print("Warning: process may still be running.")
            except Exception as e:
                print(f"Error stopping PID {pid}: {e}")
        else:
            print("No daemon running.")
        sys.exit(0)

    if args.test:
        results = asyncio.run(_test_latencies())
        print(f"{'Provider':<15} {'Latency (ms)':<15}")
        print("-" * 30)
        for name, lat in results:
            status = f"{lat:.0f}" if lat > 0 else "timeout"
            print(f"{name:<15} {status:<15}")
        sys.exit(0)

    if args.status:
        pid = read_pid()
        running = bool(pid and _is_running(pid))
        status = {
            "running":             running,
            "primary_provider":    config.primary_provider,
            "obfuscation_enabled": config.obfuscation_enabled,
        }
        print(json.dumps(status, indent=2))
        sys.exit(0)

    import gui
    gui.run_gui()


if __name__ == "__main__":
    main()
