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


def _confirmation_state(signal, ratio_floor: float) -> str:
    ratio = signal.volume_ratio or 0.0
    if ratio >= max(2.0, ratio_floor + 0.2):
        return "Near actionable"
    if ratio >= ratio_floor:
        return "Needs trigger"
    return "Filtered out"


inject_css()
render_sidebar()
st.markdown("## Breakout Confirmation")
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
index_bias = " | ".join(
    f"{row.symbol}: {row.wall_type or 'N/A'} wall {row.proximity_pct or 0.0:.2f}% away"
    for row in index_rows
)
confirmed = [signal for signal in snapshot["merged_signals"] if (signal.volume_ratio or 0.0) >= ratio_floor]

st.markdown(
    """
    <div class="nubra-desk-hero">
      <div class="nubra-kicker">Setup Filter</div>
      <h1 class="nubra-desk-title">Needs confirmation</h1>
      <p class="nubra-desk-copy">
        This page is the quality gate between raw discovery and deeper work. It should show only the names that still deserve attention after the first scan, while staying honest about how light the current confirmation logic still is.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

cols = st.columns(4)
with cols[0]:
    metric_card("Candidates", str(len(confirmed)), "Names still above the current threshold.")
with cols[1]:
    metric_card("Ratio floor", f"{ratio_floor:.1f}x", "Current abnormal-volume requirement.", accent="#57b6ff")
with cols[2]:
    metric_card("Regime inputs", str(len(index_rows)), "Index pressure layers currently in play.", accent="#f8b84e")
with cols[3]:
    metric_card("Best ratio", f"{max((signal.volume_ratio or 0.0 for signal in confirmed), default=0.0):.2f}x", "Strongest candidate left after filtering.", accent="#24c48e")

if errors:
    callout("Live data issue", " | ".join(str(error) for error in errors if error))

lead_cols = st.columns([1.05, 0.95], gap="large")
with lead_cols[0]:
    section_header("Filtered board", "Shortlist that survived the first scan.")
    confirm_frame = pd.DataFrame(
        [
            {
                "symbol": signal.symbol,
                "volume ratio": round(signal.volume_ratio or 0.0, 2),
            }
            for signal in confirmed[:6]
        ]
    )
    if not confirm_frame.empty:
        st.bar_chart(confirm_frame.set_index("symbol"), height=255)
    else:
        callout("No names cleared the filter", "Lower the volume confirmation floor to widen the shortlist.")
with lead_cols[1]:
    section_header("Desk read", "Keep the pass-fail logic visible.")
    callout(
        "Current limitation",
        "This page is still mostly volume-led. It is useful as a tighter shortlist, but not yet a full confirmation engine.",
    )
    if confirmed:
        leader = confirmed[0]
        callout(
            "Current leader",
            f"{leader.symbol} is the strongest surviving name at {leader.volume_ratio or 0.0:.2f}x abnormal volume.",
        )

left, right = st.columns([1.15, 0.95], gap="large")
with left:
    section_header("Shortlist", "The names most worth pushing into symbol drilldown.")
    for signal in confirmed[:6]:
        action_cols = st.columns([0.86, 0.14])
        with action_cols[0]:
            callout(
                f"{signal.symbol}  |  {_confirmation_state(signal, ratio_floor)}",
                "Volume {:.2f}x. Check price acceptance, not just participation, before treating it as executable.".format(signal.volume_ratio or 0.0),
            )
        with action_cols[1]:
            st.write("")
            if st.button("Open", key=f"confirm_open_{signal.symbol}", use_container_width=True):
                _open_drilldown(signal.symbol)
    if not confirmed:
        callout("No names cleared the filter", "Try lowering the ratio floor to widen the shortlist.")

with right:
    section_header("Regime filter", "Read each candidate against current index pressure.")
    confirmation_frame = pd.DataFrame(
        [
            {
                "index": row.symbol,
                "wall_type": row.wall_type,
                "Distance from current price (%)": round(row.proximity_pct or 999.0, 2),
                "bias": row.bias,
            }
            for row in index_rows
        ]
    )
    if not confirmation_frame.empty:
        st.bar_chart(confirmation_frame.set_index("index")[["Distance from current price (%)"]], height=240)
        st.dataframe(confirmation_frame, use_container_width=True, height=220)
        if index_bias:
            callout("Current regime read", index_bias)
    else:
        callout("No index context yet", "Once the OI scan yields rows, this area becomes the market backdrop panel.")

section_header("Filtered table", "Full list left after the current threshold.")
dataframe_card(
    [
        {
            "symbol": signal.symbol,
            "state": _confirmation_state(signal, ratio_floor),
            "volume ratio": round(signal.volume_ratio or 0.0, 2),
            "decision note": "Still needs actual price confirmation",
        }
        for signal in confirmed
    ]
)
if used_cache:
    st.caption("Showing cached snapshot data to keep the page responsive.")
