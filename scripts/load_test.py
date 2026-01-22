from __future__ import annotations

import time
import statistics
import httpx
import os
import random

BASE = os.environ.get("LOADTEST_BASE_URL", "http://127.0.0.1:8000")
API_KEY = os.environ.get("DEMO_API_KEY", "demo_key")

def sample_payload():
    return {
        "age": random.randint(18, 70),
        "income": max(0, random.gauss(80000, 25000)),
        "account_age_days": random.randint(0, 2000),
        "num_txn_30d": random.randint(0, 80),
        "avg_txn_amount_30d": max(0, random.gauss(120, 60)),
        "num_chargebacks_180d": random.randint(0, 2),
        "device_change_count_30d": random.randint(0, 4),
        "geo_distance_from_last_txn_km": max(0, random.gauss(25, 40)),
        "is_international": random.random() < 0.08,
        "merchant_risk_score": min(1.0, max(0.0, random.random())),
    }

def main():
    n = int(os.environ.get("LOADTEST_N", "200"))
    url = f"{BASE}/v1/score"
    times = []
    ok = 0

    with httpx.Client(timeout=10.0) as client:
        # warmup
        for _ in range(5):
            client.post(url, headers={"X-API-Key": API_KEY}, json=sample_payload())

        start = time.perf_counter()
        for _ in range(n):
            t0 = time.perf_counter()
            r = client.post(url, headers={"X-API-Key": API_KEY}, json=sample_payload())
            dt = (time.perf_counter() - t0) * 1000
            times.append(dt)
            if r.status_code == 200:
                ok += 1

        total = time.perf_counter() - start

    times_sorted = sorted(times)
    p50 = times_sorted[int(0.50 * (len(times_sorted)-1))]
    p95 = times_sorted[int(0.95 * (len(times_sorted)-1))]
    rps = n / total

    print(f"requests={n} ok={ok} total_s={total:.2f} rps={rps:.2f}")
    print(f"latency_ms p50={p50:.2f} p95={p95:.2f} mean={statistics.mean(times):.2f}")

if __name__ == "__main__":
    main()
