"""
Safe manual capture CLI (Playwright). Ensures repo root is on ``sys.path`` when run as
``python backend\\main.py`` or ``python -m backend.main`` from the project root.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.safe_capture_cli import main  # noqa: E402

if __name__ == "__main__":
    main()
