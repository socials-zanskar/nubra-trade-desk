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
from nubra_dash.models import WallSignal
from nubra_dash.ui.runtime import load_snapshot_with_feedback, render_refresh_bar
from nubra_dash.ui.shell import get_runtime_app_config, get_selected_symbols, render_sidebar
from nubra_dash.ui.theme import inject_css
from nubra_dash.ui.widgets import callout, dataframe_card, metric_card, section_header

load_local_env()


def _open_drilldown(symbol: str) -> None:
    st.session_state["nubra_focus_symbol"] = symbol
    st.switch_page("pages/6_Symbol_Drilldown.py")


def _confirmation_state(signal, ratio_floor: float) -> str:
    ratio = signal.volume_ratio or 0.0
    if ratio >= max(2.0, ratio_floor + 0.35):
        return "Near actionable"
    if ratio >= ratio_floor:
        return "Needs trigger"
    return "Filtered"


def _decision_note(signal, ratio_floor: float) -> str:
    ratio = signal.volume_ratio or 0.0
    if ratio >= max(2.0, ratio_floor + 0.35):
        return "Participation is strong enough that price structure is the only remaining gate."
    if ratio >= ratio_floor:
        return "The volume passes the filter, but the name still needs cleaner price acceptance."
    return "This does not currently deserve escalation."


inject_css()
render_sidebar()
config = get_runtime_app_config()
selected_symbols = get_selected_symbols()
render_refresh_bar("breakout_confirmation", config, selected_symbols, live_auth=False, prefer_database=True)
snapshot, used_cache = load_snapshot_with_feedback(
    "Loading breakout shortlist...",
    config,
    selected_symbols,
    live_auth=False,
    prefer_database=True,
)

errors = snapshot["volume_batch"].errors + snapshot["wall_batch"].errors
ratio_floor = st.slider("Volume confirmation floor", min_value=1.0, max_value=3.0, value=1.5, step=0.1)
index_rows = [row for row in snapshot["index_wall_batch"].rows if isinstance(row, WallSignal)]
confirmed = [signal for signal in snapshot["merged_signals"] if (signal.volume_ratio or 0.0) >= ratio_floor]
near_actionable = [signal for signal in confirmed if _confirmation_state(signal, ratio_floor) == "Near actionable"]
watch_candidates = [signal for signal in confirmed if _confirmation_state(signal, ratio_floor) == "Needs trigger"]
best_ratio = max((signal.volume_ratio or 0.0 for signal in confirmed), default=0.0)

st.markdown(
    """
    <div class="nubra-desk-hero">
      <div class="nubra-kicker">Breakout confirmation</div>
      <h1 class="nubra-desk-title">Confirmation gate</h1>
      <p class="nubra-desk-copy">
        Volume gets a name through the gate. Price and structure still decide the trade.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

metric_cols = st.columns(3)
with metric_cols[0]:
    metric_card("Surviving names", str(len(confirmed)), "Names still above the current floor.")
with metric_cols[1]:
    metric_card("Near actionable", str(len(near_actionable)), "Volume is already strong enough to justify drilldown.", accent="#22c55e")
with metric_cols[2]:
    metric_card("Best ratio", f"{best_ratio:.2f}x", "Strongest surviving participation.", accent="#4ea1ff")

if errors:
    callout("Data issue", " | ".join(str(error) for error in errors if error))

left, right = st.columns([1.15, 0.85], gap="large")
with left:
    section_header("Filtered board", "Names that survived the first pass.")
    if confirmed:
        chart_frame = pd.DataFrame(
            [{"symbol": signal.symbol, "volume ratio": round(signal.volume_ratio or 0.0, 2)} for signal in confirmed[:6]]
        ).set_index("symbol")
        st.bar_chart(chart_frame, height=270)
    else:
        callout("No names cleared the filter", "Lower the floor if you want a wider shortlist.")

with right:
    section_header("Regime filter", "Check the shortlist against index pressure.")
    if index_rows:
        regime_frame = pd.DataFrame(
            [
                {
                    "index": row.symbol,
                    "wall type": row.wall_type,
                    "distance %": round(row.proximity_pct or 999.0, 2),
                    "bias": row.bias,
                }
                for row in index_rows
            ]
        )
        st.bar_chart(regime_frame.set_index("index")[["distance %"]], height=220)
        dataframe_card(regime_frame)
    else:
        callout("No regime rows yet", "This section becomes useful once OI wall context is available.")

left, right = st.columns([1.15, 0.85], gap="large")
with left:
    section_header("Shortlist", "Push only these into deeper symbol work.")
    if confirmed:
        for signal in confirmed[:8]:
            row_cols = st.columns([0.84, 0.16], gap="small")
            with row_cols[0]:
                callout(
                    f"{signal.symbol} | {_confirmation_state(signal, ratio_floor)} | {(signal.volume_ratio or 0.0):.2f}x",
                    _decision_note(signal, ratio_floor),
                )
            with row_cols[1]:
                st.write("")
                if st.button("Open", key=f"confirm_open_{signal.symbol}", width="stretch"):
                    _open_drilldown(signal.symbol)
    else:
        callout("No shortlist", "There is nothing left after the current filter.")

section_header("Filtered table", "Everything still left after the current threshold.")
dataframe_card(
    [
        {
            "symbol": signal.symbol,
            "state": _confirmation_state(signal, ratio_floor),
            "volume ratio": round(signal.volume_ratio or 0.0, 2),
            "decision note": _decision_note(signal, ratio_floor),
        }
        for signal in confirmed
    ]
)

if used_cache:
    st.caption("Showing cached snapshot data to keep the page responsive.")
