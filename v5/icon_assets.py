"""Choose one release-channel icon for both native platform packages."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil


ICONS = Path(__file__).resolve().parent / "macos/design/icons"


def release_channel(version, override=None):
    channel = override if override is not None else os.environ.get("MINER_RELEASE_CHANNEL")
    if channel is not None:
        if channel not in {"stable", "beta"}:
            raise ValueError("MINER_RELEASE_CHANNEL must be stable or beta")
        return channel
    tag = os.environ.get("GITHUB_REF_NAME", "")
    if os.environ.get("GITHUB_REF_TYPE") == "tag" and re.fullmatch(
        r"miner-[a-z]+-v\d+(?:\.\d+)*", tag
    ):
        return "stable"
    # ALPHA is also a product codename; official builds select stable explicitly.
    # Legacy pre-release versions keep the beta icon until promoted by packaging.
    return "stable" if re.fullmatch(r"\d+(?:\.\d+)*", version) else "beta"


def bundle_icon(destination, version, override=None):
    channel = release_channel(version, override)
    directory = ICONS / channel
    png = directory / "AppIcon.png"
    if not png.is_file():
        raise ValueError(f"Missing {channel} icon; never fall back to the other release channel")
    shutil.copyfile(png, Path(destination) / "AppIcon.png")
    return {"channel": channel, "sha256": hashlib.sha256(png.read_bytes()).hexdigest()}


def install_macos_icon(resources, icon):
    if icon["channel"] == "stable":
        directory = ICONS / "stable"
        for name in ("AppIcon.icns", "Assets.car"):
            if not (directory / name).is_file():
                raise ValueError(f"Missing native official icon resource: {name}")
            shutil.copyfile(directory / name, Path(resources) / name)


def macos_icon_info(icon):
    info = {"MINERReleaseChannel": icon["channel"]}
    if icon["channel"] == "stable":
        native = json.loads((ICONS / "stable/icon-verification.json").read_text())
        # Keep AppIcon.icns as the fallback for Macs predating Icon Composer.
        info["CFBundleIconName"] = native["info"].get("CFBundleIconName", "MINER")
    return info
