"""Normalized models consumed by the Streamlit UI."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class AuthSession:
    """Resolved Nubra session details."""

    mode: str
    environment: str
    client: Any | None = None
    market_data: Any | None = None
    is_available: bool = False
    error: str | None = None


@dataclass(frozen=True, slots=True)
class VolumeSignal:
    """Normalized output from the volume breakout scanner."""

    symbol: str
    candle_time: str
    current_volume: float | None
    average_volume: float | None
    volume_ratio: float | None
    scan_status: str = "ok"
    signal_summary: str | None = None
    baseline_details: str | None = None
    price_details: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OIWallCandidate:
    """Expanded candidate row from the multi-wall scanner."""

    symbol: str
    ltp: float
    wall_side: str
    rank: int
    strike: float
    oi: float
    dist_pct: float
    selected: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class WallSignal:
    """Normalized output from the OI wall scanner."""

    symbol: str
    ltp: float | None
    wall_type: str | None
    wall_strike: float | None
    wall_oi: float | None
    proximity_pct: float | None
    bias: str | None = None
    exchange: str | None = None
    expiry: str | None = None
    selected: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class MergedSignal:
    """Unified signal card used by the future UI."""

    symbol: str
    ltp: float | None
    volume_ratio: float | None
    current_volume: float | None
    average_volume: float | None
    wall_type: str | None
    wall_strike: float | None
    wall_proximity_pct: float | None
    bias: str | None
    signal_grade: str
    signal_reason: str
    setup_type: str = "Scanner"
    confidence: float = 0.0
    action_state: str = "Cooling"
    regime_alignment: str = "Neutral"
    trigger_price: float | None = None
    invalidation_price: float | None = None
    first_target: float | None = None
    why_now: str | None = None
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SymbolDrilldown:
    """Symbol-level detail model for chart and narrative pages."""

    symbol: str
    exchange: str | None
    ltp: float | None
    volume_signal: VolumeSignal | None
    wall_signal: WallSignal | None
    merged_signal: MergedSignal | None
    history_points: int = 0
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ScanResultBatch:
    """Container for scanner outputs and fallback diagnostics."""

    source: str
    rows: tuple[Any, ...] = ()
    errors: tuple[str, ...] = ()
    raw: Any | None = None

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AppState:
    """Lightweight state snapshot for the UI layer later on."""

    auth: AuthSession | None = None
    volume: ScanResultBatch | None = None
    walls: ScanResultBatch | None = None
    merged: tuple[MergedSignal, ...] = ()
