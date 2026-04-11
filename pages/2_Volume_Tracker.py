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


inject_css()
render_sidebar()
st.markdown("## Volume Tracker")
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
          <div class="nubra-kicker">Today's volume</div>
          <h1 class="nubra-desk-title">Participation into the close</h1>
          <p class="nubra-desk-copy">
            The session is over, so this page shifts from live scan mode into an end-of-day participation board. Use it to see which names truly commanded attention by the close.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    with cols[0]:
        metric_card("Top symbol", str(summary.get("top_symbol") or "None"), "Highest-ranked stored leader.")
    with cols[1]:
        metric_card("Top ratio", f"{float(summary.get('top_volume_ratio') or 0.0):.2f}x", "Best abnormal participation captured today.", accent="#57b6ff")
    with cols[2]:
        metric_card("Priority names", str(summary.get("priority_signals") or 0), "Names worth reviewing after the close.", accent="#f8b84e")
    with cols[3]:
        metric_card("Stored leaders", str(len(leaders)), "Rows preserved for today's close board.", accent="#24c48e")

    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        section_header("Top participation today", "Best names from the final EOD board.")
        if leaders:
            leaderboard = pd.DataFrame(
                [
                    {
                        "symbol": row.get("symbol"),
                        "volume ratio": round(float(row.get("volume_ratio") or 0.0), 2),
                    }
                    for row in leaders[:10]
                ]
            )
            st.bar_chart(leaderboard.set_index("symbol"), height=320)
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
            callout("No close leaders yet", "The post-close sync will populate today's participation board.")

    with right:
        section_header("Close read", "What the volume board says after the bell.")
        callout(
            "Strongest name",
            f"{summary.get('top_symbol') or 'None'} printed the strongest stored ratio at {float(summary.get('top_volume_ratio') or 0.0):.2f}x.",
        )
        callout(
            "Index backdrop",
            f"NIFTY: {summary.get('nifty_bias') or 'No saved bias'} | SENSEX: {summary.get('sensex_bias') or 'No saved bias'}",
        )
        if summary.get("top_signal_reason"):
            callout("Why it mattered", str(summary.get("top_signal_reason")))

    if used_cache:
        st.caption("Showing the latest stored close summary for faster response.")
    st.stop()

st.markdown(
    """
    <div class="nubra-desk-hero">
      <div class="nubra-kicker">Scanner</div>
      <h1 class="nubra-desk-title">Emerging participation</h1>
      <p class="nubra-desk-copy">
        Use this page as the raw scan console. The job here is not to make final decisions. It is to isolate where participation is actually changing so only the strongest names move forward.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

filters = st.columns([0.34, 0.26, 0.18, 0.22])
with filters[0]:
    min_ratio = st.slider("Minimum volume ratio", min_value=0.0, max_value=max(3.0, round(top_ratio + 0.5, 1)), value=1.0, step=0.1)
with filters[1]:
    show_only_strong = st.toggle("Show only 2x+ spikes", value=False)
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

cols = st.columns(4)
with cols[0]:
    metric_card("Tracked", str(len(selected_symbols)), "Current basket size for the scan.")
with cols[1]:
    metric_card("Best ratio", f"{top_ratio:.2f}x", "Highest abnormal participation in this snapshot.", accent="#57b6ff")
with cols[2]:
    metric_card("2x+ spikes", str(len([row for row in volume_rows if (row.volume_ratio or 0.0) >= 2.0])), "Names currently above the stronger attention threshold.", accent="#f8b84e")
with cols[3]:
    metric_card("Visible", str(len(filtered_rows)), "Rows left after filters.", accent="#24c48e")

if errors:
    callout("Live data issue", " | ".join(str(error) for error in errors if error))

st.write("")
lead_cols = st.columns([1.05, 0.95], gap="large")
with lead_cols[0]:
    section_header("Top scan hits", "Quick read on where participation is changing fastest.")
    leaderboard = pd.DataFrame(
        [
            {
                "symbol": row.symbol,
                "volume ratio": round(row.volume_ratio or 0.0, 2),
            }
            for row in filtered_rows[:8]
        ]
    )
    if not leaderboard.empty:
        st.bar_chart(leaderboard.set_index("symbol"), height=280)
    else:
        callout("No symbols match the filter", "Try lowering the ratio threshold or turning off the 2x-only toggle.")
with lead_cols[1]:
    section_header("Scanner read", "What deserves the next click.")
    if filtered_rows:
        lead = filtered_rows[0]
        callout(
            f"Lead candidate | {lead.symbol}",
            f"Participation is running at {lead.volume_ratio or 0.0:.2f}x versus baseline, with current traded volume at {lead.current_volume or 0.0:,.0f}.",
        )
    callout(
        "How to use it",
        "Filter noise here first. The goal is to leave only the names worth validating elsewhere.",
    )

left, right = st.columns([1.05, 1.05], gap="large")
with left:
    section_header("Participation buckets", "Good scanners separate real movement from background activity.")
    bucket_rows = [
        {"bucket": "3x or higher", "count": len([row for row in volume_rows if (row.volume_ratio or 0.0) >= 3.0])},
        {"bucket": "2x to 3x", "count": len([row for row in volume_rows if 2.0 <= (row.volume_ratio or 0.0) < 3.0])},
        {"bucket": "1x to 2x", "count": len([row for row in volume_rows if 1.0 <= (row.volume_ratio or 0.0) < 2.0])},
        {"bucket": "Below 1x", "count": len([row for row in volume_rows if (row.volume_ratio or 0.0) < 1.0])},
    ]
    st.dataframe(pd.DataFrame(bucket_rows), use_container_width=True, hide_index=True)
    callout(
        "Desk note",
        "If most names are in the 1x to 2x bucket, your scanner is still in discovery mode and not yet in decision mode.",
    )

with right:
    section_header("Forward list", "Names most worth pushing into setup validation.")
    for row in filtered_rows[:4]:
        callout(
            row.symbol,
            f"{row.volume_ratio or 0.0:.2f}x abnormal volume. Current traded volume {row.current_volume or 0.0:,.0f}.",
        )
    if not filtered_rows:
        callout("No candidates yet", "Once the filters allow rows through, the strongest names appear here first.")

section_header("Scanner table", "Dense scan output for the active filters.")
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
st.caption(f"Viewing scan universe: {st.session_state.get('nubra_selected_basket', config.scans.default_basket)}")
if used_cache:
    st.caption("Showing cached snapshot data to keep the page responsive.")
