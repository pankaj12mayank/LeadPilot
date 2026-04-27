"""
Streamlit dashboard for LeadPilot safe-captured leads (SQLite).

Run from repository root::

    python -m streamlit run frontend/streamlit_dashboard.py
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

try:
    import pandas as pd
except ImportError:  # pragma: no cover — optional until ``pip install -r requirements.txt``
    pd = None  # type: ignore[assignment]

try:
    import streamlit as st
except ImportError:  # pragma: no cover
    st = None  # type: ignore[assignment]

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import config  # noqa: E402
from database.safe_capture_store import fetch_all_leads, init_safe_capture_db, update_lead_status  # noqa: E402
from exports.safe_capture_csv_export import leads_to_export_dataframe  # noqa: E402

STATUSES = ("NEW", "CONTACTED", "REPLIED", "CLOSED")
TIERS = ("HOT", "WARM", "COLD")
TABLE_COLUMNS = [
    "id",
    "captured_at",
    "name",
    "title",
    "company",
    "industry",
    "source_platform",
    "tier",
    "status",
    "score",
    "location",
    "email",
    "website",
    "profile_url",
]


def _filter_dataframe(
    df: "pd.DataFrame",
    *,
    platform: str,
    tier: str,
    status: str,
) -> "pd.DataFrame":
    out = df
    if platform and platform != "All":
        out = out[out["source_platform"].astype(str) == platform]
    if tier and tier != "All":
        out = out[out["tier"].astype(str).str.upper() == tier.upper()]
    if status and status != "All":
        out = out[out["status"].astype(str).str.upper() == status.upper()]
    return out


def main() -> None:
    if st is None or pd is None:
        missing = [name for name, mod in (("pandas", pd), ("streamlit", st)) if mod is None]
        raise SystemExit(
            "LeadPilot safe-capture dashboard requires: "
            + ", ".join(missing)
            + ". From the repo root run: python -m pip install "
            + " ".join(missing)
        )

    st.set_page_config(
        page_title="LeadPilot — Leads",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(
        """
        <style>
            .block-container { padding-top: 1.25rem; padding-bottom: 2rem; max-width: 1200px; }
            div[data-testid="stMetricValue"] { font-size: 1.65rem; }
            h1 { letter-spacing: -0.02em; font-weight: 600; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    config.ensure_data_dirs()
    init_safe_capture_db()

    st.title("LeadPilot")
    st.caption("Safe capture leads · SQLite · filters & export")

    rows = fetch_all_leads()
    if not rows:
        st.info(
            "No leads yet. Start the API with **`run.bat`**, then capture from a terminal: "
            "**`python -m backend.main`** (safe manual capture), or use the in-app capture flows when connected."
        )
        st.code(f"Database: {config.SAFE_CAPTURE_DB_PATH}", language="text")
        st.code(f"CSV mirror: {config.SAFE_CAPTURE_CSV_PATH}", language="text")
        return

    df = pd.DataFrame(rows)
    total = len(df)
    hot_total = int((df["tier"].astype(str).str.upper() == "HOT").sum())

    with st.sidebar:
        st.header("Filters")
        platforms = sorted({str(x) for x in df["source_platform"].dropna().unique() if str(x).strip()})
        platform = st.selectbox("Source platform", ["All"] + platforms, index=0)
        tier = st.selectbox("Tier", ["All"] + list(TIERS), index=0)
        status = st.selectbox("Status", ["All"] + list(STATUSES), index=0)
        st.divider()
        st.caption("Paths")
        st.text(str(config.SAFE_CAPTURE_DB_PATH))
        st.text(str(config.SAFE_CAPTURE_CSV_PATH))

    filtered = _filter_dataframe(df, platform=platform, tier=tier, status=status)
    displayed = len(filtered)
    hot_filtered = int((filtered["tier"].astype(str).str.upper() == "HOT").sum())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total leads", f"{total:,}")
    m2.metric("HOT leads (all)", f"{hot_total:,}")
    m3.metric("Matching filters", f"{displayed:,}")
    m4.metric("HOT in view", f"{hot_filtered:,}")

    st.divider()

    exp_left, exp_right = st.columns((1.1, 1))
    with exp_left:
        st.subheader("Recent captures")
        recent = df.sort_values("captured_at", ascending=False).head(8)
        show_cols = [c for c in TABLE_COLUMNS if c in recent.columns]
        st.dataframe(
            recent[show_cols],
            use_container_width=True,
            hide_index=True,
            height=320,
        )
    with exp_right:
        st.subheader("Update status")
        ids = [int(x) for x in filtered["id"].tolist()] if len(filtered) else []
        if not ids:
            st.warning("No leads match the current filters. Clear a filter to pick an id.")
        else:
            pick = st.selectbox("Lead id", options=ids, format_func=lambda i: f"#{i}")
            new_status = st.selectbox("New status", options=STATUSES, key="status_pick")
            if st.button("Save status", type="primary"):
                update_lead_status(int(pick), new_status)
                st.success("Status saved.")
                rerun = getattr(st, "rerun", None) or getattr(st, "experimental_rerun", None)
                if callable(rerun):
                    rerun()

    st.divider()
    st.subheader("All leads (filtered)")

    export_df = leads_to_export_dataframe(filtered.to_dict("records"))
    buf = io.StringIO()
    export_df.to_csv(buf, index=False)
    csv_bytes = buf.getvalue().encode("utf-8")

    dl, _spacer = st.columns([1, 3])
    with dl:
        st.download_button(
            label="Export filtered CSV",
            data=csv_bytes,
            file_name="leadpilot_safe_leads_export.csv",
            mime="text/csv",
            use_container_width=True,
        )

    show_main = [c for c in TABLE_COLUMNS if c in filtered.columns]
    if "enrichment_json" in filtered.columns:
        show_main = [c for c in show_main if c != "enrichment_json"]
    st.dataframe(
        filtered[show_main],
        use_container_width=True,
        hide_index=True,
        height=420,
    )


if __name__ == "__main__":
    main()
