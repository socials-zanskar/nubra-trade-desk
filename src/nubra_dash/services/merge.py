"""Combine scanner outputs into one app-friendly signal layer."""

from __future__ import annotations

from typing import Iterable

from ..models import MergedSignal, VolumeSignal, WallSignal


def merge_signals(
    volume_signals: Iterable[VolumeSignal],
    wall_signals: Iterable[WallSignal],
    *,
    regime_signals: Iterable[WallSignal] = (),
) -> tuple[MergedSignal, ...]:
    """Join volume and wall outputs into a single ranked signal list."""
    volume_map = {signal.symbol: signal for signal in volume_signals if signal.symbol}
    wall_map = {signal.symbol: signal for signal in wall_signals if signal.symbol}
    symbols = sorted(set(volume_map) | set(wall_map))
    regime_alignment, regime_note = _resolve_regime(regime_signals)
    merged: list[MergedSignal] = []

    for symbol in symbols:
        volume = volume_map.get(symbol)
        wall = wall_map.get(symbol)
        score = _score_signal(volume, wall, regime_alignment=regime_alignment, regime_note=regime_note)
        merged.append(
            MergedSignal(
                symbol=symbol,
                ltp=wall.ltp if wall else None,
                volume_ratio=volume.volume_ratio if volume else None,
                current_volume=volume.current_volume if volume else None,
                average_volume=volume.average_volume if volume else None,
                wall_type=wall.wall_type if wall else None,
                wall_strike=wall.wall_strike if wall else None,
                wall_proximity_pct=wall.proximity_pct if wall else None,
                bias=wall.bias if wall else None,
                signal_grade=score["grade"],
                signal_reason=score["reason"],
                setup_type=score["setup_type"],
                confidence=score["confidence"],
                action_state=score["action_state"],
                regime_alignment=regime_alignment,
                trigger_price=score["trigger_price"],
                invalidation_price=score["invalidation_price"],
                first_target=score["first_target"],
                why_now=score["why_now"],
            )
        )

    return tuple(sorted(merged, key=_sort_key))


def _score_signal(
    volume: VolumeSignal | None,
    wall: WallSignal | None,
    *,
    regime_alignment: str,
    regime_note: str,
) -> dict[str, object]:
    ratio = volume.volume_ratio if volume and volume.volume_ratio is not None else 0.0
    proximity = wall.proximity_pct if wall and wall.proximity_pct is not None else 999.0
    ltp = wall.ltp if wall else None

    confidence = min(95.0, ratio * 34.0)
    if wall and proximity <= 0.5:
        confidence += 10.0
    elif wall and proximity <= 1.0:
        confidence += 6.0

    if regime_alignment == "Supportive":
        confidence += 8.0
    elif regime_alignment == "Opposing":
        confidence -= 8.0

    confidence = max(10.0 if volume or wall else 0.0, min(99.0, round(confidence, 1)))

    if ratio >= 2.0:
        setup_type = "Expansion breakout"
        action_state = "Actionable"
    elif ratio >= 1.4:
        setup_type = "Building participation"
        action_state = "Building"
    elif ratio >= 1.05:
        setup_type = "Early interest"
        action_state = "Watching"
    elif wall:
        setup_type = "Regime-only context"
        action_state = "Cooling"
    else:
        setup_type = "Background"
        action_state = "Cooling"

    if confidence >= 78:
        grade = "A"
    elif confidence >= 62:
        grade = "B"
    elif confidence >= 40:
        grade = "C"
    else:
        grade = "D"

    if volume and wall and proximity <= 0.5:
        reason = f"{setup_type} with nearby {wall.wall_type or 'wall'} shelf"
    elif volume:
        reason = f"{setup_type} driven by {ratio:.2f}x abnormal participation"
    elif wall:
        reason = "Index or wall context is present, but stock participation is missing"
    else:
        reason = "No usable signal"

    why_now = reason if not regime_note else f"{reason}. {regime_note}"
    trigger_price = ltp * 1.002 if ltp else None
    invalidation_price = ltp * 0.994 if ltp else None
    first_target = ltp * 1.01 if ltp else None

    return {
        "grade": grade,
        "reason": reason,
        "setup_type": setup_type,
        "confidence": confidence,
        "action_state": action_state,
        "trigger_price": trigger_price,
        "invalidation_price": invalidation_price,
        "first_target": first_target,
        "why_now": why_now,
    }


def _resolve_regime(regime_signals: Iterable[WallSignal]) -> tuple[str, str]:
    rows = [row for row in regime_signals if row.bias]
    if not rows:
        return "Neutral", "Index regime is neutral or unavailable."

    bullish = sum(1 for row in rows if (row.bias or "").strip().lower() == "bullish")
    bearish = sum(1 for row in rows if (row.bias or "").strip().lower() == "bearish")
    nearest = min((row.proximity_pct for row in rows if row.proximity_pct is not None), default=None)

    if bullish > bearish:
        note = "Index regime is supportive."
        if nearest is not None:
            note = f"Index regime is supportive, with the nearest major wall {nearest:.2f}% away."
        return "Supportive", note
    if bearish > bullish:
        note = "Index regime is opposing."
        if nearest is not None:
            note = f"Index regime is opposing, with the nearest major wall {nearest:.2f}% away."
        return "Opposing", note
    return "Neutral", "Index regime is mixed."


def _sort_key(signal: MergedSignal) -> tuple[float, float]:
    score_order = {"A": 0, "B": 1, "C": 2, "D": 3}
    return score_order.get(signal.signal_grade, 9), -(signal.confidence or signal.volume_ratio or 0.0)
