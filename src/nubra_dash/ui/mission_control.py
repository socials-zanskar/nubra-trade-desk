from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from nubra_dash.config import AppConfig
from nubra_dash.models import MergedSignal, WallSignal
from nubra_dash.ui.widgets import callout, compact_table


def render_mission_control_home(
    *,
    app_config: AppConfig,
    snapshot: dict[str, object],
    selected_symbols: tuple[str, ...],
    used_cache: bool,
) -> None:
    auth_session = snapshot["auth_session"]
    merged = tuple(snapshot["merged_signals"] or ())
    volume_rows = tuple(snapshot["volume_batch"].rows or ())
    wall_rows = tuple(snapshot["index_wall_batch"].rows or ())
    index_rows = [row for row in wall_rows if isinstance(row, WallSignal)]

    actionables = [signal for signal in merged if (signal.volume_ratio or 0.0) >= 1.5]
    watchers = [signal for signal in merged if 1.1 <= (signal.volume_ratio or 0.0) < 1.5]
    cooling = [signal for signal in merged if (signal.volume_ratio or 0.0) < 1.1]
    regime_bias = _resolve_regime_bias(index_rows)
    session_live = bool(auth_session and auth_session.is_available)
    now = datetime.now().strftime("%I:%M %p")

    st.markdown(
        f"""
        <div class="nubra-desk-hero">
          <div class="nubra-kicker">Trading Desk</div>
          <h1 class="nubra-desk-title">What matters now</h1>
          <p class="nubra-desk-copy">
            Focus the open on the cleanest setups, read them against index pressure, and only escalate to deeper work when the board still looks tradable.
          </p>
          <p class="nubra-subtle nubra-mission-copy">
            <span class="nubra-chip tone-cyan">{len(selected_symbols)} names</span>
            <span class="nubra-chip tone-green">{len(actionables)} actionable</span>
            <span class="nubra-chip tone-amber">{len(watchers)} building</span>
            <span class="nubra-chip tone-blue">{regime_bias}</span>
            <span class="nubra-chip tone-purple">{now}</span>
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    kpi_cols = st.columns(4, gap="small")
    kpi_rows = [
        ("Regime", regime_bias.split()[0], "Index backdrop", _regime_accent(regime_bias), _sparkline(_metric_wave(len(index_rows) + len(actionables)))),
        ("Actionable", str(len(actionables)), "Near decision", "#57b6ff", _sparkline(_metric_wave(len(actionables)))),
        ("Building", str(len(watchers)), "Need confirmation", "#f8b84e", _sparkline(_metric_wave(len(watchers)))),
        ("Cooling", str(len(cooling)), "Not urgent", "#88A3BB", _sparkline(_metric_wave(len(cooling)))),
    ]
    for col, (label, value, detail, accent, sparkline) in zip(kpi_cols, kpi_rows, strict=True):
        with col:
            _status_tile(label, value, detail, accent=accent, sparkline=sparkline, live=session_live)

    st.write("")
    left_col, center_col, right_col = st.columns([0.28, 0.46, 0.26], gap="large")

    with left_col:
        st.markdown(_rail_header("Actionable now", "Best-ranked names"), unsafe_allow_html=True)
        priority_rows = actionables[:5] if actionables else merged[:5]
        if priority_rows:
            for idx, signal in enumerate(priority_rows, start=1):
                _focus_card(
                    f"{idx}. {signal.symbol}",
                    _signal_summary(signal),
                    f"{_signal_state(signal)} | {(signal.volume_ratio or 0.0):.2f}x",
                    accent=_grade_color(signal.signal_grade),
                )
        else:
            callout("No setups", "No symbols cleared the current filters.")

    with center_col:
        st.markdown(_panel_header("Ranked decision board", "Scan speed over narration"), unsafe_allow_html=True)
        if merged:
            st.plotly_chart(_build_momentum_figure(list(merged[:8])), use_container_width=True, theme=None)
        else:
            callout("No chart", "No current signal momentum rows.")

        st.write("")
        st.markdown(_panel_header("Fast board", "Top names in one glance"), unsafe_allow_html=True)
        compact_table(_top_signal_rows(merged[:10]))

    with right_col:
        st.markdown(_rail_header("Regime filter", "Index pressure and fresh changes"), unsafe_allow_html=True)
        if index_rows:
            for row in index_rows[:2]:
                _event_card(
                    row.symbol,
                    f"{row.wall_type or 'N/A'} wall at {row.wall_strike or 0.0:,.0f}",
                    f"{row.proximity_pct or 0.0:.2f}% from spot | {row.bias or 'Neutral'}",
                    accent="#57b6ff" if row.symbol == "NIFTY" else "#9b8cff",
                )
        else:
            callout("No index context", "No current-expiry wall rows.")

        st.write("")
        regime_items = _signal_feed_items(merged, volume_rows, index_rows)
        if regime_items:
            st.markdown('<div class="nubra-feed" style="max-height: 24rem; overflow-y:auto; padding-right:0.2rem;">', unsafe_allow_html=True)
            for item in regime_items:
                _event_card(
                    item["title"],
                    item["body"],
                    f"{item['flag']} | {now}",
                    accent=_tone_color(item.get("tone", "blue")),
                )
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            callout("No feed items", "Waiting for the next market event set.")

    if used_cache:
        st.caption("Showing the latest stored snapshot for faster response.")


def _status_tile(
    label: str,
    value: str,
    detail: str,
    *,
    accent: str,
    sparkline: str,
    live: bool,
) -> None:
    live_chip = '<span class="nubra-chip tone-green">LIVE</span>' if live else ""
    st.markdown(
        f"""
        <div class="nubra-card nubra-stat-card" style="min-height:6.3rem;">
          <div class="nubra-stat-top">
            <div class="nubra-stat-label">{label}</div>
            <div class="nubra-stat-meta">{live_chip}</div>
          </div>
          <div class="nubra-stat-main">
            <div class="nubra-stat-value" style="color:{accent};">{value}</div>
            <div style="font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; color:{accent}; letter-spacing:0.08em;">{sparkline}</div>
          </div>
          <div class="nubra-subtle" style="margin-top:0.3rem;">{detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _focus_card(title: str, body: str, footer: str, *, accent: str) -> None:
    st.markdown(
        f"""
        <div style="
            border: 1px solid rgba(255,255,255,0.06);
            border-left: 3px solid {accent};
            border-radius: 10px;
            background: rgba(255,255,255,0.02);
            padding: 0.72rem 0.78rem;
            margin-bottom: 0.5rem;
        ">
          <div style="display:flex; justify-content:space-between; gap:0.4rem; align-items:start;">
            <div style="font-size:0.85rem; font-weight:700; color:#e8f1f8;">{title}</div>
            <div style="font-size:0.7rem; color:{accent}; text-transform:uppercase; letter-spacing:0.08em; font-weight:800;">{footer}</div>
          </div>
          <div style="font-size:0.78rem; color:#9aa9bb; margin-top:0.22rem; line-height:1.38;">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _event_card(title: str, body: str, footer: str, *, accent: str) -> None:
    st.markdown(
        f"""
        <div style="
            border: 1px solid rgba(255,255,255,0.06);
            border-left: 3px solid {accent};
            border-radius: 10px;
            background: rgba(255,255,255,0.02);
            padding: 0.68rem 0.76rem;
            margin-bottom: 0.45rem;
        ">
          <div style="display:flex; justify-content:space-between; gap:0.5rem; align-items:start;">
            <div style="font-size:0.84rem; font-weight:700; color:#e8f1f8;">{title}</div>
            <div style="font-size:0.66rem; color:#88a3bb; text-transform:uppercase; letter-spacing:0.08em; text-align:right;">{footer}</div>
          </div>
          <div style="font-size:0.78rem; color:#9aa9bb; line-height:1.38; margin-top:0.22rem;">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _rail_header(title: str, subtitle: str) -> str:
    return f"""
    <div style="margin-bottom:0.55rem;">
      <div style="font-size:0.72rem; color:#2ed3b7; text-transform:uppercase; letter-spacing:0.14em; font-weight:700;">{title}</div>
      <div style="font-size:0.76rem; color:#88a3bb; margin-top:0.12rem;">{subtitle}</div>
    </div>
    """


def _panel_header(title: str, subtitle: str) -> str:
    return f"""
    <div style="margin-bottom:0.55rem;">
      <div style="font-size:0.86rem; color:#e8f1f8; font-weight:800; letter-spacing:-0.02em;">{title}</div>
      <div style="font-size:0.76rem; color:#88a3bb; margin-top:0.12rem;">{subtitle}</div>
    </div>
    """


def _build_momentum_figure(rows: list[MergedSignal]) -> go.Figure:
    frame = pd.DataFrame(
        [
            {
                "symbol": row.symbol,
                "volume_ratio": float(row.volume_ratio or 0.0),
                "grade": row.signal_grade,
                "signal": row.signal_reason,
            }
            for row in rows
        ]
    )
    if frame.empty:
        return go.Figure()

    colors: list[str] = []
    for _, row in frame.iterrows():
        if row["grade"] == "A":
            colors.append("#22C55E")
        elif row["grade"] == "B":
            colors.append("#3B82F6")
        else:
            colors.append("#EF4444")

    fig = go.Figure()
    fig.add_bar(
        x=frame["volume_ratio"],
        y=frame["symbol"],
        orientation="h",
        marker=dict(color=colors, line=dict(color="rgba(255,255,255,0.12)", width=1)),
        customdata=frame[["grade", "signal"]],
        hovertemplate="<b>%{y}</b><br>Ratio %{x:.2f}x<br>Grade %{customdata[0]}<br>%{customdata[1]}<extra></extra>",
    )
    if not frame.empty:
        top_row = frame.iloc[0]
        fig.add_vline(x=float(top_row["volume_ratio"]), line_width=1, line_dash="dot", line_color="rgba(255,255,255,0.18)")
    fig.update_layout(
        height=460,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(
            title="Volume ratio",
            gridcolor="rgba(255,255,255,0.06)",
            zerolinecolor="rgba(255,255,255,0.08)",
            tickfont=dict(color="#9aa9bb"),
            title_font=dict(color="#9aa9bb"),
        ),
        yaxis=dict(
            title="Symbol",
            tickfont=dict(color="#e8f1f8", family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"),
            title_font=dict(color="#9aa9bb"),
        ),
        font=dict(color="#e8f1f8"),
    )
    return fig


def _signal_feed_items(
    merged: tuple[MergedSignal, ...],
    volume_rows: tuple[object, ...],
    index_rows: list[WallSignal],
) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    if merged:
        leader = merged[0]
        items.append(
            {
                "flag": "Top",
                "tone": "green",
                "title": leader.symbol,
                "body": f"{_signal_state(leader)} board. {leader.volume_ratio or 0.0:.2f}x participation.",
            }
        )
    items.append(
        {
            "flag": "Scan",
            "tone": "blue",
            "title": f"{len(volume_rows)} stock rows",
            "body": "Stock participation is ranked against the current basket baseline.",
        }
    )
    for row in index_rows[:2]:
        items.append(
            {
                "flag": row.symbol,
                "tone": "amber" if row.symbol == "NIFTY" else "blue",
                "title": f"{row.wall_type or 'N/A'} wall at {row.wall_strike or 0.0:.0f}",
                "body": f"{row.proximity_pct or 0.0:.2f}% from spot with {row.bias or 'Neutral'} tone.",
            }
        )
    if len(merged) > 1:
        next_signal = merged[1]
        items.append(
            {
                "flag": "Watch",
                "tone": "green",
                "title": next_signal.symbol,
                "body": f"{_signal_state(next_signal)} board with {next_signal.volume_ratio or 0.0:.2f}x activity.",
            }
        )
    return items[:5]


def _top_signal_rows(merged: tuple[MergedSignal, ...]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for signal in merged:
        rows.append(
            {
                "symbol": signal.symbol,
                "state": _signal_state(signal),
                "volume ratio": f"{signal.volume_ratio or 0.0:.2f}x",
                "desk note": _signal_summary(signal),
            }
        )
    return rows


def _grade_color(grade: str) -> str:
    return {"A": "#22C55E", "B": "#F8B84E", "C": "#3B82F6", "D": "#88A3BB"}.get(grade, "#88A3BB")


def _tone_color(tone: str) -> str:
    return {"green": "#22C55E", "blue": "#3B82F6", "amber": "#F8B84E"}.get(tone, "#3B82F6")


def _metric_wave(seed: int) -> list[int]:
    base = max(seed, 1)
    return [1, min(2, base), min(3, base + 1), min(4, base + 2), min(5, base + 3)]


def _sparkline(values: list[int]) -> str:
    blocks = "._-:=*#"
    if not values:
        return "....."
    top = max(values) or 1
    return "".join(blocks[min(len(blocks) - 1, max(0, int((value / top) * (len(blocks) - 1))))] for value in values)


def _resolve_regime_bias(index_rows: list[WallSignal]) -> str:
    if not index_rows:
        return "No regime read"
    bearish = sum(1 for row in index_rows if str(row.bias or "").lower().startswith("bear"))
    bullish = sum(1 for row in index_rows if str(row.bias or "").lower().startswith("bull"))
    if bearish > bullish:
        return "Bearish pressure"
    if bullish > bearish:
        return "Bullish pressure"
    return "Balanced pressure"


def _regime_accent(regime_bias: str) -> str:
    if "Bullish" in regime_bias:
        return "#24c48e"
    if "Balanced" in regime_bias:
        return "#f8b84e"
    return "#ff6b6b"


def _signal_state(signal: MergedSignal) -> str:
    ratio = signal.volume_ratio or 0.0
    if ratio >= 2.0:
        return "Actionable"
    if ratio >= 1.5:
        return "Watch"
    if ratio >= 1.1:
        return "Build"
    return "Cold"


def _signal_summary(signal: MergedSignal) -> str:
    ratio = signal.volume_ratio or 0.0
    if ratio >= 2.0:
        return "Strong participation. Prioritize only if the symbol is still close to its trigger."
    if ratio >= 1.5:
        return "Momentum is building. Keep it on the front board and watch for clean continuation."
    if ratio >= 1.1:
        return "Participation is improving, but it still needs confirmation before it belongs in execution prep."
    return "Activity is present, but the move is not strong enough to force attention."
