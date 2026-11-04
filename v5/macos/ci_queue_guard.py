"""Stop this beta run if no native runner is assigned within two minutes.

The source prerelease stays available. Never cancel an assigned native build.
"""
import json
import os
from pathlib import Path
import subprocess
import time


def gh(*args):
    return subprocess.check_output(["gh", *args], text=True)


def main():
    repo, run, tag = (os.environ[k] for k in ["GITHUB_REPOSITORY", "GITHUB_RUN_ID", "RELEASE_TAG"])
    if not tag.startswith("v5.0.0-beta."):
        raise ValueError("Queue guard is limited to this beta workflow")
    notes = Path("v5/macos/RELEASE_NOTES.md").read_text()
    deadline = time.monotonic() + 120
    native = []
    while True:
        jobs = json.loads(gh("api", f"repos/{repo}/actions/runs/{run}/jobs?per_page=100"))["jobs"]
        native = [j for j in jobs if j["name"].startswith("build (")]
        if native and any(j.get("runner_name") or j["status"] != "queued" for j in native):
            break
        if time.monotonic() >= deadline:
            break
        time.sleep(10)
    timed_out = bool(native) and all(j["status"] == "queued" and not j.get("runner_name") and not j.get("steps") for j in native)
    release = json.loads(gh("release", "view", tag, "--repo", repo, "--json", "name,url,isPrerelease,assets"))
    if timed_out:
        pending = Path(os.environ["RUNNER_TEMP"]) / "queue-release-notes.md"
        pending.write_text("**소스 프리릴리스입니다. macOS 서버가 배정되지 않아 이번 시도의 DMG 생성·업로드는 중단됐습니다.**\n\n" + notes)
        gh("release", "edit", tag, "--repo", repo, "--notes-file", str(pending))
    report = {"tag": tag, "source_sha": os.environ["GITHUB_SHA"], "queue_timed_out": timed_out,
              "run_url": f"https://github.com/{repo}/actions/runs/{run}", "release": release,
              "jobs": [{k: j.get(k) for k in ["name", "status", "conclusion", "runner_name", "steps"]} for j in native]}
    ref = f"miner-build-progress/{tag}-{run}"
    subprocess.run(["git", "switch", "--orphan", ref], check=True)
    Path("progress.json").write_text(json.dumps(report, indent=2))
    for key, value in [("user.name", "MINER Build Reports"), ("user.email", "github-actions[bot]@users.noreply.github.com")]:
        subprocess.run(["git", "config", key, value], check=True)
    subprocess.run(["git", "add", "progress.json"], check=True)
    subprocess.run(["git", "commit", "-m", "Record native runner assignment and beta prerelease"], check=True)
    subprocess.run(["git", "push", "origin", f"HEAD:refs/heads/{ref}"], check=True)
    if timed_out:
        # Recheck after publishing the report: assignment may have happened meanwhile.
        latest = json.loads(gh("api", f"repos/{repo}/actions/runs/{run}/jobs?per_page=100"))["jobs"]
        builds = [j for j in latest if j["name"].startswith("build (")]
        if builds and all(j["status"] == "queued" and not j.get("runner_name") for j in builds):
            gh("run", "cancel", run, "--repo", repo)


if __name__ == "__main__":
    main()
