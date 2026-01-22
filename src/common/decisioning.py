from __future__ import annotations

from typing import Any, Dict, List
from src.common.settings import SETTINGS


def expected_loss_usd(prob: float, payload: Dict[str, Any]) -> float:
    amt = float(payload.get("avg_txn_amount_30d", 0.0))
    loss = SETTINGS.loss_per_event_usd + SETTINGS.loss_amt_multiplier * amt
    return float(prob) * float(loss)


def decision_from_prob(prob: float) -> str:
    if prob >= SETTINGS.decline_threshold:
        return "decline"
    if prob >= SETTINGS.review_threshold:
        return "review"
    if prob >= SETTINGS.stepup_threshold:
        return "step_up"
    return "approve"


def rule_reason_codes(payload: Dict[str, Any]) -> List[str]:
    codes: List[str] = []
    if float(payload.get("account_age_days", 0)) < 30:
        codes.append("rule:new_account")
    if int(payload.get("num_chargebacks_180d", 0)) > 0:
        codes.append("rule:prior_chargeback")
    if float(payload.get("merchant_risk_score", 0)) > 0.75:
        codes.append("rule:high_merchant_risk")
    if bool(payload.get("is_international", False)) and float(payload.get("geo_distance_from_last_txn_km", 0)) > 1000:
        codes.append("rule:intl_far_distance")
    if int(payload.get("device_change_count_30d", 0)) >= 3:
        codes.append("rule:frequent_device_changes")
    return codes[:6]


def merge_reason_codes(shap_top_features: List[Dict[str, Any]] | None, payload: Dict[str, Any]) -> List[str]:
    codes: List[str] = []
    if shap_top_features:
        # top feature names become reason codes
        for it in shap_top_features[:4]:
            f = it.get("feature")
            if f:
                codes.append(f"shap:{f}")
    # fallback rules
    for c in rule_reason_codes(payload):
        if c not in codes:
            codes.append(c)
    return codes[:8]


def calibration_snapshot(metrics: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "calibration_method": metrics.get("calibration", "unknown"),
        "training_date": metrics.get("training_date", "unknown"),
        "auc_test": metrics.get("test", {}).get("auc"),
        "brier_test": metrics.get("test", {}).get("brier"),
        "event_definition": SETTINGS.event_definition,
    }
