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
from macos.signing import developer_identity, notarize, sign_app, validate_notary_credentials


def execute(*args):
    subprocess.run([str(a) for a in args], check=True, cwd=ROOT)


def validate_resource_paths(app):
    # HFS+/APFS/Finder can normalize Unicode filenames differently. Keep bundle
    # resource names ASCII so a signed filename cannot change during installation.
    for path in app.rglob("*"):
        if not str(path.relative_to(app)).isascii():
            raise ValueError(f"non-ASCII bundle path would risk resource sealing: {path}")


def build(expected_arch, signing="adhoc", identity=None, notary_profile=None):
    if platform.system() != "Darwin":
        raise ValueError("DMG builds require macOS (GitHub Actions workflow is provided)")
    arch = platform.machine()
    if arch != expected_arch:
        raise ValueError(f"runner architecture is {arch}, expected {expected_arch}")
    import certifi
    signed = signing == "developer-id"
    if signed:
        import os
        identity = developer_identity(identity or os.environ.get("CODE_SIGN_IDENTITY"))
        validate_notary_credentials(notary_profile)
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
    packager = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir",
            "--name", "schoolnet-cli", "--distpath", resources / "runtime",
            "--workpath", work / "pyinstaller", "--specpath", work,
            "--add-data", f"{certifi.where()}:."]
    if signed:
        packager += ["--codesign-identity", identity]
    execute(*packager, ROOT / "main.py")
    execute("xcrun", "swiftc", "-swift-version", "5", "-parse-as-library", "-O", "-framework", "AppKit", "-framework", "SwiftUI",
            "-target", f"{arch}-apple-macosx13.0", ROOT / "macos" / "App.swift",
            ROOT / "macos" / "MinerUI.swift", "-o", contents / "MacOS" / "SchoolNet")
    ui_assets = resources / "UIAssets"
    ui_assets.mkdir()
    for source in (ROOT / "macos/design/assets").iterdir():
        if source.suffix in {".png", ".json"} and source.name not in {"app-icon-ministry.png", "app-icon-ministry-sejong.png", "storyboard-reference.png"}:
            shutil.copy2(source, ui_assets / source.name)
    iconset = work / "AppIcon.iconset"
    iconset.mkdir()
    for size in [16,32,128,256,512]:
        for scale in [1,2]:
            suffix = "@2x" if scale == 2 else ""
            execute("sips", "-z", size*scale, size*scale, ui_assets / "AppIcon.png", "--out", iconset / f"icon_{size}x{size}{suffix}.png")
    execute("iconutil", "-c", "icns", iconset, "-o", resources / "AppIcon.icns")
    info = {
        "CFBundleName": "MINER", "CFBundleDisplayName": "MINER", "CFBundleIconFile": "AppIcon",
        "CFBundleIdentifier": "org.schoolnet.v5.alpha", "CFBundleExecutable": "SchoolNet",
        "CFBundlePackageType": "APPL", "CFBundleShortVersionString": "5.0.0",
        "CFBundleVersion": f"500{int(__version__.rsplit('.', 1)[1]):03d}", "SchoolNetReleaseVersion": __version__,
        "LSMinimumSystemVersion": "13.0", "NSHighResolutionCapable": True,
    }
    (contents / "Info.plist").write_bytes(plistlib.dumps(info))
    guide = (ROOT / "macos" / "사용 안내.txt").read_text(encoding="utf-8")
    if signed:
        before, section = guide.split("배포 서명\n", 1)
        _, after = section.split("설치 위치\n", 1)
        guide = before + "배포 서명\n이 배포는 Developer ID 서명과 Apple 공증·티켓 검증을 통과해야 게시됩니다.\n보안 경고가 계속되면 서명·공증 검사 결과를 확인하세요.\n\n설치 위치\n" + after
    (resources / "UserGuide.txt").write_text(guide, encoding="utf-8")
    (stage / "Read Me.txt").write_text(guide, encoding="utf-8")
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
    with (notices / "SOURCE.txt").open("a", encoding="utf-8") as stream:
        stream.write("certifi 2026.10.23 / Mozilla CA bundle (MPL-2.0): https://github.com/certifi/python-certifi\n")
    build_info = {"version": __version__, "architecture": arch, "build_os": platform.mac_ver()[0],
                  "python": platform.python_version(), "signed": "developer-id" if signed else "ad-hoc",
                  "notarization_required": signed}
    (resources / "build-info.json").write_text(json.dumps(build_info, indent=2), encoding="utf-8")
    validate_resource_paths(app)
    if signed:
        sign_app(app, identity, execute)
    else:
        # Ad-hoc is explicit; configured Developer ID failures never fall back.
        execute("codesign", "--force", "--deep", "--sign", "-", app)
    execute("codesign", "--verify", "--deep", "--strict", app)
    cli = resources / "runtime" / "schoolnet-cli" / "schoolnet-cli"
    execute(cli, "--version")
    execute(cli, "--help")
    execute(cli, "desktop", "status")
    smoke = work / "schema-smoke"
    execute(cli, "init", "--directory", smoke, "--platform", "macos")
    execute(engine, "check", "-c", smoke / "sing-box.json")
    app_receipt = None
    if signed:
        archive = work / "notary-app.zip"
        execute("ditto", "-c", "-k", "--keepParent", app, archive)
        app_receipt = notarize(archive, work / "app-notarization.json", execute, notary_profile)
        # ZIP submissions cannot be stapled; staple the submitted app itself.
        execute("xcrun", "stapler", "staple", app)
        execute("xcrun", "stapler", "validate", app)
        execute("spctl", "--assess", "--type", "execute", "--verbose=2", app)
    (stage / "Applications").symlink_to("/Applications")
    output = ROOT / "dist"
    output.mkdir(exist_ok=True)
    name = f"SchoolNet-v{__version__}-macOS-{'AppleSilicon' if arch == 'arm64' else 'Intel'}.dmg"
    dmg = output / name
    if dmg.exists():
        raise ValueError(f"output already exists: {dmg}")
    execute("hdiutil", "create", "-volname", "SchoolNet v5 Alpha", "-srcfolder", stage,
            "-format", "UDZO", dmg)
    dmg_receipt = None
    if signed:
        execute("codesign", "--force", "--timestamp", "--sign", identity, dmg)
        dmg_receipt = notarize(dmg, work / "dmg-notarization.json", execute, notary_profile)
        execute("spctl", "--assess", "--type", "open", "--context", "context:primary-signature", "--verbose=2", dmg)
    execute("hdiutil", "verify", dmg)
    with tempfile.TemporaryDirectory(prefix="schoolnet-dmg-") as mount:
        execute("hdiutil", "attach", "-readonly", "-nobrowse", "-mountpoint", mount, dmg)
        try:
            mounted = Path(mount) / "SchoolNet v5 Alpha.app"
            execute("codesign", "--verify", "--deep", "--strict", mounted)
            execute(mounted / "Contents/Resources/runtime/schoolnet-cli/schoolnet-cli", "--version")
            # Verify the installed copy as well as the read-only volume. This
            # exercises the DMG -> filesystem boundary that broke the old guide.
            with tempfile.TemporaryDirectory(prefix="schoolnet-install-smoke-") as install_dir:
                installed = Path(install_dir) / "SchoolNet v5 Alpha.app"
                execute("ditto", mounted, installed)
                validate_resource_paths(installed)
                execute("codesign", "--verify", "--deep", "--strict", installed)
                execute(installed / "Contents/Resources/runtime/schoolnet-cli/schoolnet-cli", "--version")
                if signed:
                    execute("xcrun", "stapler", "validate", installed)
                    execute("spctl", "--assess", "--type", "execute", "--verbose=2", installed)
            if not (Path(mount) / "Applications").is_symlink():
                raise ValueError("DMG Applications shortcut is missing")
        finally:
            execute("hdiutil", "detach", mount)
    digest = hashlib.sha256(dmg.read_bytes()).hexdigest()
    dmg.with_suffix(".dmg.sha256").write_text(f"{digest}  {name}\n", encoding="utf-8")
    dmg.with_suffix(".dmg.verification.json").write_text(json.dumps({
        "version": __version__, "architecture": arch, "signing": signing,
        "app_notarization": app_receipt, "dmg_notarization": dmg_receipt,
        "dmg_to_disk_signature_verified": True, "sha256": digest,
    }, indent=2), encoding="utf-8")
    print(f"Verified DMG: {dmg}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", required=True, choices=["arm64", "x86_64"])
    parser.add_argument("--signing", choices=["adhoc", "developer-id"], default="adhoc")
    parser.add_argument("--identity", help="local Developer ID certificate name or fingerprint")
    parser.add_argument("--notary-profile", help="local notarytool keychain profile")
    args = parser.parse_args()
    build(args.arch, args.signing, args.identity, args.notary_profile)
