from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nubra_dash.models import WallSignal
from nubra_dash.ui.runtime import load_snapshot_with_feedback, render_refresh_bar
from nubra_dash.ui.shell import get_runtime_app_config, get_selected_symbols, render_sidebar
from nubra_dash.ui.theme import inject_css
from nubra_dash.ui.widgets import callout, dataframe_card, metric_card, section_header


def _open_drilldown(symbol: str) -> None:
    st.session_state["nubra_focus_symbol"] = symbol
    st.switch_page("pages/6_Symbol_Drilldown.py")


def _state_label(signal) -> str:
    ratio = signal.volume_ratio or 0.0
    if ratio >= 2.0:
        return "Actionable"
    if ratio >= 1.5:
        return "Watch"
    if ratio >= 1.1:
        return "Build"
    return "Cold"


def _pulse_note(signal) -> str:
    ratio = signal.volume_ratio or 0.0
    if ratio >= 2.0:
        return "Strong enough to check against price structure and trigger levels now."
    if ratio >= 1.5:
        return "Worth watching, but it still needs cleaner confirmation before execution prep."
    if ratio >= 1.1:
        return "Participation is improving, but not enough to force immediate attention."
    return "Still more background than front-board."


inject_css()
render_sidebar()
st.markdown("## Market Pulse")
config = get_runtime_app_config()
selected_symbols = get_selected_symbols()
render_refresh_bar("market_pulse", config, selected_symbols, live_auth=False, prefer_database=True)
snapshot, used_cache = load_snapshot_with_feedback(
    "Loading stock signals from the latest snapshot...",
    config,
    selected_symbols,
    live_auth=False,
    prefer_database=True,
)

merged = tuple(snapshot["merged_signals"])
top_signal = merged[0] if merged else None
top_volume = max((signal.volume_ratio or 0.0 for signal in merged), default=0.0)
index_rows = [row for row in snapshot["index_wall_batch"].rows if isinstance(row, WallSignal)]
nearby_walls = sum(1 for row in index_rows if (row.proximity_pct or 999.0) <= 2.0)
errors = snapshot["volume_batch"].errors + snapshot["index_wall_batch"].errors
actionable = [signal for signal in merged if (signal.volume_ratio or 0.0) >= 1.5]
build = [signal for signal in merged if 1.1 <= (signal.volume_ratio or 0.0) < 1.5]
cooling = [signal for signal in merged if (signal.volume_ratio or 0.0) < 1.1]

st.markdown(
    """
    <div class="nubra-desk-hero">
      <div class="nubra-kicker">Trading Desk</div>
      <h1 class="nubra-desk-title">Actionable board</h1>
      <p class="nubra-desk-copy">
        Start here when you want the shortest path from broad scan to names worth deeper work. This page should help you decide what earns attention now, what needs more confirmation, and what is only background noise.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

lead_cols = st.columns([1.15, 0.85], gap="large")
with lead_cols[0]:
    section_header("Actionable now", "Strongest names first.")
    spotlight = pd.DataFrame(
        [
            {
                "symbol": signal.symbol,
                "state": _state_label(signal),
                "volume ratio": round(signal.volume_ratio or 0.0, 2),
            }
            for signal in (actionable[:6] if actionable else merged[:6])
        ]
    )
    if not spotlight.empty:
        st.bar_chart(spotlight.set_index("symbol")[["volume ratio"]], height=260)
    else:
        callout("No shortlist yet", "No names are standing out in the current snapshot.")
with lead_cols[1]:
    section_header("Desk read", "Keep the board tight.")
    callout(
        "Use this board",
        "Push only the clearest names into drilldown. If the symbol is not strong here, it probably does not deserve more screen time yet.",
    )
    if top_signal:
        callout(
            "Current leader",
            f"{top_signal.symbol} is leading with {top_signal.volume_ratio or 0.0:.2f}x participation.",
        )

cols = st.columns(4)
with cols[0]:
    metric_card("Actionable", str(len(actionable)), "Names closest to deserving a real decision.")
with cols[1]:
    metric_card("Building", str(len(build)), f"Best ratio on the board: {top_volume:.2f}x", accent="#57b6ff")
with cols[2]:
    metric_card("Regime risk", str(nearby_walls), "Index walls close enough to matter to broad market tone.", accent="#f8b84e")
with cols[3]:
    metric_card("Cooling", str(len(cooling)), "Names still visible but not forcing attention.", accent="#24c48e")

if errors:
    callout("Live data issue", " | ".join(str(error) for error in errors if error))

left, right = st.columns([1.25, 0.9], gap="large")
with left:
    section_header("Decision shortlist", "Only the front-board names belong here.")
    top_rows = list(actionable[:6] if actionable else merged[:6])
    if top_rows:
        for signal in top_rows:
            detail_cols = st.columns([0.86, 0.14])
            with detail_cols[0]:
                callout(
                    f"{signal.symbol}  |  {_state_label(signal)}",
                    f"Volume {signal.volume_ratio or 0.0:.2f}x. {_pulse_note(signal)}",
                )
            with detail_cols[1]:
                st.write("")
                if st.button("Drill down", key=f"pulse_open_{signal.symbol}", use_container_width=True):
                    _open_drilldown(signal.symbol)
    else:
        callout("No merged signals yet", "This snapshot did not produce a decision shortlist.")

with right:
    section_header("Regime filter", "Read the shortlist against index pressure before escalating any symbol.")
    pressure_rows = [
        {
            "Index": row.symbol,
            "Wall type": row.wall_type,
            "Wall strike": round(row.wall_strike or 0.0, 0),
            "Distance from current price (%)": round(row.proximity_pct or 999.0, 2),
            "Bias": row.bias,
        }
        for row in index_rows
    ]
    if pressure_rows:
        pressure_frame = pd.DataFrame(pressure_rows).set_index("Index")
        st.bar_chart(pressure_frame[["Distance from current price (%)"]], height=220)
        st.dataframe(pressure_frame, use_container_width=True, height=225)
    else:
        callout("No index context yet", "Once the OI scan yields rows, this panel shows NIFTY and SENSEX current-expiry pressure.")

section_header("Ranked board", "Full ordering for the current universe.")
dataframe_card(
    [
        {
            "symbol": signal.symbol,
            "state": _state_label(signal),
            "volume ratio": round(signal.volume_ratio or 0.0, 2),
            "decision note": _pulse_note(signal),
        }
        for signal in merged
    ]
)
st.caption(f"Viewing scan universe: {st.session_state.get('nubra_selected_basket', config.scans.default_basket)}")
if used_cache:
    st.caption("Showing cached snapshot data to keep the page responsive.")
