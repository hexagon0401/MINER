"""Publish macOS client DNS service-binding guard; retain previous releases unchanged."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

TAG='miner-strata-v2.0.0-preview.7'

def assemble(source,output):
    source=Path(source);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    manifest={'tag':TAG,'codename':'STRATA','release_version':'2.0.0','preview_revision':7,'prerelease':True,
              'scope':'macOS supplemental Riot DNS and OS path verification','payloads_rebuilt':True,'platforms':[],
              'windows_unchanged_release':'miner-strata-v2.0.0-preview.1','manual_game_gates_passed':False}
    icon=hashlib.sha256((Path(__file__).resolve().parents[2]/'v5/macos/design/icons/beta/AppIcon.png').read_bytes()).hexdigest()
    sums=[]
    for arch,kind in [('arm64','AppleSilicon'),('x86_64','Intel')]:
        name=f'MINER-STRATA-v2.0.0-preview.7-macOS-{kind}.dmg';paths=list(source.rglob(name))
        if len(paths)!=1:raise ValueError('Exactly one native DMG per architecture required')
        binary=paths[0];receipt=json.loads(binary.with_name(name+'.verification.json').read_text())
        digest=hashlib.sha256(binary.read_bytes()).hexdigest()
        if receipt.get('version')!='5.0.0-strata.2.0.0-preview.7' or receipt.get('source_commit')!=os.environ['GITHUB_SHA'] or receipt.get('architecture')!=arch or receipt.get('sha256')!=digest:raise ValueError('Native payload identity mismatch')
        if receipt.get('release_channel')!='beta' or receipt.get('app_icon_sha256')!=icon:raise ValueError('Beta artwork mismatch')
        if not all(receipt.get(key) is True for key in ('dmg_to_disk_signature_verified','finder_background_layout_verified')):raise ValueError('DMG integrity/layout check missing')
        if not all(receipt.get(key,{}).get('ok') is True for key in ('native_ui_smoke','helper_smoke','commands','updater','selective_network')):raise ValueError('Required native regression missing')
        preflight=receipt.get('session_preflight',{})
        if not all(preflight.get(key) is True for key in ('ok','packaged_cli','live_client_allowed','active_game_allowed','reconnect_notice_reported','long_paths_with_spaces','client_not_terminated')):raise ValueError('Packaged client-start regression missing')
        if preflight.get('real_lol_tested') is not False:raise ValueError('Inert fixture cannot certify real LoL')
        if receipt['selective_network'].get('proxy_doh_real_ip_no_hostname_recursion') is not True:raise ValueError('Proxy DNS isolation regression missing')
        if receipt['selective_network'].get('os_client_path',{}).get('os_dns_synthetic') is not True or receipt['selective_network']['os_client_path'].get('tls_verified') is not True:raise ValueError('OS client path regression missing')
        normal=receipt['updater'].get('normal_launch',{})
        if not all(normal.get(key) is True for key in ('ok','launch_services_normal_startup','event_loop_ready','finished_launching','visible_main_window','reopen_received','normal_quit')):raise ValueError('Real normal-launch verification missing')
        if normal.get('ui_smoke_mode') is not False or normal.get('warp_or_tun_activation_requested') is not False:raise ValueError('Launch verification used an injected UI or changed network')
        for file in (binary,binary.with_name(name+'.verification.json')):shutil.copyfile(file,output/file.name)
        sums.append(f'{digest}  {name}\n')
        (output/(name+'.sha256')).write_text(sums[-1])
        manifest['platforms'].append({'filename':name,'architecture':arch,'sha256':digest,'source_commit':receipt['source_commit']})
    for binary in source.rglob('MINER-Diagnostics-*.zip'):
        if binary.name in {p.name for p in output.iterdir()}:raise ValueError('Duplicate diagnostic package')
        receipt=json.loads(binary.with_name(binary.name+'.verification.json').read_text());digest=hashlib.sha256(binary.read_bytes()).hexdigest()
        if receipt.get('source_commit')!=os.environ['GITHUB_SHA'] or receipt.get('sha256')!=digest or receipt.get('ok') is not True:raise ValueError('Diagnostic proof mismatch')
        for file in (binary,binary.with_name(binary.name+'.verification.json')):shutil.copyfile(file,output/file.name)
        sums.append(f'{digest}  {binary.name}\n')
    (output/'SHA256SUMS.txt').write_text(''.join(sums))
    (output/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':assemble(*sys.argv[1:])
