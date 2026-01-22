from __future__ import annotations

import time
from fastapi import HTTPException

from src.common.redis_client import get_redis
from src.common.auth import Principal


def check_rate_limit(principal: Principal) -> None:
    """
    Redis-backed fixed-window rate limiter:
      key: rl:{api_key}:{window_epoch_minute}
      INCR + EXPIRE
    """
    r = get_redis()
    if r is None:
        # If Redis isn't available, fail open (demo-friendly).
        return

    rpm = max(1, int(principal.rpm))
    window = int(time.time() // 60)
    key = f"rl:{principal.api_key}:{window}"
    n = r.incr(key)
    if n == 1:
        r.expire(key, 120)
    if n > rpm:
        raise HTTPException(
            status_code=429,
            detail={"error": "rate_limited", "message": f"Exceeded {rpm} rpm", "retry_after_seconds": 10},
            headers={"Retry-After": "10"},
        )
