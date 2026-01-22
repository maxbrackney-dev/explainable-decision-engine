from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, Union

from fastapi import Header, HTTPException

from src.common.settings import SETTINGS


@dataclass(frozen=True)
class Principal:
    api_key: str
    role: str  # admin | analyst | viewer
    rpm: int
    read_only: bool
    expires_at: Optional[str]  # ISO8601 Z string

    def to_dict(self) -> Dict[str, Any]:
        return {
            "api_key_suffix": self.api_key[-4:] if self.api_key else "",
            "role": self.role,
            "rpm": self.rpm,
            "read_only": self.read_only,
            "expires_at": self.expires_at,
        }


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_expires(expires_at: Optional[str]) -> Optional[datetime]:
    if not expires_at:
        return None
    s = str(expires_at).strip()
    if not s:
        return None
    # accept ISO with Z
    if s.endswith("Z"):
        s = s.replace("Z", "+00:00")
    return datetime.fromisoformat(s).astimezone(timezone.utc)


def _load_key_map() -> Dict[str, Dict[str, Any]]:
    """
    Returns a dict:
      api_key -> {rpm, role, read_only, expires_at}
    """
    out: Dict[str, Dict[str, Any]] = {}

    # Single-key mode (admin, no expiry)
    if SETTINGS.demo_api_key:
        out[SETTINGS.demo_api_key] = {
            "rpm": SETTINGS.default_rpm,
            "role": "admin",
            "read_only": False,
            "expires_at": None,
        }

    # Multi-key mode
    if SETTINGS.demo_api_keys_json:
        try:
            raw = json.loads(SETTINGS.demo_api_keys_json)
            if isinstance(raw, dict):
                for k, v in raw.items():
                    if isinstance(v, int):
                        # Backwards compatible: {"key": 60}
                        out[str(k)] = {"rpm": int(v), "role": "analyst", "read_only": False, "expires_at": None}
                    elif isinstance(v, dict):
                        out[str(k)] = {
                            "rpm": int(v.get("rpm", SETTINGS.default_rpm)),
                            "role": str(v.get("role", "analyst")),
                            "read_only": bool(v.get("read_only", False)),
                            "expires_at": v.get("expires_at", None),
                        }
        except Exception:
            # If malformed, ignore it (but keep single-key if present)
            pass

    return out


def require_principal(x_api_key: Optional[str] = Header(default=None)) -> Principal:
    key_map = _load_key_map()

    if not key_map:
        raise HTTPException(
            status_code=500,
            detail={"error": "server_misconfigured", "message": "No DEMO_API_KEY or DEMO_API_KEYS_JSON set"},
        )

    if not x_api_key:
        raise HTTPException(status_code=401, detail={"error": "unauthorized", "message": "Missing X-API-Key"})

    if x_api_key not in key_map:
        raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "Invalid API key"})

    meta = key_map[x_api_key]
    expires_at = meta.get("expires_at")
    exp_dt = _parse_expires(expires_at)

    if exp_dt and _now_utc() >= exp_dt:
        raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "API key expired"})

    role = str(meta.get("role", "analyst")).lower()
    if role not in {"admin", "analyst", "viewer"}:
        role = "analyst"

    rpm = int(meta.get("rpm", SETTINGS.default_rpm))
    read_only = bool(meta.get("read_only", False))

    return Principal(
        api_key=x_api_key,
        role=role,
        rpm=rpm,
        read_only=read_only,
        expires_at=meta.get("expires_at"),
    )


def require_admin(principal: Principal) -> None:
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "Admin role required"})


def require_write(principal: Principal) -> None:
    if principal.read_only:
        raise HTTPException(status_code=403, detail={"error": "forbidden", "message": "Read-only key: write actions blocked"})
