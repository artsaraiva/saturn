from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from saturn.daemon.routes import contradictions, facts, health, ingest, query, revisions


def create_app(workspace: Path | None = None) -> FastAPI:
    app = FastAPI(title="Saturn", version="0.1.0")
    app.state.workspace = workspace
    app.include_router(health.router, prefix="/api")
    app.include_router(facts.router, prefix="/api")
    app.include_router(query.router, prefix="/api")
    app.include_router(contradictions.router, prefix="/api")
    app.include_router(revisions.router, prefix="/api")
    app.include_router(ingest.router, prefix="/api")
    return app
