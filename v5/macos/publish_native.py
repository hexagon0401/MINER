"""Publish only receipts that match the exact native DMG and source commit."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main(directory):
    root, tag, sha, repo = Path(directory), os.environ['RELEASE_TAG'], os.environ['SOURCE_SHA'], os.environ['GITHUB_REPOSITORY']
    dmgs = list(root.glob('*.dmg'))
    if len(dmgs) != 1: raise ValueError('Expected one native DMG')
    dmg = dmgs[0]
    receipt_path = dmg.with_suffix('.dmg.verification.json')
    receipt = json.loads(receipt_path.read_text())
    digest = hashlib.sha256(dmg.read_bytes()).hexdigest()
    if receipt['version'] != tag[1:] or receipt['sha256'] != digest or receipt.get('dmg_to_disk_signature_verified') is not True or receipt.get('native_ui_smoke', {}).get('ok') is not True:
        raise ValueError('Native verification/provenance mismatch')
    receipt['source_sha'] = sha
    receipt_path.write_text(json.dumps(receipt, indent=2))
    receipt['run_url'] = f'https://github.com/{repo}/actions/runs/{os.environ["GITHUB_RUN_ID"]}'
    subprocess.run(['git','fetch','--depth=1','origin',sha],check=True)
    release = json.loads(subprocess.check_output(['gh','release','view',tag,'--repo',repo,'--json','assets'], text=True))
    existing = {a['name']: a for a in release['assets']}
    for path in sorted(root.iterdir()):
        if not path.is_file(): continue
        if path.name in existing:
            actual = existing[path.name].get('digest')
            if actual != 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest():
                raise ValueError('Refusing to overwrite existing asset: ' + path.name)
            continue
        subprocess.run(['gh','release','upload',tag,str(path),'--repo',repo],check=True)
    notes = root / 'verified-notes.md'
    notes.write_text(f'**Apple Silicon DMG 검증·업로드 완료.**\n\n소스: `{sha}`\n\nDMG SHA-256: `{digest}`\n\n' + subprocess.check_output(['git','show',f'{sha}:v5/macos/RELEASE_NOTES.md'],text=True))
    subprocess.run(['gh','release','edit',tag,'--repo',repo,'--prerelease','--notes-file',str(notes)],check=True)


if __name__ == '__main__': main(sys.argv[1])
