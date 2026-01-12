from __future__ import annotations

from typing import Any, Dict
import json

from src.common.settings import SETTINGS
from src.common.logging import get_logger

logger = get_logger("metrics_queue")

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not SETTINGS.redis_url:
        return None
    try:
        import redis  # type: ignore

        _client = redis.Redis.from_url(SETTINGS.redis_url, decode_responses=True)
        return _client
    except Exception as e:
        logger.info("redis_unavailable", extra={"ctx": {"err": str(e)}})
        return None


def emit_metric(event: Dict[str, Any]) -> None:
    """
    Optional metrics queue. Keep payload non-PII.
    """
    client = _get_client()
    if client is None:
        return
    try:
        client.lpush("decision_engine:metrics", json.dumps(event))
        client.ltrim("decision_engine:metrics", 0, 2000)
    except Exception as e:
        logger.info("redis_emit_failed", extra={"ctx": {"err": str(e)}})