from __future__ import annotations

from pathlib import Path
import shutil
import joblib
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import roc_auc_score, brier_score_loss

from src.common.settings import SETTINGS
from src.common.utils import write_json
from src.common.logging import get_logger
from src.common.model_registry import add_model
from src.training.data_gen import generate_synthetic_risk_data, FEATURES

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


def _eval(y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    return {
        "auc": float(roc_auc_score(y_true, y_prob)),
        "brier": float(brier_score_loss(y_true, y_prob)),
    }


def _fairness_by_age(y_true: np.ndarray, y_prob: np.ndarray, ages: np.ndarray) -> dict:
    buckets = [
        ("13_17", (13, 17)),
        ("18_25", (18, 25)),
        ("26_40", (26, 40)),
        ("41_60", (41, 60)),
        ("61_100", (61, 100)),
    ]
    out = {
        "note": "This is not a fairness certification. Synthetic data can still encode synthetic bias.",
        "buckets": [],
    }
    for name, (lo, hi) in buckets:
        mask = (ages >= lo) & (ages <= hi)
        if mask.sum() < 50:
            continue
        out["buckets"].append({
            "bucket": name,
            "n": int(mask.sum()),
            "auc": float(roc_auc_score(y_true[mask], y_prob[mask])),
            "brier": float(brier_score_loss(y_true[mask], y_prob[mask])),
            "prevalence": float(y_true[mask].mean()),
        })
    return out


def main() -> None:
    base_artifacts = Path("artifacts")
    version_dir = base_artifacts / _stamp()
    latest_dir = base_artifacts / "latest"
    version_dir.mkdir(parents=True, exist_ok=True)

    df = generate_synthetic_risk_data(n=25000, seed=42)
    X = df[FEATURES].copy()
    y = df["high_risk"].astype(int).values

    X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp)

    lr = Pipeline(steps=[("scaler", StandardScaler()), ("clf", LogisticRegression(max_iter=2000, solver="lbfgs"))])
    lr_cal = CalibratedClassifierCV(lr, method="sigmoid", cv=3)

    gbc = GradientBoostingClassifier(random_state=42)
    gbc_cal = CalibratedClassifierCV(gbc, method="sigmoid", cv=3)

    logger.info("Fitting LR calibrator...", extra={"ctx": {"stage": "fit_lr"}})
    lr_cal.fit(X_train, y_train)

    logger.info("Fitting GBC calibrator...", extra={"ctx": {"stage": "fit_gbc"}})
    gbc_cal.fit(X_train, y_train)

    lr_val = lr_cal.predict_proba(X_val)[:, 1]
    gbc_val = gbc_cal.predict_proba(X_val)[:, 1]

    lr_eval = _eval(y_val, lr_val)
    gbc_eval = _eval(y_val, gbc_val)

    def key(m): return (m["auc"], -m["brier"])
    chosen = "logistic_regression" if key(lr_eval) >= key(gbc_eval) else "gradient_boosting"
    model = lr_cal if chosen == "logistic_regression" else gbc_cal

    test_prob = model.predict_proba(X_test)[:, 1]
    test_eval = _eval(y_test, test_prob)

    stats = _feature_stats(X_train)

    # store decision thresholds (env-configurable at serve time, but we persist defaults)
    thresholds = {
        "step_up": SETTINGS.stepup_threshold,
        "review": SETTINGS.review_threshold,
        "decline": SETTINGS.decline_threshold,
        "fp_cost_usd": SETTINGS.fp_cost_usd,
        "fn_cost_usd": SETTINGS.fn_cost_usd,
        "max_review_rate": SETTINGS.max_review_rate,
        "event_definition": SETTINGS.event_definition,
    }

    training_date = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    metrics = {
        "training_date": training_date,
        "model_type": chosen,
        "selection": {"lr_val": lr_eval, "gbc_val": gbc_eval, "chosen": chosen},
        "test": test_eval,
        "thresholds": thresholds,
        "calibration": "CalibratedClassifierCV(method=sigmoid)",
        "limitations": "Synthetic demo only. Not for real-world eligibility decisions.",
        "artifact_version_dir": str(version_dir),
    }

    feature_schema = {
        "features": FEATURES,
        "types": {f: "float" for f in FEATURES},
        "stats": stats,
        "notes": "Synthetic schema. Not real banking data.",
    }

    joblib.dump(model, version_dir / SETTINGS.model_filename)
    write_json(version_dir / SETTINGS.feature_schema_filename, feature_schema)
    write_json(version_dir / SETTINGS.metrics_filename, metrics)

    model_card = f"""# Model Card — Explainable Decision Engine

## Summary
Synthetic demo that outputs a probability for: **{SETTINGS.event_definition}**.

## Intended Use
- Demonstrate calibrated risk scoring, explainability, and production-style serving patterns.

## Not Intended For
- Real-world underwriting, fraud, or eligibility decisions.

## Notes
- Synthetic data can still encode synthetic bias.
- This is not a fairness certification.
"""
    (version_dir / SETTINGS.model_card_filename).write_text(model_card, encoding="utf-8")

    fairness = _fairness_by_age(y_test, test_prob, X_test["age"].to_numpy())
    write_json(version_dir / SETTINGS.fairness_report_filename, fairness)

    bg = X_train.sample(n=100, random_state=42)
    global_sample = X_train.sample(n=400, random_state=7)
    joblib.dump(bg, version_dir / SETTINGS.shap_background_filename)
    joblib.dump(global_sample, version_dir / SETTINGS.global_shap_sample_filename)

    _copy_to_latest(version_dir, latest_dir)

    # append to registry
    add_model(str(version_dir), metrics)

    logger.info(
        "Training complete",
        extra={"ctx": {
            "chosen": chosen,
            "val_lr_auc": lr_eval["auc"],
            "val_gbc_auc": gbc_eval["auc"],
            "test_auc": test_eval["auc"],
            "test_brier": test_eval["brier"],
            "version_dir": str(version_dir),
            "latest_dir": str(latest_dir),
        }},
    )


if __name__ == "__main__":
    main()
