"""GitHub-only coordinator: retry infrastructure, never rewrite a release tag."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

TAG = "v5.0.0-beta.1"
SOURCE_SHA = "8cc4f8f880b2d438b297941af038f743aca18af4"
WORKFLOW = "miner-native-build.yml"


def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def release_complete(release, receipt):
    if not receipt or receipt.get("version") != TAG[1:] or receipt.get("source_sha") != SOURCE_SHA:
        return False
    name = f"MINER-{TAG}-macOS-AppleSilicon.dmg"
    asset = next((a for a in release.get("assets", []) if a.get("name") == name), None)
    return bool(asset and receipt.get("dmg_to_disk_signature_verified") is True
                and receipt.get("native_ui_smoke", {}).get("ok") is True
                and receipt.get("sha256") and asset.get("digest") in (None, "sha256:" + receipt["sha256"]))


def decide(release, receipt, runs):
    if release_complete(release, receipt):
        return {"state": "complete", "dispatch": False}
    relevant = [r for r in runs if r.get("display_title", "").startswith(f"MINER native {TAG} (")]
    if any(r["status"] != "completed" for r in relevant):
        return {"state": "waiting_active", "dispatch": False}
    latest = relevant[0] if relevant else None
    if latest and latest.get("conclusion") == "failure":
        return {"state": "needs_fix", "dispatch": False, "run_url": latest["html_url"]}
    runner = "macos-15" if latest and "(macos-26)" in latest["display_title"] else "macos-26"
    return {"state": "retry_requested", "dispatch": True, "runner": runner}


def write_report(value):
    ref = "miner-retry-state/beta1"
    # Separate index/tree; no checkout changes, no removal of the executing script.
    with tempfile.TemporaryDirectory() as temp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(temp) / "index"))
        subprocess.run(["git", "read-tree", "--empty"], env=env, check=True)
        blob = subprocess.check_output(["git", "hash-object", "-w", "--stdin"], input=json.dumps(value, indent=2).encode()).decode().strip()
        subprocess.run(["git", "update-index", "--add", "--cacheinfo", f"100644,{blob},retry.json"], env=env, check=True)
        tree = subprocess.check_output(["git", "write-tree"], env=env, text=True).strip()
        # Fetch only if the report already exists; append history instead of force-pushing.
        found = subprocess.run(["git", "fetch", "origin", f"refs/heads/{ref}"], capture_output=True)
        args = ["git", "commit-tree", tree, "-m", "Record beta 1 retry decision"]
        if found.returncode == 0:
            args += ["-p", subprocess.check_output(["git", "rev-parse", "FETCH_HEAD"], text=True).strip()]
        commit = subprocess.check_output(args, env=dict(os.environ, GIT_AUTHOR_NAME="MINER Build Reports", GIT_AUTHOR_EMAIL="github-actions[bot]@users.noreply.github.com", GIT_COMMITTER_NAME="MINER Build Reports", GIT_COMMITTER_EMAIL="github-actions[bot]@users.noreply.github.com"), text=True).strip()
        subprocess.run(["git", "push", "origin", f"{commit}:refs/heads/{ref}"], check=True)


def main():
    repo = os.environ["GITHUB_REPOSITORY"]
    release = json.loads(gh("release", "view", TAG, "--repo", repo, "--json", "url,assets"))
    receipt = None
    with tempfile.TemporaryDirectory() as directory:
        result = subprocess.run(["gh", "release", "download", TAG, "--repo", repo, "--pattern", "*AppleSilicon.dmg.verification.json", "--dir", directory], capture_output=True)
        if result.returncode == 0:
            receipt = json.loads(next(Path(directory).glob("*.json")).read_text())
    runs = json.loads(gh("api", f"repos/{repo}/actions/workflows/{WORKFLOW}/runs?per_page=100"))["workflow_runs"]
    decision = decide(release, receipt, runs)
    if decision["dispatch"]:
        gh("workflow", "run", WORKFLOW, "--repo", repo, "--ref", "main", "-f", f"release_tag={TAG}", "-f", f"runner={decision['runner']}")
    write_report({**decision, "tag": TAG, "source_sha": SOURCE_SHA, "release_url": release["url"]})
    print(json.dumps(decision))


if __name__ == "__main__":
    main()
