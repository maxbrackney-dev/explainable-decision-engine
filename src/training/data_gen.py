from __future__ import annotations

import numpy as np
import pandas as pd


FEATURES = [
    "age",
    "income",
    "account_age_days",
    "num_txn_30d",
    "avg_txn_amount_30d",
    "num_chargebacks_180d",
    "device_change_count_30d",
    "geo_distance_from_last_txn_km",
    "is_international",
    "merchant_risk_score",
]


def generate_synthetic_risk_data(n: int = 20000, seed: int = 42) -> pd.DataFrame:
    """
    Synthetic, realistic-ish dataset for "risk scoring".
    This is NOT real banking data.
    """
    rng = np.random.default_rng(seed)

    age = rng.integers(13, 100, size=n)
    income = np.clip(rng.lognormal(mean=10.7, sigma=0.6, size=n), 0, 350000)
    account_age_days = rng.integers(0, 3650 * 3, size=n)

    num_txn_30d = np.clip(rng.negative_binomial(n=10, p=0.35, size=n), 0, 300)
    avg_txn_amount_30d = np.clip(rng.lognormal(mean=3.5, sigma=0.8, size=n), 0, 5000)

    num_chargebacks_180d = np.clip(rng.poisson(lam=0.15, size=n), 0, 10)
    device_change_count_30d = np.clip(rng.poisson(lam=0.5, size=n), 0, 20)

    geo_distance_from_last_txn_km = np.clip(rng.exponential(scale=30, size=n), 0, 20000)
    spikes = rng.random(n) < 0.03
    geo_distance_from_last_txn_km[spikes] += rng.uniform(1000, 8000, size=spikes.sum())

    is_international = (rng.random(n) < 0.08).astype(int)
    merchant_risk_score = np.clip(rng.beta(a=1.5, b=6.0, size=n), 0, 1)
    high_merch = rng.random(n) < 0.05
    merchant_risk_score[high_merch] = np.clip(
        merchant_risk_score[high_merch] + rng.uniform(0.4, 0.8, size=high_merch.sum()), 0, 1
    )

    df = pd.DataFrame(
        {
            "age": age,
            "income": income,
            "account_age_days": account_age_days,
            "num_txn_30d": num_txn_30d,
            "avg_txn_amount_30d": avg_txn_amount_30d,
            "num_chargebacks_180d": num_chargebacks_180d,
            "device_change_count_30d": device_change_count_30d,
            "geo_distance_from_last_txn_km": geo_distance_from_last_txn_km,
            "is_international": is_international,
            "merchant_risk_score": merchant_risk_score,
        }
    )

    # Rules + noise => label
    score = (
        0.015 * (30 - np.clip(df["account_age_days"], 0, 30))
        + 0.8 * df["merchant_risk_score"]
        + 0.35 * (df["num_chargebacks_180d"] > 0).astype(int)
        + 0.08 * df["num_chargebacks_180d"]
        + 0.06 * df["device_change_count_30d"]
        + 0.00022 * np.clip(df["geo_distance_from_last_txn_km"], 0, 8000)
        + 0.25 * df["is_international"]
        + 0.0015 * np.clip(df["num_txn_30d"] - 40, 0, 999)
        + 0.0012 * np.clip(df["avg_txn_amount_30d"] - 200, 0, 9999)
    )

    score -= 0.003 * np.clip(df["age"] - 30, 0, 70)
    score -= 0.0000025 * np.clip(df["income"] - 50000, 0, 300000)
    score -= 0.0002 * np.clip(df["account_age_days"] - 180, 0, 999999)

    noise = rng.normal(0, 0.35, size=n)
    logits = score + noise
    prob = 1 / (1 + np.exp(-logits))

    # prevalence not too high
    high_risk = (prob > 0.55).astype(int)

    df["high_risk"] = high_risk
    return df