from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

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
    KernelExplainer w/ predict_fn that always returns 1D (n,) and uses DataFrame columns
    to keep sklearn pipelines happy.
    """
    def predict_fn(X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(1, -1)
        X_df = pd.DataFrame(X, columns=feature_list)
        # return 1D vector (n,)
        return np.asarray(model.predict_proba(X_df)[:, 1], dtype=float)

    bg = background_df[feature_list].to_numpy(dtype=float)
    if bg.ndim == 1:
        bg = bg.reshape(1, -1)

    return shap.KernelExplainer(predict_fn, bg)


def explain_local(
    explainer: shap.KernelExplainer,
    model: Any,
    x_row_df: pd.DataFrame,
    feature_list: List[str],
    top_k: int = 6,
) -> LocalExplanation:
    pred = float(model.predict_proba(x_row_df)[:, 1][0])

    x = x_row_df[feature_list].to_numpy(dtype=float)
    if x.ndim == 1:
        x = x.reshape(1, -1)

    # keep nsamples modest; stabilize KernelExplainer
    shap_vals = explainer.shap_values(x, nsamples=200, l1_reg="num_features(10)")
    shap_vals = np.asarray(shap_vals)

    # normalize shapes
    if shap_vals.ndim == 3:
        shap_vals = shap_vals[0]
    if shap_vals.ndim == 1:
        shap_vals = shap_vals.reshape(1, -1)

    shap_row = shap_vals[0].reshape(-1)

    baseline = float(np.asarray(explainer.expected_value).reshape(-1)[0])
    baseline = float(np.clip(baseline, 0.0, 1.0))

    abs_sum = float(np.sum(np.abs(shap_row)) + 1e-12)
    items: List[Dict] = []
    for f, v in zip(feature_list, shap_row):
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
    return LocalExplanation(baseline, pred, items[:top_k])


def _fallback_global_importance(
    model: Any,
    sample_df: pd.DataFrame,
    feature_list: List[str],
    n_permute: int = 2,
) -> List[Dict]:
    """
    Fast global importance fallback: permutation drop in predicted probability variance proxy.
    Not SHAP, but stable and still meaningful for "global importance".
    """
    X = sample_df[feature_list].copy()
    base = np.asarray(model.predict_proba(X)[:, 1], dtype=float)

    rng = np.random.default_rng(42)
    importances = []

    for f in feature_list:
        drops = []
        for _ in range(n_permute):
            Xp = X.copy()
            Xp[f] = rng.permutation(Xp[f].values)
            p = np.asarray(model.predict_proba(Xp)[:, 1], dtype=float)
            drops.append(float(np.mean(np.abs(p - base))))
        importances.append((f, float(np.mean(drops))))

    vals = np.array([v for _, v in importances], dtype=float)
    total = float(vals.sum() + 1e-12)

    items = [
        {
            "feature": f,
            "mean_abs_shap": v,  # keep schema compatibility
            "importance_percent": float((v / total) * 100.0),
            "method": "fallback_permutation",
        }
        for f, v in importances
    ]
    items.sort(key=lambda d: d["mean_abs_shap"], reverse=True)
    return items


def explain_global(
    explainer: shap.KernelExplainer,
    model: Any,
    sample_df: pd.DataFrame,
    feature_list: List[str],
    max_rows: int = 80,
) -> Tuple[List[Dict], str]:
    """
    Returns (items, method) where method is "shap_kernel" or "fallback_permutation".
    """
    sample = sample_df
    if len(sample) > max_rows:
        sample = sample.sample(n=max_rows, random_state=42)

    X = sample[feature_list].to_numpy(dtype=float)
    if X.ndim == 1:
        X = X.reshape(1, -1)

    try:
        # Use modest nsamples to avoid KernelExplainer internal overflow bugs
        shap_vals = explainer.shap_values(X, nsamples=200, l1_reg="num_features(10)")
        shap_vals = np.asarray(shap_vals)

        if shap_vals.ndim == 3:
            shap_vals = shap_vals[0]
        if shap_vals.ndim == 1:
            shap_vals = shap_vals.reshape(1, -1)

        mean_abs = np.mean(np.abs(shap_vals), axis=0).reshape(-1)
        total = float(mean_abs.sum() + 1e-12)

        items = []
        for f, v in zip(feature_list, mean_abs):
            v_f = float(v)
            items.append(
                {
                    "feature": f,
                    "mean_abs_shap": v_f,
                    "importance_percent": float((v_f / total) * 100.0),
                    "method": "shap_kernel",
                }
            )
        items.sort(key=lambda d: d["mean_abs_shap"], reverse=True)
        return items, "shap_kernel"

    except Exception:
        # Robust fallback
        return _fallback_global_importance(model, sample, feature_list), "fallback_permutation"
