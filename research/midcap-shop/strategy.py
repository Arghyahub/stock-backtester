"""Daily next-open portfolio simulation for the Midcap SHOP rules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from itertools import count

import numpy as np
import pandas as pd

from charges import Charges, delivery_charges, grouped_sell_charges
from config import (AVERAGE_DIVISOR, AVERAGE_TRIGGER, FRESH_DIVISOR, INITIAL_CASH,
                    MAX_AVERAGE_BUYS_PER_STOCK, RSI_LENGTH, RSI_OVERSOLD, SHORTLIST_SIZE,
                    SMA_LENGTH, TARGET_RETURN, TREND_SMA_LENGTH)


@dataclass
class Lot:
    id: int
    ticker: str
    entry_date: pd.Timestamp
    entry_price: float
    quantity: int
    buy_charges: Charges
    entry_session_number: int

    @property
    def target(self) -> float:
        return self.entry_price * (1 + TARGET_RETURN)


@dataclass
class PendingBuy:
    ticker: str
    amount: float
    kind: str


@dataclass(frozen=True)
class StrategySettings:
    """Optional confirmation gates applied to every new purchase, including averages."""
    rsi_oversold: bool = False
    trend_sma: bool = False
    stock_level_target: bool = False


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    equity_curve: pd.DataFrame
    skipped: pd.DataFrame
    charge_totals: Charges


def add_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"Open", "High", "Low", "Close", "Volume"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {', '.join(sorted(missing))}")
    result = frame.loc[:, ["Open", "High", "Low", "Close", "Volume"]].dropna().copy()
    result["sma_20"] = result["Close"].rolling(SMA_LENGTH, min_periods=SMA_LENGTH).mean()
    result["sma_200"] = result["Close"].rolling(TREND_SMA_LENGTH, min_periods=TREND_SMA_LENGTH).mean()
    result["distance_below_sma"] = result["Close"].div(result["sma_20"]).sub(1)
    delta = result["Close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / RSI_LENGTH, adjust=False, min_periods=RSI_LENGTH).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / RSI_LENGTH, adjust=False, min_periods=RSI_LENGTH).mean()
    result["rsi_14"] = 100 - 100 / (1 + gain.div(loss.where(loss.ne(0))))
    result.loc[(loss == 0) & (gain > 0), "rsi_14"] = 100.0
    result.loc[(gain == 0) & (loss > 0), "rsi_14"] = 0.0
    return result


def weakest_shortlist(frames: dict[str, pd.DataFrame], session: pd.Timestamp) -> list[str]:
    candidates: list[tuple[float, str]] = []
    for ticker, frame in frames.items():
        if session not in frame.index:
            continue
        value = frame.loc[session, "distance_below_sma"]
        if pd.notna(value):
            candidates.append((float(value), ticker))
    return [ticker for _, ticker in sorted(candidates)[:SHORTLIST_SIZE]]


class MidcapShopBacktest:
    def __init__(self, frames: dict[str, pd.DataFrame], actions: dict[str, pd.DataFrame] | None = None,
                 initial_cash: float = INITIAL_CASH, settings: StrategySettings | None = None) -> None:
        self.frames = {ticker: add_indicators(frame) for ticker, frame in frames.items()}
        self.actions = actions or {}
        self.settings = settings or StrategySettings()
        self.cash = initial_cash
        self.lots: list[Lot] = []
        self.pending_buys: list[PendingBuy] = []
        self.pending_sells: set[int] = set()
        self.trade_rows: list[dict[str, object]] = []
        self.skipped_rows: list[dict[str, object]] = []
        self.equity_rows: list[dict[str, object]] = []
        self.charge_totals = Charges()
        self.ids = count(1)

    def _action_row(self, ticker: str, session: pd.Timestamp) -> pd.Series | None:
        frame = self.actions.get(ticker)
        if frame is None or session not in frame.index:
            return None
        return frame.loc[session]

    def _apply_actions(self, session: pd.Timestamp) -> None:
        for ticker in {lot.ticker for lot in self.lots}:
            row = self._action_row(ticker, session)
            if row is None:
                continue
            split = float(row.get("Stock Splits", 0.0) or 0.0)
            dividend = float(row.get("Dividends", 0.0) or 0.0)
            ticker_lots = [lot for lot in self.lots if lot.ticker == ticker]
            if split not in (0.0, 1.0):
                for lot in ticker_lots:
                    lot.quantity = int(round(lot.quantity * split))
                    lot.entry_price /= split
            if dividend:
                self.cash += dividend * sum(lot.quantity for lot in ticker_lots)

    def _latest_price(self, ticker: str, session: pd.Timestamp, field: str = "Close") -> float | None:
        frame = self.frames[ticker]
        if session not in frame.index or pd.isna(frame.loc[session, field]):
            return None
        return float(frame.loc[session, field])

    def _portfolio_equity(self, session: pd.Timestamp) -> float:
        total = self.cash
        for lot in self.lots:
            price = self._latest_price(lot.ticker, session)
            if price is not None:
                total += lot.quantity * price
        return total

    def _passes_buy_filters(self, ticker: str, session: pd.Timestamp) -> bool:
        row = self.frames[ticker].loc[session]
        if self.settings.rsi_oversold and (pd.isna(row["rsi_14"]) or row["rsi_14"] >= RSI_OVERSOLD):
            return False
        if self.settings.trend_sma and (pd.isna(row["sma_200"]) or row["Close"] <= row["sma_200"]):
            return False
        return True

    def _execute_sells(self, session: pd.Timestamp, session_number: int) -> None:
        sell_lots = [lot for lot in self.lots if lot.id in self.pending_sells]
        self.pending_sells.clear()
        by_ticker: dict[str, list[Lot]] = {}
        for lot in sell_lots:
            by_ticker.setdefault(lot.ticker, []).append(lot)
        for ticker, lots in by_ticker.items():
            price = self._latest_price(ticker, session, "Open")
            if price is None or price <= 0:
                self.skipped_rows.extend({"date": session, "ticker": ticker, "kind": "sell",
                                          "reason": "missing_open"} for _ in lots)
                self.pending_sells.update(lot.id for lot in lots)
                continue
            charges = grouped_sell_charges([price * lot.quantity for lot in lots])
            for lot, sell_charge in zip(lots, charges):
                turnover = price * lot.quantity
                self.cash += turnover - sell_charge.total
                self.charge_totals = self.charge_totals.plus(sell_charge)
                gross = (price - lot.entry_price) * lot.quantity
                self.trade_rows.append({"ticker": ticker, "entry_date": lot.entry_date,
                    "exit_date": session, "entry_price": lot.entry_price, "exit_price": price,
                    "quantity": lot.quantity, "target_price": lot.target, "gross_pnl": gross,
                    "net_pnl": gross - lot.buy_charges.total - sell_charge.total,
                    "holding_sessions": session_number - lot.entry_session_number + 1,
                    **{f"buy_{k}": v for k, v in asdict(lot.buy_charges).items()},
                    **{f"sell_{k}": v for k, v in asdict(sell_charge).items()}})
                self.lots.remove(lot)

    def _execute_buys(self, session: pd.Timestamp, session_number: int) -> None:
        orders, self.pending_buys = self.pending_buys, []
        for order in orders:
            price = self._latest_price(order.ticker, session, "Open")
            if price is None or price <= 0:
                self.skipped_rows.append({"date": session, "ticker": order.ticker, "kind": order.kind,
                                          "reason": "missing_open"})
                continue
            quantity = int(order.amount // price)
            if quantity < 1:
                self.skipped_rows.append({"date": session, "ticker": order.ticker, "kind": order.kind,
                                          "reason": "amount_below_one_share"})
                continue
            while quantity:
                charges = delivery_charges(quantity * price, "buy")
                if quantity * price + charges.total <= self.cash + 1e-9:
                    break
                quantity -= 1
            if not quantity:
                self.skipped_rows.append({"date": session, "ticker": order.ticker, "kind": order.kind,
                                          "reason": "insufficient_cash"})
                continue
            self.cash -= quantity * price + charges.total
            self.charge_totals = self.charge_totals.plus(charges)
            self.lots.append(Lot(next(self.ids), order.ticker, session, price, quantity, charges,
                                 session_number))

    def _queue_orders(self, session: pd.Timestamp) -> None:
        if self.settings.stock_level_target:
            for ticker in {lot.ticker for lot in self.lots}:
                ticker_lots = [lot for lot in self.lots if lot.ticker == ticker]
                close = self._latest_price(ticker, session)
                quantity = sum(lot.quantity for lot in ticker_lots)
                average_cost = sum(lot.entry_price * lot.quantity for lot in ticker_lots) / quantity
                if close is not None and close >= average_cost * (1 + TARGET_RETURN):
                    self.pending_sells.update(lot.id for lot in ticker_lots)
        else:
            for lot in self.lots:
                close = self._latest_price(lot.ticker, session)
                if close is not None and close >= lot.target:
                    self.pending_sells.add(lot.id)
        shortlist = weakest_shortlist(self.frames, session)
        if len(shortlist) < SHORTLIST_SIZE:
            return
        held = {lot.ticker for lot in self.lots}
        fresh = next((ticker for ticker in shortlist if ticker not in held and self._passes_buy_filters(ticker, session)), None)
        equity = self._portfolio_equity(session)
        if fresh:
            self.pending_buys.append(PendingBuy(fresh, equity / FRESH_DIVISOR, "fresh"))
            return
        eligible: list[tuple[float, str]] = []
        for ticker in held:
            price = self._latest_price(ticker, session)
            ticker_lots = [lot for lot in self.lots if lot.ticker == ticker]
            # The initial lot plus at most three averaging lots may be open at once.
            if (price is None or not ticker_lots or not self._passes_buy_filters(ticker, session)
                    or len(ticker_lots) >= 1 + MAX_AVERAGE_BUYS_PER_STOCK):
                continue
            last = max(ticker_lots, key=lambda lot: lot.entry_date)
            decline = price / last.entry_price - 1
            if decline < -AVERAGE_TRIGGER:
                eligible.append((decline, ticker))
        if eligible:
            self.pending_buys.append(PendingBuy(min(eligible)[1], equity / AVERAGE_DIVISOR, "average"))

    def run(self, start: pd.Timestamp, end: pd.Timestamp) -> BacktestResult:
        sessions = sorted(set().union(*(frame.index for frame in self.frames.values())))
        session_number = 0
        for session in sessions:
            if session < start or session > end:
                continue
            session_number += 1
            self._apply_actions(session)
            self._execute_sells(session, session_number)
            self._execute_buys(session, session_number)
            self._queue_orders(session)
            equity = self._portfolio_equity(session)
            self.equity_rows.append({"date": session, "cash": self.cash, "holdings_value": equity - self.cash,
                                     "equity": equity, "open_lots": len(self.lots)})
        return BacktestResult(pd.DataFrame(self.trade_rows), pd.DataFrame(self.equity_rows),
                              pd.DataFrame(self.skipped_rows), self.charge_totals)
