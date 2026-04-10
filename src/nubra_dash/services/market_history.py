"""Direct historical-data helpers for drilldowns."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Iterable

import pandas as pd


def fetch_historical_data(
    market_data: Any,
    symbols: Iterable[str],
    *,
    exchange: str,
    instrument_type: str = "STOCK",
    fields: Iterable[str] | None = None,
    start_date: datetime | str | None = None,
    end_date: datetime | str | None = None,
    interval: int | str = "5m",
) -> Any:
    """Lightweight wrapper around `market_data.historical_data(...)`.

    The exact Nubra response shape is intentionally left raw here so the UI
    can decide whether to chart or inspect the payload directly.
    """
    request = {
        "exchange": exchange,
        "type": instrument_type,
        "values": list(symbols),
        "fields": list(fields or ("open", "high", "low", "close", "cumulative_volume")),
        "startDate": _coerce_timestamp(start_date or _default_start()),
        "endDate": _coerce_timestamp(end_date or _default_end()),
        "interval": interval,
        "intraDay": False,
        "realTime": False,
    }
    return market_data.historical_data(request)


def normalize_history_points(response: Any, symbol: str) -> pd.DataFrame:
    """Flatten a Nubra historical response into a chart-friendly frame."""
    if response is None or not getattr(response, "result", None):
        return pd.DataFrame()

    chart_blob = None
    for group in response.result:
        for item in getattr(group, "values", []) or []:
            if symbol in item:
                chart_blob = item[symbol]
                break
        if chart_blob is not None:
            break

    if chart_blob is None:
        return pd.DataFrame()

    series_names = ("open", "high", "low", "close", "cumulative_volume")
    buckets: dict[int, dict[str, float | datetime]] = {}

    for field_name in series_names:
        for point in getattr(chart_blob, field_name, []) or []:
            row = buckets.setdefault(point.timestamp, {})
            row["timestamp"] = pd.to_datetime(point.timestamp, utc=True)
            row[field_name] = point.value / 100 if field_name != "cumulative_volume" else point.value

    frame = pd.DataFrame(buckets.values()).sort_values("timestamp")
    if frame.empty:
        return frame
    frame["timestamp"] = frame["timestamp"].dt.tz_convert("Asia/Kolkata")
    frame["close_change_pct"] = frame["close"].pct_change().fillna(0.0) * 100
    return frame.reset_index(drop=True)


def _coerce_timestamp(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.astimezone()
        return value.isoformat()
    return str(value)


def _default_end() -> datetime:
    return datetime.now().astimezone()


def _default_start() -> datetime:
    return _default_end() - timedelta(days=5)
