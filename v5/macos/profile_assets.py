"""Bundle the developer's public GitHub avatar; no runtime profile requests."""
import hashlib
import json
from pathlib import Path
import urllib.request


def bundle_avatar(ui_assets, work, execute):
    ui_assets, work = Path(ui_assets), Path(work)
    profile = json.loads((ui_assets / "developer-profile.json").read_text())
    request = urllib.request.Request(profile["avatarURL"], headers={"User-Agent": "MINER-build", "Accept": "image/png,image/jpeg"})
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.headers.get_content_type() not in {"image/png", "image/jpeg"}:
            raise ValueError("GitHub avatar response is not a PNG or JPEG image")
        data = response.read(4 * 1024 * 1024 + 1)
    if not data or len(data) > 4 * 1024 * 1024:
        raise ValueError("GitHub avatar is empty or exceeds 4 MiB")
    original = work / "developer-avatar-source"
    original.write_bytes(data)
    avatar = ui_assets / "developer-avatar.png"
    execute("sips", "-s", "format", "png", "-Z", "256", original, "--out", avatar)
    return {"login": profile["login"], "name": profile["name"], "profile_url": profile["profileURL"],
            "avatar_url": profile["avatarURL"], "avatar_sha256": hashlib.sha256(avatar.read_bytes()).hexdigest()}
