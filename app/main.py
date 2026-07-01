"""
ASGI entry for Uvicorn from the repository root::

    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Re-exports the FastAPI application built in ``backend.app.main``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure repo root is on sys.path so ``import config`` works
# inside ``backend.app.main`` regardless of CWD or PYTHONPATH.
_REPO_ROOT = str(Path(__file__).resolve().parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from backend.app.main import app

__all__ = ["app"]
