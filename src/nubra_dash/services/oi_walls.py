"""Adapters for nubra-oi-walls."""

from __future__ import annotations

from typing import Any, Iterable

from ..models import OIWallCandidate, ScanResultBatch, WallSignal


def _import_scanner():
    try:
        from nubra_oi_walls import run_multi_wall_proximity_scan, run_wall_proximity_scan
    except Exception as exc:  # pragma: no cover - import fallback
        raise RuntimeError("nubra-oi-walls is not installed or could not be imported.") from exc
    return run_wall_proximity_scan, run_multi_wall_proximity_scan


def run_oi_walls_scan(
    market_data: Any,
    symbols: Iterable[str],
    *,
    normalize: bool = False,
    exchange: str = "NSE",
) -> ScanResultBatch:
    """Run the primary wall scan and normalize the output."""
    try:
        run_wall_proximity_scan, _ = _import_scanner()
        df = run_wall_proximity_scan(
            stocks=list(symbols),
            market_data=market_data,
            normalize=normalize,
            exchange=exchange,
        )
        rows = tuple(_to_wall_signals(df, exchange=exchange))
        return ScanResultBatch(source="nubra_oi_walls", rows=rows, raw=df)
    except Exception as exc:
        return ScanResultBatch(source="nubra_oi_walls", errors=(str(exc),))


def run_multi_wall_scan(
    market_data: Any,
    symbols: Iterable[str],
    *,
    top_n: int = 3,
    normalize: bool = False,
    exchange: str = "NSE",
) -> ScanResultBatch:
    """Run the expanded wall scan for clustered support/resistance context."""
    try:
        _, run_multi_wall_proximity_scan = _import_scanner()
        df = run_multi_wall_proximity_scan(
            stocks=list(symbols),
            market_data=market_data,
            top_n=top_n,
            normalize=normalize,
            exchange=exchange,
        )
        rows = tuple(_to_wall_candidates(df))
        return ScanResultBatch(source="nubra_oi_walls_multi", rows=rows, raw=df)
    except Exception as exc:
        return ScanResultBatch(source="nubra_oi_walls_multi", errors=(str(exc),))


def _to_wall_signals(frame: Any, *, exchange: str) -> list[WallSignal]:
    if frame is None:
        return []

    try:
        rows = frame.to_dict(orient="records")
    except Exception:
        rows = []

    signals: list[WallSignal] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        wall_type = str(row.get("Wall Type", row.get("wall_type", ""))).strip() or None
        wall_strike = _to_float(row.get("Wall Strike", row.get("wall_strike")))
        wall_oi = _to_float(row.get("Strength", row.get("wall_oi")))
        signals.append(
            WallSignal(
                symbol=str(row.get("Stock", row.get("symbol", ""))).strip().upper(),
                ltp=_to_float(row.get("LTP", row.get("ltp"))),
                wall_type=wall_type,
                wall_strike=wall_strike,
                wall_oi=wall_oi,
                proximity_pct=_parse_percent(row.get("Proximity", row.get("proximity_pct"))),
                bias=str(row.get("Bias", row.get("bias", ""))).strip() or None,
                exchange=exchange,
            )
        )
    return signals


def _to_wall_candidates(frame: Any) -> list[OIWallCandidate]:
    if frame is None:
        return []

    try:
        rows = frame.to_dict(orient="records")
    except Exception:
        rows = []

    candidates: list[OIWallCandidate] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        candidates.append(
            OIWallCandidate(
                symbol=str(row.get("symbol", "")).strip().upper(),
                ltp=_to_float(row.get("ltp")),
                wall_side=str(row.get("wall_side", "")).strip().upper(),
                rank=int(row.get("rank", 0) or 0),
                strike=_to_float(row.get("strike")),
                oi=_parse_oi(row.get("oi")),
                dist_pct=_to_float(row.get("dist_pct")) or 0.0,
                selected=str(row.get("selected", "")).strip().lower() in {"yes", "true", "1"},
            )
        )
    return candidates


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(str(value).replace(",", "").replace("Rs", "").strip())
    except Exception:
        return None


def _parse_percent(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).replace("%", "").strip()
    return _to_float(text)


def _parse_oi(value: Any) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().upper().replace(",", "")
    multipliers = {"CR": 10_000_000.0, "L": 100_000.0}
    for suffix, multiplier in multipliers.items():
        if text.endswith(suffix):
            try:
                return float(text[: -len(suffix)].strip()) * multiplier
            except Exception:
                return 0.0
    try:
        return float(text)
    except Exception:
        return 0.0
