"""Promote exact verified Beta 1 payloads into the ALPHA v1 named release."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

NAME='MINER ALPHA v1'
TAG='miner-alpha-v1'
ARTIFACTS=[('macOS-AppleSilicon.dmg','arm64','8b430e5d4fac61d6e3c0e3a42f6058d22dc5ad0532df6b85672bc474a0eb40e4'),
 ('macOS-Intel.dmg','x86_64','51012a4dd35bf7b3042c80df645fe40115ae1f69c56cc06580e37b748abb23f5'),
 ('Windows-x64-Setup.exe','x64','9258d19e12e2a010d20060a435b5470415086c8aa4be71537660c0e7346478b6')]


def promote(source,output):
    source,output=Path(source),Path(output);output.mkdir(parents=True,exist_ok=True)
    manifest={'name':NAME,'tag':TAG,'codename':'ALPHA','release_version':1,'prerelease':False,
       'source_release':'miner-alpha-universal-beta.1','payloads_rebuilt':False,'platforms':[]}
    sums=[]
    for suffix,arch,expected in ARTIFACTS:
        original=f'MINER-Alpha-Universal-Beta1-{suffix}';name=f'MINER-ALPHA-v1-{suffix}'
        binary=source/original;receipt=json.loads((source/(original+'.verification.json')).read_text(encoding='utf-8'))
        digest=hashlib.sha256(binary.read_bytes()).hexdigest()
        assert expected==digest==receipt['sha256'],f'Payload or receipt changed: {suffix}'
        assert receipt['architecture']==arch
        if suffix.endswith('.dmg'):
            assert receipt['native_ui_smoke']['ok'] and receipt['dmg_to_disk_signature_verified'] and receipt['finder_background_layout_verified']
        else:assert receipt['ui']['ok'] and receipt['installer_verified'] and receipt['uninstaller_verified']
        shutil.copyfile(binary,output/name)
        receipt.update({'release_name':NAME,'release_codename':'ALPHA','release_version':1,'filename':name,
            'promoted_from_filename':original,'binary_modified':False})
        (output/(name+'.verification.json')).write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        line=f'{digest}  {name}\n';(output/(name+'.sha256')).write_text(line,encoding='utf-8');sums.append(line)
        manifest['platforms'].append({'filename':name,'architecture':arch,'sha256':digest,'internal_build_version':receipt['version'],
            'original_source_tag':receipt['source_tag']})
    (output/'release-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (output/'SHA256SUMS.txt').write_text(''.join(sums),encoding='utf-8')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':promote(*sys.argv[1:])
