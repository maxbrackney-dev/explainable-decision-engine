from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any, Dict, Optional


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base: Dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "time": int(time.time() * 1000),
        }
        if hasattr(record, "ctx") and isinstance(record.ctx, dict):
            base.update(record.ctx)
        if record.exc_info:
            base["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(base, ensure_ascii=False)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    h = logging.StreamHandler(sys.stdout)
    h.setFormatter(JsonFormatter())
    logger.addHandler(h)
    logger.propagate = False
    return logger


class LogTimer:
    def __init__(self) -> None:
        self.start = time.perf_counter()

    def ms(self) -> int:
        return int((time.perf_counter() - self.start) * 1000)


def with_ctx(logger: logging.Logger, ctx: Optional[dict] = None) -> logging.LoggerAdapter:
    return logging.LoggerAdapter(logger, extra={"ctx": ctx or {}})
