"""
ASGI entry for Uvicorn from the repository root::

    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Re-exports the FastAPI application built in ``backend.app.main``.
"""

from __future__ import annotations

from backend.app.main import app

__all__ = ["app"]
