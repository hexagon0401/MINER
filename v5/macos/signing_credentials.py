#!/usr/bin/env python3
"""Import CI signing credentials into a temporary keychain, never into Git."""
import argparse
import base64
import os
from pathlib import Path
import re
import secrets
import shlex
import shutil
import subprocess
import tempfile

VARIABLES = ("APPLE_CERTIFICATE_P12_BASE64", "APPLE_CERTIFICATE_PASSWORD", "APPLE_TEAM_ID")


def output(name, value):
    if "\n" in value or "\r" in value:
        raise ValueError("invalid action output")
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
        stream.write(f"{name}={value}\n")


def security(*arguments):
    try:
        return subprocess.run(["security", *arguments], check=True, capture_output=True, text=True).stdout
    except subprocess.CalledProcessError:
        # CalledProcessError string includes argv (possibly passwords).
        raise ValueError("macOS security command failed; check certificate type, private key, and password") from None


def prepare():
    present = [bool(os.environ.get(name)) for name in VARIABLES]
    if not any(present):
        if os.environ.get("NOTARY_CONFIGURED") == "true":
            raise ValueError("notary credentials are configured but Developer ID certificate secrets are missing")
        output("enabled", "false")
        print("No Developer ID credentials configured; build remains explicitly ad-hoc.")
        return
    if not all(present):
        raise ValueError("incomplete signing configuration: " + ", ".join(n for n in VARIABLES if not os.environ.get(n)))
    root = Path(tempfile.mkdtemp(prefix="schoolnet-signing-", dir=os.environ["RUNNER_TEMP"]))
    keychain = root / "signing.keychain-db"
    p12 = root / "certificate.p12"
    password = secrets.token_urlsafe(32)
    try:
        p12.write_bytes(base64.b64decode("".join(os.environ[VARIABLES[0]].split()), validate=True))
        p12.chmod(0o600)
        old = shlex.split(security("list-keychains", "-d", "user"))
        security("create-keychain", "-p", password, str(keychain))
        security("set-keychain-settings", "-lut", "21600", str(keychain))
        security("unlock-keychain", "-p", password, str(keychain))
        security("import", str(p12), "-k", str(keychain), "-P", os.environ[VARIABLES[1]],
                 "-T", "/usr/bin/codesign", "-T", "/usr/bin/security")
        security("set-key-partition-list", "-S", "apple-tool:,apple:,codesign:", "-s", "-k", password, str(keychain))
        security("list-keychains", "-d", "user", "-s", str(keychain), *old)
        identities = security("find-identity", "-v", "-p", "codesigning", str(keychain))
        matches = [(digest, name) for digest, name in re.findall(r'\b([A-Fa-f0-9]{40})\s+"([^"]+)"', identities)
                   if name.startswith("Developer ID Application:") and name.endswith(f"({os.environ[VARIABLES[2]]})")]
        if len(matches) != 1:
            raise ValueError("expected one valid Developer ID Application identity for APPLE_TEAM_ID")
        output("identity", matches[0][0])
        output("keychain", str(keychain))
        output("enabled", "true")
        print("Developer ID identity imported into an ephemeral CI keychain.")
    except Exception:
        if keychain.exists():
            security("delete-keychain", str(keychain))
        shutil.rmtree(root)
        raise
    finally:
        p12.unlink(missing_ok=True)


def cleanup(value):
    keychain = Path(value).resolve()
    root = Path(os.environ["RUNNER_TEMP"]).resolve()
    if not keychain.is_relative_to(root) or not keychain.parent.name.startswith("schoolnet-signing-") or keychain.name != "signing.keychain-db":
        raise ValueError("refusing cleanup outside the temporary SchoolNet keychain")
    if keychain.exists():
        security("delete-keychain", str(keychain))
    shutil.rmtree(keychain.parent, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cleanup")
    args = parser.parse_args()
    try:
        cleanup(args.cleanup) if args.cleanup else prepare()
    except (OSError, ValueError):
        parser.exit(1, "Signing credential setup failed; check configured secret names and certificate validity.\n")
