"""Postgres helpers for Supabase-backed snapshot storage."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any, Iterable
from zoneinfo import ZoneInfo

import pandas as pd

if TYPE_CHECKING:
    import psycopg
    from psycopg.rows import dict_row
else:
    psycopg = None
    dict_row = None

from ..config import DatabaseConfig
from ..models import MergedSignal, OIWallCandidate, ScanResultBatch, SymbolDrilldown, VolumeSignal, WallSignal
from .option_chain import OptionChainSnapshot


@dataclass(frozen=True, slots=True)
class SyncStats:
    symbols_upserted: int = 0
    volume_latest_upserted: int = 0
    volume_history_inserted: int = 0
    signal_board_latest_upserted: int = 0
    signal_board_history_inserted: int = 0
    index_wall_latest_upserted: int = 0
    index_wall_history_inserted: int = 0
    index_multi_wall_latest_upserted: int = 0
    index_multi_wall_history_inserted: int = 0
    index_ladder_latest_upserted: int = 0
    index_ladder_history_inserted: int = 0
    symbol_drilldown_latest_upserted: int = 0
    symbol_drilldown_history_inserted: int = 0
    alert_events_inserted: int = 0
    signal_transitions_inserted: int = 0
    market_eod_upserted: int = 0
    stock_eod_upserted: int = 0


def connect_db(config: DatabaseConfig):
    psycopg_module = _require_psycopg()
    if config.host and config.password:
        return psycopg_module.connect(
            host=_normalize_host(config.host),
            port=config.port,
            dbname=config.name,
            user=config.user,
            password=config.password,
        )
    dsn = config.connection_string()
    if not dsn:
        raise ValueError("Missing Supabase/Postgres connection details. Fill SUPABASE_DB_URL or host/password fields.")
    return psycopg_module.connect(dsn)


def apply_schema(connection, schema_sql: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(schema_sql)
    connection.commit()


def load_latest_volume_batch(
    connection,
    symbols: Iterable[str],
) -> tuple[ScanResultBatch, datetime | None]:
    chosen = tuple(dict.fromkeys(symbols))
    if not chosen:
        return ScanResultBatch(source="supabase_volume_latest"), None

    with connection.cursor(row_factory=_dict_row_factory()) as cursor:
        cursor.execute(
            """
            select
                symbol,
                scanned_at,
                candle_time,
                current_volume,
                average_volume,
                volume_ratio,
                signal_summary,
                raw_json
            from volume_snapshots_latest
            where symbol = any(%s)
            order by volume_ratio desc nulls last, symbol asc
            """,
            (list(chosen),),
        )
        rows = cursor.fetchall()

    signals: list[VolumeSignal] = []
    scanned_times: list[datetime] = []
    for row in rows:
        payload = _coerce_json(row.get("raw_json"))
        signals.append(
            VolumeSignal(
                symbol=payload.get("symbol") or row["symbol"],
                candle_time=payload.get("candle_time") or row.get("candle_time") or "",
                current_volume=_coerce_float(payload.get("current_volume"), row.get("current_volume")),
                average_volume=_coerce_float(payload.get("average_volume"), row.get("average_volume")),
                volume_ratio=_coerce_float(payload.get("volume_ratio"), row.get("volume_ratio")),
                scan_status=payload.get("scan_status") or "ok",
                signal_summary=payload.get("signal_summary") or row.get("signal_summary"),
                baseline_details=payload.get("baseline_details"),
                price_details=payload.get("price_details"),
            )
        )
        if row.get("scanned_at"):
            scanned_times.append(row["scanned_at"])

    latest = max(scanned_times) if scanned_times else None
    return ScanResultBatch(source="supabase_volume_latest", rows=tuple(signals), raw={"scanned_at": latest}), latest


def load_latest_index_wall_batch(
    connection,
    index_symbols: Iterable[str],
) -> tuple[ScanResultBatch, datetime | None]:
    chosen = tuple(dict.fromkeys(index_symbols))
    if not chosen:
        return ScanResultBatch(source="supabase_index_walls_latest"), None

    with connection.cursor(row_factory=_dict_row_factory()) as cursor:
        cursor.execute(
            """
            select
                index_symbol,
                exchange,
                expiry,
                scanned_at,
                spot_price,
                wall_type,
                wall_strike,
                wall_open_interest,
                distance_from_current_price_pct,
                bias,
                raw_json
            from index_wall_snapshots_latest
            where index_symbol = any(%s)
            order by index_symbol asc
            """,
            (list(chosen),),
        )
        rows = cursor.fetchall()

    signals: list[WallSignal] = []
    scanned_times: list[datetime] = []
    for row in rows:
        payload = _coerce_json(row.get("raw_json"))
        signals.append(
            WallSignal(
                symbol=payload.get("symbol") or row["index_symbol"],
                ltp=_coerce_float(payload.get("ltp"), row.get("spot_price")),
                wall_type=payload.get("wall_type") or row.get("wall_type"),
                wall_strike=_coerce_float(payload.get("wall_strike"), row.get("wall_strike")),
                wall_oi=_coerce_float(payload.get("wall_oi"), row.get("wall_open_interest")),
                proximity_pct=_coerce_float(
                    payload.get("proximity_pct"),
                    row.get("distance_from_current_price_pct"),
                ),
                bias=payload.get("bias") or row.get("bias"),
                exchange=payload.get("exchange") or row.get("exchange"),
                expiry=payload.get("expiry") or row.get("expiry"),
                selected=payload.get("selected"),
            )
        )
        if row.get("scanned_at"):
            scanned_times.append(row["scanned_at"])

    latest = max(scanned_times) if scanned_times else None
    return ScanResultBatch(source="supabase_index_walls_latest", rows=tuple(signals), raw={"scanned_at": latest}), latest


def load_latest_signal_board(
    connection,
    symbols: Iterable[str],
) -> tuple[tuple[MergedSignal, ...], datetime | None]:
    chosen = tuple(dict.fromkeys(symbols))
    if not chosen:
        return (), None

    with connection.cursor(row_factory=_dict_row_factory()) as cursor:
        cursor.execute(
            """
            select
                symbol,
                scanned_at,
                ltp,
                volume_ratio,
                current_volume,
                average_volume,
                wall_type,
                wall_strike,
                wall_proximity_pct,
                bias,
                signal_grade,
                signal_reason,
                setup_type,
                confidence,
                action_state,
                regime_alignment,
                trigger_price,
                invalidation_price,
                first_target,
                why_now,
                raw_json
            from stock_signal_board_latest
            where symbol = any(%s)
            order by
                case signal_grade
                    when 'A' then 0
                    when 'B' then 1
                    when 'C' then 2
                    else 9
                end asc,
                confidence desc nulls last,
                volume_ratio desc nulls last,
                symbol asc
            """,
            (list(chosen),),
        )
        rows = cursor.fetchall()

    signals: list[MergedSignal] = []
    scanned_times: list[datetime] = []
    for row in rows:
        payload = _coerce_json(row.get("raw_json"))
        updated_at = _coerce_datetime(payload.get("updated_at"), row.get("scanned_at"))
        signals.append(
            MergedSignal(
                symbol=payload.get("symbol") or row["symbol"],
                ltp=_coerce_float(payload.get("ltp"), row.get("ltp")),
                volume_ratio=_coerce_float(payload.get("volume_ratio"), row.get("volume_ratio")),
                current_volume=_coerce_float(payload.get("current_volume"), row.get("current_volume")),
                average_volume=_coerce_float(payload.get("average_volume"), row.get("average_volume")),
                wall_type=payload.get("wall_type") or row.get("wall_type"),
                wall_strike=_coerce_float(payload.get("wall_strike"), row.get("wall_strike")),
                wall_proximity_pct=_coerce_float(payload.get("wall_proximity_pct"), row.get("wall_proximity_pct")),
                bias=payload.get("bias") or row.get("bias"),
                signal_grade=payload.get("signal_grade") or row.get("signal_grade") or "D",
                signal_reason=payload.get("signal_reason") or row.get("signal_reason") or "No usable signal",
                setup_type=payload.get("setup_type") or row.get("setup_type") or "Scanner",
                confidence=_coerce_float(payload.get("confidence"), row.get("confidence")) or 0.0,
                action_state=payload.get("action_state") or row.get("action_state") or "Cooling",
                regime_alignment=payload.get("regime_alignment") or row.get("regime_alignment") or "Neutral",
                trigger_price=_coerce_float(payload.get("trigger_price"), row.get("trigger_price")),
                invalidation_price=_coerce_float(payload.get("invalidation_price"), row.get("invalidation_price")),
                first_target=_coerce_float(payload.get("first_target"), row.get("first_target")),
                why_now=payload.get("why_now") or row.get("why_now"),
                updated_at=updated_at or datetime.now(UTC),
            )
        )
        if row.get("scanned_at"):
            scanned_times.append(row["scanned_at"])

    latest = max(scanned_times) if scanned_times else None
    return tuple(signals), latest


def load_latest_index_multi_wall_batch(
    connection,
    index_symbols: Iterable[str],
) -> tuple[ScanResultBatch, datetime | None]:
    chosen = tuple(dict.fromkeys(index_symbols))
    if not chosen:
        return ScanResultBatch(source="supabase_index_multi_wall_latest"), None

    with connection.cursor(row_factory=_dict_row_factory()) as cursor:
        cursor.execute(
            """
            select
                index_symbol,
                rank,
                wall_side,
                strike,
                open_interest,
                distance_from_current_price_pct,
                selected,
                spot_price,
                scanned_at,
                raw_json
            from index_multi_wall_latest
            where index_symbol = any(%s)
            order by index_symbol asc, rank asc, strike asc
            """,
            (list(chosen),),
        )
        rows = cursor.fetchall()

    candidates: list[OIWallCandidate] = []
    scanned_times: list[datetime] = []
    for row in rows:
        payload = _coerce_json(row.get("raw_json"))
        candidates.append(
            OIWallCandidate(
                symbol=payload.get("symbol") or row["index_symbol"],
                ltp=_coerce_float(payload.get("ltp"), row.get("spot_price")) or 0.0,
                wall_side=payload.get("wall_side") or row.get("wall_side") or "",
                rank=int(payload.get("rank") or row.get("rank") or 0),
                strike=_coerce_float(payload.get("strike"), row.get("strike")) or 0.0,
                oi=_coerce_float(payload.get("oi"), row.get("open_interest")) or 0.0,
                dist_pct=_coerce_float(payload.get("dist_pct"), row.get("distance_from_current_price_pct")) or 0.0,
                selected=bool(payload.get("selected")) if payload.get("selected") is not None else bool(row.get("selected")),
            )
        )
        if row.get("scanned_at"):
            scanned_times.append(row["scanned_at"])

    latest = max(scanned_times) if scanned_times else None
    return ScanResultBatch(source="supabase_index_multi_wall_latest", rows=tuple(candidates), raw={"scanned_at": latest}), latest


def load_latest_index_ladder_snapshots(
    connection,
    index_symbols: Iterable[str],
) -> tuple[OptionChainSnapshot, ...]:
    chosen = tuple(dict.fromkeys(index_symbols))
    if not chosen:
        return ()

    with connection.cursor(row_factory=_dict_row_factory()) as cursor:
        cursor.execute(
            """
            select
                index_symbol,
                exchange,
                expiry,
                scanned_at,
                spot_price,
                strike,
                call_open_interest,
                put_open_interest,
                call_volume,
                put_volume
            from index_wall_ladder_latest
            where index_symbol = any(%s)
            order by index_symbol asc, strike asc
            """,
            (list(chosen),),
        )
        rows = cursor.fetchall()

    grouped: dict[str, list[dict[str, Any]]] = {}
    metadata: dict[str, dict[str, Any]] = {}
    for row in rows:
        symbol = row["index_symbol"]
        grouped.setdefault(symbol, []).append(
            {
                "strike": float(row["strike"]),
                "call_oi": float(row.get("call_open_interest") or 0),
                "put_oi": float(row.get("put_open_interest") or 0),
                "call_volume": float(row.get("call_volume") or 0),
                "put_volume": float(row.get("put_volume") or 0),
            }
        )
        metadata.setdefault(
            symbol,
            {
                "exchange": row.get("exchange"),
                "expiry": row.get("expiry"),
                "spot": float(row.get("spot_price") or 0),
            },
        )

    snapshots: list[OptionChainSnapshot] = []
    for symbol, ladder_rows in grouped.items():
        meta = metadata.get(symbol, {})
        snapshots.append(
            OptionChainSnapshot(
                symbol=symbol,
                exchange=str(meta.get("exchange") or ""),
                expiry=meta.get("expiry"),
                spot=float(meta.get("spot") or 0),
                frame=pd.DataFrame(ladder_rows),
            )
        )
    return tuple(snapshots)


def load_latest_symbol_drilldowns(
    connection,
    symbols: Iterable[str],
) -> dict[str, SymbolDrilldown]:
    chosen = tuple(dict.fromkeys(symbols))
    if not chosen:
        return {}

    with connection.cursor(row_factory=_dict_row_factory()) as cursor:
        cursor.execute(
            """
            select
                symbol,
                scanned_at,
                exchange,
                ltp,
                volume_ratio,
                signal_grade,
                setup_type,
                confidence,
                action_state,
                regime_alignment,
                trigger_price,
                invalidation_price,
                first_target,
                primary_note,
                secondary_note,
                raw_json
            from symbol_drilldown_latest
            where symbol = any(%s)
            order by symbol asc
            """,
            (list(chosen),),
        )
        rows = cursor.fetchall()

    drilldowns: dict[str, SymbolDrilldown] = {}
    for row in rows:
        payload = _coerce_json(row.get("raw_json"))
        drilldowns[row["symbol"]] = SymbolDrilldown(
            symbol=row["symbol"],
            exchange=payload.get("exchange") or row.get("exchange"),
            ltp=_coerce_float(payload.get("ltp"), row.get("ltp")),
            volume_signal=None,
            wall_signal=None,
            merged_signal=MergedSignal(
                symbol=row["symbol"],
                ltp=_coerce_float(payload.get("ltp"), row.get("ltp")),
                volume_ratio=_coerce_float(payload.get("volume_ratio"), row.get("volume_ratio")),
                current_volume=_coerce_float(payload.get("current_volume")),
                average_volume=_coerce_float(payload.get("average_volume")),
                wall_type=payload.get("wall_type"),
                wall_strike=_coerce_float(payload.get("wall_strike")),
                wall_proximity_pct=_coerce_float(payload.get("wall_proximity_pct")),
                bias=payload.get("bias"),
                signal_grade=payload.get("signal_grade") or row.get("signal_grade") or "D",
                signal_reason=payload.get("signal_reason") or payload.get("primary_note") or "No usable signal",
                setup_type=payload.get("setup_type") or row.get("setup_type") or "Scanner",
                confidence=_coerce_float(payload.get("confidence"), row.get("confidence")) or 0.0,
                action_state=payload.get("action_state") or row.get("action_state") or "Cooling",
                regime_alignment=payload.get("regime_alignment") or row.get("regime_alignment") or "Neutral",
                trigger_price=_coerce_float(payload.get("trigger_price"), row.get("trigger_price")),
                invalidation_price=_coerce_float(payload.get("invalidation_price"), row.get("invalidation_price")),
                first_target=_coerce_float(payload.get("first_target"), row.get("first_target")),
                why_now=payload.get("why_now") or row.get("primary_note"),
                updated_at=_coerce_datetime(payload.get("updated_at"), row.get("scanned_at")) or datetime.now(UTC),
            ),
            notes=tuple(
                note for note in (row.get("primary_note"), row.get("secondary_note")) if isinstance(note, str) and note.strip()
            ),
        )
    return drilldowns


def load_recent_alert_events(
    connection,
    *,
    symbols: Iterable[str] | None = None,
    limit: int = 12,
) -> tuple[dict[str, Any], ...]:
    chosen = tuple(dict.fromkeys(symbols or ()))
    params: list[Any] = []
    where = ""
    if chosen:
        where = "where symbol = any(%s)"
        params.append(list(chosen))
    params.append(limit)

    with connection.cursor(row_factory=_dict_row_factory()) as cursor:
        cursor.execute(
            f"""
            select
                symbol,
                scanned_at,
                event_type,
                title,
                body,
                priority,
                action_state,
                confidence,
                raw_json
            from alert_events
            {where}
            order by scanned_at desc, priority desc, symbol asc
            limit %s
            """,
            tuple(params),
        )
        rows = cursor.fetchall()

    return tuple(
        {
            "symbol": row.get("symbol"),
            "scanned_at": row.get("scanned_at"),
            "event_type": row.get("event_type"),
            "title": row.get("title"),
            "body": row.get("body"),
            "priority": row.get("priority"),
            "action_state": row.get("action_state"),
            "confidence": _coerce_float(row.get("confidence")) or 0.0,
            "raw": _coerce_json(row.get("raw_json")),
        }
        for row in rows
    )


def load_watchlist_symbols(
    connection,
    *,
    slug: str = "desk",
) -> tuple[str, ...]:
    with connection.cursor(row_factory=_dict_row_factory()) as cursor:
        cursor.execute(
            """
            select wi.symbol
            from watchlists w
            join watchlist_items wi on wi.watchlist_id = w.id
            where w.slug = %s
            order by wi.updated_at desc, wi.symbol asc
            """,
            (slug,),
        )
        rows = cursor.fetchall()
    return tuple(row["symbol"] for row in rows)


def save_watchlist_symbols(
    connection,
    *,
    symbols: Iterable[str],
    slug: str = "desk",
    title: str = "Desk Watchlist",
) -> int:
    chosen = tuple(dict.fromkeys(symbol for symbol in symbols if symbol))
    with connection.cursor(row_factory=_dict_row_factory()) as cursor:
        cursor.execute(
            """
            insert into watchlists (slug, title)
            values (%s, %s)
            on conflict (slug)
            do update set
                title = excluded.title,
                updated_at = timezone('utc', now())
            returning id
            """,
            (slug, title),
        )
        watchlist_id = cursor.fetchone()["id"]
        cursor.execute("delete from watchlist_items where watchlist_id = %s", (watchlist_id,))
        if chosen:
            cursor.executemany(
                """
                insert into watchlist_items (watchlist_id, symbol, source, state, notes_json)
                values (%s, %s, %s, %s, %s::jsonb)
                """,
                [
                    (watchlist_id, symbol, "ui", None, json.dumps({}))
                    for symbol in chosen
                ],
            )
    connection.commit()
    return len(chosen)


def record_sync_run(
    connection,
    *,
    started_at: datetime,
    finished_at: datetime,
    status: str,
    symbol_source: str,
    symbol_count: int,
    details: dict[str, Any],
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into sync_runs (
                started_at,
                finished_at,
                status,
                symbol_source,
                symbol_count,
                details_json
            )
            values (%s, %s, %s, %s, %s, %s::jsonb)
            """,
            (
                _ensure_utc(started_at),
                _ensure_utc(finished_at),
                status,
                symbol_source,
                symbol_count,
                json.dumps(details),
            ),
        )
    connection.commit()


def upsert_symbols(
    connection,
    rows: Iterable[dict[str, Any]],
) -> int:
    payload = list(rows)
    if not payload:
        return 0
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            insert into symbols (
                symbol,
                exchange,
                sector,
                industry,
                is_active,
                source
            )
            values (%(symbol)s, %(exchange)s, %(sector)s, %(industry)s, %(is_active)s, %(source)s)
            on conflict (symbol)
            do update set
                exchange = excluded.exchange,
                sector = excluded.sector,
                industry = excluded.industry,
                is_active = excluded.is_active,
                source = excluded.source,
                updated_at = timezone('utc', now())
            """,
            payload,
        )
    connection.commit()
    return len(payload)


def store_volume_batches(
    connection,
    *,
    scanned_at: datetime,
    interval: str,
    lookback_days: int,
    batch: ScanResultBatch,
) -> tuple[int, int]:
    rows = [row for row in batch.rows if isinstance(row, VolumeSignal)]
    if not rows:
        return 0, 0

    latest_payload = [
        {
            "symbol": row.symbol,
            "scanned_at": _ensure_utc(scanned_at),
            "candle_time": row.candle_time or None,
            "current_volume": row.current_volume,
            "average_volume": row.average_volume,
            "volume_ratio": row.volume_ratio,
            "signal_summary": row.signal_summary,
            "interval": interval,
            "lookback_days": lookback_days,
            "raw_json": json.dumps(row.to_dict()),
        }
        for row in rows
    ]

    with connection.cursor() as cursor:
        cursor.executemany(
            """
            insert into volume_snapshots_latest (
                symbol,
                scanned_at,
                candle_time,
                current_volume,
                average_volume,
                volume_ratio,
                signal_summary,
                interval,
                lookback_days,
                raw_json
            )
            values (
                %(symbol)s,
                %(scanned_at)s,
                %(candle_time)s,
                %(current_volume)s,
                %(average_volume)s,
                %(volume_ratio)s,
                %(signal_summary)s,
                %(interval)s,
                %(lookback_days)s,
                %(raw_json)s::jsonb
            )
            on conflict (symbol)
            do update set
                scanned_at = excluded.scanned_at,
                candle_time = excluded.candle_time,
                current_volume = excluded.current_volume,
                average_volume = excluded.average_volume,
                volume_ratio = excluded.volume_ratio,
                signal_summary = excluded.signal_summary,
                interval = excluded.interval,
                lookback_days = excluded.lookback_days,
                raw_json = excluded.raw_json
            """,
            latest_payload,
        )
        cursor.executemany(
            """
            insert into volume_snapshots_history (
                symbol,
                scanned_at,
                candle_time,
                current_volume,
                average_volume,
                volume_ratio,
                signal_summary,
                interval,
                lookback_days,
                raw_json
            )
            values (
                %(symbol)s,
                %(scanned_at)s,
                %(candle_time)s,
                %(current_volume)s,
                %(average_volume)s,
                %(volume_ratio)s,
                %(signal_summary)s,
                %(interval)s,
                %(lookback_days)s,
                %(raw_json)s::jsonb
            )
            """,
            latest_payload,
        )
    connection.commit()
    return len(latest_payload), len(latest_payload)


def store_signal_board(
    connection,
    *,
    scanned_at: datetime,
    signals: Iterable[MergedSignal],
) -> tuple[int, int, int, int]:
    rows = list(signals)
    if not rows:
        return 0, 0, 0, 0

    previous = _load_previous_signal_rows(connection, [row.symbol for row in rows])

    payload = [
        {
            "symbol": row.symbol,
            "scanned_at": _ensure_utc(scanned_at),
            "ltp": row.ltp,
            "volume_ratio": row.volume_ratio,
            "current_volume": row.current_volume,
            "average_volume": row.average_volume,
            "wall_type": row.wall_type,
            "wall_strike": row.wall_strike,
            "wall_proximity_pct": row.wall_proximity_pct,
            "bias": row.bias,
            "signal_grade": row.signal_grade,
            "signal_reason": row.signal_reason,
            "setup_type": row.setup_type,
            "confidence": row.confidence,
            "action_state": row.action_state,
            "regime_alignment": row.regime_alignment,
            "trigger_price": row.trigger_price,
            "invalidation_price": row.invalidation_price,
            "first_target": row.first_target,
            "why_now": row.why_now,
            "raw_json": json.dumps(_merged_signal_payload(row)),
        }
        for row in rows
    ]

    with connection.cursor() as cursor:
        cursor.executemany(
            """
            insert into stock_signal_board_latest (
                symbol,
                scanned_at,
                ltp,
                volume_ratio,
                current_volume,
                average_volume,
                wall_type,
                wall_strike,
                wall_proximity_pct,
                bias,
                signal_grade,
                signal_reason,
                setup_type,
                confidence,
                action_state,
                regime_alignment,
                trigger_price,
                invalidation_price,
                first_target,
                why_now,
                raw_json
            )
            values (
                %(symbol)s,
                %(scanned_at)s,
                %(ltp)s,
                %(volume_ratio)s,
                %(current_volume)s,
                %(average_volume)s,
                %(wall_type)s,
                %(wall_strike)s,
                %(wall_proximity_pct)s,
                %(bias)s,
                %(signal_grade)s,
                %(signal_reason)s,
                %(setup_type)s,
                %(confidence)s,
                %(action_state)s,
                %(regime_alignment)s,
                %(trigger_price)s,
                %(invalidation_price)s,
                %(first_target)s,
                %(why_now)s,
                %(raw_json)s::jsonb
            )
            on conflict (symbol)
            do update set
                scanned_at = excluded.scanned_at,
                ltp = excluded.ltp,
                volume_ratio = excluded.volume_ratio,
                current_volume = excluded.current_volume,
                average_volume = excluded.average_volume,
                wall_type = excluded.wall_type,
                wall_strike = excluded.wall_strike,
                wall_proximity_pct = excluded.wall_proximity_pct,
                bias = excluded.bias,
                signal_grade = excluded.signal_grade,
                signal_reason = excluded.signal_reason,
                setup_type = excluded.setup_type,
                confidence = excluded.confidence,
                action_state = excluded.action_state,
                regime_alignment = excluded.regime_alignment,
                trigger_price = excluded.trigger_price,
                invalidation_price = excluded.invalidation_price,
                first_target = excluded.first_target,
                why_now = excluded.why_now,
                raw_json = excluded.raw_json
            """,
            payload,
        )
        cursor.executemany(
            """
            insert into stock_signal_board_history (
                symbol,
                scanned_at,
                ltp,
                volume_ratio,
                current_volume,
                average_volume,
                wall_type,
                wall_strike,
                wall_proximity_pct,
                bias,
                signal_grade,
                signal_reason,
                setup_type,
                confidence,
                action_state,
                regime_alignment,
                trigger_price,
                invalidation_price,
                first_target,
                why_now,
                raw_json
            )
            values (
                %(symbol)s,
                %(scanned_at)s,
                %(ltp)s,
                %(volume_ratio)s,
                %(current_volume)s,
                %(average_volume)s,
                %(wall_type)s,
                %(wall_strike)s,
                %(wall_proximity_pct)s,
                %(bias)s,
                %(signal_grade)s,
                %(signal_reason)s,
                %(setup_type)s,
                %(confidence)s,
                %(action_state)s,
                %(regime_alignment)s,
                %(trigger_price)s,
                %(invalidation_price)s,
                %(first_target)s,
                %(why_now)s,
                %(raw_json)s::jsonb
            )
            """,
            payload,
        )
        transition_payload = _build_signal_transition_payload(scanned_at, rows, previous)
        if transition_payload:
            cursor.executemany(
                """
                insert into signal_transitions (
                    symbol,
                    scanned_at,
                    previous_state,
                    current_state,
                    previous_grade,
                    current_grade,
                    previous_confidence,
                    current_confidence,
                    raw_json
                )
                values (
                    %(symbol)s,
                    %(scanned_at)s,
                    %(previous_state)s,
                    %(current_state)s,
                    %(previous_grade)s,
                    %(current_grade)s,
                    %(previous_confidence)s,
                    %(current_confidence)s,
                    %(raw_json)s::jsonb
                )
                """,
                transition_payload,
            )
        alert_payload = _build_alert_event_payload(scanned_at, rows, previous)
        if alert_payload:
            cursor.executemany(
                """
                insert into alert_events (
                    symbol,
                    scanned_at,
                    event_type,
                    title,
                    body,
                    priority,
                    action_state,
                    confidence,
                    raw_json
                )
                values (
                    %(symbol)s,
                    %(scanned_at)s,
                    %(event_type)s,
                    %(title)s,
                    %(body)s,
                    %(priority)s,
                    %(action_state)s,
                    %(confidence)s,
                    %(raw_json)s::jsonb
                )
                """,
                alert_payload,
            )
    connection.commit()
    return len(payload), len(payload), len(transition_payload), len(alert_payload)


def store_symbol_drilldowns(
    connection,
    *,
    scanned_at: datetime,
    exchange: str,
    signals: Iterable[MergedSignal],
) -> tuple[int, int]:
    rows = list(signals)
    if not rows:
        return 0, 0

    payload = []
    for row in rows:
        primary_note = row.why_now or row.signal_reason
        secondary_note = _build_drilldown_secondary_note(row)
        payload.append(
            {
                "symbol": row.symbol,
                "scanned_at": _ensure_utc(scanned_at),
                "exchange": exchange,
                "ltp": row.ltp,
                "volume_ratio": row.volume_ratio,
                "signal_grade": row.signal_grade,
                "setup_type": row.setup_type,
                "confidence": row.confidence,
                "action_state": row.action_state,
                "regime_alignment": row.regime_alignment,
                "trigger_price": row.trigger_price,
                "invalidation_price": row.invalidation_price,
                "first_target": row.first_target,
                "primary_note": primary_note,
                "secondary_note": secondary_note,
                "raw_json": json.dumps(_merged_signal_payload(row) | {"primary_note": primary_note, "secondary_note": secondary_note}),
            }
        )

    with connection.cursor() as cursor:
        cursor.executemany(
            """
            insert into symbol_drilldown_latest (
                symbol,
                scanned_at,
                exchange,
                ltp,
                volume_ratio,
                signal_grade,
                setup_type,
                confidence,
                action_state,
                regime_alignment,
                trigger_price,
                invalidation_price,
                first_target,
                primary_note,
                secondary_note,
                raw_json
            )
            values (
                %(symbol)s,
                %(scanned_at)s,
                %(exchange)s,
                %(ltp)s,
                %(volume_ratio)s,
                %(signal_grade)s,
                %(setup_type)s,
                %(confidence)s,
                %(action_state)s,
                %(regime_alignment)s,
                %(trigger_price)s,
                %(invalidation_price)s,
                %(first_target)s,
                %(primary_note)s,
                %(secondary_note)s,
                %(raw_json)s::jsonb
            )
            on conflict (symbol)
            do update set
                scanned_at = excluded.scanned_at,
                exchange = excluded.exchange,
                ltp = excluded.ltp,
                volume_ratio = excluded.volume_ratio,
                signal_grade = excluded.signal_grade,
                setup_type = excluded.setup_type,
                confidence = excluded.confidence,
                action_state = excluded.action_state,
                regime_alignment = excluded.regime_alignment,
                trigger_price = excluded.trigger_price,
                invalidation_price = excluded.invalidation_price,
                first_target = excluded.first_target,
                primary_note = excluded.primary_note,
                secondary_note = excluded.secondary_note,
                raw_json = excluded.raw_json
            """,
            payload,
        )
        cursor.executemany(
            """
            insert into symbol_drilldown_history (
                symbol,
                scanned_at,
                exchange,
                ltp,
                volume_ratio,
                signal_grade,
                setup_type,
                confidence,
                action_state,
                regime_alignment,
                trigger_price,
                invalidation_price,
                first_target,
                primary_note,
                secondary_note,
                raw_json
            )
            values (
                %(symbol)s,
                %(scanned_at)s,
                %(exchange)s,
                %(ltp)s,
                %(volume_ratio)s,
                %(signal_grade)s,
                %(setup_type)s,
                %(confidence)s,
                %(action_state)s,
                %(regime_alignment)s,
                %(trigger_price)s,
                %(invalidation_price)s,
                %(first_target)s,
                %(primary_note)s,
                %(secondary_note)s,
                %(raw_json)s::jsonb
            )
            """,
            payload,
        )
    connection.commit()
    return len(payload), len(payload)


def store_index_walls(
    connection,
    *,
    scanned_at: datetime,
    batch: ScanResultBatch,
) -> tuple[int, int]:
    rows = [row for row in batch.rows if isinstance(row, WallSignal)]
    if not rows:
        return 0, 0

    payload = [
        {
            "index_symbol": row.symbol,
            "exchange": row.exchange,
            "expiry": row.expiry,
            "scanned_at": _ensure_utc(scanned_at),
            "spot_price": row.ltp,
            "wall_type": row.wall_type,
            "wall_strike": row.wall_strike,
            "wall_open_interest": row.wall_oi,
            "distance_from_current_price_pct": row.proximity_pct,
            "bias": row.bias,
            "raw_json": json.dumps(row.to_dict()),
        }
        for row in rows
    ]

    with connection.cursor() as cursor:
        cursor.executemany(
            """
            insert into index_wall_snapshots_latest (
                index_symbol,
                exchange,
                expiry,
                scanned_at,
                spot_price,
                wall_type,
                wall_strike,
                wall_open_interest,
                distance_from_current_price_pct,
                bias,
                raw_json
            )
            values (
                %(index_symbol)s,
                %(exchange)s,
                %(expiry)s,
                %(scanned_at)s,
                %(spot_price)s,
                %(wall_type)s,
                %(wall_strike)s,
                %(wall_open_interest)s,
                %(distance_from_current_price_pct)s,
                %(bias)s,
                %(raw_json)s::jsonb
            )
            on conflict (index_symbol)
            do update set
                exchange = excluded.exchange,
                expiry = excluded.expiry,
                scanned_at = excluded.scanned_at,
                spot_price = excluded.spot_price,
                wall_type = excluded.wall_type,
                wall_strike = excluded.wall_strike,
                wall_open_interest = excluded.wall_open_interest,
                distance_from_current_price_pct = excluded.distance_from_current_price_pct,
                bias = excluded.bias,
                raw_json = excluded.raw_json
            """,
            payload,
        )
        cursor.executemany(
            """
            insert into index_wall_snapshots_history (
                index_symbol,
                exchange,
                expiry,
                scanned_at,
                spot_price,
                wall_type,
                wall_strike,
                wall_open_interest,
                distance_from_current_price_pct,
                bias,
                raw_json
            )
            values (
                %(index_symbol)s,
                %(exchange)s,
                %(expiry)s,
                %(scanned_at)s,
                %(spot_price)s,
                %(wall_type)s,
                %(wall_strike)s,
                %(wall_open_interest)s,
                %(distance_from_current_price_pct)s,
                %(bias)s,
                %(raw_json)s::jsonb
            )
            """,
            payload,
        )
    connection.commit()
    return len(payload), len(payload)


def store_index_multi_walls(
    connection,
    *,
    scanned_at: datetime,
    batch: ScanResultBatch,
) -> tuple[int, int]:
    rows = [row for row in batch.rows if isinstance(row, OIWallCandidate)]
    if not rows:
        return 0, 0

    symbols = sorted({row.symbol for row in rows if row.symbol})
    with connection.cursor() as cursor:
        for symbol in symbols:
            cursor.execute("delete from index_multi_wall_latest where index_symbol = %s", (symbol,))

    payload = [
        {
            "index_symbol": row.symbol,
            "rank": row.rank,
            "wall_side": row.wall_side,
            "strike": row.strike,
            "open_interest": row.oi,
            "distance_from_current_price_pct": row.dist_pct,
            "selected": row.selected,
            "spot_price": row.ltp,
            "scanned_at": _ensure_utc(scanned_at),
            "raw_json": json.dumps(row.to_dict()),
        }
        for row in rows
    ]
    deduped_payload = list(
        {
            (
                item["index_symbol"],
                item["rank"],
                item["strike"],
                item["wall_side"],
            ): item
            for item in payload
        }.values()
    )

    with connection.cursor() as cursor:
        cursor.executemany(
            """
            insert into index_multi_wall_latest (
                index_symbol,
                rank,
                wall_side,
                strike,
                open_interest,
                distance_from_current_price_pct,
                selected,
                spot_price,
                scanned_at,
                raw_json
            )
            values (
                %(index_symbol)s,
                %(rank)s,
                %(wall_side)s,
                %(strike)s,
                %(open_interest)s,
                %(distance_from_current_price_pct)s,
                %(selected)s,
                %(spot_price)s,
                %(scanned_at)s,
                %(raw_json)s::jsonb
            )
            """,
            deduped_payload,
        )
        cursor.executemany(
            """
            insert into index_multi_wall_history (
                index_symbol,
                rank,
                wall_side,
                strike,
                open_interest,
                distance_from_current_price_pct,
                selected,
                spot_price,
                scanned_at,
                raw_json
            )
            values (
                %(index_symbol)s,
                %(rank)s,
                %(wall_side)s,
                %(strike)s,
                %(open_interest)s,
                %(distance_from_current_price_pct)s,
                %(selected)s,
                %(spot_price)s,
                %(scanned_at)s,
                %(raw_json)s::jsonb
            )
            """,
            deduped_payload,
        )
    connection.commit()
    return len(deduped_payload), len(deduped_payload)


def store_index_ladders(
    connection: psycopg.Connection,
    *,
    scanned_at: datetime,
    snapshots: Iterable[OptionChainSnapshot],
) -> tuple[int, int]:
    latest_count = 0
    history_count = 0
    with connection.cursor() as cursor:
        for snapshot in snapshots:
            cursor.execute("delete from index_wall_ladder_latest where index_symbol = %s", (snapshot.symbol,))
            payload = [
                {
                    "index_symbol": snapshot.symbol,
                    "exchange": snapshot.exchange,
                    "expiry": snapshot.expiry,
                    "scanned_at": _ensure_utc(scanned_at),
                    "spot_price": snapshot.spot,
                    "strike": float(row["strike"]),
                    "call_open_interest": float(row["call_oi"]),
                    "put_open_interest": float(row["put_oi"]),
                    "call_volume": float(row["call_volume"]),
                    "put_volume": float(row["put_volume"]),
                    "raw_json": json.dumps(
                        {
                            "strike": float(row["strike"]),
                            "call_oi": float(row["call_oi"]),
                            "put_oi": float(row["put_oi"]),
                            "call_volume": float(row["call_volume"]),
                            "put_volume": float(row["put_volume"]),
                        }
                    ),
                }
                for row in snapshot.frame.to_dict(orient="records")
            ]
            if not payload:
                continue
            cursor.executemany(
                """
                insert into index_wall_ladder_latest (
                    index_symbol,
                    exchange,
                    expiry,
                    scanned_at,
                    spot_price,
                    strike,
                    call_open_interest,
                    put_open_interest,
                    call_volume,
                    put_volume,
                    raw_json
                )
                values (
                    %(index_symbol)s,
                    %(exchange)s,
                    %(expiry)s,
                    %(scanned_at)s,
                    %(spot_price)s,
                    %(strike)s,
                    %(call_open_interest)s,
                    %(put_open_interest)s,
                    %(call_volume)s,
                    %(put_volume)s,
                    %(raw_json)s::jsonb
                )
                """,
                payload,
            )
            cursor.executemany(
                """
                insert into index_wall_ladder_history (
                    index_symbol,
                    exchange,
                    expiry,
                    scanned_at,
                    spot_price,
                    strike,
                    call_open_interest,
                    put_open_interest,
                    call_volume,
                    put_volume,
                    raw_json
                )
                values (
                    %(index_symbol)s,
                    %(exchange)s,
                    %(expiry)s,
                    %(scanned_at)s,
                    %(spot_price)s,
                    %(strike)s,
                    %(call_open_interest)s,
                    %(put_open_interest)s,
                    %(call_volume)s,
                    %(put_volume)s,
                    %(raw_json)s::jsonb
                )
                """,
                payload,
            )
            latest_count += len(payload)
            history_count += len(payload)
    connection.commit()
    return latest_count, history_count


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _coerce_json(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        return json.loads(value)
    return {}


def _coerce_float(*values: Any) -> float | None:
    for value in values:
        if value is None or value == "":
            continue
        return float(value)
    return None


def _coerce_datetime(*values: Any) -> datetime | None:
    for value in values:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value.strip():
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                continue
    return None


def _normalize_host(value: str) -> str:
    text = value.strip()
    if "://" in text:
        text = text.split("://", 1)[1]
    if "@" in text:
        text = text.rsplit("@", 1)[1]
    if "/" in text:
        text = text.split("/", 1)[0]
    if ":" in text and text.count(":") == 1:
        host_part, port_part = text.split(":", 1)
        if port_part.isdigit():
            return host_part
    return text


def _merged_signal_payload(signal: MergedSignal) -> dict[str, Any]:
    return {
        "symbol": signal.symbol,
        "ltp": signal.ltp,
        "volume_ratio": signal.volume_ratio,
        "current_volume": signal.current_volume,
        "average_volume": signal.average_volume,
        "wall_type": signal.wall_type,
        "wall_strike": signal.wall_strike,
        "wall_proximity_pct": signal.wall_proximity_pct,
        "bias": signal.bias,
        "signal_grade": signal.signal_grade,
        "signal_reason": signal.signal_reason,
        "setup_type": signal.setup_type,
        "confidence": signal.confidence,
        "action_state": signal.action_state,
        "regime_alignment": signal.regime_alignment,
        "trigger_price": signal.trigger_price,
        "invalidation_price": signal.invalidation_price,
        "first_target": signal.first_target,
        "why_now": signal.why_now,
        "updated_at": signal.updated_at.isoformat(),
    }


def _load_previous_signal_rows(connection, symbols: Iterable[str]) -> dict[str, dict[str, Any]]:
    chosen = tuple(dict.fromkeys(symbols))
    if not chosen:
        return {}
    with connection.cursor(row_factory=_dict_row_factory()) as cursor:
        cursor.execute(
            """
            select symbol, signal_grade, confidence, action_state, setup_type, raw_json
            from stock_signal_board_latest
            where symbol = any(%s)
            """,
            (list(chosen),),
        )
        rows = cursor.fetchall()
    previous: dict[str, dict[str, Any]] = {}
    for row in rows:
        payload = _coerce_json(row.get("raw_json"))
        previous[row["symbol"]] = {
            "signal_grade": payload.get("signal_grade") or row.get("signal_grade"),
            "confidence": _coerce_float(payload.get("confidence"), row.get("confidence")) or 0.0,
            "action_state": payload.get("action_state") or row.get("action_state"),
            "setup_type": payload.get("setup_type") or row.get("setup_type"),
        }
    return previous


def _build_signal_transition_payload(
    scanned_at: datetime,
    rows: Iterable[MergedSignal],
    previous: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    transitions: list[dict[str, Any]] = []
    for row in rows:
        prior = previous.get(row.symbol)
        if not prior:
            transitions.append(
                {
                    "symbol": row.symbol,
                    "scanned_at": _ensure_utc(scanned_at),
                    "previous_state": None,
                    "current_state": row.action_state,
                    "previous_grade": None,
                    "current_grade": row.signal_grade,
                    "previous_confidence": None,
                    "current_confidence": row.confidence,
                    "raw_json": json.dumps({"kind": "first_seen", "current": _merged_signal_payload(row)}),
                }
            )
            continue
        if (
            prior.get("action_state") == row.action_state
            and prior.get("signal_grade") == row.signal_grade
            and round(float(prior.get("confidence") or 0.0), 1) == round(float(row.confidence or 0.0), 1)
        ):
            continue
        transitions.append(
            {
                "symbol": row.symbol,
                "scanned_at": _ensure_utc(scanned_at),
                "previous_state": prior.get("action_state"),
                "current_state": row.action_state,
                "previous_grade": prior.get("signal_grade"),
                "current_grade": row.signal_grade,
                "previous_confidence": prior.get("confidence"),
                "current_confidence": row.confidence,
                "raw_json": json.dumps({"previous": prior, "current": _merged_signal_payload(row)}),
            }
        )
    return transitions


def _build_alert_event_payload(
    scanned_at: datetime,
    rows: Iterable[MergedSignal],
    previous: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for row in rows:
        prior = previous.get(row.symbol)
        is_new = prior is None
        escalated = prior is not None and (prior.get("action_state") != row.action_state)
        if row.action_state not in {"Actionable", "Building"} and not escalated:
            continue
        if row.action_state == "Actionable":
            event_type = "actionable"
            priority = 3
        elif escalated:
            event_type = "state_change"
            priority = 2
        else:
            event_type = "building"
            priority = 1
        title = f"{row.symbol} {row.action_state.lower()}"
        body = row.why_now or row.signal_reason
        if is_new:
            body = f"New name on the board. {body}"
        elif escalated and prior:
            body = f"State moved from {prior.get('action_state', 'Unknown')} to {row.action_state}. {body}"
        alerts.append(
            {
                "symbol": row.symbol,
                "scanned_at": _ensure_utc(scanned_at),
                "event_type": event_type,
                "title": title,
                "body": body,
                "priority": priority,
                "action_state": row.action_state,
                "confidence": row.confidence,
                "raw_json": json.dumps(_merged_signal_payload(row)),
            }
        )
    return alerts


def _build_drilldown_secondary_note(signal: MergedSignal) -> str:
    details: list[str] = []
    if signal.volume_ratio is not None:
        details.append(f"Volume is running at {signal.volume_ratio:.2f}x baseline.")
    if signal.regime_alignment:
        details.append(f"Regime is {signal.regime_alignment.lower()}.")
    if signal.trigger_price is not None and signal.invalidation_price is not None:
        details.append(
            f"Trigger {signal.trigger_price:.2f}; invalidation {signal.invalidation_price:.2f}."
        )
    return " ".join(details) or "Stored summary is ready for a deeper live drilldown if needed."


def store_market_eod_summary(
    connection,
    *,
    scanned_at: datetime,
    symbol_source: str,
    signals: Iterable[MergedSignal],
    index_walls: Iterable[WallSignal],
) -> tuple[int, int]:
    trading_day = _trading_day_for(scanned_at)
    rows = list(signals)
    wall_rows = [row for row in index_walls if isinstance(row, WallSignal)]
    top_signal = rows[0] if rows else None
    priority_count = sum(1 for signal in rows if signal.signal_grade in {"A", "B"})
    wall_map = {row.symbol: row for row in wall_rows}
    nifty = wall_map.get("NIFTY")
    sensex = wall_map.get("SENSEX")

    summary_payload = {
        "trading_day": trading_day,
        "scanned_at": _ensure_utc(scanned_at),
        "symbol_source": symbol_source,
        "total_signals": len(rows),
        "priority_signals": priority_count,
        "top_symbol": top_signal.symbol if top_signal else None,
        "top_grade": top_signal.signal_grade if top_signal else None,
        "top_volume_ratio": top_signal.volume_ratio if top_signal else None,
        "top_signal_reason": top_signal.signal_reason if top_signal else None,
        "nifty_bias": nifty.bias if nifty else None,
        "nifty_wall_type": nifty.wall_type if nifty else None,
        "nifty_wall_strike": nifty.wall_strike if nifty else None,
        "sensex_bias": sensex.bias if sensex else None,
        "sensex_wall_type": sensex.wall_type if sensex else None,
        "sensex_wall_strike": sensex.wall_strike if sensex else None,
        "raw_json": json.dumps(
            {
                "leaders": [_merged_signal_payload(signal) for signal in rows[:10]],
                "index_walls": [
                    {
                        "symbol": row.symbol,
                        "bias": row.bias,
                        "wall_type": row.wall_type,
                        "wall_strike": row.wall_strike,
                        "proximity_pct": row.proximity_pct,
                    }
                    for row in wall_rows
                ],
            }
        ),
    }

    leader_payloads = [
        {
            "trading_day": trading_day,
            "symbol": signal.symbol,
            "rank": rank,
            "scanned_at": _ensure_utc(scanned_at),
            "signal_grade": signal.signal_grade,
            "signal_reason": signal.signal_reason,
            "volume_ratio": signal.volume_ratio,
            "setup_type": signal.setup_type,
            "confidence": signal.confidence,
            "action_state": signal.action_state,
            "ltp": signal.ltp,
            "raw_json": json.dumps(_merged_signal_payload(signal)),
        }
        for rank, signal in enumerate(rows[:25], start=1)
    ]

    with connection.cursor() as cursor:
        cursor.execute(
            """
            insert into market_eod_summary (
                trading_day, scanned_at, symbol_source, total_signals, priority_signals,
                top_symbol, top_grade, top_volume_ratio, top_signal_reason,
                nifty_bias, nifty_wall_type, nifty_wall_strike,
                sensex_bias, sensex_wall_type, sensex_wall_strike, raw_json
            ) values (
                %(trading_day)s, %(scanned_at)s, %(symbol_source)s, %(total_signals)s, %(priority_signals)s,
                %(top_symbol)s, %(top_grade)s, %(top_volume_ratio)s, %(top_signal_reason)s,
                %(nifty_bias)s, %(nifty_wall_type)s, %(nifty_wall_strike)s,
                %(sensex_bias)s, %(sensex_wall_type)s, %(sensex_wall_strike)s, %(raw_json)s::jsonb
            )
            on conflict (trading_day) do update set
                scanned_at = excluded.scanned_at,
                symbol_source = excluded.symbol_source,
                total_signals = excluded.total_signals,
                priority_signals = excluded.priority_signals,
                top_symbol = excluded.top_symbol,
                top_grade = excluded.top_grade,
                top_volume_ratio = excluded.top_volume_ratio,
                top_signal_reason = excluded.top_signal_reason,
                nifty_bias = excluded.nifty_bias,
                nifty_wall_type = excluded.nifty_wall_type,
                nifty_wall_strike = excluded.nifty_wall_strike,
                sensex_bias = excluded.sensex_bias,
                sensex_wall_type = excluded.sensex_wall_type,
                sensex_wall_strike = excluded.sensex_wall_strike,
                raw_json = excluded.raw_json
            """,
            summary_payload,
        )

        if leader_payloads:
            cursor.execute("delete from stock_eod_leaders where trading_day = %s", (trading_day,))
            cursor.executemany(
                """
                insert into stock_eod_leaders (
                    trading_day, symbol, rank, scanned_at, signal_grade, signal_reason,
                    volume_ratio, setup_type, confidence, action_state, ltp, raw_json
                ) values (
                    %(trading_day)s, %(symbol)s, %(rank)s, %(scanned_at)s, %(signal_grade)s, %(signal_reason)s,
                    %(volume_ratio)s, %(setup_type)s, %(confidence)s, %(action_state)s, %(ltp)s, %(raw_json)s::jsonb
                )
                """,
                leader_payloads,
            )
    connection.commit()
    return 1, len(leader_payloads)


def load_latest_market_eod_summary(connection) -> dict[str, Any] | None:
    with connection.cursor(row_factory=_dict_row_factory()) as cursor:
        cursor.execute(
            """
            select *
            from market_eod_summary
            order by trading_day desc
            limit 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return None

        cursor.execute(
            """
            select symbol, rank, signal_grade, signal_reason, volume_ratio, setup_type, confidence, action_state, ltp
            from stock_eod_leaders
            where trading_day = %s
            order by rank asc, symbol asc
            """,
            (row["trading_day"],),
        )
        leaders = cursor.fetchall()

    return {
        "summary": dict(row),
        "leaders": tuple(dict(item) for item in leaders),
    }


def _trading_day_for(value: datetime) -> date:
    return _ensure_utc(value).astimezone(ZoneInfo("Asia/Kolkata")).date()


def _require_psycopg():
    try:
        import psycopg as psycopg_module
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "psycopg is not installed. Install dependencies from requirements.txt to enable Supabase/Postgres-backed snapshots."
        ) from exc
    return psycopg_module


def _dict_row_factory():
    try:
        from psycopg.rows import dict_row as factory
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "psycopg is not installed. Install dependencies from requirements.txt to enable Supabase/Postgres-backed snapshots."
        ) from exc
    return factory
