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
from nubra_dash.models import OIWallCandidate, WallSignal
from nubra_dash.services import slice_chain_window
from nubra_dash.ui.runtime import load_snapshot_with_feedback, render_refresh_bar
from nubra_dash.ui.shell import get_runtime_app_config, get_selected_symbols, render_sidebar
from nubra_dash.ui.theme import inject_css
from nubra_dash.ui.widgets import callout, dataframe_card, hero, metric_card, section_header

load_local_env()


def _build_focus_figure(frame, *, spot: float, selected_strikes: set[float], selected_side: str | None) -> go.Figure:
    plot_frame = frame.copy()
    call_colors = ["#57b6ff" if row["strike"] in selected_strikes and selected_side == "CALL" else "#b53f45" for _, row in plot_frame.iterrows()]
    put_colors = ["#57b6ff" if row["strike"] in selected_strikes and selected_side == "PUT" else "#1fa971" for _, row in plot_frame.iterrows()]
    fig = go.Figure()
    fig.add_bar(
        x=-plot_frame["call_oi"],
        y=plot_frame["strike"],
        orientation="h",
        name="Call open interest",
        marker_color=call_colors,
        customdata=plot_frame["call_oi"],
        hovertemplate="Strike %{y}<br>Call open interest %{customdata:,.0f}<extra></extra>",
    )
    fig.add_bar(
        x=plot_frame["put_oi"],
        y=plot_frame["strike"],
        orientation="h",
        name="Put open interest",
        marker_color=put_colors,
        hovertemplate="Strike %{y}<br>Put open interest %{x:,.0f}<extra></extra>",
    )
    fig.add_hline(y=spot, line_color="#f8b84e", line_width=2, line_dash="dot", annotation_text=f"Spot {spot:,.2f}")
    for strike in selected_strikes:
        fig.add_hline(y=strike, line_color="#57b6ff", line_width=1.5)
    fig.update_layout(
        barmode="overlay",
        height=660,
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
st.title("Multi-Wall Explorer")
config = get_runtime_app_config()
render_refresh_bar("multi_wall_explorer", config, get_selected_symbols(), live_auth=False, prefer_database=True)
snapshot, used_cache = load_snapshot_with_feedback(
    "Loading multi-wall candidates...",
    config,
    get_selected_symbols(),
    live_auth=False,
    prefer_database=True,
)

candidates = [row for row in snapshot["index_multi_wall_batch"].rows if isinstance(row, OIWallCandidate)]
wall_rows = [row for row in snapshot["index_wall_batch"].rows if isinstance(row, WallSignal)]
symbol_options = sorted({row.symbol for row in candidates}) or sorted({row.symbol for row in wall_rows})
selected_symbol = st.selectbox("Focus index", symbol_options, index=0) if symbol_options else ""
symbol_rows = [row for row in candidates if row.symbol == selected_symbol]
selected = [row for row in symbol_rows if row.selected]
dominant = next((row for row in wall_rows if row.symbol == selected_symbol), None)
errors = snapshot["index_wall_batch"].errors + snapshot["index_multi_wall_batch"].errors

chain_map = {item.symbol: item for item in tuple(snapshot.get("index_ladders") or ())}

hero(
    "Focused strike-structure explorer for index options.",
    "This page is for the deeper look: highlighted candidate walls are drawn directly on the ladder so users can see whether option interest is stacked tightly or spread out around the current price.",
    tags=["Index context", "Multi-wall", "Strike explorer", "Visual structure"],
)

cols = st.columns(4)
with cols[0]:
    metric_card("Focus index", selected_symbol or "N/A", "Current index under the lens.")
with cols[1]:
    metric_card("Candidates", str(len(symbol_rows)), "Expanded walls for the selected index.", accent="#57b6ff")
with cols[2]:
    metric_card("Resolved walls", str(len(selected)), "Rows marked by the scanner as the selected near wall.", accent="#f8b84e")
with cols[3]:
    metric_card("Top N", str(config.scans.multi_wall_top_n), "Current cluster depth per index.", accent="#24c48e")

if errors:
    callout("Live data issue", " | ".join(str(error) for error in errors if error))

if selected_symbol and selected_symbol in chain_map:
    chain_snapshot = chain_map[selected_symbol]
    selected_strikes = {row.strike for row in symbol_rows}
    selected_side = selected[0].wall_side if selected else (dominant.wall_type if dominant else None)
    window = slice_chain_window(chain_snapshot.frame, chain_snapshot.spot, strikes_each_side=18)
    section_header(
        f"{selected_symbol} strike explorer",
        f"Expiry {chain_snapshot.expiry or 'N/A'} | Spot {chain_snapshot.spot:,.2f} | "
        f"Selected side {selected_side or 'N/A'}",
    )
    st.plotly_chart(
        _build_focus_figure(window, spot=chain_snapshot.spot, selected_strikes=selected_strikes, selected_side=selected_side),
        use_container_width=True,
    )

left, right = st.columns([1.05, 0.95], gap="large")
with left:
    section_header("Selected ladder rows", "The candidate strikes returned by the multi-wall scanner.")
    dataframe_card(
        [
            {
                "Index": row.symbol,
                "Wall side": row.wall_side,
                "Rank": row.rank,
                "Strike": row.strike,
                "Open interest": int(row.oi),
                "Distance from current price (%)": round(row.dist_pct, 2),
                "Selected wall": row.selected,
            }
            for row in symbol_rows
        ]
    )

with right:
    section_header("Why this page exists", "This is where the index options structure becomes visual instead of abstract.")
    callout(
        "Interpretation",
        (
            f"{selected_symbol or 'Index'} currently has {len(symbol_rows)} highlighted candidate strikes. "
            f"The dominant scanner wall is {dominant.wall_type if dominant and dominant.wall_type else 'N/A'} "
            f"at {dominant.wall_strike if dominant and dominant.wall_strike is not None else 'N/A'}."
        ),
    )
    if selected_symbol and selected_symbol in chain_map:
        callout(
            "Use case",
            "Read this page when the user wants to know whether nearby option interest is concentrated into one shelf or layered across multiple strikes.",
        )

if used_cache:
    st.caption("Showing cached live data to keep the page responsive.")
