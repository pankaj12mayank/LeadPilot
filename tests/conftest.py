"""Pytest: isolate API meta DB and load FastAPI app once per process."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Must run before importing application modules that read ``config``.
_test_data = Path(tempfile.mkdtemp(prefix="leadpilot-pytest-"))
os.environ["API_META_DB_PATH"] = str(_test_data / "api_meta.db")
os.environ["SECRET_KEY"] = "pytest-secret-not-for-production"
os.environ["CORS_ORIGINS"] = "*"
os.environ["LOG_LEVEL"] = "WARNING"
os.environ["API_ROOT_PATH"] = "/api"

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


def pytest_sessionfinish(session, exitstatus) -> None:  # noqa: ARG001
    """Best-effort cleanup of temp DB directory."""
    try:
        import shutil

        shutil.rmtree(_test_data, ignore_errors=True)
    except OSError:
        pass


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c
