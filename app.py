from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nubra_dash.bootstrap import load_local_env
from nubra_dash.models import VolumeSignal, WallSignal
from nubra_dash.services import slice_chain_window
from nubra_dash.ui.runtime import load_snapshot_with_feedback, render_refresh_bar
from nubra_dash.ui.shell import get_runtime_app_config, get_selected_symbols, render_sidebar
from nubra_dash.ui.theme import get_plotly_palette, inject_css
from nubra_dash.ui.widgets import callout, metric_card, section_header

load_local_env()


def _build_volume_preview(rows: list[VolumeSignal]) -> go.Figure:
    palette = get_plotly_palette()
    preview = sorted(rows, key=lambda row: row.volume_ratio or 0.0, reverse=True)[:8]
    frame = pd.DataFrame(
        [
            {
                "symbol": row.symbol,
                "volume_ratio": round(row.volume_ratio or 0.0, 2),
            }
            for row in preview
        ]
    )
    fig = go.Figure()
    fig.add_bar(
        x=frame["volume_ratio"] if not frame.empty else [],
        y=frame["symbol"] if not frame.empty else [],
        orientation="h",
        marker=dict(
            color=palette["success"],
            line=dict(color=palette["accent"], width=1.2),
        ),
        hovertemplate="%{y}<br>%{x:.2f}x relative volume<extra></extra>",
    )
    fig.update_layout(
        height=360,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor=palette["bg"],
        plot_bgcolor=palette["panel"],
        font=dict(color=palette["text"]),
        xaxis=dict(title="Relative volume", gridcolor=palette["grid"], zerolinecolor=palette["zero"]),
        yaxis=dict(autorange="reversed", gridcolor="rgba(0,0,0,0)"),
    )
    return fig


def _build_oi_preview(chain_snapshot, wall_signal: WallSignal | None) -> go.Figure:
    palette = get_plotly_palette()
    window = slice_chain_window(chain_snapshot.frame, chain_snapshot.spot, strikes_each_side=8).copy()
    window["call_oi_neg"] = -window["call_oi"]

    fig = go.Figure()
    fig.add_bar(
        x=window["call_oi_neg"],
        y=window["strike"],
        orientation="h",
        name="Call OI",
        marker_color=palette["danger"],
        hovertemplate="Strike %{y}<br>Call OI %{customdata:,.0f}<extra></extra>",
        customdata=window["call_oi"],
    )
    fig.add_bar(
        x=window["put_oi"],
        y=window["strike"],
        orientation="h",
        name="Put OI",
        marker_color=palette["success"],
        hovertemplate="Strike %{y}<br>Put OI %{x:,.0f}<extra></extra>",
    )
    fig.add_hline(
        y=chain_snapshot.spot,
        line_width=2,
        line_dash="dot",
        line_color=palette["warning"],
        annotation_text=f"Spot {chain_snapshot.spot:,.0f}",
        annotation_position="top left",
    )
    if wall_signal and wall_signal.wall_strike is not None:
        fig.add_hline(
            y=wall_signal.wall_strike,
            line_width=2,
            line_color=palette["accent_2"],
            annotation_text=f"{wall_signal.wall_type} wall {wall_signal.wall_strike:,.0f}",
            annotation_position="bottom left",
        )
    fig.update_layout(
        barmode="overlay",
        height=360,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor=palette["bg"],
        plot_bgcolor=palette["panel"],
        font=dict(color=palette["text"]),
        xaxis=dict(title="Open interest", gridcolor=palette["grid"], zerolinecolor=palette["zero"]),
        yaxis=dict(title="Strike", gridcolor=palette["grid"]),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


st.set_page_config(
    page_title="Nubra Signal Discovery",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
render_sidebar("Home")

config = get_runtime_app_config()
selected_symbols = get_selected_symbols()
snapshot, used_cache = load_snapshot_with_feedback(
    "Loading desk preview...",
    config,
    selected_symbols,
    live_auth=False,
    prefer_database=True,
)
render_refresh_bar("home", config, selected_symbols, live_auth=False, prefer_database=True)

volume_rows = [row for row in snapshot["volume_batch"].rows if isinstance(row, VolumeSignal)]
top_volume_rows = sorted(volume_rows, key=lambda row: row.volume_ratio or 0.0, reverse=True)[:5]
top_ratio = max((row.volume_ratio or 0.0 for row in volume_rows), default=0.0)

wall_rows = [row for row in snapshot["index_wall_batch"].rows if isinstance(row, WallSignal)]
wall_map = {row.symbol: row for row in wall_rows}
chain_snapshots = tuple(snapshot.get("index_ladders") or ())
focus_chain = chain_snapshots[0] if chain_snapshots else None
focus_wall = wall_map.get(focus_chain.symbol) if focus_chain else None

st.markdown(
    """
    <div class="nubra-desk-hero">
      <div class="nubra-kicker">Focused desk</div>
      <h1 class="nubra-desk-title">Volume breakout on the left. Option structure on the right.</h1>
      <p class="nubra-desk-copy">
        Use the previews below to understand what Nubra APIs are surfacing instantly, then jump into the dedicated pages from the header when you want the full board.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns(2, gap="large")

with left:
    st.markdown(
        """
        <div class="nubra-card" style="margin-bottom:0.85rem;">
          <div class="nubra-kicker">Volume breakout</div>
          <h2 style="margin:0 0 0.35rem 0;">Live breakout preview</h2>
          <p class="nubra-desk-copy" style="margin:0;">Top names ranked by relative volume against their baseline.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if top_volume_rows:
        metric_cols = st.columns(3)
        with metric_cols[0]:
            metric_card("Lead name", top_volume_rows[0].symbol, "Strongest breakout on the board.")
        with metric_cols[1]:
            metric_card("Top ratio", f"{top_ratio:.2f}x", "Highest relative volume right now.", accent="#4ea1ff")
        with metric_cols[2]:
            metric_card("2x+ names", str(len([row for row in volume_rows if (row.volume_ratio or 0.0) >= 2.0])), "Names already above a serious breakout threshold.", accent="#22c55e")

        st.plotly_chart(_build_volume_preview(top_volume_rows), width="stretch")
        section_header("Breakout names", "Fast read of the leaders on the current board.")
        for row in top_volume_rows[:3]:
            callout(
                f"{row.symbol} | {(row.volume_ratio or 0.0):.2f}x",
                f"Current volume {(row.current_volume or 0.0):,.0f} versus average {(row.average_volume or 0.0):,.0f}.",
            )
    else:
        callout("No breakout preview yet", "Once a stored snapshot lands, the top breakout chart will appear here.")

with right:
    st.markdown(
        """
        <div class="nubra-card" style="margin-bottom:0.85rem;">
          <div class="nubra-kicker">Options structure</div>
          <h2 style="margin:0 0 0.35rem 0;">Current chain preview</h2>
          <p class="nubra-desk-copy" style="margin:0;">A direct read of current-expiry OI shelves with the scanner wall overlaid.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if focus_chain:
        metric_cols = st.columns(3)
        with metric_cols[0]:
            metric_card("Focus index", focus_chain.symbol, "Current home-screen option preview.")
        with metric_cols[1]:
            metric_card("Spot", f"{focus_chain.spot:,.2f}", "Underlying index spot level.", accent="#4ea1ff")
        with metric_cols[2]:
            metric_card(
                "Dominant wall",
                f"{focus_wall.wall_type} {focus_wall.wall_strike:,.0f}" if focus_wall and focus_wall.wall_type and focus_wall.wall_strike is not None else "Pending",
                "Scanner wall currently nearest to the price structure.",
                accent="#8b6cff",
            )

        st.plotly_chart(_build_oi_preview(focus_chain, focus_wall), width="stretch")
        section_header("Structure read", "What the options snapshot is saying.")
        callout(
            focus_chain.symbol,
            (
                f"Spot is {focus_chain.spot:,.2f}. "
                f"{focus_wall.bias or 'Neutral'} pressure with the dominant {focus_wall.wall_type} wall "
                f"at {focus_wall.wall_strike:,.0f}."
            )
            if focus_wall and focus_wall.wall_type and focus_wall.wall_strike is not None
            else f"Spot is {focus_chain.spot:,.2f}. No dominant wall has been resolved yet."
        )
    else:
        callout("No options preview yet", "Once a ladder snapshot is available, the option-chain preview will appear here.")

if used_cache:
    st.caption("Home is reading the latest stored snapshot so the preview stays fast and stable.")
