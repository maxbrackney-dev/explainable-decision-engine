from __future__ import annotations

from typing import Dict, List

from src.common.settings import SETTINGS
from src.common.utils import normalize_features_ordered, z_score_warnings


def predict_probability(model, payload: Dict, feature_list: List[str]) -> float:
    # Use DataFrame with feature names to match training and avoid sklearn warnings.
    X = normalize_features_ordered(payload, feature_list)
    return float(model.predict_proba(X)[:, 1][0])


def compute_warnings(payload: Dict, means: Dict[str, float], stds: Dict[str, float]) -> List[str]:
    # Convert bool -> numeric so stats apply, avoid PII, keep deterministic.
    x_num = {
        k: (1.0 if payload[k] is True else 0.0) if isinstance(payload[k], bool) else float(payload[k])
        for k in payload.keys()
    }
    return z_score_warnings(x_num, means, stds, SETTINGS.ood_z_threshold)


def label_from_threshold(prob: float, threshold: float) -> str:
    return "high_risk" if prob >= threshold else "low_risk"