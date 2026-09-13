"""Zerodha retail equity-delivery charge calculations."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from config import (DP_SELL_PER_SCRIP_DAY, GST_RATE, NSE_TRANSACTION_RATE, SEBI_RATE,
                    STAMP_BUY_RATE, STT_RATE)


@dataclass(frozen=True)
class Charges:
    brokerage: float = 0.0
    stt: float = 0.0
    transaction: float = 0.0
    sebi: float = 0.0
    gst: float = 0.0
    stamp: float = 0.0
    dp: float = 0.0

    @property
    def total(self) -> float:
        return sum(asdict(self).values())

    def plus(self, other: "Charges") -> "Charges":
        return Charges(**{key: getattr(self, key) + getattr(other, key)
                          for key in asdict(self)})


def delivery_charges(turnover: float, side: str, dp: float = 0.0) -> Charges:
    """Return current NSE/Zerodha delivery charges for one executed order."""
    if turnover < 0 or side not in {"buy", "sell"}:
        raise ValueError("turnover must be non-negative and side must be buy or sell")
    transaction = turnover * NSE_TRANSACTION_RATE
    sebi = turnover * SEBI_RATE
    return Charges(stt=turnover * STT_RATE, transaction=transaction, sebi=sebi,
                   gst=GST_RATE * (transaction + sebi),
                   stamp=turnover * STAMP_BUY_RATE if side == "buy" else 0.0,
                   dp=dp)


def grouped_sell_charges(turnovers: list[float]) -> list[Charges]:
    """Allocate one DP debit across lots in a same-scrip, same-day sale."""
    if not turnovers:
        return []
    total = sum(turnovers)
    if total <= 0:
        raise ValueError("sell turnover must be positive")
    return [delivery_charges(value, "sell", DP_SELL_PER_SCRIP_DAY * value / total)
            for value in turnovers]
