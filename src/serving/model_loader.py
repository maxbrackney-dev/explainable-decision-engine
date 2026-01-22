from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
from src.common.settings import SETTINGS
from src.common.utils import read_json
from src.common.logging import get_logger

logger = get_logger("model_loader")


@dataclass(frozen=True)
class LoadedArtifacts:
    model: Any
    feature_list: List[str]
    stats_means: Dict[str, float]
    stats_stds: Dict[str, float]
    metrics: Dict[str, Any]
    model_card: str
    fairness_report: Dict[str, Any]
    artifacts_dir: Path


def load_artifacts(artifacts_dir: Optional[Path] = None) -> LoadedArtifacts:
    ad = artifacts_dir or SETTINGS.artifacts_dir

    model = joblib.load(ad / SETTINGS.model_filename)
    schema = read_json(ad / SETTINGS.feature_schema_filename)
    metrics = read_json(ad / SETTINGS.metrics_filename)
    model_card = (ad / SETTINGS.model_card_filename).read_text(encoding="utf-8")

    fairness_path = ad / SETTINGS.fairness_report_filename
    fairness = read_json(fairness_path) if fairness_path.exists() else {}

    feature_list = schema["features"]
    stats_means = schema["stats"]["means"]
    stats_stds = schema["stats"]["stds"]

    logger.info("Artifacts loaded", extra={"ctx": {"artifacts_dir": str(ad), "model_type": metrics.get("model_type")}})
    return LoadedArtifacts(model, feature_list, stats_means, stats_stds, metrics, model_card, fairness, ad)
