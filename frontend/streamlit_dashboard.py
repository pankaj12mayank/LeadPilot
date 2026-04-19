"""
Streamlit dashboard for safe-captured leads (SQLite).

Run from repository root::

    python -m streamlit run frontend/streamlit_dashboard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import config  # noqa: E402
from database.safe_capture_store import fetch_all_leads, init_safe_capture_db, update_lead_status  # noqa: E402

STATUSES = ("NEW", "CONTACTED", "REPLIED", "CLOSED")


def main() -> None:
    st.set_page_config(page_title="LeadPilot — Safe captures", layout="wide")
    st.title("LeadPilot — Safe manual captures")
    st.caption("Read-only by default; status updates write back to SQLite.")

    config.ensure_data_dirs()
    init_safe_capture_db()

    rows = fetch_all_leads()
    if not rows:
        st.info("No leads yet. Run **capture** from `run.bat capture` or `python -m backend.safe_capture_cli`.")
        st.code(f"DB: {config.SAFE_CAPTURE_DB_PATH}", language="text")
        return

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.subheader("Update status")
    ids = [int(r["id"]) for r in rows]
    pick = st.selectbox("Lead id", options=ids, format_func=lambda i: f"#{i}")
    new_status = st.selectbox("Status", options=STATUSES)
    if st.button("Save status"):
        update_lead_status(int(pick), new_status)
        st.success("Updated.")
        rerun = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
        if callable(rerun):
            rerun()


if __name__ == "__main__":
    main()
