from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def z_score_warnings(x: Dict[str, float], means: Dict[str, float], stds: Dict[str, float], z_threshold: float) -> List[str]:
    warnings: List[str] = []
    for k, v in x.items():
        if k not in means or k not in stds:
            continue
        s = float(stds[k])
        if s <= 1e-12:
            continue
        z = (float(v) - float(means[k])) / s
        if abs(z) >= z_threshold:
            warnings.append(f"ood_warning:{k}:z={z:.2f} (threshold={z_threshold})")
    return warnings


def normalize_features_ordered(payload: Dict[str, Any], feature_list: List[str]) -> pd.DataFrame:
    row = {f: payload[f] for f in feature_list}
    return pd.DataFrame([row], columns=feature_list)
