"""Adapters for nubra-volume-breakout."""

from __future__ import annotations

from typing import Any, Iterable

from ..models import ScanResultBatch, VolumeSignal


def _import_scanner():
    try:
        from nubra_volume_breakout import run_volume_breakout
    except Exception as exc:  # pragma: no cover - import fallback
        raise RuntimeError(
            "nubra-volume-breakout is not installed or could not be imported."
        ) from exc
    return run_volume_breakout


def run_volume_breakout_scan(
    market_data: Any,
    symbols: Iterable[str],
    *,
    lookback_days: int,
    interval: int | str,
    rank: int,
    exchange: str = "NSE",
    instrument_type: str = "STOCK",
    baseline_mode: str = "same_slot",
) -> ScanResultBatch:
    """Run the vendor scanner and normalize the output into model rows."""
    try:
        scanner = _import_scanner()
        df = scanner(
            market_data=market_data,
            stocks=list(symbols),
            lookback_days=lookback_days,
            interval=interval,
            rank=rank,
            exchange=exchange,
            instrument_type=instrument_type,
            baseline_mode=baseline_mode,
        )
        rows = tuple(_to_volume_signals(df))
        return ScanResultBatch(source="nubra_volume_breakout", rows=rows, raw=df)
    except Exception as exc:
        return ScanResultBatch(source="nubra_volume_breakout", errors=(str(exc),))


def _to_volume_signals(frame: Any) -> list[VolumeSignal]:
    if frame is None:
        return []

    records = getattr(frame, "to_dict", None)
    if callable(records):
        try:
            rows = frame.to_dict(orient="records")
        except Exception:
            rows = []
    else:
        rows = list(frame) if isinstance(frame, list) else []

    signals: list[VolumeSignal] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        signals.append(
            VolumeSignal(
                symbol=str(row.get("symbol", "")).strip().upper(),
                candle_time=str(row.get("candle_time", "")).strip(),
                current_volume=_to_float(row.get("current_volume")),
                average_volume=_to_float(row.get("average_volume")),
                volume_ratio=_to_float(row.get("volume_ratio")),
            )
        )
    return signals


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None
