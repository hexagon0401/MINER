"""Collect all three verified universal installers into an immutable release."""
import os
import hashlib
import json
from pathlib import Path
import shutil
import sys


VERSION = "2.0.0"
TAG = "miner-strata-v2.0.0-preview.1"


def assemble(source, output):
    source, output = Path(source), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    icon = Path(__file__).resolve().parents[2] / "v5/macos/design/icons/beta/AppIcon.png"
    icon_digest = hashlib.sha256(icon.read_bytes()).hexdigest()
    manifest = {"name": f"MINER STRATA v{VERSION} Preview 1", "tag": TAG, "codename": "STRATA",
                "release_version": VERSION, "prerelease": True, "payloads_rebuilt": True,
                "change": "Owned service lifetime, truthful health, bounded diagnostics; manual game gates pending",
                "platforms": []}
    sums = []
    for suffix, architecture, pattern in [
        ("macOS-AppleSilicon.dmg", "arm64", "*macOS-AppleSilicon.dmg"),
        ("macOS-Intel.dmg", "x86_64", "*macOS-Intel.dmg"),
        ("Windows-x64-Setup.exe", "x64", "*Windows-x64-Setup.exe"),
    ]:
        candidates = list(source.rglob(pattern))
        if len(candidates) != 1:
            raise ValueError(f"Exactly one installer required: {architecture}")
        binary = candidates[0]
        receipt = json.loads(binary.with_name(binary.name + ".verification.json").read_text())
        guard=receipt.get('startup_guard_native',{})
        if guard.get('supported') is not True or guard.get('game_open') is not False or guard.get('league_client_open') is not False:
            raise ValueError('Native startup guard not verified')
        expected_version = VERSION if suffix.endswith('.exe') else '5.0.0-strata.'+VERSION+'-preview.1'
        if receipt.get('version')!=expected_version:raise ValueError('Packaged version differs from release')
        if receipt.get('source_commit')!=os.environ.get('GITHUB_SHA'):raise ValueError('Native platforms were not built from the publishing commit')
        digest = hashlib.sha256(binary.read_bytes()).hexdigest()
        if receipt["sha256"] != digest or receipt["architecture"] != architecture:
            raise ValueError("Installer checksum/architecture mismatch")
        if receipt.get("release_channel") != "beta" or receipt.get("app_icon_sha256") != icon_digest:
            raise ValueError("Installer does not contain the verified official icon")
        if suffix.endswith(".dmg"):
            if not all([receipt["native_ui_smoke"]["ok"], receipt["dmg_to_disk_signature_verified"],
                        receipt["finder_background_layout_verified"]]):
                raise ValueError("Native Mac package verification failed")
            if not receipt.get("helper_smoke",{}).get("ok"): raise ValueError("Native helper peer authentication must pass")
            if not receipt.get("commands",{}).get("ok"):raise ValueError("Native command deadlines/cancellation unverified")
            if not receipt.get("selective_network",{}).get("game_service_tcp_proxied"):raise ValueError("Game-origin Riot TCP route unverified")
            baseline = "7999c5ba0c99fe9b3d7b605b839f5cfaad092387"
        else:
            if not all([receipt["ui"]["ok"], receipt["installer_verified"],
                        receipt["upgrade_verified"], receipt["uninstaller_verified"]]):
                raise ValueError("Windows package verification failed")
            baseline = "e94f5b99dc782cbd2acee1b29e3d5b29e35f431b"
        selective=receipt.get('selective_network',{})
        for check in ['ok','real_ip_routes_bypass_tun','ordinary_os_dns_and_tls','remote_dns_and_continuous_client_tcp',
                      'original_dns_recovered_before_engine_stop','engine_crash_dns_recovered','ordinary_https_after_recovery','dhcp_or_manual_mode_preserved','synthetic_ipv6_remote_dns_tcp']:
            if selective.get(check) is not True:raise ValueError('Native selective network proof missing: '+check)
        if suffix.endswith('.exe') and (receipt.get('upgrade_from')!='1.2.0' or receipt.get('upgrade_preserves_user_data') is not True or selective.get('windows_guardian_tested') is not True or selective.get('packaged_guardian_verified') is not True):
            raise ValueError('Published Windows v1.2.0 upgrade or recovery guardian not verified')
        if not receipt.get('updater',{}).get('ok'):raise ValueError('Packaged automatic update did not pass')
        if suffix.endswith('.exe') and (not receipt.get('obsolete_runtime_removed') or not receipt.get('failed_upgrade_rollback_verified')):raise ValueError('Windows old-file cleanup / rollback unverified')
        if suffix.endswith('.exe'):
            scm=receipt.get('strata_service',{})
            if scm.get('scm_installed_host_executed') is not True or scm.get('owner_pipe_authenticated') is not True:raise ValueError('Packaged SCM host unverified')
            lifetime=scm.get('lifetime_fixture',{})
            if not all(lifetime.get(key) is True for key in ('scm_owns_child_after_client_exit','nonowner_pipe_denied','service_crash_job_cleanup','restart_requires_recovery')):raise ValueError('SCM lifetime fixture failed')
        name = f"MINER-STRATA-v{VERSION}-preview.1-{suffix}"
        shutil.copyfile(binary, output / name)
        receipt.update({"release_version": VERSION, "release_codename": "STRATA",
                        "original_baseline": baseline, "source_commit": os.environ.get("GITHUB_SHA"), "filename": name})
        (output / (name + ".verification.json")).write_text(json.dumps(receipt, indent=2) + "\n")
        line = f"{digest}  {name}\n"
        (output / (name + ".sha256")).write_text(line)
        sums.append(line)
        manifest["platforms"].append({"filename": name, "architecture": architecture,
                                      "sha256": digest, "internal_build_version": receipt["version"],
                                      "original_baseline": baseline, "source_commit": os.environ.get("GITHUB_SHA"), "app_icon_sha256": icon_digest})
    diagnostics=list(source.rglob('MINER-Diagnostics-*.zip'))
    if len(diagnostics)!=3:raise ValueError('Three native diagnostic packages required')
    for binary in diagnostics:
        receipt=json.loads(binary.with_name(binary.name+'.verification.json').read_text())
        digest=hashlib.sha256(binary.read_bytes()).hexdigest()
        if receipt.get('sha256')!=digest or receipt.get('source_commit')!=os.environ.get('GITHUB_SHA') or receipt.get('ok') is not True:raise ValueError('Diagnostic proof mismatch')
        for path in (binary,binary.with_name(binary.name+'.verification.json')):shutil.copyfile(path,output/path.name)
        sums.append(f'{digest}  {binary.name}\n')
    manifest['manual_gates']={'mac_10_game_cycles':'PENDING_USER_MACBOOK','windows_11_vanguard':'UNVERIFIED','performance_comparison':'UNVERIFIED','stable_release_allowed':False}
    (output / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "SHA256SUMS.txt").write_text("".join(sums))


if __name__ == "__main__":
    assemble(*sys.argv[1:])
