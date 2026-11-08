from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .logging_conf import setup_logging
from .routes import admin, chat, models, responses


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(
        title="ManaTee — untrusted LLM proxy PoC",
        docs_url=None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(chat.router)
    app.include_router(responses.router)
    app.include_router(models.router)
    app.include_router(admin.router)

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok", "service": "manatee"}

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": "manatee"}

    return app


app = create_app()
