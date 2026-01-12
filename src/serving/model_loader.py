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
    artifacts_dir: Path


def load_artifacts(artifacts_dir: Optional[Path] = None) -> LoadedArtifacts:
    ad = artifacts_dir or SETTINGS.artifacts_dir

    model_path = ad / SETTINGS.model_filename
    schema_path = ad / SETTINGS.feature_schema_filename
    metrics_path = ad / SETTINGS.metrics_filename
    card_path = ad / SETTINGS.model_card_filename

    model = joblib.load(model_path)
    schema = read_json(schema_path)
    metrics = read_json(metrics_path)
    model_card = card_path.read_text(encoding="utf-8")

    feature_list = schema["features"]
    stats_means = schema["stats"]["means"]
    stats_stds = schema["stats"]["stds"]

    logger.info("Artifacts loaded", extra={"ctx": {"artifacts_dir": str(ad), "model_type": metrics.get("model_type")}})

    return LoadedArtifacts(
        model=model,
        feature_list=feature_list,
        stats_means=stats_means,
        stats_stds=stats_stds,
        metrics=metrics,
        model_card=model_card,
        artifacts_dir=ad,
    )