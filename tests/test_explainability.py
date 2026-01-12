from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_explain_returns_top_features_non_empty():
    payload = {
        "age": 19,
        "income": 12000,
        "account_age_days": 12,
        "num_txn_30d": 55,
        "avg_txn_amount_30d": 280.0,
        "num_chargebacks_180d": 2,
        "device_change_count_30d": 4,
        "geo_distance_from_last_txn_km": 2200.0,
        "is_international": True,
        "merchant_risk_score": 0.92,
    }
    r = client.post("/v1/explain", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "explanation" in data
    exp = data["explanation"]
    assert "top_features" in exp
    assert isinstance(exp["top_features"], list)
    assert len(exp["top_features"]) > 0
    first = exp["top_features"][0]
    assert set(first.keys()) == {"feature", "shap_value", "direction", "contribution_percent"}