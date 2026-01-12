from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from datetime import date


@dataclass(frozen=True)
class Settings:
    project_name: str = "explainable-decision-engine"

    # Serving defaults to artifacts/latest. Training writes versioned dirs and refreshes latest.
    artifacts_dir: Path = Path(os.environ.get("ARTIFACTS_DIR", "artifacts/latest"))

    model_filename: str = "model.joblib"
    feature_schema_filename: str = "feature_schema.json"
    metrics_filename: str = "metrics.json"
    model_card_filename: str = "model_card.md"
    shap_background_filename: str = "shap_background.joblib"
    global_shap_sample_filename: str = "global_shap_sample.joblib"

    api_version: str = "v1"
    model_version: str = os.environ.get("MODEL_VERSION", date.today().isoformat())

    ood_z_threshold: float = float(os.environ.get("OOD_Z_THRESHOLD", "3.5"))
    explain_top_k: int = int(os.environ.get("EXPLAIN_TOP_K", "6"))

    # Rate limiting / batching
    rate_limit_rpm: int = int(os.environ.get("RATE_LIMIT_RPM", "120"))
    batch_max_rows: int = int(os.environ.get("BATCH_MAX_ROWS", "250"))

    # Optional Redis metrics queue
    redis_url: str = os.environ.get("REDIS_URL", "").strip()


SETTINGS = Settings()