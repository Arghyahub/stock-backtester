"""Vercel serverless entrypoint for the backend service."""

import os

from fastapi import Request

os.chdir(os.path.dirname(os.path.dirname(__file__)))

from app.main import app  # noqa: E402


@app.middleware("http")
async def remove_service_prefix(request: Request, call_next):
    """Allow the backend to receive either its direct or rewritten service path."""
    prefix = "/api/backend"
    path = request.scope["path"]
    if path == prefix or path.startswith(f"{prefix}/"):
        request.scope["path"] = path[len(prefix):] or "/"
    return await call_next(request)
