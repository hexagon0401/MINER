"""Expose bounded build diagnostics through GitHub check annotations."""
import os
from pathlib import Path


for path in sorted(Path(os.environ["RUNNER_TEMP"]).glob("*release-*.log")):
    tail = path.read_text(errors="replace")[-6000:]
    escaped = tail.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::error title={path.name}::{escaped}")
