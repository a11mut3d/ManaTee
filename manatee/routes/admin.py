from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from ..admin_ui import ADMIN_HTML
from ..auth import get_store
from ..config import get_settings
from ..stats import get_stats

router = APIRouter(prefix="/admin")


def _check(request: Request) -> None:
    token = request.headers.get("x-admin-token") or request.cookies.get("manatee_admin")
    if token != get_settings().admin_token:
        raise HTTPException(403, "forbidden")


@router.get("/ui", response_class=HTMLResponse)
async def ui() -> str:
    # HTML публичный (без секретов), все данные — через защищённые API-ручки.
    return ADMIN_HTML


@router.post("/login")
async def login(request: Request) -> dict[str, Any]:
    body = await request.json()
    token = body.get("token", "")
    if token != get_settings().admin_token:
        raise HTTPException(403, "bad token")
    return {"ok": True}


@router.get("/stats")
async def stats(request: Request) -> dict[str, Any]:
    _check(request)
    st = get_stats().snapshot()
    ks = get_store().summary()
    return {
        **st,
        "total_keys": ks["total"],
        "active_keys": ks["active"],
        "revoked_keys": ks["revoked"],
    }


@router.get("/keys")
async def list_keys(request: Request) -> dict[str, Any]:
    _check(request)
    return {"keys": get_store().list_full()}


@router.post("/keys")
async def create_key(request: Request, label: str = "") -> dict[str, Any]:
    _check(request)
    return {"key": get_store().create(label), "label": label}


@router.post("/revoke")
async def revoke_key(request: Request, key: str) -> dict[str, Any]:
    _check(request)
    return {"revoked": get_store().revoke(key)}
