from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class Settings:
    project_name: str = "explainable-decision-engine"
    api_version: str = "v1"

    artifacts_dir: Path = Path(os.environ.get("ARTIFACTS_DIR", "artifacts/latest"))

    model_filename: str = "model.joblib"
    feature_schema_filename: str = "feature_schema.json"
    metrics_filename: str = "metrics.json"
    model_card_filename: str = "model_card.md"
    shap_background_filename: str = "shap_background.joblib"
    global_shap_sample_filename: str = "global_shap_sample.joblib"
    fairness_report_filename: str = "fairness_report.json"
    registry_filename: str = "registry.json"

    # Auth
    demo_api_key: str = os.environ.get("DEMO_API_KEY", "").strip()
    demo_api_keys_json: str = os.environ.get("DEMO_API_KEYS_JSON", "").strip()  # optional: {"keyA":60,"keyB":10}

    # Redis
    redis_url: str = os.environ.get("REDIS_URL", "").strip()

    # Distributed rate limits (fallbacks)
    default_rpm: int = int(os.environ.get("DEFAULT_RPM", "60"))

    # Drift
    drift_z_threshold: float = float(os.environ.get("DRIFT_Z_THRESHOLD", "3.5"))

    # Decisioning / Loss model
    event_definition: str = os.environ.get("RISK_EVENT_DEFINITION", "chargeback_within_180d")
    loss_per_event_usd: float = float(os.environ.get("LOSS_PER_EVENT_USD", "180.0"))
    loss_amt_multiplier: float = float(os.environ.get("LOSS_AMT_MULTIPLIER", "0.15"))  # avg_txn_amount weight
    stepup_threshold: float = float(os.environ.get("STEPUP_THRESHOLD", "0.35"))
    review_threshold: float = float(os.environ.get("REVIEW_THRESHOLD", "0.55"))
    decline_threshold: float = float(os.environ.get("DECLINE_THRESHOLD", "0.80"))

    # Cost curve (used for threshold optimization metadata)
    fp_cost_usd: float = float(os.environ.get("FP_COST_USD", "2.50"))     # manual review / friction
    fn_cost_usd: float = float(os.environ.get("FN_COST_USD", "180.0"))    # expected loss
    max_review_rate: float = float(os.environ.get("MAX_REVIEW_RATE", "0.05"))  # capacity constraint


SETTINGS = Settings()
