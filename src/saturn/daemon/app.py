from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from saturn.daemon.routes import health


def create_app(workspace: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.workspace = workspace
        yield

    app = FastAPI(title="Saturn", version="0.1.0", lifespan=lifespan)
    app.include_router(health.router, prefix="/api")
    return app
