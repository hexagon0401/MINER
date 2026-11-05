"""Verify the latest official ALPHA release before updating the public cask."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile


REPOSITORY = "hexagon0401/MINER"
ROOT = Path(__file__).resolve().parents[2]
VERSION = r"[1-9][0-9]*(?:\.(?:0|[1-9][0-9]*))*"
ARCHITECTURES = {"arm64": "AppleSilicon", "x86_64": "Intel"}


def version_key(version):
    if not isinstance(version, str) or not re.fullmatch(VERSION, version):
        raise ValueError("Unsupported ALPHA release version")
    parts = [int(part) for part in version.split(".")]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def current_values(text):
    version = re.findall(r'^  version "([^"]+)"$', text, re.MULTILINE)
    hashes = re.search(
        r'  sha256 arm:   "([a-f0-9]{64})",\n         intel: "([a-f0-9]{64})"', text
    )
    expected_url = (
        '  url "https://github.com/hexagon0401/MINER/releases/download/'
        'miner-alpha-v#{version}/MINER-ALPHA-v#{version}-macOS-#{arch}.dmg",'
    )
    if len(version) != 1 or not hashes or expected_url not in text:
        raise ValueError("Cask format changed; review the updater before publishing")
    version_key(version[0])
    return version[0], dict(zip(ARCHITECTURES, hashes.groups()))


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def update(release, download, cask_path, receipt_path):
    """Download returns a local Path for an exact asset name; no shell is used."""
    if release.get("draft") is not False or release.get("prerelease") is not False:
        return "Skipped draft or prerelease"
    tag = release.get("tag_name", "")
    match = re.fullmatch(r"miner-alpha-v(" + VERSION + r")", tag)
    if not match:
        return "Skipped release outside the supported ALPHA version scheme"
    version = match[1]
    original = cask_path.read_text()
    previous, previous_hashes = current_values(original)
    if version_key(version) < version_key(previous):
        return "Skipped older release; cask was not downgraded"
    if version_key(version) == version_key(previous) and version != previous:
        raise ValueError("Equivalent version spelling changed; use a new release version")

    names = {
        architecture: f"MINER-ALPHA-v{version}-macOS-{suffix}.dmg"
        for architecture, suffix in ARCHITECTURES.items()
    }
    required = ["release-manifest.json", *names.values()]
    assets = {}
    for name in required:
        found = [asset for asset in release.get("assets", []) if asset.get("name") == name]
        if len(found) != 1 or found[0].get("state") != "uploaded":
            raise ValueError(f"Release requires one completely uploaded asset: {name}")
        assets[name] = found[0]
    release_id = release.get("id")
    if not isinstance(release_id, int) or any(
        not isinstance(asset.get("id"), int) for asset in assets.values()
    ):
        raise ValueError("Missing GitHub release/asset identity")
    identities = {name: asset["id"] for name, asset in assets.items()}

    # Immutable assets already verified by this updater need not be downloaded on
    # every scheduled run. Replacing an asset changes its ID and forces rechecking.
    if receipt_path.exists() and version == previous:
        receipt = json.loads(receipt_path.read_text())
        if (
            receipt.get("release_id") == release_id
            and receipt.get("tag") == tag
            and receipt.get("asset_ids") == identities
            and receipt.get("sha256") == previous_hashes
            and receipt.get("downloads_verified") is True
        ):
            return "Already verified and current"

    manifest = json.loads(download("release-manifest.json").read_text())
    if (
        manifest.get("tag") != tag
        or manifest.get("codename") != "ALPHA"
        or str(manifest.get("release_version")) != version
        or manifest.get("prerelease") is not False
    ):
        raise ValueError("Manifest does not identify this official ALPHA release")

    hashes = {}
    for architecture, filename in names.items():
        entries = [
            item for item in manifest.get("platforms", [])
            if item.get("filename") == filename
        ]
        if len(entries) != 1 or entries[0].get("architecture") != architecture:
            raise ValueError(f"Missing or ambiguous manifest platform: {architecture}")
        expected = entries[0].get("sha256", "")
        if not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
            raise ValueError(f"Invalid SHA-256 for {filename}")
        actual = sha256(download(filename))
        if actual != expected:
            raise ValueError(f"Downloaded DMG checksum mismatch: {filename}")
        github_digest = assets[filename].get("digest")
        if github_digest and github_digest != f"sha256:{actual}":
            raise ValueError(f"GitHub asset checksum mismatch: {filename}")
        hashes[architecture] = actual

    if version == previous and hashes != previous_hashes:
        raise ValueError("Published version payload changed; publish a new version instead")

    updated = original.replace(f'  version "{previous}"', f'  version "{version}"', 1)
    for architecture in ARCHITECTURES:
        updated = updated.replace(previous_hashes[architecture], hashes[architecture], 1)
    # All metadata and both DMGs must pass before either tracked file is changed.
    receipt = {
        "repository": REPOSITORY,
        "release_id": release_id,
        "tag": tag,
        "version": version,
        "asset_ids": identities,
        "sha256": hashes,
        "downloads_verified": True,
    }
    cask_path.write_text(updated)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    return f"Verified ALPHA v{version}; cask and download receipt are current"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cask", type=Path, default=ROOT / "Casks/miner.rb")
    parser.add_argument(
        "--receipt", type=Path,
        default=Path(__file__).parent / "latest.verification.json",
    )
    args = parser.parse_args()
    # releases/latest is GitHub's official latest non-prerelease, not the newest
    # tag by publication date. Never select an event payload or a user-supplied URL.
    release = json.loads(subprocess.check_output(
        ["gh", "api", f"repos/{REPOSITORY}/releases/latest"], text=True, timeout=60
    ))
    with tempfile.TemporaryDirectory(prefix="miner-homebrew-") as temporary:
        directory = Path(temporary)

        def download(filename):
            subprocess.run(
                ["gh", "release", "download", release["tag_name"], "--repo", REPOSITORY,
                 "--pattern", filename, "--dir", str(directory)],
                check=True, timeout=600,
            )
            return directory / filename

        print(update(release, download, args.cask, args.receipt))


if __name__ == "__main__":
    main()
