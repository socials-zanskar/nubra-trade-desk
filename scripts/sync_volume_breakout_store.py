from __future__ import annotations

import argparse
import base64
import csv
import json
import logging
import os
import sys
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pandas as pd
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SUPABASE_SCHEMA = ROOT / "supabase" / "schema.sql"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nubra_dash.config import load_app_config
from nubra_dash.services.auth import load_auth_session
from nubra_dash.services.db import (
    apply_schema,
    connect_db,
    record_sync_run,
    upsert_dashboard_universe,
    upsert_dashboard_universe_members,
    upsert_instruments,
    upsert_ohlcv_1m_bars,
    upsert_stock_taxonomy,
)


logger = logging.getLogger("sync_volume_breakout_store")
IST = ZoneInfo("Asia/Kolkata")
MAX_SYMBOLS_PER_QUERY = 10


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sync instruments and 1-minute historical bars for the NubraOSS Volume Breakout dashboard."
    )
    parser.add_argument("--environment", default="PROD", choices=["PROD", "UAT"], help="Nubra environment.")
    parser.add_argument("--lookback-days", type=int, default=20, help="Historical lookback window.")
    parser.add_argument("--batch-size", type=int, default=50, help="Requested historical batch size.")
    parser.add_argument("--symbols-csv", default="data/universes/nifty300_symbols.csv", help="Tracked-universe CSV path.")
    parser.add_argument("--universe-slug", default="volume-breakout-v1", help="Universe slug stored in Supabase.")
    parser.add_argument("--universe-title", default="Volume Breakout V1", help="Universe title stored in Supabase.")
    parser.add_argument("--limit", type=int, default=0, help="Optional limit for testing.")
    return parser.parse_args()


def main() -> int:
    load_dotenv(ROOT / ".env", override=False)
    load_dotenv(ROOT / ".env.local", override=False)
    configure_logging()
    args = parse_args()
    started_at = datetime.now(UTC)

    try:
        config = load_app_config()
        config = replace(
            config,
            auth=replace(config.auth, mode="user", environment=args.environment, use_env_creds=True),
        )
        auth_session = load_auth_session(config.auth)
        if not auth_session.is_available or auth_session.client is None:
            raise RuntimeError(f"Nubra auth failed: {auth_session.error}")

        session_token = _extract_session_token(auth_session.client)
        if not session_token:
            raise RuntimeError("Failed to extract Nubra session token from the authenticated SDK client.")
        device_id = _extract_device_id(auth_session.client, session_token) or _default_device_id()
        if not device_id:
            raise RuntimeError("Unable to resolve device id. Set PHONE_NO or NUBRA_DEVICE_ID.")

        instrument_rows = fetch_cash_stock_refdata(
            session_token=session_token,
            device_id=device_id,
            environment=args.environment,
            exchanges=("NSE", "BSE"),
        )
        tracked_rows = load_symbol_rows(args.symbols_csv)
        if args.limit and args.limit > 0:
            tracked_rows = tracked_rows[: args.limit]

        instruments_by_key = {
            (str(row["symbol"]).upper(), str(row["exchange"]).upper()): row for row in instrument_rows
        }
        eligible_rows = [
            row for row in tracked_rows if (str(row["symbol"]), str(row["exchange"])) in instruments_by_key
        ]

        with connect_db(config.database) as connection:
            apply_schema(connection, SUPABASE_SCHEMA.read_text(encoding="utf-8"))
            instruments_upserted = upsert_instruments(connection, instrument_rows)
            upsert_dashboard_universe(
                connection,
                slug=args.universe_slug,
                title=args.universe_title,
                description="Tracked stock universe for the NubraOSS Volume Breakout dashboard.",
            )
            upsert_dashboard_universe_members(
                connection,
                universe_slug=args.universe_slug,
                rows=[
                    {
                        "universe_slug": args.universe_slug,
                        "symbol": row["symbol"],
                        "exchange": row["exchange"],
                        "sector": row["sector"],
                        "industry": row["industry"],
                        "sort_order": row["sort_order"],
                        "is_active": True,
                    }
                    for row in eligible_rows
                ],
            )
            upsert_stock_taxonomy(
                connection,
                rows=[
                    {
                        "symbol": row["symbol"],
                        "exchange": row["exchange"],
                        "sector": row["sector"],
                        "industry": row["industry"],
                        "notes_json": "{}",
                    }
                    for row in eligible_rows
                ],
            )

            end_dt = datetime.now(UTC)
            start_dt = end_dt - timedelta(days=args.lookback_days)
            effective_batch_size = min(max(args.batch_size, 1), MAX_SYMBOLS_PER_QUERY)
            if effective_batch_size != args.batch_size:
                logger.info(
                    "Requested batch_size=%s exceeds historical API max; using batch_size=%s instead.",
                    args.batch_size,
                    effective_batch_size,
                )

            total_bar_rows = 0
            processed_symbols = 0
            for batch in chunked(eligible_rows, effective_batch_size):
                symbols = tuple(str(row["symbol"]) for row in batch if str(row["exchange"]) == "NSE")
                if not symbols:
                    continue
                frames = fetch_historical_frames(
                    session_token=session_token,
                    device_id=device_id,
                    environment=args.environment,
                    symbols=symbols,
                    start_dt=start_dt,
                    end_dt=end_dt,
                )
                total_bar_rows += upsert_ohlcv_1m_bars(
                    connection,
                    to_ohlcv_rows(frames, exchange="NSE"),
                )
                processed_symbols += len(symbols)
                logger.info(
                    "Volume breakout storage sync progress | symbols=%s/%s | bar_rows=%s",
                    processed_symbols,
                    len(eligible_rows),
                    total_bar_rows,
                )

            record_sync_run(
                connection,
                started_at=started_at,
                finished_at=datetime.now(UTC),
                status="success",
                symbol_source="volume_breakout_storage",
                symbol_count=len(eligible_rows),
                details={
                    "environment": args.environment,
                    "device_id": device_id,
                    "universe_slug": args.universe_slug,
                    "tracked_symbols": len(tracked_rows),
                    "eligible_symbols": len(eligible_rows),
                    "instruments_upserted": instruments_upserted,
                    "ohlcv_rows_upserted": total_bar_rows,
                    "lookback_days": args.lookback_days,
                    "batch_size_requested": args.batch_size,
                    "batch_size_effective": effective_batch_size,
                },
            )

        logger.info(
            "Volume breakout storage sync complete | instruments=%s | eligible_symbols=%s | ohlcv_rows=%s",
            len(instrument_rows),
            len(eligible_rows),
            total_bar_rows,
        )
        return 0
    except Exception as exc:
        logger.exception("Volume breakout storage sync failed")
        try:
            config = load_app_config()
            with connect_db(config.database) as connection:
                apply_schema(connection, SUPABASE_SCHEMA.read_text(encoding="utf-8"))
                record_sync_run(
                    connection,
                    started_at=started_at,
                    finished_at=datetime.now(UTC),
                    status="error",
                    symbol_source="volume_breakout_storage",
                    symbol_count=0,
                    details={"error": str(exc)},
                )
        except Exception:
            pass
        return 1


def _default_device_id() -> str:
    phone = (os.getenv("PHONE_NO", "") or "").strip()
    return f"Nubra-OSS-{phone}" if phone else ""


def _extract_session_token(client: Any) -> str | None:
    token_data = getattr(client, "token_data", None)
    if isinstance(token_data, dict):
        for key in ("session_token", "access_token", "token"):
            value = token_data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    candidates = ("session_token", "access_token", "token", "jwt_token", "auth_token", "BEARER_TOKEN")
    for name in candidates:
        value = getattr(client, name, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    for attr_name in ("client", "_client", "session", "_session", "auth"):
        nested = getattr(client, attr_name, None)
        if nested is None:
            continue
        for name in candidates:
            value = getattr(nested, name, None)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_device_id(client: Any, session_token: str) -> str | None:
    direct = (os.getenv("NUBRA_DEVICE_ID", "") or "").strip()
    if direct:
        return direct

    token_data = getattr(client, "token_data", None)
    if isinstance(token_data, dict):
        for key in ("device_id", "deviceId"):
            value = token_data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    try:
        parts = session_token.split(".")
        if len(parts) < 2:
            return None
        payload = parts[1]
        padding = "=" * (-len(payload) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(payload + padding).decode("utf-8"))
        value = decoded.get("deviceId")
        if isinstance(value, str) and value.strip():
            return value.strip()
    except Exception:
        return None
    return None


def _base_url(environment: str) -> str:
    return "https://uatapi.nubra.io" if environment == "UAT" else "https://api.nubra.io"


def _request_headers(session_token: str, device_id: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {session_token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-device-id": device_id,
    }


def _extract_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    return (
        payload.get("message")
        or payload.get("detail")
        or payload.get("error")
        or f"Nubra request failed with status {response.status_code}."
    )


def fetch_cash_stock_refdata(
    *,
    session_token: str,
    device_id: str,
    environment: str,
    exchanges: tuple[str, ...],
) -> list[dict[str, Any]]:
    today_ist = datetime.now(IST).strftime("%Y-%m-%d")
    raw_rows: list[dict[str, Any]] = []

    with httpx.Client(timeout=30.0) as client:
        for exchange in exchanges:
            response = client.get(
                f"{_base_url(environment)}/refdata/refdata/{today_ist}",
                params={"exchange": exchange},
                headers=_request_headers(session_token, device_id),
            )
            if response.status_code >= 400:
                raise RuntimeError(_extract_error(response))
            payload = response.json()
            rows = payload.get("refdata", [])
            if isinstance(rows, list):
                raw_rows.extend(rows)

    instruments: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in raw_rows:
        derivative_type = str(row.get("derivative_type") or "").strip().upper()
        option_type = str(row.get("option_type") or "").strip().upper()
        if derivative_type in {"FUT", "OPT"} or option_type in {"CE", "PE"}:
            continue

        stock_name = str(row.get("stock_name") or "").strip().upper()
        symbol = str(row.get("symbol") or row.get("asset") or row.get("stock_name") or "").strip().upper()
        exchange = str(row.get("exchange") or "").strip().upper()
        ref_id = _coerce_positive_int(row.get("ref_id"))
        if not symbol or not exchange or ref_id is None:
            continue

        key = (symbol, exchange)
        if key in seen:
            continue
        seen.add(key)
        instruments.append(
            {
                "symbol": symbol,
                "display_name": stock_name or symbol,
                "exchange": exchange,
                "ref_id": ref_id,
                "tick_size": _coerce_positive_int(row.get("tick_size"), 1) or 1,
                "lot_size": _coerce_positive_int(row.get("lot_size"), 1) or 1,
                "instrument_type": "STOCK",
                "is_active": True,
                "source": "nubra_refdata_sync",
                "raw_json": json.dumps(row),
            }
        )

    instruments.sort(key=lambda item: (item["exchange"], item["display_name"]))
    return instruments


def load_symbol_rows(path_value: str) -> list[dict[str, str | int | bool | None]]:
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        raise FileNotFoundError(f"Universe CSV not found: {path}")

    rows: list[dict[str, str | int | bool | None]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, raw in enumerate(reader, start=1):
            symbol = (raw.get("symbol") or raw.get("Symbol") or "").strip().upper()
            exchange = (raw.get("exchange") or raw.get("Exchange") or "NSE").strip().upper()
            if not symbol:
                continue
            rows.append(
                {
                    "symbol": symbol,
                    "exchange": exchange,
                    "sector": (raw.get("sector") or raw.get("Sector") or "").strip() or None,
                    "industry": (raw.get("industry") or raw.get("Industry") or "").strip() or None,
                    "sort_order": index,
                }
            )
    return rows


def chunked(items: list[dict[str, str | int | bool | None]], size: int) -> list[list[dict[str, str | int | bool | None]]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def fetch_historical_frames(
    *,
    session_token: str,
    device_id: str,
    environment: str,
    symbols: tuple[str, ...],
    start_dt: datetime,
    end_dt: datetime,
) -> dict[str, pd.DataFrame]:
    payload = {
        "query": [
            {
                "exchange": "NSE",
                "type": "STOCK",
                "values": list(symbols),
                "fields": ["open", "high", "low", "close", "cumulative_volume"],
                "startDate": start_dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "endDate": end_dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "interval": "1m",
                "intraDay": True,
                "realTime": False,
            }
        ]
    }

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{_base_url(environment)}/charts/timeseries",
            json=payload,
            headers=_request_headers(session_token, device_id),
        )
        if response.status_code >= 400:
            raise RuntimeError(_extract_error(response))
        data = response.json()
    return normalize_history_payload(data)


def normalize_history_payload(payload: dict[str, Any]) -> dict[str, pd.DataFrame]:
    symbol_frames: dict[str, pd.DataFrame] = {}
    for result_item in payload.get("result", []):
        for stock_data in result_item.get("values", []):
            for symbol, symbol_chart in stock_data.items():
                frame = pd.DataFrame(
                    {
                        "open": points_to_series(symbol_chart.get("open", [])),
                        "high": points_to_series(symbol_chart.get("high", [])),
                        "low": points_to_series(symbol_chart.get("low", [])),
                        "close": points_to_series(symbol_chart.get("close", [])),
                        "cumulative_volume": points_to_series(symbol_chart.get("cumulative_volume", [])),
                    }
                ).sort_index()
                if frame.empty:
                    continue
                frame = frame[~frame.index.duplicated(keep="last")]
                frame["bucket_volume"] = derive_bucket_volume(frame["cumulative_volume"])
                for field in ("open", "high", "low", "close"):
                    frame[field] = frame[field] / 100.0
                symbol_frames[str(symbol).strip().upper()] = frame
    return symbol_frames


def points_to_series(points: list[dict[str, Any]]) -> pd.Series:
    timestamps: list[int] = []
    values: list[float] = []
    for point in points:
        timestamp = point.get("ts")
        value = point.get("v")
        if timestamp is None or value is None:
            continue
        timestamps.append(int(timestamp))
        values.append(float(value))
    if not timestamps:
        return pd.Series(dtype="float64")
    index = pd.to_datetime(timestamps, unit="ns", utc=True).tz_convert(IST)
    return pd.Series(values, index=index, dtype="float64")


def derive_bucket_volume(cumulative: pd.Series) -> pd.Series:
    diffed = cumulative.diff()
    return diffed.where(diffed.ge(0), cumulative).fillna(cumulative)


def to_ohlcv_rows(frames: dict[str, pd.DataFrame], *, exchange: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol, frame in frames.items():
        if frame.empty:
            continue
        for timestamp, row in frame.iterrows():
            rows.append(
                {
                    "symbol": symbol,
                    "exchange": exchange,
                    "bucket_timestamp": timestamp.astimezone(UTC).to_pydatetime(),
                    "open_price": float(row["open"]),
                    "high_price": float(row["high"]),
                    "low_price": float(row["low"]),
                    "close_price": float(row["close"]),
                    "bucket_volume": float(row["bucket_volume"]) if pd.notna(row["bucket_volume"]) else None,
                    "cumulative_volume": float(row["cumulative_volume"]) if pd.notna(row["cumulative_volume"]) else None,
                    "source": "nubra_trade_desk_backfill",
                    "raw_json": json.dumps(
                        {
                            "symbol": symbol,
                            "exchange": exchange,
                            "bucket_timestamp_ist": timestamp.strftime("%Y-%m-%d %H:%M:%S %Z"),
                            "open": float(row["open"]),
                            "high": float(row["high"]),
                            "low": float(row["low"]),
                            "close": float(row["close"]),
                            "bucket_volume": float(row["bucket_volume"]) if pd.notna(row["bucket_volume"]) else None,
                            "cumulative_volume": float(row["cumulative_volume"]) if pd.notna(row["cumulative_volume"]) else None,
                        }
                    ),
                }
            )
    return rows


def _coerce_positive_int(value: object, fallback: int | None = None) -> int | None:
    try:
        coerced = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return fallback
    if coerced <= 0:
        return fallback
    return coerced


if __name__ == "__main__":
    raise SystemExit(main())
