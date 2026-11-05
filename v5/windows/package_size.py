"""Remove unsupported Qt features, preserving the QML/Fluent rendering stack."""
from pathlib import Path
import shutil

UNUSED = ("QtQuick3D", "QtWebEngine", "QtWebView", "QtMultimedia", "QtPdf", "QtLocation",
          "QtPositioning", "QtSensors", "QtCharts", "QtDataVisualization", "QtGraphs",
          "QtSpatialAudio", "QtVirtualKeyboard", "QtRemoteObjects", "QtScxml", "QtWebChannel")


def prune(root):
    root = Path(root)
    removed = []
    for path in list(root.rglob("*")):
        if not path.exists(): continue
        stem = path.name.replace("Qt6", "Qt", 1)
        if not any(stem.startswith(prefix) for prefix in UNUSED): continue
        if path.is_file() and path.suffix.lower() not in {".dll", ".pyd"}: continue
        size = sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) if path.is_dir() else path.stat().st_size
        removed.append({"path": str(path.relative_to(root)), "bytes": size})
        if path.is_dir(): shutil.rmtree(path)
        else: path.unlink()
    largest = sorted((p for p in root.rglob("*") if p.is_file()), key=lambda p:p.stat().st_size, reverse=True)[:20]
    return {"removed_bytes": sum(p["bytes"] for p in removed), "removed": removed,
            "largest_remaining": [{"path":str(p.relative_to(root)),"bytes":p.stat().st_size} for p in largest]}
