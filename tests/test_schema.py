import pytest
from pydantic import ValidationError
from src.common.schema import RiskRequest


def test_schema_rejects_unknown_fields():
    payload = {
        "age": 30,
        "income": 50000,
        "account_age_days": 100,
        "num_txn_30d": 10,
        "avg_txn_amount_30d": 20.0,
        "num_chargebacks_180d": 0,
        "device_change_count_30d": 1,
        "geo_distance_from_last_txn_km": 1.0,
        "is_international": False,
        "merchant_risk_score": 0.2,
        "lol_nope": 123,
    }
    with pytest.raises(ValidationError):
        RiskRequest(**payload)


def test_schema_rejects_bad_ranges():
    payload = {
        "age": 5,  # too low
        "income": 50000,
        "account_age_days": 100,
        "num_txn_30d": 10,
        "avg_txn_amount_30d": 20.0,
        "num_chargebacks_180d": 0,
        "device_change_count_30d": 1,
        "geo_distance_from_last_txn_km": 1.0,
        "is_international": False,
        "merchant_risk_score": 0.2,
    }
    with pytest.raises(ValidationError):
        RiskRequest(**payload)