from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)


def test_health():
    r = client.get("/v1/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "request_id" in data


def test_score_returns_stable_shape():
    payload = {
        "age": 34,
        "income": 78000,
        "account_age_days": 400,
        "num_txn_30d": 22,
        "avg_txn_amount_30d": 55.25,
        "num_chargebacks_180d": 0,
        "device_change_count_30d": 1,
        "geo_distance_from_last_txn_km": 10.0,
        "is_international": False,
        "merchant_risk_score": 0.15,
    }
    r = client.post("/v1/score", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "risk_probability" in data
    assert "risk_label" in data
    assert "warnings" in data
    assert isinstance(data["warnings"], list)
    assert data["risk_label"] in ["high_risk", "low_risk"]
    assert 0.0 <= float(data["risk_probability"]) <= 1.0


def test_batch_score_smoke():
    payload = {
        "items": [
            {
                "age": 34,
                "income": 78000,
                "account_age_days": 400,
                "num_txn_30d": 22,
                "avg_txn_amount_30d": 55.25,
                "num_chargebacks_180d": 0,
                "device_change_count_30d": 1,
                "geo_distance_from_last_txn_km": 10.0,
                "is_international": False,
                "merchant_risk_score": 0.15,
            }
        ]
    }
    r = client.post("/v1/batch-score", json=payload)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["count"] == 1
    assert isinstance(data["results"], list)
    assert data["results"][0]["risk_label"] in ["high_risk", "low_risk"]