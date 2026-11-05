"""Apply icon/packaging changes to the exact ALPHA v1 platform baselines."""
import argparse
from pathlib import Path
import re
import shutil
import subprocess


ROOT = Path(__file__).resolve().parents[2]
BASELINES = {
    "macos": "7999c5ba0c99fe9b3d7b605b839f5cfaad092387",
    "windows": "e94f5b99dc782cbd2acee1b29e3d5b29e35f431b",
}
RELEASE = "1.0.1"


def replace(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f"Pinned packaging baseline changed: {old!r}")
    return text.replace(old, new, 1)


def prepare(source, platform):
    sha = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if sha != BASELINES[platform]:
        raise ValueError("Release source must match the verified ALPHA v1 baseline")
    base = source / "v5"
    shutil.copyfile(ROOT / "v5/icon_assets.py", base / "icon_assets.py")
    shutil.copytree(ROOT / "v5/macos/design/icons", base / "macos/design/icons", dirs_exist_ok=True)
    build_path = base / platform / "build.py"
    text = build_path.read_text()
    if platform == "macos":
        text = replace(text, "from schoolnet import __version__", "from schoolnet import __version__\nfrom icon_assets import bundle_icon, install_macos_icon, macos_icon_info")
        text = replace(text, '    iconset = work / "AppIcon.iconset"', '    icon = bundle_icon(ui_assets, __version__)\n    iconset = work / "AppIcon.iconset"')
        marker = '    execute("iconutil", "-c", "icns", iconset, "-o", resources / "AppIcon.icns")'
        text = replace(text, marker, marker + '\n    install_macos_icon(resources, icon)')
        marker = '    (contents / "Info.plist").write_bytes(plistlib.dumps(info))'
        text = replace(text, marker, '    info.update(macos_icon_info(icon))\n' + marker)
        text = replace(text, '"CFBundleVersion": "502101"', '"CFBundleVersion": "502102"')
        text = replace(text, '"notarization_required": signed, "developer": developer}', '"notarization_required": signed, "developer": developer, "app_icon": icon}')
        text = replace(text, '"developer": developer, "app_icon_sha256":', '"developer": developer, "release_channel": icon["channel"], "app_icon_sha256":')
        version = base / "schoolnet/__init__.py"
        version.write_text(replace(version.read_text(), '"5.0.0-beta.1.1"', '"5.0.0-alpha.1.0.1"'))
        layout = base / "macos/dmg_layout.py"
        layout.write_text(replace(layout.read_text(), '"MINER BETA"', '"MINER ALPHA"'))
    else:
        marker = "from windows.version import VERSION, FILE_VERSION, LABEL, TAG, STEM"
        text = replace(text, marker, marker + "\nfrom icon_assets import bundle_icon")
        marker = "    with Image.open(art/'AppIcon.png') as icon:"
        text = replace(text, marker, "    app_icon=bundle_icon(art,VERSION)\n" + marker)
        text = replace(text, "'authenticode_signed':False,", "'authenticode_signed':False,'app_icon_sha256':app_icon['sha256'],'release_channel':app_icon['channel'],")
        (base / "windows/version.py").write_text(
            "VERSION = '5.0.0-alpha.1.0.1-windows.9'\n"
            "FILE_VERSION = '5.0.0.9'\n"
            "LABEL = 'MINER ALPHA v1.0.1 · Windows'\n"
            "TAG = 'miner-alpha-v1.0.1'\n"
            "STEM = 'MINER-ALPHA-v1.0.1-Windows-x64'\n"
        )
    build_path.write_text(text)
    print(f"Prepared {platform} ALPHA v{RELEASE} from {sha}; only icons and packaging metadata changed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("platform", choices=BASELINES)
    args = parser.parse_args()
    prepare(args.source.resolve(), args.platform)
