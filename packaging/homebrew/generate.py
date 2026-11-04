"""Generate a cask only from an actually verified native release receipt."""
import argparse
import json
from pathlib import Path
import re


def generate(receipt,output):
    data=json.loads(Path(receipt).read_text())
    version=data.get('version','');digest=data.get('sha256','');sha=data.get('source_sha','')
    if not re.fullmatch(r'5\.0\.0-beta\.\d+',version) or not re.fullmatch(r'[a-f0-9]{64}',digest) or not re.fullmatch(r'[a-f0-9]{40}',sha): raise ValueError('Invalid version/hash/source provenance')
    if data.get('architecture')!='arm64' or not data.get('dmg_to_disk_signature_verified') or data.get('native_ui_smoke',{}).get('ok') is not True: raise ValueError('Native DMG/UI verification required')
    if version!='5.0.0-beta.1':
        catalog=data.get('school_catalog',{})
        if catalog.get('complete') is not True or catalog.get('fixture') is not False: raise ValueError('Beta 2 requires the complete official catalog')
    text=(Path(__file__).parent/'templates/miner-beta.rb.in').read_text()
    note='This build has Developer ID signing and Apple notarization.' if data.get('signing')=='developer-id' and (data.get('app_notarization') or {}).get('status')=='Accepted' else 'This beta is ad-hoc signed and is not Apple notarized.'
    text=text.replace('@VERSION@',version).replace('@SHA256@',digest).replace('@SIGNING_NOTE@',note)
    Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(text)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('receipt',type=Path);p.add_argument('--output',type=Path,default=Path(__file__).parent/'Casks/miner-beta.rb');a=p.parse_args();generate(a.receipt,a.output)
