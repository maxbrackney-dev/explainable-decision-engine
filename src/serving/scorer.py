from __future__ import annotations

from typing import Dict, List

from src.common.utils import normalize_features_ordered, z_score_warnings


def predict_probability(model, payload: Dict, feature_list: List[str]) -> float:
    X = normalize_features_ordered(payload, feature_list)
    return float(model.predict_proba(X)[:, 1][0])


def ood_warnings(payload: Dict, means: Dict[str, float], stds: Dict[str, float], z_threshold: float) -> List[str]:
    x_num = {k: (1.0 if payload[k] is True else 0.0) if isinstance(payload[k], bool) else float(payload[k]) for k in payload.keys()}
    return z_score_warnings(x_num, means, stds, z_threshold)
