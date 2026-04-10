from __future__ import annotations

import csv
import logging
import sys
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SUPABASE_SCHEMA = ROOT / "supabase" / "schema.sql"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nubra_dash.bootstrap import load_local_env
from nubra_dash.config import LIQUID_STOCKS_SYMBOLS, TOP_FNO_SYMBOLS, load_app_config
from nubra_dash.services import get_dashboard_snapshot
from nubra_dash.services.auth import load_auth_session
from nubra_dash.services.db import (
    SyncStats,
    apply_schema,
    connect_db,
    store_index_multi_walls,
    store_symbol_drilldowns,
    store_signal_board,
    record_sync_run,
    store_index_ladders,
    store_index_walls,
    store_volume_batches,
    upsert_symbols,
)
from nubra_dash.services.option_chain import fetch_index_option_chains


logger = logging.getLogger("sync_supabase")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main() -> int:
    load_local_env()
    configure_logging()
    started_at = datetime.now(UTC)
    config = load_app_config()
    config = replace(
        config,
        auth=replace(config.auth, mode="user", environment="PROD", use_env_creds=True),
    )
    symbols, symbol_rows = resolve_symbol_universe(config)
    logger.info("Resolved symbol universe | source=%s | count=%s", config.scheduler.symbol_source, len(symbols))

    auth_session = load_auth_session(config.auth)
    if not auth_session.is_available or auth_session.market_data is None:
        raise RuntimeError(f"Nubra auth failed: {auth_session.error}")

    snapshot = get_dashboard_snapshot(config, symbols, prefer_database=False)
    option_chains = fetch_index_option_chains(auth_session.market_data)

    with connect_db(config.database) as connection:
        apply_schema(connection, SUPABASE_SCHEMA.read_text(encoding="utf-8"))
        stats = run_sync(
            connection=connection,
            scanned_at=snapshot["generated_at"],
            symbol_rows=symbol_rows,
            snapshot=snapshot,
            option_chains=option_chains,
            config=config,
        )
        record_sync_run(
            connection,
            started_at=started_at,
            finished_at=datetime.now(UTC),
            status="success",
            symbol_source=config.scheduler.symbol_source,
            symbol_count=len(symbol_rows),
            details={
                "volume_rows": stats.volume_latest_upserted,
                "signal_board_rows": stats.signal_board_latest_upserted,
                "signal_transitions": stats.signal_transitions_inserted,
                "alert_events": stats.alert_events_inserted,
                "index_wall_rows": stats.index_wall_latest_upserted,
                "index_multi_wall_rows": stats.index_multi_wall_latest_upserted,
                "index_ladder_rows": stats.index_ladder_latest_upserted,
                "drilldown_rows": stats.symbol_drilldown_latest_upserted,
            },
        )

    logger.info(
        "Supabase sync complete | symbols=%s | volume_latest=%s | signal_board=%s | transitions=%s | alerts=%s | index_walls=%s | index_multi=%s | index_ladders=%s | drilldowns=%s",
        stats.symbols_upserted,
        stats.volume_latest_upserted,
        stats.signal_board_latest_upserted,
        stats.signal_transitions_inserted,
        stats.alert_events_inserted,
        stats.index_wall_latest_upserted,
        stats.index_multi_wall_latest_upserted,
        stats.index_ladder_latest_upserted,
        stats.symbol_drilldown_latest_upserted,
    )
    return 0


def run_sync(*, connection, scanned_at, symbol_rows, snapshot, option_chains, config) -> SyncStats:
    scanned_at = scanned_at.astimezone(UTC) if scanned_at.tzinfo else scanned_at.replace(tzinfo=UTC)
    symbol_count = upsert_symbols(connection, symbol_rows)
    volume_latest, volume_history = store_volume_batches(
        connection,
        scanned_at=scanned_at,
        interval=config.scans.volume_interval,
        lookback_days=config.scans.lookback_days,
        batch=snapshot["volume_batch"],
    )
    signal_latest, signal_history, transition_rows, alert_rows = store_signal_board(
        connection,
        scanned_at=scanned_at,
        signals=snapshot["merged_signals"],
    )
    drilldown_latest, drilldown_history = store_symbol_drilldowns(
        connection,
        scanned_at=scanned_at,
        exchange=config.scans.exchange,
        signals=snapshot["merged_signals"],
    )
    index_latest, index_history = store_index_walls(
        connection,
        scanned_at=scanned_at,
        batch=snapshot["index_wall_batch"],
    )
    multi_latest, multi_history = store_index_multi_walls(
        connection,
        scanned_at=scanned_at,
        batch=snapshot["index_multi_wall_batch"],
    )
    ladder_latest, ladder_history = store_index_ladders(
        connection,
        scanned_at=scanned_at,
        snapshots=option_chains,
    )
    return SyncStats(
        symbols_upserted=symbol_count,
        volume_latest_upserted=volume_latest,
        volume_history_inserted=volume_history,
        signal_board_latest_upserted=signal_latest,
        signal_board_history_inserted=signal_history,
        signal_transitions_inserted=transition_rows,
        alert_events_inserted=alert_rows,
        index_wall_latest_upserted=index_latest,
        index_wall_history_inserted=index_history,
        index_multi_wall_latest_upserted=multi_latest,
        index_multi_wall_history_inserted=multi_history,
        index_ladder_latest_upserted=ladder_latest,
        index_ladder_history_inserted=ladder_history,
        symbol_drilldown_latest_upserted=drilldown_latest,
        symbol_drilldown_history_inserted=drilldown_history,
    )


def resolve_symbol_universe(config) -> tuple[tuple[str, ...], list[dict[str, object]]]:
    source = config.scheduler.symbol_source
    if source == "liquid":
        symbols = tuple(LIQUID_STOCKS_SYMBOLS)
        return symbols, _seed_rows(symbols, source="liquid")
    if source == "csv":
        return _load_symbol_csv(config.scheduler.symbols_csv)
    symbols = tuple(TOP_FNO_SYMBOLS)
    return symbols, _seed_rows(symbols, source="top_fno")


def _seed_rows(symbols: tuple[str, ...], *, source: str) -> list[dict[str, object]]:
    return [
        {
            "symbol": symbol,
            "exchange": "NSE",
            "sector": None,
            "industry": None,
            "is_active": True,
            "source": source,
        }
        for symbol in symbols
    ]


def _load_symbol_csv(path_value: str | None) -> tuple[tuple[str, ...], list[dict[str, object]]]:
    if not path_value:
        raise ValueError("SCAN_SYMBOL_SOURCE=csv requires SCAN_SYMBOLS_CSV to be set.")
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise FileNotFoundError(f"Symbol CSV not found: {path}")

    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for raw in reader:
            symbol = (raw.get("symbol") or raw.get("Symbol") or "").strip().upper()
            if not symbol:
                continue
            rows.append(
                {
                    "symbol": symbol,
                    "exchange": (raw.get("exchange") or raw.get("Exchange") or "NSE").strip().upper(),
                    "sector": (raw.get("sector") or raw.get("Sector") or "").strip() or None,
                    "industry": (raw.get("industry") or raw.get("Industry") or "").strip() or None,
                    "is_active": True,
                    "source": "csv",
                }
            )
    symbols = tuple(row["symbol"] for row in rows)
    return symbols, rows


if __name__ == "__main__":
    raise SystemExit(main())
