from __future__ import annotations

import hashlib
import json
import time
from datetime import datetime
from typing import Iterable

import streamlit as st

from nubra_dash.services import get_dashboard_snapshot, refresh_database_snapshot


def load_live_snapshot(
    config,
    symbols: Iterable[str],
    *,
    ttl_seconds: int | None = None,
    live_auth: bool = False,
    prefer_database: bool = True,
):
    """Load and briefly cache live scanner results for responsive pages."""
    chosen_symbols = tuple(symbols)
    ttl = ttl_seconds or config.scans.refresh_seconds
    cache_key = _make_cache_key(config.auth.environment, chosen_symbols, live_auth=live_auth, prefer_database=prefer_database)
    now = time.time()

    cached = st.session_state.get(cache_key)
    if cached:
        if prefer_database and not live_auth:
            return cached["snapshot"], True
        if now - cached["ts"] < ttl:
            return cached["snapshot"], True

    snapshot = get_dashboard_snapshot(
        config,
        chosen_symbols,
        live_auth=live_auth,
        prefer_database=prefer_database,
    )
    st.session_state[cache_key] = {"ts": now, "snapshot": snapshot}
    return snapshot, False


def load_snapshot_with_feedback(
    message: str,
    config,
    symbols: Iterable[str],
    *,
    ttl_seconds: int | None = None,
    live_auth: bool = False,
    prefer_database: bool = True,
):
    if has_cached_snapshot(config, symbols, live_auth=live_auth, prefer_database=prefer_database):
        return load_live_snapshot(
            config,
            symbols,
            ttl_seconds=ttl_seconds,
            live_auth=live_auth,
            prefer_database=prefer_database,
        )
    with st.spinner(message):
        return load_live_snapshot(
            config,
            symbols,
            ttl_seconds=ttl_seconds,
            live_auth=live_auth,
            prefer_database=prefer_database,
        )


def has_cached_snapshot(
    config,
    symbols: Iterable[str],
    *,
    live_auth: bool = False,
    prefer_database: bool = True,
) -> bool:
    cache_key = _make_cache_key(
        config.auth.environment,
        tuple(symbols),
        live_auth=live_auth,
        prefer_database=prefer_database,
    )
    return cache_key in st.session_state


def render_refresh_bar(
    page_key: str,
    config,
    symbols: Iterable[str],
    *,
    live_auth: bool = False,
    prefer_database: bool = True,
) -> None:
    chosen_symbols = tuple(symbols)
    cached = st.session_state.get(
        _make_cache_key(
            config.auth.environment,
            chosen_symbols,
            live_auth=live_auth,
            prefer_database=prefer_database,
        )
    )
    snapshot = cached.get("snapshot") if cached else None
    generated_at = snapshot.get("generated_at") if snapshot else None
    data_source = snapshot.get("data_source") if snapshot else None
    data_present = _snapshot_has_visible_data(snapshot)
    last_updated = generated_at.strftime("%d %b %I:%M %p") if isinstance(generated_at, datetime) else ("Ready in session" if data_present else "Waiting for refresh")
    freshness = _format_snapshot_age(generated_at) if isinstance(generated_at, datetime) else ("Session view" if data_present else "No snapshot yet")
    status_label = _resolve_status_label(
        data_source=data_source,
        live_auth=live_auth,
        generated_at=generated_at,
        data_present=data_present,
    )
    mode_label = "Live" if data_source == "live" else "Stored"

    st.markdown(
        f"""
        <div class="nubra-refresh-bar trader-strip">
          <div class="nubra-refresh-cluster">
            <span class="nubra-status-dot"></span>
            <span class="nubra-refresh-strong">{status_label}</span>
            <span class="nubra-refresh-chip">{mode_label}</span>
            <span class="nubra-refresh-meta">Age {freshness}</span>
            <span class="nubra-refresh-meta">Updated {last_updated}</span>
          </div>
          <div class="nubra-refresh-side">
            Reload fetches the latest shared view. Upstream refresh is admin-only.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    admin_refresh_enabled = bool(getattr(config.scans, "enable_admin_refresh", False) and prefer_database and _database_is_configured(config))
    if admin_refresh_enabled:
        left, admin_col, middle, right = st.columns([0.12, 0.16, 0.39, 0.33], gap="small")
    else:
        left, middle, right = st.columns([0.13, 0.52, 0.35], gap="small")
    with left:
        if st.button("Reload", key=f"{page_key}_reload", width="stretch", type="primary"):
            clear_snapshot_cache(config, chosen_symbols, live_auth=live_auth, prefer_database=prefer_database)
            st.rerun()
    if admin_refresh_enabled:
        with admin_col:
            if st.button("Refresh upstream", key=f"{page_key}_upstream_refresh", width="stretch"):
                clear_snapshot_cache(config, chosen_symbols, live_auth=False, prefer_database=True)
                with st.spinner("Running admin snapshot refresh..."):
                    refresh_database_snapshot(config, chosen_symbols)
                st.rerun()
    with middle:
        st.markdown(
            '<div class="nubra-inline-note">Use Reload when you want the newest stored snapshot without waiting for a full page session reset.</div>',
            unsafe_allow_html=True,
        )
    with right:
        right_note = "Stored mode is the default product path: fast, shared, and stable."
        if admin_refresh_enabled:
            right_note = "Admin upstream refresh writes a new shared snapshot for everyone. Most users should stay on stored mode."
        st.markdown(
            f'<div class="nubra-inline-note" style="text-align:right;">{right_note}</div>',
            unsafe_allow_html=True,
        )


def clear_snapshot_cache(config, symbols: Iterable[str], *, live_auth: bool = False, prefer_database: bool = True) -> None:
    cache_key = _make_cache_key(
        config.auth.environment,
        tuple(symbols),
        live_auth=live_auth,
        prefer_database=prefer_database,
    )
    st.session_state.pop(cache_key, None)


def _make_cache_key(environment: str, symbols: tuple[str, ...], *, live_auth: bool, prefer_database: bool) -> str:
    payload = {
        "environment": environment,
        "symbols": symbols,
        "live_auth": live_auth,
        "prefer_database": prefer_database,
    }
    digest = hashlib.md5(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return f"nubra_snapshot_{digest}"


def _database_is_configured(config) -> bool:
    db = getattr(config, "database", None)
    return bool(db and (db.url or db.host))


def _format_snapshot_age(generated_at: datetime) -> str:
    now = datetime.now(generated_at.tzinfo) if generated_at.tzinfo else datetime.now()
    age_seconds = max(0, int((now - generated_at).total_seconds()))
    if age_seconds < 60:
        return f"{age_seconds}s ago"
    if age_seconds < 3600:
        return f"{age_seconds // 60}m ago"
    hours = age_seconds // 3600
    minutes = (age_seconds % 3600) // 60
    return f"{hours}h {minutes}m ago"


def _resolve_status_label(
    *,
    data_source: str | None,
    live_auth: bool,
    generated_at: datetime | None,
    data_present: bool,
) -> str:
    if generated_at is None:
        return "Session view ready" if data_present else "Sync pending"
    if data_source == "live":
        return "Live context"
    if live_auth:
        return "Snapshot + live context"
    return "Stored snapshot"


def _snapshot_has_visible_data(snapshot: dict[str, object] | None) -> bool:
    if not snapshot:
        return False
    merged = tuple(snapshot.get("merged_signals") or ())
    volume_rows = tuple(getattr(snapshot.get("volume_batch"), "rows", ()) or ())
    wall_rows = tuple(getattr(snapshot.get("index_wall_batch"), "rows", ()) or ())
    eod = snapshot.get("eod_summary") or {}
    leaders = tuple(eod.get("leaders") or ()) if isinstance(eod, dict) else ()
    return bool(merged or volume_rows or wall_rows or leaders)
