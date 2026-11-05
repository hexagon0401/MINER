"""Compile the supplied Icon Composer document using Apple's native compiler."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import subprocess


def compile_icon(source, output):
    output.mkdir(parents=True, exist_ok=True)
    info = output / "icon-info.plist"
    subprocess.run([
        "xcrun", "actool", "--compile", str(output), "--platform", "macosx",
        "--minimum-deployment-target", "13.0", "--app-icon", source.stem,
        "--output-partial-info-plist", str(info), str(source),
    ], check=True)
    icons = list(output.glob("*.icns"))
    if len(icons) != 1:
        raise ValueError("Native compiler must emit one backwards-compatible ICNS")
    iconset = output / "Export.iconset"
    subprocess.run(["iconutil", "-c", "iconset", str(icons[0]), "-o", str(iconset)], check=True)
    png = iconset / "icon_512x512@2x.png"
    if not png.exists():
        raise ValueError("Native icon must include a 1024px PNG for Windows and older Macs")
    shutil.copyfile(png, output / "AppIcon.png")
    if icons[0].name != "AppIcon.icns":
        shutil.copyfile(icons[0], output / "AppIcon.icns")
    metadata = plistlib.loads(info.read_bytes())
    receipt = {
        "source": "MINER.icon",
        "compiler": "Apple actool + iconutil",
        "channel": "stable",
        "info": metadata,
        "sha256": hashlib.sha256(png.read_bytes()).hexdigest(),
    }
    (output / "icon-verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    compile_icon(args.source.resolve(), args.output.resolve())
