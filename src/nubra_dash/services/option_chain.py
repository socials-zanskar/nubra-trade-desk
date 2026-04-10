"""Option-chain helpers for visual OI ladders."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd


INDEX_CHAIN_TARGETS: tuple[tuple[str, str], ...] = (
    ("NIFTY", "NSE"),
    ("SENSEX", "BSE"),
)


@dataclass(frozen=True, slots=True)
class OptionChainSnapshot:
    symbol: str
    exchange: str
    expiry: str | None
    spot: float
    frame: pd.DataFrame


def fetch_index_option_chains(market_data: Any) -> tuple[OptionChainSnapshot, ...]:
    snapshots: list[OptionChainSnapshot] = []
    for symbol, exchange in INDEX_CHAIN_TARGETS:
        try:
            response = market_data.option_chain(symbol, exchange=exchange)
            chain = response.chain
            spot = _paise_to_price(getattr(chain, "current_price", 0))
            expiry = str(getattr(chain, "expiry", "") or "")
            frame = normalize_option_chain(chain)
            snapshots.append(
                OptionChainSnapshot(
                    symbol=symbol,
                    exchange=exchange,
                    expiry=expiry,
                    spot=spot,
                    frame=frame,
                )
            )
        except Exception:
            continue
    return tuple(snapshots)


def normalize_option_chain(chain: Any) -> pd.DataFrame:
    ce_map = {getattr(item, "strike_price", None): item for item in (getattr(chain, "ce", None) or [])}
    pe_map = {getattr(item, "strike_price", None): item for item in (getattr(chain, "pe", None) or [])}
    strikes = sorted({strike for strike in ce_map if strike is not None} | {strike for strike in pe_map if strike is not None})
    rows: list[dict[str, float]] = []
    for strike in strikes:
        ce = ce_map.get(strike)
        pe = pe_map.get(strike)
        rows.append(
            {
                "strike": _paise_to_price(strike),
                "call_oi": float(getattr(ce, "open_interest", 0) or 0),
                "put_oi": float(getattr(pe, "open_interest", 0) or 0),
                "call_volume": float(getattr(ce, "volume", 0) or 0),
                "put_volume": float(getattr(pe, "volume", 0) or 0),
            }
        )
    return pd.DataFrame(rows)


def slice_chain_window(frame: pd.DataFrame, spot: float, *, strikes_each_side: int = 14) -> pd.DataFrame:
    if frame.empty:
        return frame
    indexed = frame.copy()
    indexed["distance"] = (indexed["strike"] - spot).abs()
    indexed = indexed.sort_values(["distance", "strike"])
    window = indexed.head(strikes_each_side * 2 + 1).sort_values("strike").drop(columns=["distance"])
    return window.reset_index(drop=True)


def _paise_to_price(value: Any) -> float:
    try:
        return float(value or 0) / 100
    except Exception:
        return 0.0
