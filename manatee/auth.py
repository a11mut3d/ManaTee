from __future__ import annotations

import json
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from fastapi import HTTPException, Request

from .config import get_settings


class KeyStore:
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._data: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text("utf-8"))
                return
            except Exception:
                pass
        self._data = {}
        self._flush()

    def _flush(self) -> None:
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False), "utf-8"
        )

    def create(self, label: str = "") -> str:
        with self._lock:
            key = "sk-" + secrets.token_urlsafe(24)
            self._data[key] = {
                "label": label,
                "created": time.time(),
                "active": True,
                "requests": 0,
            }
            self._flush()
            return key

    def validate(self, key: str) -> dict[str, Any] | None:
        rec = self._data.get(key)
        return rec if rec and rec.get("active") else None

    def record_use(self, key: str) -> None:
        rec = self._data.get(key)
        if rec:
            rec["requests"] = int(rec.get("requests", 0)) + 1

    def revoke(self, key: str) -> bool:
        with self._lock:
            rec = self._data.get(key)
            if not rec:
                return False
            rec["active"] = False
            self._flush()
            return True

    def list_masked(self) -> list[dict[str, Any]]:
        out = []
        for k, v in self._data.items():
            out.append({"key": k[:6] + "…" + k[-4:], **v})
        return out

    def list_full(self) -> list[dict[str, Any]]:
        return [{"key": k, **v} for k, v in self._data.items()]

    def summary(self) -> dict[str, int]:
        total = len(self._data)
        active = sum(1 for v in self._data.values() if v.get("active"))
        return {"total": total, "active": active, "revoked": total - active}


_store: KeyStore | None = None


def get_store() -> KeyStore:
    global _store
    if _store is None:
        _store = KeyStore(get_settings().keys_file)
    return _store


def _extract_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("x-api-key", "").strip()


async def require_key(request: Request) -> str:
    key = _extract_key(request)
    if not key or get_store().validate(key) is None:
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": "invalid api key",
                    "type": "invalid_request_error",
                    "code": "invalid_api_key",
                }
            },
        )
    get_store().record_use(key)
    return key
