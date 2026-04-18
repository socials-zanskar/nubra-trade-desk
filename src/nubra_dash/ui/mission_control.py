from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from nubra_dash.config import AppConfig
from nubra_dash.models import MergedSignal, WallSignal
from nubra_dash.ui.theme import get_plotly_palette
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
    eod_summary = snapshot.get("eod_summary")

    if snapshot.get("is_post_close") and eod_summary:
        _render_eod_mission_control(
            eod_summary=eod_summary,
            selected_symbols=selected_symbols,
            auth_session=auth_session,
            used_cache=used_cache,
        )
        return

    actionables = [signal for signal in merged if (signal.volume_ratio or 0.0) >= 1.5]
    watchers = [signal for signal in merged if 1.1 <= (signal.volume_ratio or 0.0) < 1.5]
    cooling = [signal for signal in merged if (signal.volume_ratio or 0.0) < 1.1]
    regime_bias = _resolve_regime_bias(index_rows)
    session_live = bool(auth_session and auth_session.is_available)
    now = datetime.now().strftime("%I:%M %p")

    st.markdown(
        f"""
        <div class="nubra-desk-hero">
          <div class="nubra-kicker">Mission control</div>
          <h1 class="nubra-desk-title">Desk first. Symbols second.</h1>
          <p class="nubra-desk-copy">
            Read the strongest names, the board state, and the index backdrop in one pass.
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
        st.markdown(_rail_header("Front board", "Best-ranked names right now"), unsafe_allow_html=True)
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
        st.markdown(_panel_header("Signal board", "Fast ranking, minimal narration"), unsafe_allow_html=True)
        if merged:
            st.plotly_chart(_build_momentum_figure(list(merged[:8])), width="stretch", theme=None)
        else:
            callout("No chart", "No current signal momentum rows.")

        st.write("")
        st.markdown(_panel_header("Quick table", "Top names in one glance"), unsafe_allow_html=True)
        compact_table(_top_signal_rows(merged[:10]))

    with right_col:
        st.markdown(_rail_header("Backdrop", "Index pressure and fresh changes"), unsafe_allow_html=True)
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


def _render_eod_mission_control(
    *,
    eod_summary: dict[str, object],
    selected_symbols: tuple[str, ...],
    auth_session,
    used_cache: bool,
) -> None:
    summary = dict(eod_summary.get("summary") or {})
    leaders = tuple(eod_summary.get("leaders") or ())
    regime_bias = _resolve_eod_bias(summary)
    close_note = _close_snapshot_label(summary.get("scanned_at"))
    session_live = bool(auth_session and auth_session.is_available)
    priority_leaders = leaders[:5]

    st.markdown(
        f"""
        <div class="nubra-desk-hero">
          <div class="nubra-kicker">Close summary</div>
          <h1 class="nubra-desk-title">Close summary</h1>
          <p class="nubra-subtle nubra-mission-copy">
            <span class="nubra-chip tone-blue">{len(selected_symbols)} names tracked</span>
            <span class="nubra-chip tone-green">{summary.get("priority_signals", 0)} priority setups</span>
            <span class="nubra-chip tone-cyan">{summary.get("top_symbol") or "No leader"}</span>
            <span class="nubra-chip tone-purple">{close_note}</span>
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    kpi_cols = st.columns(4, gap="small")
    kpi_rows = [
        ("Top symbol", str(summary.get("top_symbol") or "None"), "Best name into the close", "#57b6ff", _sparkline(_metric_wave(len(leaders) or 1))),
        ("Priority", str(summary.get("priority_signals") or 0), "Signals that stayed front-board", "#22C55E", _sparkline(_metric_wave(int(summary.get("priority_signals") or 0)))),
        ("Top ratio", f"{float(summary.get('top_volume_ratio') or 0.0):.2f}x", "Best participation print today", "#F8B84E", _sparkline(_metric_wave(int(float(summary.get('top_volume_ratio') or 0.0) * 2) or 1))),
        ("Regime", regime_bias, "Index pressure at the close", _regime_accent(regime_bias), _sparkline(_metric_wave(2 if 'Balanced' in regime_bias else 4))),
    ]
    for col, (label, value, detail, accent, sparkline) in zip(kpi_cols, kpi_rows, strict=True):
        with col:
            _status_tile(label, value, detail, accent=accent, sparkline=sparkline, live=session_live)

    st.write("")
    left_col, center_col, right_col = st.columns([0.25, 0.5, 0.25], gap="large")

    with left_col:
        st.markdown(_rail_header("Immediate focus", "Leaders worth revisiting"), unsafe_allow_html=True)
        if priority_leaders:
            for row in priority_leaders:
                _focus_card(
                    f"{row.get('rank', '-')}. {row.get('symbol', 'Unknown')}",
                    row.get("signal_reason") or "Stored EOD leader.",
                    f"{row.get('action_state') or 'Watch'} | {float(row.get('volume_ratio') or 0.0):.2f}x",
                    accent=_grade_color(str(row.get("signal_grade") or "C")),
                )
        else:
            callout("No leaders saved", "The post-close summary will populate here once an EOD sync completes.")

    with center_col:
        st.markdown(_panel_header("Close board", "Top setups at the bell"), unsafe_allow_html=True)
        if leaders:
            st.plotly_chart(_build_eod_momentum_figure(leaders[:8]), width="stretch", theme=None)
            st.write("")
            st.markdown(_panel_header("Priority table", "Clean summary of today's strongest names"), unsafe_allow_html=True)
            compact_table(_top_eod_rows(leaders[:10]))
        else:
            callout("No close board", "No leaders were stored for the current trading day.")

    with right_col:
        st.markdown(_rail_header("Index pressure", "NIFTY and SENSEX at close"), unsafe_allow_html=True)
        for item in _eod_index_events(summary):
            _event_card(item["title"], item["body"], item["footer"], accent=item["accent"])

        st.write("")
        st.markdown(_rail_header("Market feed", "Close-time takeaways"), unsafe_allow_html=True)
        st.markdown('<div class="nubra-feed" style="max-height: 24rem; overflow-y:auto; padding-right:0.2rem;">', unsafe_allow_html=True)
        for item in _eod_feed_items(summary, leaders):
            _event_card(item["title"], item["body"], item["footer"], accent=item["accent"])
        st.markdown("</div>", unsafe_allow_html=True)

    if used_cache:
        st.caption("Showing the latest stored close snapshot for fast response.")


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
            <div style="font-size:0.85rem; font-weight:700; color:var(--color-text);">{title}</div>
            <div style="font-size:0.7rem; color:{accent}; text-transform:uppercase; letter-spacing:0.08em; font-weight:800;">{footer}</div>
          </div>
          <div style="font-size:0.78rem; color:var(--color-muted); margin-top:0.22rem; line-height:1.38;">{body}</div>
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
            <div style="font-size:0.84rem; font-weight:700; color:var(--color-text);">{title}</div>
            <div style="font-size:0.66rem; color:var(--color-muted); text-transform:uppercase; letter-spacing:0.08em; text-align:right;">{footer}</div>
          </div>
          <div style="font-size:0.78rem; color:var(--color-muted); line-height:1.38; margin-top:0.22rem;">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _rail_header(title: str, subtitle: str) -> str:
    return f"""
    <div style="margin-bottom:0.55rem;">
      <div style="font-size:0.72rem; color:#2ed3b7; text-transform:uppercase; letter-spacing:0.14em; font-weight:700;">{title}</div>
      <div style="font-size:0.76rem; color:var(--color-muted); margin-top:0.12rem;">{subtitle}</div>
    </div>
    """


def _panel_header(title: str, subtitle: str) -> str:
    return f"""
    <div style="margin-bottom:0.55rem;">
      <div style="font-size:0.86rem; color:var(--color-text); font-weight:800; letter-spacing:-0.02em;">{title}</div>
      <div style="font-size:0.76rem; color:var(--color-muted); margin-top:0.12rem;">{subtitle}</div>
    </div>
    """


def _build_momentum_figure(rows: list[MergedSignal]) -> go.Figure:
    colorscheme = get_plotly_palette()
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
            colors.append(colorscheme["success"])
        elif row["grade"] == "B":
            colors.append(colorscheme["accent_2"])
        else:
            colors.append(colorscheme["danger"])

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
        fig.add_vline(x=float(top_row["volume_ratio"]), line_width=1, line_dash="dot", line_color=colorscheme["zero"])
    fig.update_layout(
        height=460,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor=colorscheme["bg"],
        plot_bgcolor=colorscheme["bg"],
        showlegend=False,
        xaxis=dict(
            title="Volume ratio",
            gridcolor=colorscheme["grid"],
            zerolinecolor=colorscheme["zero"],
            tickfont=dict(color=colorscheme["muted"]),
            title_font=dict(color=colorscheme["muted"]),
        ),
        yaxis=dict(
            title="Symbol",
            tickfont=dict(color=colorscheme["text"], family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"),
            title_font=dict(color=colorscheme["muted"]),
        ),
        font=dict(color=colorscheme["text"]),
    )
    return fig


def _build_eod_momentum_figure(rows: tuple[dict[str, object], ...] | list[dict[str, object]]) -> go.Figure:
    colorscheme = get_plotly_palette()
    frame = pd.DataFrame(
        [
            {
                "symbol": row.get("symbol"),
                "volume_ratio": float(row.get("volume_ratio") or 0.0),
                "grade": row.get("signal_grade"),
                "signal": row.get("signal_reason"),
            }
            for row in rows
        ]
    )
    if frame.empty:
        return go.Figure()

    colors = [_grade_color(str(grade or "C")) for grade in frame["grade"]]
    fig = go.Figure()
    fig.add_bar(
        x=frame["volume_ratio"],
        y=frame["symbol"],
        orientation="h",
        marker=dict(color=colors, line=dict(color="rgba(255,255,255,0.12)", width=1)),
        customdata=frame[["grade", "signal"]],
        hovertemplate="<b>%{y}</b><br>Ratio %{x:.2f}x<br>Grade %{customdata[0]}<br>%{customdata[1]}<extra></extra>",
    )
    fig.update_layout(
        height=460,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor=colorscheme["bg"],
        plot_bgcolor=colorscheme["bg"],
        showlegend=False,
        xaxis=dict(
            title="Volume ratio",
            gridcolor=colorscheme["grid"],
            zerolinecolor=colorscheme["zero"],
            tickfont=dict(color=colorscheme["muted"]),
            title_font=dict(color=colorscheme["muted"]),
        ),
        yaxis=dict(
            title="Symbol",
            tickfont=dict(color=colorscheme["text"], family="ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"),
            title_font=dict(color=colorscheme["muted"]),
        ),
        font=dict(color=colorscheme["text"]),
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


def _top_eod_rows(rows: tuple[dict[str, object], ...] | list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "symbol": row.get("symbol"),
            "state": row.get("action_state") or "Watch",
            "grade": row.get("signal_grade") or "C",
            "volume ratio": f"{float(row.get('volume_ratio') or 0.0):.2f}x",
            "desk note": row.get("signal_reason") or "Stored EOD leader.",
        }
        for row in rows
    ]


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


def _resolve_eod_bias(summary: dict[str, object]) -> str:
    biases = [str(summary.get("nifty_bias") or ""), str(summary.get("sensex_bias") or "")]
    bearish = sum(1 for bias in biases if bias.lower().startswith("bear"))
    bullish = sum(1 for bias in biases if bias.lower().startswith("bull"))
    if bearish > bullish:
        return "Bearish pressure"
    if bullish > bearish:
        return "Bullish pressure"
    return "Balanced pressure"


def _close_snapshot_label(scanned_at: object) -> str:
    if not scanned_at:
        return "Close snapshot pending"
    return f"Close stored {str(scanned_at)[:16].replace('T', ' ')}"


def _eod_index_events(summary: dict[str, object]) -> list[dict[str, str]]:
    items = []
    nifty_title = f"NIFTY | {summary.get('nifty_wall_type') or 'N/A'} {float(summary.get('nifty_wall_strike') or 0.0):.0f}"
    sensex_title = f"SENSEX | {summary.get('sensex_wall_type') or 'N/A'} {float(summary.get('sensex_wall_strike') or 0.0):.0f}"
    items.append(
        {
            "title": nifty_title,
            "body": str(summary.get("nifty_bias") or "No closing wall bias saved."),
            "footer": "NIFTY close",
            "accent": "#3B82F6",
        }
    )
    items.append(
        {
            "title": sensex_title,
            "body": str(summary.get("sensex_bias") or "No closing wall bias saved."),
            "footer": "SENSEX close",
            "accent": "#9b8cff",
        }
    )
    return items


def _eod_feed_items(summary: dict[str, object], leaders: tuple[dict[str, object], ...]) -> list[dict[str, str]]:
    items = [
        {
            "title": "Top close leader",
            "body": f"{summary.get('top_symbol') or 'No leader'} closed as the strongest stored setup with {float(summary.get('top_volume_ratio') or 0.0):.2f}x participation.",
            "footer": "Leader | close",
            "accent": "#22C55E",
        },
        {
            "title": "Priority count",
            "body": f"{int(summary.get('priority_signals') or 0)} names held priority status into the final stored snapshot.",
            "footer": "Board | close",
            "accent": "#F8B84E",
        },
    ]
    for row in leaders[:3]:
        items.append(
            {
                "title": str(row.get("symbol") or "Leader"),
                "body": str(row.get("signal_reason") or "Stored EOD leader."),
                "footer": f"{row.get('action_state') or 'Watch'} | {float(row.get('volume_ratio') or 0.0):.2f}x",
                "accent": _grade_color(str(row.get("signal_grade") or "C")),
            }
        )
    return items[:5]
