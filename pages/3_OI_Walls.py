from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nubra_dash.bootstrap import load_local_env
from nubra_dash.models import WallSignal
from nubra_dash.services import slice_chain_window
from nubra_dash.ui.runtime import load_snapshot_with_feedback, render_refresh_bar
from nubra_dash.ui.shell import get_runtime_app_config, get_selected_symbols, render_sidebar
from nubra_dash.ui.theme import get_plotly_palette, inject_css
from nubra_dash.ui.widgets import callout, dataframe_card, metric_card, section_header

load_local_env()


def _build_oi_ladder(frame, *, spot: float, wall_signal: WallSignal | None) -> go.Figure:
    colorscheme = get_plotly_palette()
    plot_frame = frame.copy()
    plot_frame["call_oi_neg"] = -plot_frame["call_oi"]
    fig = go.Figure()
    fig.add_bar(
        x=plot_frame["call_oi_neg"],
        y=plot_frame["strike"],
        orientation="h",
        name="Call open interest",
        marker_color=colorscheme["danger"],
        hovertemplate="Strike %{y}<br>Call open interest %{customdata:,.0f}<extra></extra>",
        customdata=plot_frame["call_oi"],
    )
    fig.add_bar(
        x=plot_frame["put_oi"],
        y=plot_frame["strike"],
        orientation="h",
        name="Put open interest",
        marker_color=colorscheme["success"],
        hovertemplate="Strike %{y}<br>Put open interest %{x:,.0f}<extra></extra>",
    )
    fig.add_hline(
        y=spot,
        line_width=2,
        line_dash="dot",
        line_color=colorscheme["warning"],
        annotation_text=f"Spot {spot:,.2f}",
        annotation_position="top left",
    )
    if wall_signal and wall_signal.wall_strike is not None:
        fig.add_hline(
            y=wall_signal.wall_strike,
            line_width=2,
            line_color=colorscheme["accent_2"],
            annotation_text=f"{wall_signal.wall_type} wall {wall_signal.wall_strike:,.0f}",
            annotation_position="bottom left",
        )
    fig.update_layout(
        barmode="overlay",
        height=620,
        margin=dict(l=10, r=10, t=20, b=10),
        paper_bgcolor=colorscheme["bg"],
        plot_bgcolor=colorscheme["panel"],
        font=dict(color=colorscheme["text"]),
        xaxis=dict(title="Open interest by strike", zeroline=True, zerolinecolor=colorscheme["zero"], gridcolor=colorscheme["grid"]),
        yaxis=dict(title="Strike", gridcolor=colorscheme["grid"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def _wall_summary(chain_snapshot, wall_signal: WallSignal | None) -> str:
    if not wall_signal:
        return f"Spot is at {chain_snapshot.spot:,.2f}. No dominant wall has been resolved yet."
    return (
        f"Spot is at {chain_snapshot.spot:,.2f}. The scanner is reading {wall_signal.bias or 'Neutral'} pressure "
        f"with the dominant {wall_signal.wall_type or 'N/A'} wall at {wall_signal.wall_strike or 0.0:,.0f}, "
        f"{wall_signal.proximity_pct or 0.0:.2f}% away from spot."
    )


inject_css()
render_sidebar()
config = get_runtime_app_config()
selected_symbols = get_selected_symbols()
render_refresh_bar("oi_walls", config, selected_symbols, live_auth=False, prefer_database=True)
snapshot, used_cache = load_snapshot_with_feedback(
    "Loading OI wall scans...",
    config,
    selected_symbols,
    live_auth=False,
    prefer_database=True,
)

wall_rows = [row for row in snapshot["index_wall_batch"].rows if isinstance(row, WallSignal)]
wall_map = {row.symbol: row for row in wall_rows}
errors = snapshot["index_wall_batch"].errors + snapshot["index_multi_wall_batch"].errors
chain_snapshots = tuple(snapshot.get("index_ladders") or ())

st.markdown(
    """
    <div class="nubra-desk-hero">
      <div class="nubra-kicker">Nubra index structure</div>
      <h1 class="nubra-desk-title">See the actual option shelves, not just the scanner label</h1>
      <p class="nubra-desk-copy">
        Raw index ladders with the dominant scanner wall overlaid on top.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

cols = st.columns(4)
with cols[0]:
    metric_card("Tracked indices", str(len(chain_snapshots) or len(wall_rows)), "Benchmarks currently visualized.")
with cols[1]:
    metric_card("Resolved walls", str(len(wall_rows)), "Dominant current-expiry walls from the scanner.", accent="#4ea1ff")
with cols[2]:
    metric_card("Ladders", str(len(chain_snapshots)), "Stored raw option-chain ladders available.", accent="#f5b342")
with cols[3]:
    metric_card("Mode", "Stored", "Reading shared precomputed ladder snapshots.", accent="#22c55e")

if errors:
    callout("Data issue", " | ".join(str(error) for error in errors if error))

if not chain_snapshots:
    callout("No ladders returned", "No stored ladder snapshot is available yet. Run the backend worker or manual refresh first.")

for chain_snapshot in chain_snapshots:
    st.write("")
    wall_signal = wall_map.get(chain_snapshot.symbol)
    window = slice_chain_window(chain_snapshot.frame, chain_snapshot.spot, strikes_each_side=14)

    st.markdown(
        f"""
        <div class="nubra-desk-hero" style="padding:0.95rem 1rem; margin-bottom:0.8rem;">
          <div class="nubra-kicker">{chain_snapshot.symbol}</div>
          <h2 class="nubra-desk-title" style="font-size:1.55rem;">Current-expiry ladder</h2>
          <p class="nubra-desk-copy" style="max-width:none;">
            Expiry {chain_snapshot.expiry or 'N/A'} | Spot {chain_snapshot.spot:,.2f} | Wall {wall_signal.wall_type if wall_signal else 'N/A'} {wall_signal.wall_strike if wall_signal and wall_signal.wall_strike is not None else 'N/A'}
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.plotly_chart(
        _build_oi_ladder(window, spot=chain_snapshot.spot, wall_signal=wall_signal),
        width="stretch",
    )

    left, right = st.columns([0.9, 1.1], gap="large")
    with left:
        section_header("Desk read", "What the ladder is saying right now.")
        callout(chain_snapshot.symbol, _wall_summary(chain_snapshot, wall_signal))

    with right:
        section_header("Selected ladder rows", "The raw ladder values behind the chart.")
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
    st.caption("Showing cached ladder data to keep the page responsive.")
