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


def _state_label(signal) -> str:
    ratio = signal.volume_ratio or 0.0
    if ratio >= 2.0:
        return "Actionable"
    if ratio >= 1.5:
        return "Watch"
    if ratio >= 1.1:
        return "Build"
    return "Cold"


def _desk_note(signal) -> str:
    ratio = signal.volume_ratio or 0.0
    if ratio >= 2.0:
        return "Participation is already strong enough to justify immediate structure review."
    if ratio >= 1.5:
        return "This is worth keeping on the front board, but it still needs cleaner acceptance."
    if ratio >= 1.1:
        return "There is movement here, but not enough urgency to crowd the front board."
    return "This is visible, not decisive."


def _index_context(index_rows: list[WallSignal]) -> list[dict[str, object]]:
    return [
        {
            "index": row.symbol,
            "bias": row.bias or "Neutral",
            "wall": f"{row.wall_type or 'N/A'} {float(row.wall_strike or 0.0):.0f}",
            "distance %": round(row.proximity_pct or 999.0, 2),
        }
        for row in index_rows
    ]


inject_css()
render_sidebar()
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
eod_summary = snapshot.get("eod_summary")
top_signal = merged[0] if merged else None
index_rows = [row for row in snapshot["index_wall_batch"].rows if isinstance(row, WallSignal)]
actionable = [signal for signal in merged if (signal.volume_ratio or 0.0) >= 1.5]
build = [signal for signal in merged if 1.1 <= (signal.volume_ratio or 0.0) < 1.5]
cooling = [signal for signal in merged if (signal.volume_ratio or 0.0) < 1.1]
best_ratio = max((signal.volume_ratio or 0.0 for signal in merged), default=0.0)
index_context = _index_context(index_rows)
errors = snapshot["volume_batch"].errors + snapshot["index_wall_batch"].errors

if snapshot.get("is_post_close") and eod_summary:
    summary = dict(eod_summary.get("summary") or {})
    leaders = tuple(eod_summary.get("leaders") or ())

    st.markdown(
        """
        <div class="nubra-desk-hero">
          <div class="nubra-kicker">Close context</div>
          <h1 class="nubra-desk-title">What actually held into the bell</h1>
          <p class="nubra-desk-copy">
            Stored close board for the names and index pressure that held into the bell.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    with cols[0]:
        metric_card("Top symbol", str(summary.get("top_symbol") or "None"), "Strongest stored leader.")
    with cols[1]:
        metric_card("Priority names", str(summary.get("priority_signals") or 0), "Setups that stayed worth revisiting.", accent="#4ea1ff")
    with cols[2]:
        metric_card("Top ratio", f"{float(summary.get('top_volume_ratio') or 0.0):.2f}x", "Best close participation.", accent="#f5b342")
    with cols[3]:
        metric_card("NIFTY bias", str(summary.get("nifty_bias") or "Mixed"), "Close backdrop.", accent="#22c55e")

    left, right = st.columns([1.2, 0.8], gap="large")
    with left:
        section_header("Close board", "Best names from the final stored summary.")
        if leaders:
            dataframe_card(
                [
                    {
                        "rank": row.get("rank"),
                        "symbol": row.get("symbol"),
                        "state": row.get("action_state"),
                        "grade": row.get("signal_grade"),
                        "volume ratio": round(float(row.get("volume_ratio") or 0.0), 2),
                        "reason": row.get("signal_reason"),
                    }
                    for row in leaders[:10]
                ]
            )
        else:
            callout("No close board yet", "Run the post-close sync once to populate this view.")

    with right:
        section_header("Index close context", "Final options pressure framing the day.")
        callout(
            "NIFTY",
            f"{summary.get('nifty_bias') or 'No saved bias'} | {summary.get('nifty_wall_type') or 'N/A'} wall at {float(summary.get('nifty_wall_strike') or 0.0):.0f}",
        )
        callout(
            "SENSEX",
            f"{summary.get('sensex_bias') or 'No saved bias'} | {summary.get('sensex_wall_type') or 'N/A'} wall at {float(summary.get('sensex_wall_strike') or 0.0):.0f}",
        )
        if summary.get("top_signal_reason"):
            callout("Desk takeaway", str(summary.get("top_signal_reason")))

    if used_cache:
        st.caption("Showing the latest stored close summary for fast response.")
    st.stop()

st.markdown(
    """
    <div class="nubra-desk-hero">
      <div class="nubra-kicker">Market pulse</div>
      <h1 class="nubra-desk-title">Front board for the current session</h1>
      <p class="nubra-desk-copy">
        The shortest useful read on stock participation and index pressure.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

metric_cols = st.columns(3)
with metric_cols[0]:
    metric_card("Actionable", str(len(actionable)), "Names closest to a real decision.")
with metric_cols[1]:
    metric_card("Best ratio", f"{best_ratio:.2f}x", "Strongest participation on the board.", accent="#f5b342")
with metric_cols[2]:
    metric_card("Index layers", str(len(index_rows)), "Nearby regime inputs in play.", accent="#22c55e")

if errors:
    callout("Data issue", " | ".join(str(error) for error in errors if error))

left, right = st.columns([1.25, 0.75], gap="large")
with left:
    section_header("Front board", "The shortest useful list right now.")
    shortlist = list(actionable[:6] if actionable else merged[:6])
    if shortlist:
        chart_frame = pd.DataFrame(
            [{"symbol": signal.symbol, "volume ratio": round(signal.volume_ratio or 0.0, 2)} for signal in shortlist]
        ).set_index("symbol")
        st.bar_chart(chart_frame, height=280)
        st.write("")
        for signal in shortlist:
            row_cols = st.columns([0.84, 0.16], gap="small")
            with row_cols[0]:
                callout(
                    f"{signal.symbol} | {_state_label(signal)} | {(signal.volume_ratio or 0.0):.2f}x",
                    _desk_note(signal),
                )
            with row_cols[1]:
                st.write("")
                if st.button("Open", key=f"pulse_open_{signal.symbol}", width="stretch"):
                    _open_drilldown(signal.symbol)
    else:
        callout("No active board", "No symbols are standing out in the current snapshot.")

with right:
    section_header("Market backdrop", "Index pressure before symbol conviction.")
    if index_context:
        for row in index_context:
            callout(
                row["index"],
                f"{row['bias']} | {row['wall']} | {row['distance %']:.2f}% away",
            )
    else:
        callout("No index context yet", "Once OI wall rows are available, this panel becomes the market backdrop.")

section_header("Ranked board", "Full ordering for the current universe.")
dataframe_card(
    [
        {
            "symbol": signal.symbol,
            "state": _state_label(signal),
            "volume ratio": round(signal.volume_ratio or 0.0, 2),
            "decision note": _desk_note(signal),
        }
        for signal in merged
    ]
)

if used_cache:
    st.caption("Showing cached snapshot data to keep the page responsive.")
