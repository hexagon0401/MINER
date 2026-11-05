"""Assemble verified per-platform Beta 1 artifacts without changing binary bytes."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

MAC_COMMIT='7999c5ba0c99fe9b3d7b605b839f5cfaad092387'
MAC_TAG='v5.0.0-beta.1.1'
WINDOWS_TAG='v5.0.0-beta.1.1-windows.8'
TITLE='MINER ALPHA universial Beta 1'
PREFIX='MINER-Alpha-Universal-Beta1'
PINNED={'AppleSilicon':'8b430e5d4fac61d6e3c0e3a42f6058d22dc5ad0532df6b85672bc474a0eb40e4',
        'Windows-x64':'9258d19e12e2a010d20060a435b5470415086c8aa4be71537660c0e7346478b6'}


def assemble(source,output,tag):
    source,output=Path(source),Path(output)
    output.mkdir(parents=True,exist_ok=True)
    files=[('AppleSilicon',f'MINER-v{MAC_TAG[1:]}-macOS-AppleSilicon.dmg',f'{PREFIX}-macOS-AppleSilicon.dmg','arm64',MAC_TAG),
           ('Intel',f'MINER-v{MAC_TAG[1:]}-macOS-Intel.dmg',f'{PREFIX}-macOS-Intel.dmg','x86_64',MAC_TAG),
           ('Windows-x64',f'MINER-{WINDOWS_TAG}-Windows-x64-Setup.exe',f'{PREFIX}-Windows-x64-Setup.exe','x64',WINDOWS_TAG)]
    manifest={'name':TITLE,'tag':tag,'single_fat_binary':False,'platforms':[]}
    sums=[]
    for platform,original,name,arch,origin_tag in files:
        binary=source/original
        receipt=json.loads(binary.with_suffix(binary.suffix+'.verification.json').read_text(encoding='utf-8'))
        digest=hashlib.sha256(binary.read_bytes()).hexdigest()
        assert digest==receipt['sha256'],f'Bad receipt digest: {platform}'
        assert platform not in PINNED or PINNED[platform]==digest,f'Pinned artifact changed: {platform}'
        assert receipt['architecture']==arch,f'Wrong architecture: {platform}'
        assert receipt['version']==origin_tag[1:],f'Wrong version: {platform}'
        if platform=='Windows-x64':
            assert all(receipt[k] for k in ('installer_verified','uninstaller_verified','upgrade_verified'))
            assert receipt['ui']['ok'] and receipt['native_tun']['graceful_stop']
        else:
            assert receipt['dmg_to_disk_signature_verified'] and receipt['finder_background_layout_verified']
            assert receipt['native_ui_smoke']['ok']
        shutil.copyfile(binary,output/name)
        receipt.update({'source_tag':origin_tag,'original_filename':original,'filename':name})
        if platform!='Windows-x64':receipt['source_commit']=MAC_COMMIT
        (output/(name+'.verification.json')).write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        (output/(name+'.sha256')).write_text(f'{digest}  {name}\n',encoding='utf-8')
        sums.append(f'{digest}  {name}')
        manifest['platforms'].append({'platform':platform,'filename':name,'sha256':digest,'source_tag':origin_tag,'app_version':receipt['version'],
            'signing':receipt.get('signing','unsigned' if not receipt.get('authenticode_signed') else 'authenticode')})
    (output/'SHA256SUMS.txt').write_text('\n'.join(sums)+'\n',encoding='utf-8')
    (output/'release-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2))


if __name__=='__main__':assemble(*sys.argv[1:])
