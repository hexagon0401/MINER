"""
main.py - Entry point: CLI parsing + GUI launch
"""

import sys
import argparse
import asyncio
import json
import logging
from dataclasses import asdict

from settings import Settings, setup_logging
from gui import SchoolNetApp
from recon import run_recon
from network_manager import apply_optimization, restore_original, measure_latency
from doh_proxy import DoHProxy
from recon import PROVIDERS

def write_pid():
    import os
    pid_file = os.path.expanduser("~/.schoolnet.pid")
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

def read_pid():
    import os
    pid_file = os.path.expanduser("~/.schoolnet.pid")
    if os.path.exists(pid_file):
        with open(pid_file, "r") as f:
            return int(f.read().strip())
    return None

def main():
    parser = argparse.ArgumentParser(description="SchoolNet Optimizer CLI")
    parser.add_argument("--recon", action="store_true", help="Run recon and print result JSON")
    parser.add_argument("--start", action="store_true", help="Recon + optimize + start proxy (no GUI)")
    parser.add_argument("--stop", action="store_true", help="Stop daemon and restore DNS")
    parser.add_argument("--status", action="store_true", help="Print current status JSON")
    parser.add_argument("--test", action="store_true", help="Test latency to all providers")
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
        if opt_res.success:
            print(json.dumps(asdict(opt_res)))
            proxy = DoHProxy(res, config)
            try:
                asyncio.run(proxy.start())
            except KeyboardInterrupt:
                pass
            finally:
                asyncio.run(restore_original(res, config))
        else:
            print(json.dumps(asdict(opt_res)))
            sys.exit(1)
        sys.exit(0)

    if args.stop:
        import os, signal
        pid = read_pid()
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Sent SIGTERM to {pid}")
            except Exception as e:
                print(f"Error stopping PID {pid}: {e}")
        else:
            print("No daemon running.")
        sys.exit(0)

    if args.test:
        print("Latency Test Results:")
        print(f"{'Provider':<15} {'Latency (ms)':<15}")
        print("-" * 30)
        for name, url in PROVIDERS.items():
            lat = measure_latency(url)
            print(f"{name:<15} {lat:<15.0f}")
        sys.exit(0)

    if args.status:
        pid = read_pid()
        try:
            import psutil
            running = False
            if pid and psutil.pid_exists(pid):
                running = True
        except ImportError:
            running = pid is not None

        status = {
            "running": running,
            "primary_provider": config.primary_provider,
            "obfuscation_enabled": config.obfuscation_enabled
        }
        print(json.dumps(status, indent=2))
        sys.exit(0)

    app = SchoolNetApp(config)
    app.check_first_launch()
    app.run()

if __name__ == "__main__":
    main()
