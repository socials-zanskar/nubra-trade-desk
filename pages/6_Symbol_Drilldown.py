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
from nubra_dash.models import OIWallCandidate, WallSignal
from nubra_dash.services.auth import load_auth_session
from nubra_dash.services.market_history import fetch_historical_data, normalize_history_points
from nubra_dash.ui.runtime import load_snapshot_with_feedback, render_refresh_bar
from nubra_dash.ui.shell import get_runtime_app_config, get_selected_symbols, render_sidebar
from nubra_dash.ui.theme import inject_css
from nubra_dash.ui.widgets import callout, dataframe_card, metric_card, section_header

load_local_env()

inject_css()
render_sidebar()
config = get_runtime_app_config()
selected_symbols = get_selected_symbols()
render_refresh_bar("symbol_drilldown", config, selected_symbols, live_auth=False, prefer_database=True)
snapshot, used_cache = load_snapshot_with_feedback(
    "Loading stored drilldown context...",
    config,
    selected_symbols,
    live_auth=False,
    prefer_database=True,
)

merged = tuple(snapshot["merged_signals"])
candidate_symbols = [signal.symbol for signal in merged] or list(selected_symbols)
drilldown_summaries = snapshot.get("drilldown_summaries", {})
default_focus = st.session_state.get("nubra_focus_symbol")
if default_focus not in candidate_symbols:
    default_focus = candidate_symbols[0] if candidate_symbols else ""
if candidate_symbols:
    default_index = candidate_symbols.index(default_focus) if default_focus in candidate_symbols else 0
    symbol = st.selectbox("Choose symbol", candidate_symbols, index=default_index)
else:
    symbol = ""
st.session_state["nubra_focus_symbol"] = symbol

focus = next((signal for signal in merged if signal.symbol == symbol), None)
stored_drilldown = drilldown_summaries.get(symbol)
index_rows = [row for row in snapshot["index_wall_batch"].rows if isinstance(row, WallSignal)]
wall_ladder = [row for row in snapshot["index_multi_wall_batch"].rows if isinstance(row, OIWallCandidate)]
history_frame = pd.DataFrame()
history_error = None
live_detail_enabled = bool(getattr(config.scans, "enable_live_drilldown", False))
live_detail_key = f"nubra_live_drilldown::{symbol}"
if not symbol:
    st.session_state.pop(live_detail_key, None)

st.markdown(
    """
    <div class="nubra-desk-hero">
      <div class="nubra-kicker">Symbol drilldown</div>
      <h1 class="nubra-desk-title">One-name decision page</h1>
      <p class="nubra-desk-copy">
        Read the setup, the levels, and the backdrop before you spend more time on the name.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

cols = st.columns(3)
with cols[0]:
    metric_card("Symbol", symbol or "N/A", "Current focus name.")
with cols[1]:
    metric_card("Volume ratio", f"{(focus.volume_ratio or 0.0):.2f}x" if focus else "N/A", "Participation versus baseline.", accent="#4ea1ff")
with cols[2]:
    metric_card("Action state", focus.action_state if focus else "N/A", "Stored board state.", accent="#f5b342")

cta_cols = st.columns([0.22, 0.78])
with cta_cols[0]:
    if symbol and live_detail_enabled and st.button("Load live detail", width="stretch"):
        st.session_state[live_detail_key] = True

if symbol and st.session_state.get(live_detail_key):
    auth_session = load_auth_session(config.auth)
    if auth_session and auth_session.market_data:
        try:
            response = fetch_historical_data(auth_session.market_data, [symbol], exchange=config.scans.exchange, interval=config.scans.volume_interval)
            history_frame = normalize_history_points(response, symbol)
        except Exception as exc:  # pragma: no cover
            history_error = str(exc)
    else:
        history_error = auth_session.error if auth_session else "Live drilldown session is unavailable."

left, right = st.columns([1.05, 0.95], gap="large")
with left:
    section_header("Price and volume", "Use live detail only if the setup already deserves it.")
    if not history_frame.empty:
        price_frame = history_frame.set_index("timestamp")[["close"]]
        st.line_chart(price_frame, height=280)
        volume_chart = history_frame.set_index("timestamp")[["cumulative_volume"]].tail(40)
        st.area_chart(volume_chart, height=180)
    elif history_error:
        callout("History unavailable", history_error)
    else:
        if live_detail_enabled:
            callout("Stored mode active", "Use the live-detail button only when this symbol has clearly earned a deeper look.")
        else:
            callout("Stored mode only", "Live drilldown is disabled. This page is reading worker-computed summaries from Supabase.")

with right:
    section_header("Decision read", "Use this to decide whether the setup deserves more work.")
    if focus:
        callout("Setup", f"{focus.setup_type} | {focus.action_state} | confidence {focus.confidence:.0f}")
        callout("Why now", focus.why_now or focus.signal_reason)
        if stored_drilldown and getattr(stored_drilldown, 'notes', None):
            callout("Stored note", stored_drilldown.notes[0])
        elif focus.volume_ratio is not None:
            callout("Participation", f"Current candle participation is {focus.volume_ratio:.2f}x versus baseline.")
        levels = []
        if focus.trigger_price is not None:
            levels.append(f"Trigger {focus.trigger_price:.2f}")
        if focus.invalidation_price is not None:
            levels.append(f"Invalidation {focus.invalidation_price:.2f}")
        if focus.first_target is not None:
            levels.append(f"Target {focus.first_target:.2f}")
        if levels:
            callout("Levels", " | ".join(levels))
        if index_rows:
            callout(
                "Index backdrop",
                "Index context: "
                + " | ".join(
                    f"{row.symbol} {row.wall_type or 'N/A'} wall {row.proximity_pct or 0.0:.2f}% away"
                    for row in index_rows
                ),
            )

with st.expander("Index wall ladder", expanded=False):
    dataframe_card(
        [
            {
                "Index": row.symbol,
                "Wall side": row.wall_side,
                "Rank": row.rank,
                "Strike": row.strike,
                "Open interest": row.oi,
                "Distance from current price (%)": round(row.dist_pct, 2),
                "Selected wall": row.selected,
            }
            for row in wall_ladder
        ]
    )

if used_cache:
    st.caption("Showing cached stored snapshot data to keep the page responsive.")
