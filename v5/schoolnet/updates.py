"""Explicit, TLS-verified installer downloads from MINER's official release."""
import hashlib
import json
from pathlib import Path
import re
import ssl
import subprocess
import sys
import urllib.request
from urllib.parse import urlparse

from . import __release_version__

REPO = "hexagon0401/MINER"
BASE = f"https://github.com/{REPO}/releases/download/"
MAX_DOWNLOAD = 256 * 1024 * 1024


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r"[1-9]\d*(?:\.\d+)*", value):
        raise ValueError("Unsupported official version")
    parts = [int(n) for n in value.split(".")]
    while len(parts) > 1 and parts[-1] == 0: parts.pop()
    return tuple(parts)


class HTTPSRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, url):
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in {
            "github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com",
            "github-releases.githubusercontent.com",
        }:
            raise ValueError("Unexpected release download redirect")
        return super().redirect_request(request, fp, code, message, headers, url)


def open_url(url, timeout=30):
    import certifi
    context = ssl.create_default_context(cafile=certifi.where())
    opener = urllib.request.build_opener(HTTPSRedirect(), urllib.request.HTTPSHandler(context=context))
    return opener.open(urllib.request.Request(url, headers={"User-Agent": "MINER-updater"}), timeout=timeout)


def get_json(url):
    with open_url(url,timeout=8) as response:
        raw = response.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024: raise ValueError("Release metadata too large")
    return json.loads(raw)


def select(release, manifest, platform, architecture, current=__release_version__):
    if release.get("draft") is not False or release.get("prerelease") is not False:
        raise ValueError("Only official releases can be installed")
    target = str(manifest.get("release_version", ""))
    version(target)
    tag = f"miner-alpha-v{target}"
    if release.get("tag_name") != tag or manifest.get("tag") != tag or manifest.get("prerelease") is not False or manifest.get("codename") != "ALPHA":
        raise ValueError("Release metadata disagrees")
    suffix = {("macos", "arm64"): "macOS-AppleSilicon.dmg", ("macos", "x86_64"): "macOS-Intel.dmg",
              ("windows", "x64"): "Windows-x64-Setup.exe"}.get((platform, architecture))
    if suffix is None: raise ValueError("Unsupported update architecture")
    name = f"MINER-ALPHA-v{target}-{suffix}"
    entries = [p for p in manifest.get("platforms", []) if p.get("filename") == name]
    assets = [a for a in release.get("assets", []) if a.get("name") == name and a.get("state") == "uploaded"]
    if len(entries) != 1 or len(assets) != 1: raise ValueError("Installer is not completely published")
    digest = entries[0].get("sha256", "")
    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest): raise ValueError("Invalid installer checksum")
    expected_arch = architecture
    if entries[0].get("architecture") != expected_arch: raise ValueError("Installer architecture disagrees")
    github_digest = assets[0].get("digest")
    if github_digest and github_digest != "sha256:" + digest: raise ValueError("GitHub checksum disagrees")
    return {"version": target, "current": current, "available": version(target) > version(current),
            "filename": name, "url": BASE + tag + "/" + name, "sha256": digest}


def check(platform, architecture):
    release = get_json(f"https://api.github.com/repos/{REPO}/releases/latest")
    tag = release.get("tag_name", "")
    if not re.fullmatch(r"miner-alpha-v[1-9]\d*(?:\.\d+)*", tag):
        raise ValueError("Latest release uses an unsupported release scheme")
    manifest = get_json(BASE + tag + "/release-manifest.json")
    info = select(release, manifest, platform, architecture)
    brew = homebrew() if platform == "macos" else None
    return {**info, "manager": "homebrew" if brew else "installer", "brew": brew}


def homebrew():
    if sys.platform != "darwin": return None
    for path in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew"):
        if Path(path).is_file():
            try:
                result = subprocess.run([path, "list", "--cask", "--versions", "miner"], capture_output=True, text=True, timeout=15)
                if result.returncode == 0 and result.stdout.strip(): return path
            except (OSError, subprocess.TimeoutExpired): pass
    return None


def download(info, directory):
    name = info["filename"]
    if Path(name).name != name or not re.fullmatch(r"MINER-ALPHA-v[1-9]\d*(?:\.\d+)*-(?:macOS-(?:AppleSilicon|Intel)\.dmg|Windows-x64-Setup\.exe)", name):
        raise ValueError("Unsafe update filename")
    if not info["url"].startswith(BASE) or not re.fullmatch(r"[a-f0-9]{64}", info["sha256"]):
        raise ValueError("Unsafe download metadata")
    directory = Path(directory)
    if directory.is_symlink(): raise ValueError("Update directory must not be a symlink")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    target = directory / name
    temporary = directory / (name + ".download")
    if target.is_symlink() or temporary.is_symlink(): raise ValueError("Update file must not be a symlink")
    digest = hashlib.sha256()
    try:
        with open_url(info["url"]) as response, temporary.open("wb") as output:
            size = 0
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk: break
                size += len(chunk)
                if size > MAX_DOWNLOAD: raise ValueError("Installer exceeds download limit")
                digest.update(chunk); output.write(chunk)
        if digest.hexdigest() != info["sha256"]: raise ValueError("Installer checksum verification failed")
        temporary.replace(target)
        return {**info, "path": str(target.resolve()), "verified": True}
    finally:
        temporary.unlink(missing_ok=True)
