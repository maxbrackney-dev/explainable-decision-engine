from __future__ import annotations

from pathlib import Path
import shutil
import joblib
from datetime import datetime, timezone

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV

from src.common.settings import SETTINGS
from src.common.utils import write_json
from src.common.logging import get_logger
from src.training.data_gen import generate_synthetic_risk_data, FEATURES
from src.training.evaluate import evaluate_binary_probs

logger = get_logger("training")


def _feature_stats(df: pd.DataFrame) -> dict:
    means = {c: float(df[c].astype(float).mean()) for c in FEATURES}
    stds = {c: float(df[c].astype(float).std(ddof=0) + 1e-9) for c in FEATURES}
    return {"means": means, "stds": stds}


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def _copy_to_latest(version_dir: Path, latest_dir: Path) -> None:
    latest_dir.parent.mkdir(parents=True, exist_ok=True)
    if latest_dir.exists():
        shutil.rmtree(latest_dir)
    shutil.copytree(version_dir, latest_dir)


def main() -> None:
    base_artifacts = Path("artifacts")
    version_dir = base_artifacts / _stamp()
    latest_dir = base_artifacts / "latest"
    version_dir.mkdir(parents=True, exist_ok=True)

    df = generate_synthetic_risk_data(n=25000, seed=42)
    X = df[FEATURES].copy()
    y = df["high_risk"].astype(int).values

    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
    )

    lr = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000, solver="lbfgs")),
        ]
    )
    lr_cal = CalibratedClassifierCV(lr, method="sigmoid", cv=3)

    gbc = GradientBoostingClassifier(random_state=42)
    gbc_cal = CalibratedClassifierCV(gbc, method="sigmoid", cv=3)

    logger.info("Fitting LR calibrator...", extra={"ctx": {"stage": "fit_lr"}})
    lr_cal.fit(X_train, y_train)

    logger.info("Fitting GBC calibrator...", extra={"ctx": {"stage": "fit_gbc"}})
    gbc_cal.fit(X_train, y_train)

    lr_val_prob = lr_cal.predict_proba(X_val)[:, 1]
    gbc_val_prob = gbc_cal.predict_proba(X_val)[:, 1]

    lr_eval = evaluate_binary_probs(y_val, lr_val_prob)
    gbc_eval = evaluate_binary_probs(y_val, gbc_val_prob)

    def score_key(res) -> tuple:
        return (res.auc, -res.brier)

    chosen = "logistic_regression" if score_key(lr_eval) >= score_key(gbc_eval) else "gradient_boosting"
    model = lr_cal if chosen == "logistic_regression" else gbc_cal

    test_prob = model.predict_proba(X_test)[:, 1]
    test_eval = evaluate_binary_probs(y_test, test_prob)

    threshold = 0.5
    stats = _feature_stats(X_train)

    feature_schema = {
        "features": FEATURES,
        "types": {
            "age": "int",
            "income": "float",
            "account_age_days": "int",
            "num_txn_30d": "int",
            "avg_txn_amount_30d": "float",
            "num_chargebacks_180d": "int",
            "device_change_count_30d": "int",
            "geo_distance_from_last_txn_km": "float",
            "is_international": "bool",
            "merchant_risk_score": "float",
        },
        "stats": stats,
        "notes": "Synthetic schema. Not real banking data.",
    }

    # timezone-aware UTC timestamp (no deprecation warning)
    training_date = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    metrics = {
        "training_date": training_date,
        "model_type": chosen,
        "selection": {
            "lr_val": lr_eval.to_dict(),
            "gbc_val": gbc_eval.to_dict(),
            "chosen": chosen,
        },
        "test": test_eval.to_dict(),
        "threshold": threshold,
        "calibration": "CalibratedClassifierCV(method=sigmoid)",
        "limitations": "Synthetic demo only. Not for real-world decisions.",
        "artifact_version_dir": str(version_dir),
    }

    joblib.dump(model, version_dir / SETTINGS.model_filename)
    write_json(version_dir / SETTINGS.feature_schema_filename, feature_schema)
    write_json(version_dir / SETTINGS.metrics_filename, metrics)

    model_card = """# Model Card — Explainable Decision Engine

## Summary
This project trains a model on **synthetic** data to score "risk" for educational/portfolio purposes.

## Intended Use
- Demonstrate ML training + calibration + explainability patterns
- Demonstrate strict API schema validation and guardrails

## Not Intended For
- Real-world banking, fraud, credit, underwriting, or law enforcement decisions
- Any decision affecting a person's eligibility, finances, housing, employment, or rights

## Data
- Fully synthetic tabular dataset generated by rules + noise.
- **Not real banking data.**

## Model
- Two models trained: Logistic Regression and Gradient Boosting.
- Final model selected based on validation AUC and Brier score.
- Calibrated with CalibratedClassifierCV (sigmoid).

## Explainability
- Local explanations are produced via SHAP values per-request.
- Global explanations use mean(|SHAP|) over a sample.

## Limitations
- Synthetic dataset, synthetic relationships, synthetic biases.
- No fairness evaluation.
- No drift monitoring.
- Threshold is a default and not business-optimized.

## Guardrails
- Strict type+range validation
- Reject unknown fields
- OOD warnings via z-score against training distribution
- Logs avoid PII
"""
    (version_dir / SETTINGS.model_card_filename).write_text(model_card, encoding="utf-8")

    bg = X_train.sample(n=200, random_state=42)
    global_sample = X_train.sample(n=800, random_state=7)
    joblib.dump(bg, version_dir / SETTINGS.shap_background_filename)
    joblib.dump(global_sample, version_dir / SETTINGS.global_shap_sample_filename)

    _copy_to_latest(version_dir, latest_dir)

    logger.info(
        "Training complete",
        extra={
            "ctx": {
                "chosen": chosen,
                "val_lr_auc": lr_eval.auc,
                "val_gbc_auc": gbc_eval.auc,
                "test_auc": test_eval.auc,
                "test_brier": test_eval.brier,
                "version_dir": str(version_dir),
                "latest_dir": str(latest_dir),
            }
        },
    )


if __name__ == "__main__":
    main()