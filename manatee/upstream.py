from __future__ import annotations

import httpx

from .config import get_settings


def http_client() -> httpx.AsyncClient:
    s = get_settings()
    return httpx.AsyncClient(timeout=httpx.Timeout(s.upstream_timeout, connect=10.0))


def chat_url() -> str:
    return get_settings().ollama_url.rstrip("/") + "/v1/chat/completions"
