"""Developer ID signing and Apple notarization; never bypass verification."""
import base64
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

NOTARY_VARIABLES = ("APPLE_NOTARY_KEY_P8_BASE64", "APPLE_NOTARY_KEY_ID", "APPLE_NOTARY_ISSUER_ID")
MACHO_MAGIC = {bytes.fromhex(h) for h in ("feedface", "cefaedfe", "feedfacf", "cffaedfe", "cafebabe", "bebafeca", "cafebabf", "bfbafeca")}


def developer_identity(identity):
    if not identity:
        raise ValueError("Developer ID signing needs --identity or CODE_SIGN_IDENTITY")
    result = subprocess.run(["security", "find-identity", "-v", "-p", "codesigning"],
                            check=True, capture_output=True, text=True)
    for digest, name in re.findall(r'\b([A-Fa-f0-9]{40})\s+"([^"]+)"', result.stdout):
        if identity in (digest, name) and name.startswith("Developer ID Application:"):
            return digest
    raise ValueError("selected valid Developer ID Application certificate/private key was not found")


def validate_notary_credentials(profile=None):
    if not profile:
        missing = [name for name in NOTARY_VARIABLES if not os.environ.get(name)]
        if missing:
            raise ValueError("missing notarization configuration: " + ", ".join(missing))


def macho_paths(app):
    found = set()
    for path in Path(app).rglob("*"):
        if path.is_file() and not path.is_symlink():
            with path.open("rb") as stream:
                if stream.read(4) in MACHO_MAGIC:
                    found.add(path.resolve())
    return sorted(found, key=lambda p: (-len(p.parts), str(p)))


def sign_app(app, identity, execute):
    # Sign each nested executable/library first. --deep is for verification,
    # not a replacement for inside-out Developer ID signing.
    for binary in macho_paths(app):
        execute("codesign", "--force", "--all-architectures", "--options", "runtime",
                "--timestamp", "--sign", identity, binary)
    frameworks = {p.resolve() for p in Path(app).rglob("*.framework") if p.is_dir() and not p.is_symlink()}
    for framework in sorted(frameworks, key=lambda p: (-len(p.parts), str(p))):
        execute("codesign", "--force", "--options", "runtime", "--timestamp", "--sign", identity, framework)
    execute("codesign", "--force", "--options", "runtime", "--timestamp", "--sign", identity, app)
    execute("codesign", "--verify", "--deep", "--strict", app)


@contextmanager
def notary_arguments(profile=None):
    validate_notary_credentials(profile)
    if profile:
        yield ["--keychain-profile", profile]
        return
    # Key contents are never command arguments, logs, artifacts, or saved config.
    with tempfile.TemporaryDirectory(prefix="schoolnet-notary-") as directory:
        key = Path(directory) / "AuthKey.p8"
        data = base64.b64decode("".join(os.environ[NOTARY_VARIABLES[0]].split()), validate=True)
        with key.open("xb") as stream:
            stream.write(data)
        key.chmod(0o600)
        yield ["--key", str(key), "--key-id", os.environ[NOTARY_VARIABLES[1]],
               "--issuer", os.environ[NOTARY_VARIABLES[2]]]


def notarize(path, receipt, execute, profile=None):
    with notary_arguments(profile) as auth:
        command = ["xcrun", "notarytool", "submit", str(path), *auth,
                   "--wait", "--timeout", "20m", "--output-format", "json"]
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=1250)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            raise RuntimeError("Apple notarization failed or timed out; refusing distribution") from None
        report = json.loads(result.stdout)
        Path(receipt).write_text(json.dumps(report, indent=2), encoding="utf-8")
        if report.get("status") != "Accepted":
            raise RuntimeError(f"Apple notarization was not Accepted; see {receipt}")
    if Path(path).suffix.lower() != ".zip":
        execute("xcrun", "stapler", "staple", path)
        execute("xcrun", "stapler", "validate", path)
    return report
