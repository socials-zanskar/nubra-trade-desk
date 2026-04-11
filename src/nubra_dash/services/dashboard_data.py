"""High-level data facade for the Streamlit pages."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

from ..config import AppConfig, INDEX_WALL_SYMBOLS
from ..models import AuthSession, MergedSignal, ScanResultBatch, VolumeSignal, WallSignal
from .auth import load_auth_session
from .db import (
    apply_schema,
    connect_db,
    load_latest_index_ladder_snapshots,
    load_latest_index_multi_wall_batch,
    load_latest_index_wall_batch,
    load_latest_market_eod_summary,
    load_latest_signal_board,
    load_latest_symbol_drilldowns,
    load_latest_volume_batch,
    load_recent_alert_events,
    load_watchlist_symbols,
    save_watchlist_symbols as save_watchlist_symbols_db,
    store_index_multi_walls,
    store_symbol_drilldowns,
    store_signal_board,
    store_index_ladders,
    store_index_walls,
    store_volume_batches,
    upsert_symbols,
)
from .merge import merge_signals
from .oi_walls import run_multi_wall_scan, run_oi_walls_scan
from .option_chain import fetch_index_option_chains
from .volume_breakout import run_volume_breakout_scan

ROOT = Path(__file__).resolve().parents[3]
SUPABASE_SCHEMA = ROOT / "supabase" / "schema.sql"


def get_dashboard_snapshot(
    app_config: AppConfig,
    symbols: Iterable[str] | None = None,
    *,
    live_auth: bool = False,
    prefer_database: bool = True,
) -> dict[str, object]:
    """Return a page-friendly bundle of auth, scanner, and merged results."""
    chosen_symbols = tuple(symbols or app_config.scans.demo_symbols)
    if prefer_database and _database_is_configured(app_config):
        database_snapshot = _load_database_snapshot(app_config, chosen_symbols, live_auth=live_auth)
        if database_snapshot is not None:
            return database_snapshot
        if not live_auth:
            return _empty_database_snapshot(app_config, chosen_symbols)

    auth_session = load_auth_session(app_config.auth)

    if auth_session and auth_session.is_available and auth_session.market_data is not None:
        volume_batch = run_volume_breakout_scan(
            auth_session.market_data,
            chosen_symbols,
            lookback_days=app_config.scans.lookback_days,
            interval=app_config.scans.volume_interval,
            rank=app_config.scans.breakout_rank,
            exchange=app_config.scans.exchange,
        )
        index_wall_batch = run_oi_walls_scan(
            auth_session.market_data,
            INDEX_WALL_SYMBOLS,
            normalize=False,
            exchange=app_config.scans.exchange,
        )
        index_multi_wall_batch = run_multi_wall_scan(
            auth_session.market_data,
            INDEX_WALL_SYMBOLS,
            top_n=app_config.scans.multi_wall_top_n,
            normalize=False,
            exchange=app_config.scans.exchange,
        )
    else:
        error = auth_session.error if auth_session else "Unknown Nubra session error."
        volume_batch = ScanResultBatch(source="nubra_volume_breakout", errors=(error,))
        index_wall_batch = ScanResultBatch(source="nubra_oi_walls", errors=(error,))
        index_multi_wall_batch = ScanResultBatch(source="nubra_oi_walls_multi", errors=(error,))

    merged = merge_signals(
        [row for row in volume_batch.rows if isinstance(row, VolumeSignal)],
        [],
        regime_signals=[row for row in index_wall_batch.rows if isinstance(row, WallSignal)],
    )

    return {
        "auth_session": auth_session,
        "volume_batch": volume_batch,
        "wall_batch": index_wall_batch,
        "multi_wall_batch": index_multi_wall_batch,
        "stock_wall_batch": ScanResultBatch(source="stock_oi_disabled"),
        "stock_multi_wall_batch": ScanResultBatch(source="stock_oi_disabled"),
        "index_wall_batch": index_wall_batch,
        "index_multi_wall_batch": index_multi_wall_batch,
        "merged_signals": merged,
        "symbols": chosen_symbols,
        "index_symbols": INDEX_WALL_SYMBOLS,
        "index_ladders": (),
        "alert_events": tuple(_ephemeral_alert_events(merged)),
        "watchlist_symbols": (),
        "drilldown_summaries": _ephemeral_drilldown_summaries(merged, exchange=app_config.scans.exchange),
        "generated_at": datetime.now(),
        "is_demo": False,
        "data_source": "live",
        "eod_summary": None,
        "is_post_close": _is_post_close_now(),
    }


def refresh_database_snapshot(
    app_config: AppConfig,
    symbols: Iterable[str] | None = None,
) -> dict[str, int]:
    chosen_symbols = tuple(symbols or app_config.scans.demo_symbols)
    auth_session = load_auth_session(app_config.auth)
    if not auth_session.is_available or auth_session.market_data is None:
        raise RuntimeError(auth_session.error or "Nubra auth failed for snapshot refresh.")

    generated_at = datetime.now(UTC)
    volume_batch = run_volume_breakout_scan(
        auth_session.market_data,
        chosen_symbols,
        lookback_days=app_config.scans.lookback_days,
        interval=app_config.scans.volume_interval,
        rank=app_config.scans.breakout_rank,
        exchange=app_config.scans.exchange,
    )
    index_wall_batch = run_oi_walls_scan(
        auth_session.market_data,
        INDEX_WALL_SYMBOLS,
        normalize=False,
        exchange=app_config.scans.exchange,
    )
    option_chains = fetch_index_option_chains(auth_session.market_data)
    merged_signals = merge_signals(
        [row for row in volume_batch.rows if isinstance(row, VolumeSignal)],
        [],
        regime_signals=[row for row in index_wall_batch.rows if isinstance(row, WallSignal)],
    )

    with connect_db(app_config.database) as connection:
        apply_schema(connection, SUPABASE_SCHEMA.read_text(encoding="utf-8"))
        symbols_upserted = upsert_symbols(connection, _symbol_seed_rows(chosen_symbols, exchange=app_config.scans.exchange))
        volume_latest, _ = store_volume_batches(
            connection,
            scanned_at=generated_at,
            interval=app_config.scans.volume_interval,
            lookback_days=app_config.scans.lookback_days,
            batch=volume_batch,
        )
        index_latest, _ = store_index_walls(
            connection,
            scanned_at=generated_at,
            batch=index_wall_batch,
        )
        signal_latest, _, transition_rows, alert_rows = store_signal_board(
            connection,
            scanned_at=generated_at,
            signals=merged_signals,
        )
        drilldown_latest, _ = store_symbol_drilldowns(
            connection,
            scanned_at=generated_at,
            exchange=app_config.scans.exchange,
            signals=merged_signals,
        )
        index_multi_latest, _ = store_index_multi_walls(
            connection,
            scanned_at=generated_at,
            batch=run_multi_wall_scan(
                auth_session.market_data,
                INDEX_WALL_SYMBOLS,
                top_n=app_config.scans.multi_wall_top_n,
                normalize=False,
                exchange=app_config.scans.exchange,
            ),
        )
        ladder_latest, _ = store_index_ladders(
            connection,
            scanned_at=generated_at,
            snapshots=option_chains,
        )
    return {
        "symbols_upserted": symbols_upserted,
        "volume_rows": volume_latest,
        "signal_board_rows": signal_latest,
        "signal_transition_rows": transition_rows,
        "alert_event_rows": alert_rows,
        "index_wall_rows": index_latest,
        "index_multi_wall_rows": index_multi_latest,
        "index_ladder_rows": ladder_latest,
        "drilldown_rows": drilldown_latest,
    }


def _load_database_snapshot(
    app_config: AppConfig,
    chosen_symbols: tuple[str, ...],
    *,
    live_auth: bool,
) -> dict[str, object] | None:
    try:
        with connect_db(app_config.database) as connection:
            volume_batch, volume_time = load_latest_volume_batch(connection, chosen_symbols)
            index_wall_batch, wall_time = load_latest_index_wall_batch(connection, INDEX_WALL_SYMBOLS)
            merged_signals, signal_time = load_latest_signal_board(connection, chosen_symbols)
            index_multi_wall_batch, multi_wall_time = load_latest_index_multi_wall_batch(connection, INDEX_WALL_SYMBOLS)
            ladder_snapshots = load_latest_index_ladder_snapshots(connection, INDEX_WALL_SYMBOLS)
            alert_events = load_recent_alert_events(connection, symbols=chosen_symbols)
            watchlist_symbols = load_watchlist_symbols(connection)
            drilldown_summaries = load_latest_symbol_drilldowns(connection, chosen_symbols)
            eod_summary = load_latest_market_eod_summary(connection)
    except Exception:
        return None

    if not volume_batch.rows and not index_wall_batch.rows and not merged_signals:
        return None

    auth_session = AuthSession(
        mode="supabase",
        environment=app_config.auth.resolved_environment(),
        is_available=True,
    )
    if live_auth:
        live_session = load_auth_session(app_config.auth)
        auth_session = live_session
    merged = merged_signals or merge_signals(
        [row for row in volume_batch.rows if isinstance(row, VolumeSignal)],
        [],
        regime_signals=[row for row in index_wall_batch.rows if isinstance(row, WallSignal)],
    )
    generated_at = max(
        [value for value in (volume_time, wall_time, signal_time, multi_wall_time) if value is not None],
        default=datetime.now(UTC),
    )
    return {
        "auth_session": auth_session,
        "volume_batch": volume_batch,
        "wall_batch": index_wall_batch,
        "multi_wall_batch": index_multi_wall_batch,
        "stock_wall_batch": ScanResultBatch(source="stock_oi_disabled"),
        "stock_multi_wall_batch": ScanResultBatch(source="stock_oi_disabled"),
        "index_wall_batch": index_wall_batch,
        "index_multi_wall_batch": index_multi_wall_batch,
        "merged_signals": merged,
        "symbols": chosen_symbols,
        "index_symbols": INDEX_WALL_SYMBOLS,
        "index_ladders": ladder_snapshots,
        "alert_events": alert_events,
        "watchlist_symbols": watchlist_symbols,
        "drilldown_summaries": drilldown_summaries,
        "generated_at": generated_at,
        "is_demo": False,
        "data_source": "supabase",
        "eod_summary": eod_summary,
        "is_post_close": _is_post_close_now(),
    }


def _database_is_configured(app_config: AppConfig) -> bool:
    db = app_config.database
    return bool(db.url or db.host)


def _empty_database_snapshot(app_config: AppConfig, chosen_symbols: tuple[str, ...]) -> dict[str, object]:
    auth_session = AuthSession(
        mode="supabase",
        environment=app_config.auth.resolved_environment(),
        is_available=False,
        error="No stored snapshot available yet.",
    )
    empty_batch = ScanResultBatch(source="supabase", errors=("No stored snapshot available yet.",))
    return {
        "auth_session": auth_session,
        "volume_batch": empty_batch,
        "wall_batch": empty_batch,
        "multi_wall_batch": empty_batch,
        "stock_wall_batch": ScanResultBatch(source="stock_oi_disabled"),
        "stock_multi_wall_batch": ScanResultBatch(source="stock_oi_disabled"),
        "index_wall_batch": empty_batch,
        "index_multi_wall_batch": empty_batch,
        "merged_signals": (),
        "symbols": chosen_symbols,
        "index_symbols": INDEX_WALL_SYMBOLS,
        "index_ladders": (),
        "alert_events": (),
        "watchlist_symbols": (),
        "drilldown_summaries": {},
        "generated_at": None,
        "is_demo": False,
        "data_source": "pending",
        "eod_summary": None,
        "is_post_close": _is_post_close_now(),
    }


def _is_post_close_now() -> bool:
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    return now.weekday() < 5 and (now.hour, now.minute) >= (15, 30)


def _symbol_seed_rows(symbols: tuple[str, ...], *, exchange: str) -> list[dict[str, object]]:
    return [
        {
            "symbol": symbol,
            "exchange": exchange,
            "sector": None,
            "industry": None,
            "is_active": True,
            "source": "manual_refresh",
        }
        for symbol in symbols
    ]


def save_watchlist_symbols(
    app_config: AppConfig,
    symbols: Iterable[str],
    *,
    slug: str = "desk",
    title: str = "Desk Watchlist",
) -> int:
    if not _database_is_configured(app_config):
        return 0
    with connect_db(app_config.database) as connection:
        apply_schema(connection, SUPABASE_SCHEMA.read_text(encoding="utf-8"))
        return save_watchlist_symbols_db(connection, symbols=symbols, slug=slug, title=title)


def _ephemeral_alert_events(signals: tuple[MergedSignal, ...]) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for signal in signals[:8]:
        if not hasattr(signal, "symbol"):
            continue
        events.append(
            {
                "symbol": getattr(signal, "symbol", None),
                "event_type": "snapshot",
                "title": f"{getattr(signal, 'symbol', '')} {getattr(signal, 'action_state', 'watching').lower()}",
                "body": getattr(signal, "why_now", None) or getattr(signal, "signal_reason", "Snapshot signal"),
                "priority": 1,
                "action_state": getattr(signal, "action_state", None),
                "confidence": getattr(signal, "confidence", 0.0),
                "raw": {},
            }
        )
    return events


def _ephemeral_drilldown_summaries(signals: tuple[MergedSignal, ...], *, exchange: str) -> dict[str, object]:
    summaries = {}
    for signal in signals:
        if not hasattr(signal, "symbol"):
            continue
        summaries[getattr(signal, "symbol")] = {
            "exchange": exchange,
            "signal": signal,
        }
    return summaries
