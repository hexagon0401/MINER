#!/usr/bin/env python3
"""SchoolNet v5 CLI. Python 3.10+; standard library only."""
import argparse
import http.client
import json
from pathlib import Path
import subprocess
import sys

from schoolnet.config import Profile, build_config
from schoolnet.probe import benchmark
from schoolnet.runtime import doctor, instance_lock, load_profile, run, write_json
from schoolnet import __version__


def main(argv=None):
    parser = argparse.ArgumentParser(description="SchoolNet v5 alpha: Riot TCP via WARP, game direct")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="write a new profile; does not change network settings")
    init.add_argument("--directory", type=Path, required=True)
    init.add_argument("--platform", choices=["macos", "windows"], default="macos")
    init.add_argument("--proxy-port", type=int, default=40000)
    init.add_argument("--physical-interface", default="")
    render = commands.add_parser("render", help="regenerate engine config after editing profile.json")
    render.add_argument("--directory", type=Path, required=True)
    for name in ["doctor", "run"]:
        command = commands.add_parser(name)
        command.add_argument("--directory", type=Path, required=True)
        command.add_argument("--engine", default="sing-box")
        command.add_argument("--warp-cli")
        if name == "run": command.add_argument("--managed-helper", action="store_true")
    probe = commands.add_parser("benchmark", help="compare TCP connection times, not game ping")
    probe.add_argument("--host", required=True)
    probe.add_argument("--port", type=int, default=443)
    probe.add_argument("--samples", type=int, default=5)
    probe.add_argument("--proxy-port", type=int, default=40000)
    probe.add_argument("--timeout", type=float, default=3)
    warp = commands.add_parser("warp", help="configure or inspect the installed WARP Local Proxy")
    warp.add_argument("operation", choices=["connect", "status", "disconnect", "restore", "maintain"])
    warp.add_argument("--progress", action="store_true")
    warp.add_argument("--proxy-port", type=int, default=40000)
    warp.add_argument("--warp-cli")
    desktop = commands.add_parser("desktop", help="macOS app service management")
    desktop.add_argument("operation", choices=["start", "stop", "status", "uninstall", "helper-install", "helper-serve", "helper-start", "helper-stop", "helper-status"])
    desktop.add_argument("--owner", type=int)
    desktop.add_argument("--resources", type=Path)
    desktop.add_argument("--profile", type=Path)
    update = commands.add_parser("update", help="check or verify an official installer download")
    update.add_argument("operation", choices=["check", "download"])
    update.add_argument("--platform", choices=["macos", "windows"], required=True)
    update.add_argument("--arch", choices=["arm64", "x86_64", "x64"], required=True)
    update.add_argument("--directory", type=Path)
    community = commands.add_parser("community-diagnose", help="read-only school report diagnostics; no routing changes")
    community.add_argument("--directory", type=Path, required=True)
    community.add_argument("--engine", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "update":
            from schoolnet import updates
            info = updates.check(args.platform, args.arch)
            if args.operation == "download":
                if args.directory is None: raise ValueError("Download directory required")
                if not info["available"]: raise ValueError("No newer official release is available")
                info = updates.download(info, args.directory)
            print(json.dumps(info)); return 0
        elif args.command == "community-diagnose":
            from community.diagnostics import diagnose, CHECKS
            try:
                result = diagnose(args.directory, args.engine)
            except (OSError, ValueError, TypeError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                result = {"schemaVersion":1,"passed":False,"checks":dict.fromkeys(CHECKS,False),"failureCode":"diagnostic_failed"}
            print(json.dumps(result))
            return 0
        elif args.command == "init":
            profile = Profile(platform=args.platform, proxy_port=args.proxy_port,
                              physical_interface=args.physical_interface).validate()
            args.directory.mkdir(parents=True, exist_ok=True)
            with instance_lock(args.directory):
                if any((args.directory / f).exists() for f in ["profile.json", "sing-box.json"]):
                    raise ValueError("profile already exists; edit profile.json and use render")
                write_json(args.directory / "profile.json", profile.to_dict())
                write_json(args.directory / "sing-box.json", build_config(profile))
            print(f"Created {args.directory.resolve()}; no network settings changed")
        elif args.command == "render":
            with instance_lock(args.directory):
                write_json(args.directory / "sing-box.json", build_config(load_profile(args.directory)))
            print("Rendered sing-box.json; no network settings changed")
        elif args.command == "doctor":
            result = doctor(args.directory, args.engine, args.warp_cli)
            print(json.dumps(result, indent=2))
            return 0 if result["preflight_ok"] else 1
        elif args.command == "run":
            return run(args.directory, args.engine, args.warp_cli, managed_helper=args.managed_helper)
        elif args.command == "benchmark":
            result = benchmark(args.host, args.port, args.samples, args.proxy_port, args.timeout)
            print(json.dumps(result, indent=2))
            return 0 if all(p["successes"] for p in result["paths"].values()) else 1
        elif args.command == "desktop":
            if args.operation.startswith("helper-"):
                from schoolnet import macos_helper as helper
                if sys.platform != "darwin":
                    raise ValueError("Persistent helper is macOS-only")
                operation = args.operation.removeprefix("helper-")
                if operation == "install": result = helper.install(args.resources, args.profile, args.owner)
                elif operation == "serve": return helper.serve(args.owner)
                else:
                    if operation == "start":
                        from schoolnet.warp import progress
                        progress("routing", 4)
                    result = helper.request(operation, load_profile(args.profile) if operation == "start" else None)
                    if operation == "start" and result.get("running"): progress("running", 5)
                print(json.dumps(result)); return 0
            from schoolnet.macos_service import manage
            return manage(args.operation, args.resources, args.profile, args.owner)
        elif args.command == "warp":
            from schoolnet.warp import activate, deactivate, inspect, restore, progress, maintain_proxy
            if args.operation == "connect":
                result = activate(args.proxy_port, args.warp_cli, notify=progress if args.progress else None)
            elif args.operation == "restore":
                result = restore(args.warp_cli)
            elif args.operation == "status":
                result = inspect(args.proxy_port, args.warp_cli)
            elif args.operation == "maintain":
                result = maintain_proxy(args.proxy_port,args.warp_cli)
            else:
                result = deactivate(args.warp_cli)
            print(json.dumps(result, indent=2))
    except subprocess.CalledProcessError as exc:
        # Engine check diagnostics contain config paths, not app auth arguments.
        print(f"Command failed: {exc.stderr or exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, subprocess.TimeoutExpired, http.client.HTTPException) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
