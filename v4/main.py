"""
main.py - Entry point: CLI parsing + GUI launch (v4)

Changes vs v2:
- Lazy import: GUI 모드에서만 gui.py 로드
- httpx/h2 등 무거운 모듈은 CLI 명령 실행 시점에만 로드
- --self-test 옵션 추가 (네트워크 변경 없는 dry-run 검증)
- PID 파일 검증: psutil 없어도 kill(0) 방식으로 프로세스 존재 확인
"""

import sys
import argparse
import os


def _pid_path() -> str:
    return os.path.expanduser("~/.schoolnet.pid")


def write_pid():
    with open(_pid_path(), "w") as f:
        f.write(str(os.getpid()))


from typing import Optional

def read_pid() -> Optional[int]:
    path = _pid_path()
    if os.path.exists(path):
        try:
            with open(path) as f:
                return int(f.read().strip())
        except Exception:
            pass
    return None


def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # 존재하지만 권한 없음


def main():
    parser = argparse.ArgumentParser(description="SchoolNet Optimizer v4 CLI")
    parser.add_argument("--recon",     action="store_true", help="Run recon and print result JSON")
    parser.add_argument("--start",     action="store_true", help="Recon + optimize + start proxy (no GUI)")
    parser.add_argument("--stop",      action="store_true", help="Stop daemon and restore DNS")
    parser.add_argument("--status",    action="store_true", help="Print current status JSON")
    parser.add_argument("--test",      action="store_true", help="Test latency to all providers")
    parser.add_argument("--self-test", action="store_true", help="Dry-run self test (no network changes)")
    args = parser.parse_args()

    # Logging은 CLI 모드에서만 즉시 초기화
    from settings import Settings, setup_logging
    setup_logging()
    config = Settings.load()

    if args.self_test:
        from self_test import run_all_tests
        run_all_tests()
        sys.exit(0)

    if args.recon:
        import asyncio
        import json
        from dataclasses import asdict
        from recon import run_recon
        res = asyncio.run(run_recon())
        print(json.dumps(asdict(res), indent=2))
        sys.exit(0)

    if args.start:
        import asyncio
        import json
        from dataclasses import asdict
        from recon import run_recon
        from network_manager import apply_optimization, restore_original
        from doh_proxy import DoHProxy

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
        import signal, time as _time
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
        import asyncio
        import time
        import httpx
        from recon import PROVIDERS

        query = b'\x56\x78\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x07example\x03com\x00\x00\x01\x00\x01'

        async def _measure(name: str, url: str) -> tuple[str, float]:
            start = time.time()
            try:
                async with httpx.AsyncClient(http2=True, timeout=3.0) as c:
                    await c.post(url, headers={"Content-Type": "application/dns-message"}, content=query)
                return name, (time.time() - start) * 1000
            except Exception:
                return name, 0.0

        async def _test_all():
            return await asyncio.gather(*[_measure(n, u) for n, u in PROVIDERS.items()])

        results = asyncio.run(_test_all())
        print(f"{'Provider':<15} {'Latency (ms)':<15}")
        print("-" * 30)
        for name, lat in results:
            status = f"{lat:.0f}" if lat > 0 else "timeout"
            print(f"{name:<15} {status:<15}")
        sys.exit(0)

    if args.status:
        import json
        pid = read_pid()
        running = bool(pid and _is_running(pid))
        status = {
            "running":             running,
            "primary_provider":    config.primary_provider,
            "obfuscation_enabled": config.obfuscation_enabled,
        }
        print(json.dumps(status, indent=2))
        sys.exit(0)

    # No CLI flags → launch GUI
    import gui
    gui.run_gui()


if __name__ == "__main__":
    main()
