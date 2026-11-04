"""Publish only receipts that match the exact native DMG and source commit."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def validate_receipt(receipt, tag, digest):
    if receipt.get('version') != tag[1:] or receipt.get('sha256') != digest or receipt.get('architecture') != 'arm64' or receipt.get('dmg_to_disk_signature_verified') is not True or receipt.get('finder_background_layout_verified') is not True or receipt.get('native_ui_smoke', {}).get('ok') is not True:
        raise ValueError('Native verification/provenance mismatch')
    if tag != 'v5.0.0-beta.1':
        catalog = receipt.get('school_catalog', {})
        if catalog.get('complete') is not True or catalog.get('fixture') is not False or receipt.get('development_only'):
            raise ValueError('Complete official catalog required; development DMGs cannot be published')


def main(directory):
    root, tag, sha, repo = Path(directory), os.environ['RELEASE_TAG'], os.environ['SOURCE_SHA'], os.environ['GITHUB_REPOSITORY']
    dmgs = list(root.glob('*.dmg'))
    if len(dmgs) != 1: raise ValueError('Expected one native DMG')
    dmg = dmgs[0]
    receipt_path = dmg.with_suffix('.dmg.verification.json')
    receipt = json.loads(receipt_path.read_text())
    digest = hashlib.sha256(dmg.read_bytes()).hexdigest()
    validate_receipt(receipt, tag, digest)
    expected = f'MINER-{tag}-macOS-AppleSilicon.dmg'
    if dmg.name != expected or dmg.with_suffix('.dmg.sha256').read_text().strip() != f'{digest}  {expected}':
        raise ValueError('DMG name or checksum sidecar mismatch')
    allowed = {expected, expected+'.sha256', expected+'.verification.json'}
    if {p.name for p in root.iterdir() if p.is_file()} != allowed:
        raise ValueError('Unexpected release asset; refusing bulk upload')
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
