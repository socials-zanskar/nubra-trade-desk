from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nubra_dash.models import WallSignal
from nubra_dash.services import slice_chain_window
from nubra_dash.ui.runtime import load_snapshot_with_feedback, render_refresh_bar
from nubra_dash.ui.shell import get_runtime_app_config, get_selected_symbols, render_sidebar
from nubra_dash.ui.theme import inject_css
from nubra_dash.ui.widgets import callout, dataframe_card, hero, metric_card, section_header


def _build_oi_ladder(frame, *, symbol: str, spot: float, wall_signal: WallSignal | None) -> go.Figure:
    plot_frame = frame.copy()
    plot_frame["call_oi_neg"] = -plot_frame["call_oi"]
    fig = go.Figure()
    fig.add_bar(
        x=plot_frame["call_oi_neg"],
        y=plot_frame["strike"],
        orientation="h",
        name="Call open interest",
        marker_color="#c64040",
        hovertemplate="Strike %{y}<br>Call open interest %{customdata:,.0f}<extra></extra>",
        customdata=plot_frame["call_oi"],
    )
    fig.add_bar(
        x=plot_frame["put_oi"],
        y=plot_frame["strike"],
        orientation="h",
        name="Put open interest",
        marker_color="#1fa971",
        hovertemplate="Strike %{y}<br>Put open interest %{x:,.0f}<extra></extra>",
    )
    fig.add_hline(
        y=spot,
        line_width=2,
        line_dash="dot",
        line_color="#f8b84e",
        annotation_text=f"Spot {spot:,.2f}",
        annotation_position="top left",
    )
    if wall_signal and wall_signal.wall_strike is not None:
        fig.add_hline(
            y=wall_signal.wall_strike,
            line_width=2,
            line_color="#57b6ff",
            annotation_text=f"{wall_signal.wall_type} wall {wall_signal.wall_strike:,.0f}",
            annotation_position="bottom left",
        )
    fig.update_layout(
        barmode="overlay",
        height=620,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(8,19,31,0.65)",
        font=dict(color="#e8f1f8"),
        xaxis=dict(title="Open interest by strike", zeroline=True, zerolinecolor="#48657f", gridcolor="rgba(72,101,127,0.18)"),
        yaxis=dict(title="Strike", gridcolor="rgba(72,101,127,0.12)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


inject_css()
render_sidebar()
st.title("OI Walls")
config = get_runtime_app_config()
render_refresh_bar("oi_walls", config, get_selected_symbols(), live_auth=False, prefer_database=True)
snapshot, used_cache = load_snapshot_with_feedback(
    "Loading OI wall scans...",
    config,
    get_selected_symbols(),
    live_auth=False,
    prefer_database=True,
)

wall_rows = [row for row in snapshot["index_wall_batch"].rows if isinstance(row, WallSignal)]
wall_map = {row.symbol: row for row in wall_rows}
errors = snapshot["index_wall_batch"].errors + snapshot["index_multi_wall_batch"].errors

chain_snapshots = tuple(snapshot.get("index_ladders") or ())

hero(
    "Current-expiry index OI ladders.",
    "This page uses the raw option chain to draw the actual call-versus-put open-interest ladders for NIFTY and SENSEX, then overlays the dominant wall from the scanner. Distance is always shown as how far that wall is from the current price.",
    tags=["NIFTY", "SENSEX", "Current expiry", "Visual ladder"],
)

cols = st.columns(4)
with cols[0]:
    metric_card("Tracked indices", str(len(chain_snapshots) or len(wall_rows)), "Benchmarks currently visualized.")
with cols[1]:
    metric_card("Wall rows", str(len(wall_rows)), "Dominant current-expiry walls resolved by the scanner.", accent="#57b6ff")
with cols[2]:
    metric_card("Expiry ladders", str(len(chain_snapshots)), "Raw option-chain ladders available for charting.", accent="#f8b84e")
with cols[3]:
    metric_card("Data mode", "Stored", "Reading precomputed ladder data by default.", accent="#24c48e")

if errors:
    callout("Live data issue", " | ".join(str(error) for error in errors if error))

if not chain_snapshots:
    callout("No ladders returned", "No stored ladder snapshot is available yet. Run the backend worker or manual refresh first.")

for chain_snapshot in chain_snapshots:
    st.write("")
    wall_signal = wall_map.get(chain_snapshot.symbol)
    window = slice_chain_window(chain_snapshot.frame, chain_snapshot.spot, strikes_each_side=14)
    section_header(
        f"{chain_snapshot.symbol} ladder",
        f"Expiry {chain_snapshot.expiry or 'N/A'} | Spot {chain_snapshot.spot:,.2f} | "
        f"{wall_signal.wall_type if wall_signal else 'N/A'} wall {wall_signal.wall_strike if wall_signal and wall_signal.wall_strike is not None else 'N/A'}",
    )
    st.plotly_chart(
        _build_oi_ladder(window, symbol=chain_snapshot.symbol, spot=chain_snapshot.spot, wall_signal=wall_signal),
        use_container_width=True,
    )
    left, right = st.columns([0.95, 1.05], gap="large")
    with left:
        callout(
            f"{chain_snapshot.symbol} read",
            (
                f"Spot is at {chain_snapshot.spot:,.2f}. "
                f"Scanner bias is {wall_signal.bias if wall_signal and wall_signal.bias else 'N/A'}, "
                f"with the dominant {wall_signal.wall_type if wall_signal and wall_signal.wall_type else 'N/A'} wall "
                f"at {wall_signal.wall_strike if wall_signal and wall_signal.wall_strike is not None else 'N/A'}."
            ),
        )
    with right:
        dataframe_card(
            [
                {
                    "Strike": row["strike"],
                    "Call open interest": int(row["call_oi"]),
                    "Put open interest": int(row["put_oi"]),
                    "Call traded volume": int(row["call_volume"]),
                    "Put traded volume": int(row["put_volume"]),
                }
                for row in window.to_dict(orient="records")
            ]
        )

if used_cache:
    st.caption("Showing cached live data to keep the page responsive.")
