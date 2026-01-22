from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import shutil

from src.common.utils import read_json, write_json


def registry_path() -> Path:
    return Path("artifacts") / "registry.json"


def load_registry() -> Dict[str, Any]:
    p = registry_path()
    if not p.exists():
        return {"models": [], "latest": None}
    return read_json(p)


def add_model(version_dir: str, metrics: Dict[str, Any]) -> None:
    reg = load_registry()
    models: List[Dict[str, Any]] = reg.get("models", [])
    entry = {
        "version": Path(version_dir).name,
        "path": version_dir,
        "training_date": metrics.get("training_date"),
        "model_type": metrics.get("model_type"),
        "metrics_summary": {
            "auc_test": metrics.get("test", {}).get("auc"),
            "brier_test": metrics.get("test", {}).get("brier"),
        },
        "promoted_by": None,
        "promoted_at": None,
    }
    models.append(entry)
    reg["models"] = models
    if reg.get("latest") is None:
        reg["latest"] = entry["version"]
    write_json(registry_path(), reg)


def promote(version: str, promoted_by: str) -> None:
    base = Path("artifacts")
    src = base / version
    if not src.exists():
        raise FileNotFoundError(f"Unknown version dir: artifacts/{version}")

    latest = base / "latest"
    if latest.exists():
        shutil.rmtree(latest)
    shutil.copytree(src, latest)

    reg = load_registry()
    reg["latest"] = version
    for m in reg.get("models", []):
        if m.get("version") == version:
            m["promoted_by"] = promoted_by
            m["promoted_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    write_json(registry_path(), reg)
