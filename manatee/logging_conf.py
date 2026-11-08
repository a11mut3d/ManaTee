from __future__ import annotations

import json
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any

from .config import get_settings

_lock = threading.Lock()
_path: Path | None = None


def _log_path() -> Path:
    global _path
    if _path is None:
        p = Path(get_settings().log_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        _path = p
    return _path


def log_event(event: dict[str, Any]) -> None:
    event = {"ts": time.time(), **event}
    line = json.dumps(event, ensure_ascii=False)
    with _lock:
        with _log_path().open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def setup_logging() -> None:
    logging.basicConfig(
        level=get_settings().log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
        stream=sys.stdout,
    )
