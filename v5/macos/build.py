#!/usr/bin/env python3
"""Build a native-architecture app and verified DMG on macOS only."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import plistlib
import shutil
import subprocess
import sys
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from install_engine import install
from schoolnet import __version__


def execute(*args):
    subprocess.run([str(a) for a in args], check=True, cwd=ROOT)


def build(expected_arch):
    if platform.system() != "Darwin":
        raise ValueError("DMG builds require macOS (GitHub Actions workflow is provided)")
    arch = platform.machine()
    if arch != expected_arch:
        raise ValueError(f"runner architecture is {arch}, expected {expected_arch}")
    work = ROOT / "build" / f"macos-{arch}"
    if work.exists():
        raise ValueError(f"build directory already exists; preserve or remove it explicitly: {work}")
    work.mkdir(parents=True)
    stage = work / "dmg-root"
    app = stage / "SchoolNet v5 Alpha.app"
    contents = app / "Contents"
    resources = contents / "Resources"
    (contents / "MacOS").mkdir(parents=True)
    resources.mkdir()
    engine = install(resources / "bin")
    execute(sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
            "--name", "schoolnet-cli", "--distpath", resources / "runtime",
            "--workpath", work / "pyinstaller", "--specpath", work, ROOT / "main.py")
    execute("xcrun", "swiftc", "-swift-version", "5", "-O", "-framework", "AppKit",
            "-target", f"{arch}-apple-macosx13.0", ROOT / "macos" / "App.swift",
            "-o", contents / "MacOS" / "SchoolNet")
    info = {
        "CFBundleName": "SchoolNet v5 Alpha", "CFBundleDisplayName": "SchoolNet v5 Alpha",
        "CFBundleIdentifier": "org.schoolnet.v5.alpha", "CFBundleExecutable": "SchoolNet",
        "CFBundlePackageType": "APPL", "CFBundleShortVersionString": "5.0.0",
        "CFBundleVersion": f"500{int(__version__.rsplit('.', 1)[1]):03d}", "SchoolNetReleaseVersion": __version__,
        "LSMinimumSystemVersion": "13.0", "NSHighResolutionCapable": True,
    }
    (contents / "Info.plist").write_bytes(plistlib.dumps(info))
    guide = (ROOT / "macos" / "사용 안내.txt").read_text(encoding="utf-8")
    (resources / "사용 안내.txt").write_text(guide, encoding="utf-8")
    (stage / "사용 안내.txt").write_text(guide, encoding="utf-8")
    shutil.copytree(ROOT / "docs", resources / "docs")
    notices = resources / "Licenses"
    notices.mkdir()
    with urllib.request.urlopen("https://raw.githubusercontent.com/SagerNet/sing-box/v1.12.0/LICENSE", timeout=30) as response:
        (notices / "sing-box-LICENSE.txt").write_bytes(response.read())
    (notices / "SOURCE.txt").write_text(
        "sing-box 1.12.0 (GPL-3.0), corresponding upstream source and build metadata:\n"
        "https://github.com/SagerNet/sing-box/tree/v1.12.0\n"
        "https://github.com/SagerNet/sing-box/archive/refs/tags/v1.12.0.tar.gz\n"
        "Python: https://docs.python.org/3/license.html\n"
        "PyInstaller bootloader exception: https://pyinstaller.org/en/stable/license.html\n", encoding="utf-8")
    build_info = {"version": __version__, "architecture": arch, "build_os": platform.mac_ver()[0],
                  "python": platform.python_version(), "signed": "ad-hoc", "notarized": False}
    (resources / "build-info.json").write_text(json.dumps(build_info, indent=2), encoding="utf-8")
    # Ad-hoc signing provides bundle integrity only; no Developer ID/notarization claim.
    execute("codesign", "--force", "--deep", "--sign", "-", app)
    execute("codesign", "--verify", "--deep", "--strict", app)
    cli = resources / "runtime" / "schoolnet-cli" / "schoolnet-cli"
    execute(cli, "--version")
    execute(cli, "--help")
    execute(cli, "desktop", "status")
    smoke = work / "schema-smoke"
    execute(cli, "init", "--directory", smoke, "--platform", "macos")
    execute(engine, "check", "-c", smoke / "sing-box.json")
    (stage / "Applications").symlink_to("/Applications")
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    name = f"SchoolNet-v{__version__}-macOS-{'AppleSilicon' if arch == 'arm64' else 'Intel'}.dmg"
    dmg = output / name
    if dmg.exists():
        raise ValueError(f"output already exists: {dmg}")
    execute("hdiutil", "create", "-volname", "SchoolNet v5 Alpha", "-srcfolder", stage,
            "-format", "UDZO", dmg)
    execute("hdiutil", "verify", dmg)
    with tempfile.TemporaryDirectory(prefix="schoolnet-dmg-") as mount:
        execute("hdiutil", "attach", "-readonly", "-nobrowse", "-mountpoint", mount, dmg)
        try:
            mounted = Path(mount) / "SchoolNet v5 Alpha.app"
            execute("codesign", "--verify", "--deep", "--strict", mounted)
            execute(mounted / "Contents/Resources/runtime/schoolnet-cli/schoolnet-cli", "--version")
            if not (Path(mount) / "Applications").is_symlink():
                raise ValueError("DMG Applications shortcut is missing")
        finally:
            execute("hdiutil", "detach", mount)
    digest = hashlib.sha256(dmg.read_bytes()).hexdigest()
    dmg.with_suffix(".dmg.sha256").write_text(f"{digest}  {name}\n", encoding="utf-8")
    print(f"Verified DMG: {dmg}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", required=True, choices=["arm64", "x86_64"])
    args = parser.parse_args()
    build(args.arch)
