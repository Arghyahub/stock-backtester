"""Indicator, execution, and metric logic for the long-only CMF study."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from config import (ATR_LENGTH, CMF_LENGTH, CMF_THRESHOLD, EMA_LENGTH, FAST_EMA_LENGTH,
                    RISK_REWARD_RATIO, ROUND_TRIP_COST, RSI_LENGTH, RSI_MAX, RSI_MIN,
                    STOP_ATR_MULTIPLIER)


@dataclass(frozen=True)
class Trade:
    signal_date: pd.Timestamp
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    stop_price: float
    target_price: float
    exit_price: float
    exit_reason: str
    gross_return: float
    net_return: float
    holding_sessions: int


@dataclass(frozen=True)
class SimulationResult:
    trades: list[Trade]
    signal_count: int
    skipped_gap_entries: int
    skipped_while_open: int


def add_indicators(prices: pd.DataFrame) -> pd.DataFrame:
    """Calculate CMF(40), EMA(200), ATR(14), and strict upward CMF crossings."""
    required = {"Open", "High", "Low", "Close", "Volume"}
    missing = required - set(prices.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {', '.join(sorted(missing))}")
    frame = prices.loc[:, ["Open", "High", "Low", "Close", "Volume"]].dropna().copy()
    previous_close = frame["Close"].shift(1)
    frame["true_range"] = pd.concat(
        [frame["High"] - frame["Low"], (frame["High"] - previous_close).abs(),
         (frame["Low"] - previous_close).abs()], axis=1,
    ).max(axis=1)
    frame["atr"] = frame["true_range"].ewm(
        alpha=1 / ATR_LENGTH, adjust=False, min_periods=ATR_LENGTH,
    ).mean()
    price_range = frame["High"] - frame["Low"]
    multiplier = ((frame["Close"] - frame["Low"]) - (frame["High"] - frame["Close"]))
    multiplier = multiplier.div(price_range.where(price_range.ne(0)), fill_value=np.nan).fillna(0.0)
    money_flow_volume = multiplier * frame["Volume"]
    volume_sum = frame["Volume"].rolling(CMF_LENGTH, min_periods=CMF_LENGTH).sum()
    frame["cmf"] = money_flow_volume.rolling(CMF_LENGTH, min_periods=CMF_LENGTH).sum().div(
        volume_sum.where(volume_sum.ne(0)), fill_value=np.nan,
    )
    frame["ema_200"] = frame["Close"].ewm(
        span=EMA_LENGTH, adjust=False, min_periods=EMA_LENGTH,
    ).mean()
    frame["ema_50"] = frame["Close"].ewm(
        span=FAST_EMA_LENGTH, adjust=False, min_periods=FAST_EMA_LENGTH,
    ).mean()
    delta = frame["Close"].diff()
    average_gain = delta.clip(lower=0).ewm(alpha=1 / RSI_LENGTH, adjust=False,
                                           min_periods=RSI_LENGTH).mean()
    average_loss = (-delta.clip(upper=0)).ewm(alpha=1 / RSI_LENGTH, adjust=False,
                                               min_periods=RSI_LENGTH).mean()
    relative_strength = average_gain.div(average_loss.where(average_loss.ne(0)))
    frame["rsi_14"] = 100 - 100 / (1 + relative_strength)
    frame.loc[(average_loss == 0) & (average_gain > 0), "rsi_14"] = 100.0
    frame.loc[(average_gain == 0) & (average_loss > 0), "rsi_14"] = 0.0
    frame["cmf_cross_up"] = (frame["cmf"] > CMF_THRESHOLD) & (
        frame["cmf"].shift(1) <= CMF_THRESHOLD
    )
    frame["signal"] = frame["cmf_cross_up"] & (frame["Close"] > frame["ema_200"])
    frame["rsi_ema_signal"] = (
        frame["signal"]
        & (frame["Close"] > frame["ema_50"])
        & (frame["ema_50"] > frame["ema_200"])
        & frame["rsi_14"].between(RSI_MIN, RSI_MAX, inclusive="both")
    )
    return frame


def simulate(frame: pd.DataFrame, signal_column: str = "signal") -> SimulationResult:
    """Trade one long position at a time using daily OHLC and conservative collisions."""
    trades: list[Trade] = []
    signal_count = skipped_gap_entries = skipped_while_open = 0
    position: dict[str, object] | None = None
    pending_signal: dict[str, object] | None = None
    rows = frame.reset_index(names="date")

    for i, row in rows.iterrows():
        date = pd.Timestamp(row["date"])
        if pending_signal is not None:
            stop = float(pending_signal["stop_price"])
            if float(row["Open"]) <= stop:
                skipped_gap_entries += 1
            else:
                entry = float(row["Open"])
                target = entry + RISK_REWARD_RATIO * (entry - stop)
                position = {**pending_signal, "entry_date": date, "entry_price": entry,
                            "target_price": target, "entry_index": i}
            pending_signal = None

        if position is not None:
            stop, target = float(position["stop_price"]), float(position["target_price"])
            open_price, low, high = float(row["Open"]), float(row["Low"]), float(row["High"])
            # A stop gap executes at the open. Within a bar, stop wins any target collision.
            if open_price <= stop:
                trades.append(_finish(position, date, open_price, "stop_gap", i))
                position = None
            elif low <= stop:
                trades.append(_finish(position, date, stop, "stop", i))
                position = None
            elif high >= target:
                trades.append(_finish(position, date, target, "target", i))
                position = None

        if bool(row[signal_column]):
            signal_count += 1
            if position is not None or pending_signal is not None:
                skipped_while_open += 1
            elif i + 1 < len(rows):
                pending_signal = {"signal_date": date,
                                  "stop_price": float(row["Close"]) - STOP_ATR_MULTIPLIER * float(row["atr"])}

    if position is not None:
        last = rows.iloc[-1]
        trades.append(_finish(position, pd.Timestamp(last["date"]), float(last["Close"]), "sample_end", len(rows) - 1))
    return SimulationResult(trades, signal_count, skipped_gap_entries, skipped_while_open)


def _finish(position: dict[str, object], exit_date: pd.Timestamp, exit_price: float,
            reason: str, exit_index: int) -> Trade:
    entry = float(position["entry_price"])
    gross = exit_price / entry - 1
    return Trade(pd.Timestamp(position["signal_date"]), pd.Timestamp(position["entry_date"]), exit_date,
                 entry, float(position["stop_price"]), float(position["target_price"]), exit_price,
                 reason, gross, gross - ROUND_TRIP_COST, exit_index - int(position["entry_index"]) + 1)


def trade_frame(trades: list[Trade], ticker: str, industry: str, horizon: str,
                variant: str) -> pd.DataFrame:
    columns = ["variant", "horizon", "industry", "ticker", *Trade.__dataclass_fields__]
    return pd.DataFrame(
        [{"variant": variant, "horizon": horizon, "industry": industry, "ticker": ticker,
          **asdict(trade)} for trade in trades],
        columns=columns,
    )


def metrics(trades: pd.DataFrame, signals: int, skipped_gap: int, skipped_open: int) -> dict[str, object]:
    returns = trades["net_return"] if not trades.empty else pd.Series(dtype=float)
    wins, losses = returns[returns > 0], returns[returns <= 0]
    equity = (1 + returns).cumprod()
    drawdown = equity.div(equity.cummax()).sub(1) if not equity.empty else pd.Series(dtype=float)
    gross_loss = -losses.sum()
    return {
        "signal_count": signals, "executed_trade_count": len(trades),
        "skipped_gap_entries": skipped_gap, "skipped_while_open": skipped_open,
        "win_count": len(wins), "loss_count": len(losses),
        "win_rate": float((returns > 0).mean()) if not returns.empty else np.nan,
        "mean_net_return": returns.mean(), "median_net_return": returns.median(),
        "total_compounded_return": (1 + returns).prod() - 1 if not returns.empty else np.nan,
        "profit_factor": wins.sum() / gross_loss if gross_loss > 0 else (np.inf if wins.sum() > 0 else np.nan),
        "worst_trade": returns.min(), "max_sequential_drawdown": drawdown.min(),
        "average_holding_sessions": trades["holding_sessions"].mean() if not trades.empty else np.nan,
        "target_exits": int((trades["exit_reason"] == "target").sum()) if not trades.empty else 0,
        "stop_exits": int(trades["exit_reason"].isin(["stop", "stop_gap"]).sum()) if not trades.empty else 0,
        "sample_end_exits": int((trades["exit_reason"] == "sample_end").sum()) if not trades.empty else 0,
    }
