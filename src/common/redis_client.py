from __future__ import annotations

from typing import Optional
from src.common.settings import SETTINGS

_client = None


def get_redis():
    global _client
    if _client is not None:
        return _client
    if not SETTINGS.redis_url:
        return None
    try:
        import redis  # type: ignore
        _client = redis.Redis.from_url(SETTINGS.redis_url, decode_responses=True)
        return _client
    except Exception:
        return None
