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
from nubra_dash.services import save_watchlist_symbols
from nubra_dash.ui.runtime import load_snapshot_with_feedback, render_refresh_bar
from nubra_dash.ui.shell import get_runtime_app_config, get_selected_symbols, render_sidebar
from nubra_dash.ui.theme import inject_css
from nubra_dash.ui.widgets import callout, dataframe_card, metric_card, section_header

load_local_env()


def _build_alert_rows(rows):
    alerts = []
    for signal in rows:
        ratio = signal.volume_ratio or 0.0
        if ratio >= 1.5:
            level = "Active"
        elif ratio >= 1.1:
            level = "Building"
        else:
            level = "Cooling"
        alerts.append(
            {
                "symbol": signal.symbol,
                "level": level,
                "grade": signal.signal_grade,
                "volume_ratio": round(signal.volume_ratio or 0.0, 2),
                "reason": signal.signal_reason,
            }
        )
    return alerts


def _watch_note(level: str) -> str:
    if level == "Active":
        return "This name is still strong enough to stay on the front board."
    if level == "Building":
        return "Keep watching, but wait for cleaner confirmation before escalating."
    return "Useful to monitor only if the setup improves again."


inject_css()
render_sidebar()
config = get_runtime_app_config()
selected_symbols = get_selected_symbols()
render_refresh_bar("watchlist_alerts", config, selected_symbols, live_auth=False, prefer_database=True)
snapshot, used_cache = load_snapshot_with_feedback(
    "Loading watchlist snapshot...",
    config,
    selected_symbols,
    live_auth=False,
    prefer_database=True,
)

merged = tuple(snapshot["merged_signals"])
stored_watchlist = tuple(snapshot.get("watchlist_symbols", ()))
default_watchlist = ",".join(stored_watchlist or tuple(signal.symbol for signal in merged[:5]))
watchlist = st.text_input("Watchlist symbols", value=st.session_state.get("nubra_watchlist", default_watchlist))
st.session_state["nubra_watchlist"] = watchlist
watch_symbols = [item.strip().upper() for item in watchlist.split(",") if item.strip()]
watch_rows = [signal for signal in merged if signal.symbol in watch_symbols]
alerts = _build_alert_rows(watch_rows)
recent_events = [event for event in snapshot.get("alert_events", ()) if not watch_symbols or event.get("symbol") in watch_symbols]
index_rows = [row for row in snapshot["index_wall_batch"].rows if isinstance(row, WallSignal)]
errors = snapshot["volume_batch"].errors + snapshot["index_wall_batch"].errors

st.markdown(
    """
    <div class="nubra-desk-hero">
      <div class="nubra-kicker">Monitoring surface</div>
      <h1 class="nubra-desk-title">Track state changes instead of re-reading the whole board</h1>
      <p class="nubra-desk-copy">
        Watchlist + Alerts should feel like a stateful monitor. It is where users keep names they care about and see whether they are getting stronger, stalling, or cooling off.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

cols = st.columns(4)
with cols[0]:
    metric_card("Watchlist size", str(len(watch_symbols)), "User-defined follow-up set.")
with cols[1]:
    metric_card("Active", str(len([row for row in alerts if row["level"] == "Active"])), "Names demanding attention now.", accent="#4ea1ff")
with cols[2]:
    metric_card("Building", str(len([row for row in alerts if row["level"] == "Building"])), "Names improving but not yet clean.", accent="#f5b342")
with cols[3]:
    metric_card("Cooling", str(len([row for row in alerts if row["level"] == "Cooling"])), "Names losing urgency.", accent="#22c55e")

save_cols = st.columns([0.18, 0.82])
with save_cols[0]:
    if st.button("Save watchlist", width="stretch"):
        save_watchlist_symbols(config, watch_symbols)
        st.success("Watchlist saved to the shared stored workspace.")
with save_cols[1]:
    st.markdown(
        '<div class="nubra-inline-note">This list can now live in Supabase instead of only inside the current browser session.</div>',
        unsafe_allow_html=True,
    )

if errors:
    callout("Data issue", " | ".join(str(error) for error in errors if error))

left, right = st.columns([1.05, 0.95], gap="large")
with left:
    section_header("State feed", "What changed inside the monitored set.")
    if recent_events:
        for event in recent_events[:8]:
            callout(event["title"], event["body"])
    elif alerts:
        for alert in alerts[:8]:
            callout(
                f"{alert['level']} | {alert['symbol']}",
                f"Volume {alert['volume_ratio']:.2f}x. {_watch_note(alert['level'])}",
            )
    else:
        callout("No watchlist alerts yet", "Add symbols from Symbol Drilldown or type a tighter list here.")

with right:
    section_header("Market backdrop", "Broad market pressure still frames the watchlist.")
    pressure_frame = pd.DataFrame(
        [
            {
                "Index": row.symbol,
                "Wall type": row.wall_type,
                "Distance from current price (%)": round(row.proximity_pct or 999.0, 2),
                "Bias": row.bias,
            }
            for row in index_rows
        ]
    )
    if not pressure_frame.empty:
        st.bar_chart(pressure_frame.set_index("Index")[["Distance from current price (%)"]], height=220)
        st.dataframe(pressure_frame, width="stretch")
    else:
        callout("Index context appears here", "Once index OI rows load, this panel becomes the backdrop for the watchlist.")

section_header("Watchlist table", "The complete monitored set for this session.")
dataframe_card(alerts)

if used_cache:
    st.caption("Showing cached snapshot data to keep the page responsive.")
