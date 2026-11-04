"""Publish a small auditable build report, not binaries, on a separate Git ref.

Run only inside this repository's GitHub Actions after its build/release jobs.
This lets Git-only clients inspect actual publication and macOS validation results.
"""
import json
import os
from pathlib import Path
import subprocess


def gh(*args):
    return subprocess.run(["gh", *args], check=True, capture_output=True, text=True).stdout


def main():
    repo, run, tag = (os.environ[n] for n in ["GITHUB_REPOSITORY", "GITHUB_RUN_ID", "RELEASE_TAG"])
    output = Path(os.environ["REPORT_DIR"])
    output.mkdir(parents=True, exist_ok=True)
    jobs = json.loads(gh("api", f"repos/{repo}/actions/runs/{run}/jobs?per_page=100"))["jobs"]
    report = {"tag": tag, "source_sha": os.environ["GITHUB_SHA"],
              "run_url": f"https://github.com/{repo}/actions/runs/{run}",
              "build": os.environ["BUILD_RESULT"], "publication": os.environ["RELEASE_RESULT"],
              "jobs": [{"name": j["name"], "status": j["status"], "conclusion": j["conclusion"],
                        "started_at": j.get("started_at"), "completed_at": j.get("completed_at"),
                        "runner_name": j.get("runner_name"),
                        "steps": [{"name": s["name"], "status": s["status"], "conclusion": s["conclusion"]} for s in j.get("steps", [])],
                        "failed_steps": [s["name"] for s in j.get("steps", []) if s.get("conclusion") == "failure"]} for j in jobs]}
    for job in jobs:
        if job.get("conclusion") == "failure":
            try:
                log = gh("api", f"repos/{repo}/actions/jobs/{job['id']}/logs")
                (output / f"failed-job-{job['id']}.log").write_text(log[-40000:], encoding="utf-8")
            except (subprocess.CalledProcessError, UnicodeError):
                pass
    if report["publication"] == "success":
        report["release"] = json.loads(gh("release", "view", tag, "--repo", repo,
                                           "--json", "name,url,isPrerelease,assets"))
        subprocess.run(["gh", "release", "download", tag, "--repo", repo,
                        "--pattern", "*.verification.json", "--dir", str(output)], check=True)
    (output / "status.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
