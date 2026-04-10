from __future__ import annotations

import html
from collections.abc import Iterable, Mapping, Sequence

import pandas as pd
import streamlit as st

from nubra_dash.ui.theme import PALETTE


def pill(text: str) -> str:
    return status_chip(text, tone="green")


def status_chip(text: str, *, tone: str = "blue") -> str:
    tone_class = _tone_class(tone)
    safe = html.escape(text)
    return f'<span class="nubra-chip {tone_class}">{safe}</span>'


def hero(title: str, subtitle: str, tags: Iterable[str] = ()) -> None:
    tag_html = "".join(pill(tag) for tag in tags)
    st.markdown(
        f"""
        <div class="nubra-hero">
          <div class="nubra-kicker">Nubra Signal Discovery</div>
          <h1 class="nubra-hero-title">{html.escape(title)}</h1>
          <p class="nubra-subtle nubra-hero-copy">{html.escape(subtitle)}</p>
          <div class="nubra-chip-row">{tag_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(
    label: str,
    value: str,
    detail: str,
    accent: str = PALETTE.cyan,
    *,
    trend: str | None = None,
    sparkline_values: Sequence[float] | None = None,
) -> None:
    trend_markup = _trend_markup(trend)
    sparkline_markup = _sparkline_svg(sparkline_values, accent) if sparkline_values else ""
    st.markdown(
        f"""
        <div class="nubra-card nubra-metric-card">
          <div class="nubra-metric-head">
            <div class="nubra-metric-label">{html.escape(label)}</div>
            <div class="nubra-metric-meta">{trend_markup}</div>
          </div>
          <div class="nubra-metric-body">
            <div class="nubra-metric-value" style="color: {accent};">{html.escape(value)}</div>
            <div class="nubra-metric-spark">{sparkline_markup}</div>
          </div>
          <div class="nubra-subtle nubra-metric-detail">{html.escape(detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str | None = None) -> None:
    st.markdown(f"### {html.escape(title)}")
    if subtitle:
        st.caption(subtitle)


def callout(title: str, body: str) -> None:
    st.markdown(
        f"""
        <div class="nubra-callout">
          <div class="nubra-callout-title">{html.escape(title)}</div>
          <div class="nubra-subtle">{html.escape(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def mission_banner(title: str, subtitle: str, tags: Iterable[str] = ()) -> None:
    tag_html = "".join(status_chip(tag, tone="cyan") for tag in tags)
    st.markdown(
        f"""
        <div class="nubra-mission">
          <div class="nubra-kicker">Mission Control</div>
          <div class="nubra-mission-grid">
            <div class="nubra-mission-main">
              <h1 class="nubra-mission-title">{html.escape(title)}</h1>
              <p class="nubra-subtle nubra-mission-copy">{html.escape(subtitle)}</p>
            </div>
            <div class="nubra-mission-tags">{tag_html}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_card(
    label: str,
    value: str,
    detail: str,
    accent: str = PALETTE.cyan,
    tone: str | None = None,
    badge: str | None = None,
    *,
    trend: str | None = None,
    sparkline_values: Sequence[float] | None = None,
) -> None:
    badge_markup = status_chip(badge, tone=tone or "blue") if badge else ""
    trend_markup = _trend_markup(trend)
    sparkline_markup = _sparkline_svg(sparkline_values, accent) if sparkline_values else ""
    st.markdown(
        f"""
        <div class="nubra-card nubra-stat-card">
          <div class="nubra-stat-top">
            <div class="nubra-stat-label">{html.escape(label)}</div>
            <div class="nubra-stat-meta">{badge_markup}{trend_markup}</div>
          </div>
          <div class="nubra-stat-main">
            <div class="nubra-stat-value" style="color: {accent};">{html.escape(value)}</div>
            <div class="nubra-stat-spark">{sparkline_markup}</div>
          </div>
          <div class="nubra-subtle nubra-stat-detail">{html.escape(detail)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def signal_feed(items: Iterable[Mapping[str, str]]) -> None:
    st.markdown('<div class="nubra-feed">', unsafe_allow_html=True)
    for item in items:
        tone = item.get("tone", "blue")
        title = item.get("title", "")
        body = item.get("body", "")
        flag = item.get("flag", "")
        timestamp = item.get("timestamp", "")
        icon = item.get("icon", "•")
        st.markdown(
            f"""
            <div class="nubra-feed-item { _tone_class(tone) }">
              <div class="nubra-feed-title-row">
                <strong><span class="nubra-feed-icon">{html.escape(icon)}</span> <span class="nubra-chip {_tone_class(tone)}">{html.escape(flag)}</span> {html.escape(title)}</strong>
                <span class="nubra-feed-time">{html.escape(timestamp)}</span>
              </div>
              <span class="nubra-feed-body">{html.escape(body)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def compact_table(data, *, use_container_width: bool = True, hide_index: bool = True) -> None:
    frame = pd.DataFrame(data)
    st.dataframe(
        frame,
        use_container_width=use_container_width,
        hide_index=hide_index,
        height=min(460, 44 + len(frame) * 32) if not frame.empty else 168,
    )


def dataframe_card(data, *, use_container_width: bool = True, hide_index: bool = True) -> None:
    frame = pd.DataFrame(data)
    st.dataframe(frame, use_container_width=use_container_width, hide_index=hide_index)


def _tone_class(tone: str) -> str:
    return {
        "green": "tone-green",
        "blue": "tone-blue",
        "amber": "tone-amber",
        "red": "tone-red",
        "cyan": "tone-cyan",
        "purple": "tone-purple",
    }.get(tone, "tone-blue")


def _trend_markup(trend: str | None) -> str:
    if not trend:
        return ""
    safe = html.escape(trend)
    tone = "tone-green" if trend.strip().startswith("+") else "tone-red" if trend.strip().startswith("-") else "tone-blue"
    return f'<span class="nubra-trend {tone}">{safe}</span>'


def _sparkline_svg(values: Sequence[float] | None, accent: str) -> str:
    series = [float(value) for value in values or () if value is not None]
    if len(series) < 2:
        return ""

    width = 120
    height = 28
    min_value = min(series)
    max_value = max(series)
    span = max(max_value - min_value, 1e-6)
    points = []
    for index, value in enumerate(series):
        x = (index / (len(series) - 1)) * width
        y = height - (((value - min_value) / span) * (height - 4) + 2)
        points.append(f"{x:.2f},{y:.2f}")
    polyline = " ".join(points)
    escaped = html.escape(accent)
    return (
        f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="none" class="nubra-sparkline" aria-hidden="true">'
        f'<polyline fill="none" stroke="{escaped}" stroke-width="2" points="{polyline}" />'
        f"</svg>"
    )
