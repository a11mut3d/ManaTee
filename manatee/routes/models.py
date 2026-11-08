from __future__ import annotations

from fastapi import APIRouter

from ..config import get_settings

router = APIRouter()

_FAKE_IDS = ["gpt-5-codex", "gpt-4.1", "gpt-4o", "gpt-4o-mini", "o4-mini"]


@router.get("/v1/models")
async def list_models() -> dict:
    s = get_settings()
    data = [{"id": s.default_model, "object": "model", "created": 0, "owned_by": "manatee"}]
    data += [
        {"id": mid, "object": "model", "created": 0, "owned_by": "manatee"}
        for mid in _FAKE_IDS
    ]
    return {"object": "list", "data": data}
