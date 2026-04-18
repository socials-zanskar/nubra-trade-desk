from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nubra_dash.bootstrap import load_local_env
from nubra_dash.models import VolumeSignal
from nubra_dash.ui.runtime import load_snapshot_with_feedback, render_refresh_bar
from nubra_dash.ui.shell import get_runtime_app_config, get_selected_symbols, render_sidebar
from nubra_dash.ui.theme import inject_css
from nubra_dash.ui.widgets import callout, dataframe_card, metric_card, section_header

load_local_env()


def _scanner_note(row: VolumeSignal) -> str:
    ratio = row.volume_ratio or 0.0
    if ratio >= 3.0:
        return "This is real participation. It deserves immediate validation against structure."
    if ratio >= 2.0:
        return "Strong abnormal volume. Keep it on the front board."
    if ratio >= 1.2:
        return "Interesting, but still more discovery than conviction."
    return "Visible activity, not yet meaningful."


inject_css()
render_sidebar("Volume Tracker")
config = get_runtime_app_config()
selected_symbols = get_selected_symbols()
render_refresh_bar("volume_tracker", config, selected_symbols, live_auth=False, prefer_database=True)
snapshot, used_cache = load_snapshot_with_feedback(
    "Loading stock volume snapshot...",
    config,
    selected_symbols,
    live_auth=False,
    prefer_database=True,
)

volume_rows = [row for row in snapshot["volume_batch"].rows if isinstance(row, VolumeSignal)]
eod_summary = snapshot.get("eod_summary")
errors = snapshot["volume_batch"].errors
top_ratio = max((row.volume_ratio or 0.0 for row in volume_rows), default=0.0)

if snapshot.get("is_post_close") and eod_summary:
    summary = dict(eod_summary.get("summary") or {})
    leaders = tuple(eod_summary.get("leaders") or ())

    st.markdown(
        """
        <div class="nubra-desk-hero">
          <div class="nubra-kicker">Close participation</div>
          <h1 class="nubra-desk-title">Who held attention into the close</h1>
          <p class="nubra-desk-copy">
            Stored end-of-day participation board for the names that still mattered by the bell.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    with cols[0]:
        metric_card("Top symbol", str(summary.get("top_symbol") or "None"), "Strongest stored leader.")
    with cols[1]:
        metric_card("Top ratio", f"{float(summary.get('top_volume_ratio') or 0.0):.2f}x", "Best abnormal participation at the close.", accent="#4ea1ff")
    with cols[2]:
        metric_card("Priority names", str(summary.get("priority_signals") or 0), "Names worth revisiting after the bell.", accent="#f5b342")
    with cols[3]:
        metric_card("Stored rows", str(len(leaders)), "Saved participation leaders for the session.", accent="#22c55e")

    left, right = st.columns([1.2, 0.8], gap="large")
    with left:
        section_header("Close participation board", "Best names from the final stored summary.")
        if leaders:
            leaderboard = pd.DataFrame(
                [{"symbol": row.get("symbol"), "volume ratio": round(float(row.get("volume_ratio") or 0.0), 2)} for row in leaders[:10]]
            ).set_index("symbol")
            st.bar_chart(leaderboard, height=320)
            dataframe_card(
                [
                    {
                        "rank": row.get("rank"),
                        "symbol": row.get("symbol"),
                        "volume ratio": round(float(row.get("volume_ratio") or 0.0), 2),
                        "state": row.get("action_state"),
                        "reason": row.get("signal_reason"),
                    }
                    for row in leaders[:12]
                ]
            )
        else:
            callout("No close participation yet", "The post-close sync will populate this board.")

    with right:
        section_header("Close read", "What the participation board says after the bell.")
        callout(
            "Strongest name",
            f"{summary.get('top_symbol') or 'None'} closed as the strongest participation name at {float(summary.get('top_volume_ratio') or 0.0):.2f}x.",
        )
        callout(
            "Index backdrop",
            f"NIFTY: {summary.get('nifty_bias') or 'No saved bias'} | SENSEX: {summary.get('sensex_bias') or 'No saved bias'}",
        )
        if summary.get("top_signal_reason"):
            callout("Why it mattered", str(summary.get("top_signal_reason")))

    if used_cache:
        st.caption("Showing the latest stored close summary for fast response.")
    st.stop()

st.markdown(
        """
        <div class="nubra-desk-hero">
          <div class="nubra-kicker">Volume tracker</div>
          <h1 class="nubra-desk-title">Participation board</h1>
          <p class="nubra-desk-copy">
            Rank abnormal participation fast and keep only the names worth carrying into setup review.
          </p>
        </div>
        """,
    unsafe_allow_html=True,
)

filters = st.columns([0.34, 0.22, 0.18, 0.26], gap="small")
with filters[0]:
    min_ratio = st.slider("Minimum volume ratio", min_value=0.0, max_value=max(3.0, round(top_ratio + 0.5, 1)), value=1.0, step=0.1)
with filters[1]:
    show_only_strong = st.toggle("Only 2x+ names", value=False)
with filters[2]:
    max_rows = st.selectbox("Rows", options=[10, 15, 20, 30], index=1)
with filters[3]:
    sort_mode = st.selectbox("Sort", options=["Highest ratio", "Largest current volume"], index=0)

filtered_rows = [row for row in volume_rows if (row.volume_ratio or 0.0) >= min_ratio]
if show_only_strong:
    filtered_rows = [row for row in filtered_rows if (row.volume_ratio or 0.0) >= 2.0]
if sort_mode == "Largest current volume":
    filtered_rows = sorted(filtered_rows, key=lambda row: row.current_volume or 0.0, reverse=True)[:max_rows]
else:
    filtered_rows = sorted(filtered_rows, key=lambda row: row.volume_ratio or 0.0, reverse=True)[:max_rows]

two_x_spikes = len([row for row in volume_rows if (row.volume_ratio or 0.0) >= 2.0])
three_x_spikes = len([row for row in volume_rows if (row.volume_ratio or 0.0) >= 3.0])

cols = st.columns(3)
with cols[0]:
    metric_card("Filtered", str(len(filtered_rows)), "Names surviving the active filter.")
with cols[1]:
    metric_card("Best ratio", f"{top_ratio:.2f}x", "Strongest abnormal participation in this snapshot.", accent="#4ea1ff")
with cols[2]:
    metric_card("2x+/3x+", f"{two_x_spikes}/{three_x_spikes}", "How concentrated the strongest participation is.", accent="#22c55e")

if errors:
    callout("Data issue", " | ".join(str(error) for error in errors if error))

left, right = st.columns([1.2, 0.8], gap="large")
with left:
    section_header("Top participation now", "Strongest names after the active filter.")
    if filtered_rows:
        leaderboard = pd.DataFrame(
            [{"symbol": row.symbol, "volume ratio": round(row.volume_ratio or 0.0, 2)} for row in filtered_rows[:8]]
        ).set_index("symbol")
        st.bar_chart(leaderboard, height=290)
    else:
        callout("No symbols match the filter", "Lower the ratio threshold or turn off the 2x-only toggle.")

with right:
    section_header("Desk read", "Quick context for the active shortlist.")
    if filtered_rows:
        lead = filtered_rows[0]
        callout(
            f"{lead.symbol} leads the scanner",
            f"Participation is running at {(lead.volume_ratio or 0.0):.2f}x versus baseline with {(lead.current_volume or 0.0):,.0f} current volume.",
        )
        if len(filtered_rows) > 1:
            callout(
                "Scan concentration",
                f"{len(filtered_rows)} names survive the filter, with {two_x_spikes} already above 2x participation.",
            )

section_header("Priority list", "Names most worth pushing into setup review.")
if filtered_rows:
    for row in filtered_rows[:4]:
        callout(
            f"{row.symbol} | {(row.volume_ratio or 0.0):.2f}x",
            _scanner_note(row),
        )
else:
    callout("No candidates yet", "Once the filters allow rows through, the strongest names appear here.")

section_header("Live table", "Dense output for the active filter.")
dataframe_card(
    [
        {
            "symbol": row.symbol,
            "candle_time": row.candle_time,
            "current volume": row.current_volume,
            "average volume": row.average_volume,
            "volume ratio": round(row.volume_ratio or 0.0, 2),
            "signal": row.signal_summary,
        }
        for row in filtered_rows
    ]
)

if used_cache:
    st.caption("Showing cached snapshot data to keep the page responsive.")
