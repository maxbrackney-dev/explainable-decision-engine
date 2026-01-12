from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import numpy as np
import pandas as pd
import shap


@dataclass(frozen=True)
class LocalExplanation:
    baseline_probability: float
    predicted_probability: float
    top_features: List[Dict]


def _direction(v: float) -> str:
    return "increases_risk" if v >= 0 else "decreases_risk"


def build_explainer(model: Any, background_df: pd.DataFrame, feature_list: List[str]) -> shap.KernelExplainer:
    """
    We intentionally use KernelExplainer with a predict_fn that converts numpy -> DataFrame
    with the training feature names. This avoids sklearn warnings about missing feature names.

    This is slower than TreeExplainer but very stable for demos and eliminates the warning.
    """
    def predict_fn(X: np.ndarray) -> np.ndarray:
        X_df = pd.DataFrame(X, columns=feature_list)
        return model.predict_proba(X_df)[:, 1]

    bg_np = background_df[feature_list].to_numpy(dtype=float)
    return shap.KernelExplainer(predict_fn, bg_np)


def explain_local(
    explainer: shap.KernelExplainer,
    model: Any,
    x_row_df: pd.DataFrame,
    feature_list: List[str],
    top_k: int,
) -> LocalExplanation:
    """
    x_row_df must be a single-row DataFrame with the correct columns.
    """
    # Predict using DataFrame (preserves names)
    pred = float(model.predict_proba(x_row_df)[:, 1][0])

    x_np = x_row_df[feature_list].to_numpy(dtype=float)

    # Fix SHAP deprecation warning by explicitly setting new behavior
    shap_vals = np.array(
        explainer.shap_values(x_np, l1_reg="num_features(10)")[0],
        dtype=float,
    ).reshape(-1)

    baseline = float(np.array(explainer.expected_value).reshape(-1)[0])
    baseline = float(np.clip(baseline, 0.0, 1.0))

    abs_sum = float(np.sum(np.abs(shap_vals)) + 1e-12)

    items: List[Dict] = []
    for f, v in zip(feature_list, shap_vals):
        v_f = float(v)
        items.append(
            {
                "feature": f,
                "shap_value": v_f,
                "direction": _direction(v_f),
                "contribution_percent": float((abs(v_f) / abs_sum) * 100.0),
            }
        )

    items.sort(key=lambda d: abs(d["shap_value"]), reverse=True)
    top = items[:top_k]

    return LocalExplanation(
        baseline_probability=baseline,
        predicted_probability=pred,
        top_features=top,
    )


def explain_global(
    explainer: shap.KernelExplainer,
    sample_df: pd.DataFrame,
    feature_list: List[str],
    max_rows: int = 500,
) -> List[Dict]:
    sample = sample_df
    if len(sample) > max_rows:
        sample = sample.sample(n=max_rows, random_state=42)

    X_np = sample[feature_list].to_numpy(dtype=float)

    shap_vals = np.array(
        explainer.shap_values(X_np, l1_reg="num_features(10)")[0],
        dtype=float,
    )

    shap_vals = np.array(shap_vals, dtype=float)
    if shap_vals.ndim == 3:
        shap_vals = shap_vals[0]

    mean_abs = np.mean(np.abs(shap_vals), axis=0)
    total = float(np.sum(mean_abs) + 1e-12)

    items: List[Dict] = []
    for f, v in zip(feature_list, mean_abs):
        v_f = float(v)
        items.append(
            {
                "feature": f,
                "mean_abs_shap": v_f,
                "importance_percent": float((v_f / total) * 100.0),
            }
        )

    items.sort(key=lambda d: d["mean_abs_shap"], reverse=True)
    return items