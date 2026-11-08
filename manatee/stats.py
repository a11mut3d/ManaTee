from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from .config import get_settings


class Stats:
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text("utf-8"))
                if "started_at" in self._data:
                    return
            except Exception:
                pass
        self._data = {
            "started_at": time.time(),
            "requests": 0,
            "injections_model": 0,
            "injections_postprocess": 0,
            "languages": {},
            "endpoints": {},
        }
        self._flush()

    def _flush(self) -> None:
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False), "utf-8"
        )

    def inc_request(self, endpoint: str) -> None:
        with self._lock:
            self._data["requests"] = int(self._data.get("requests", 0)) + 1
            eps = self._data.setdefault("endpoints", {})
            eps[endpoint] = int(eps.get(endpoint, 0)) + 1
            self._flush()

    def inc_injection(self, language: str, source: str) -> None:
        lang = (language or "unknown").strip().lower() or "unknown"
        with self._lock:
            key = "injections_model" if source == "model" else "injections_postprocess"
            self._data[key] = int(self._data.get(key, 0)) + 1
            langs = self._data.setdefault("languages", {})
            langs[lang] = int(langs.get(lang, 0)) + 1
            self._flush()

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            d = json.loads(json.dumps(self._data))
        d["uptime"] = self._fmt_uptime(time.time() - d.get("started_at", time.time()))
        return d

    @staticmethod
    def _fmt_uptime(sec: float) -> str:
        sec = int(sec)
        h, r = divmod(sec, 3600)
        m, s = divmod(r, 60)
        if h:
            return f"{h}h {m}m {s}s"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"


_stats: Stats | None = None


def get_stats() -> Stats:
    global _stats
    if _stats is None:
        s = get_settings()
        p = Path(s.log_file).with_suffix(".stats.json")
        _stats = Stats(str(p))
    return _stats
