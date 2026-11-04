#!/usr/bin/env python3
"""Install the pinned official engine with SHA-256 verification, no root required.

Digests: GitHub's official v1.12.0 release asset metadata, checked 2026-11-04.
No TLS bypass, extraction of arbitrary archive paths, or execution of installers.
"""
import argparse
import hashlib
import io
import os
from pathlib import Path
import platform
import tarfile
import urllib.request
import zipfile

VERSION = "1.12.0"
DIGESTS = {
    "darwin-amd64": "053c387baca43acd690065cb86bdb95df5a23a51580a7d5623a9e5fa662b1fe6",
    "darwin-arm64": "212915dd5be0ea1818203f7f5a2db8e16d15229f2a2f2a28a093c34cdce9fdfa",
    "linux-amd64": "f59b1253ae0143997cb46915af30d14a33431dcbd7e39edacfcde8d73050faaf",
    "linux-arm64": "90e8b40320971db689b789ab95f54e9762bc24250f29ba59012049ab7867f456",
    "windows-amd64": "49a5b90b390974a87b4660308446dfd9630f60ac655f76383abbd5f0994b09b3",
    "windows-arm64": "b41c7322e2f3fb0e2ad2ff60db577fcf28dd05a58f7f33456ec1be4ae0540693",
}


def target_key():
    system = platform.system().lower()
    machine = {"x86_64": "amd64", "amd64": "amd64", "aarch64": "arm64", "arm64": "arm64"}.get(platform.machine().lower())
    key = f"{system}-{machine}"
    if key not in DIGESTS:
        raise ValueError(f"unsupported engine platform: {key}")
    return key


def unpack_verified(data, key):
    if hashlib.sha256(data).hexdigest() != DIGESTS[key]:
        raise ValueError("official engine archive SHA-256 mismatch; refusing installation")
    stem = f"sing-box-{VERSION}-{key}"
    name = "sing-box.exe" if key.startswith("windows-") else "sing-box"
    member = f"{stem}/{name}"
    if key.startswith("windows-"):
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            binary = archive.read(member)
    else:
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            entry = archive.getmember(member)
            if not entry.isfile():
                raise ValueError("engine archive member is not a regular file")
            binary = archive.extractfile(entry).read()
    return name, binary


def install(directory, key=None):
    key = key or target_key()
    extension = "zip" if key.startswith("windows-") else "tar.gz"
    url = f"https://github.com/SagerNet/sing-box/releases/download/v{VERSION}/sing-box-{VERSION}-{key}.{extension}"
    with urllib.request.urlopen(url, timeout=60) as response:
        data = response.read(80 * 1024 * 1024 + 1)
    if len(data) > 80 * 1024 * 1024:
        raise ValueError("engine download exceeds size limit")
    name, binary = unpack_verified(data, key)
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / name
    if destination.exists():
        if destination.read_bytes() == binary:
            print(f"Already installed and verified: {destination}")
            return destination
        raise ValueError(f"refusing to replace different existing binary: {destination}")
    # Exclusive creation preserves any existing user file, including on reruns.
    with destination.open("xb") as output:
        output.write(binary)
    if os.name != "nt":
        destination.chmod(0o755)
    print(f"Installed verified sing-box {VERSION}: {destination}")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=Path(__file__).parent / "local" / "bin")
    args = parser.parse_args()
    try:
        install(args.directory)
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile, KeyError) as exc:
        parser.exit(1, f"Error: {exc}\n")
