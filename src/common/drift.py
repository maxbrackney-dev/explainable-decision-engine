from __future__ import annotations

from typing import Dict, Any, List
import math
from src.common.redis_client import get_redis
from src.common.settings import SETTINGS


def _welford_update(n: int, mean: float, m2: float, x: float):
    n2 = n + 1
    delta = x - mean
    mean2 = mean + delta / n2
    delta2 = x - mean2
    m2_2 = m2 + delta * delta2
    return n2, mean2, m2_2


def update_drift_stats(api_key: str, payload: Dict[str, Any], feature_list: List[str]) -> None:
    r = get_redis()
    if r is None:
        return

    prefix = f"drift:{api_key}"
    for f in feature_list:
        x = payload.get(f)
        if x is None:
            continue
        if isinstance(x, bool):
            x = 1.0 if x else 0.0
        x = float(x)

        # stored as hash: n, mean, m2
        hkey = f"{prefix}:{f}"
        data = r.hgetall(hkey) or {}
        n = int(data.get("n", "0"))
        mean = float(data.get("mean", "0"))
        m2 = float(data.get("m2", "0"))

        n2, mean2, m22 = _welford_update(n, mean, m2, x)
        r.hset(hkey, mapping={"n": str(n2), "mean": str(mean2), "m2": str(m22)})
        r.expire(hkey, 60 * 60 * 24 * 14)  # 14 days


def drift_summary(api_key: str, train_means: Dict[str, float], train_stds: Dict[str, float], feature_list: List[str]) -> Dict[str, Any]:
    r = get_redis()
    out = {"api_key": api_key, "features": [], "threshold": SETTINGS.drift_z_threshold}
    if r is None:
        out["status"] = "redis_unavailable"
        return out

    prefix = f"drift:{api_key}"
    for f in feature_list:
        hkey = f"{prefix}:{f}"
        data = r.hgetall(hkey) or {}
        n = int(data.get("n", "0"))
        mean = float(data.get("mean", "0"))
        m2 = float(data.get("m2", "0"))
        var = (m2 / (n - 1)) if n > 1 else 0.0
        std = math.sqrt(var) if var > 0 else 0.0

        tmu = float(train_means.get(f, 0.0))
        tsd = float(train_stds.get(f, 1.0)) if float(train_stds.get(f, 1.0)) > 1e-12 else 1.0
        z = (mean - tmu) / tsd

        out["features"].append({
            "feature": f,
            "n": n,
            "mean": mean,
            "std": std,
            "train_mean": tmu,
            "train_std": float(train_stds.get(f, 0.0)),
            "z_delta": z,
            "drifted": abs(z) >= SETTINGS.drift_z_threshold and n >= 50,
        })
    return out


def drift_warnings(api_key: str, train_means: Dict[str, float], train_stds: Dict[str, float], feature_list: List[str]) -> List[str]:
    s = drift_summary(api_key, train_means, train_stds, feature_list)
    warnings: List[str] = []
    for it in s.get("features", []):
        if it.get("drifted"):
            warnings.append(f"drift_warning:{it['feature']}:z_delta={it['z_delta']:.2f} (threshold={SETTINGS.drift_z_threshold})")
    return warnings
