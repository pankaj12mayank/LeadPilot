"""Application package (FastAPI)."""

import sys
from pathlib import Path

# Ensure repo root (parent of backend/) is on sys.path so ``import config``
# works everywhere — whether running from repo root or from backend/ folder.
_REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
