"""Close-only indicator and execution logic for the NSE stock study."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from config import (
    ADX_LENGTH,
    ATR_LENGTH, BB_LENGTH, BB_MULTIPLIER, EMA_LENGTH, EXPANSION_LOOKBACK,
    KC_LENGTH, KC_MULTIPLIER, MAX_RANGE_ATR_MULTIPLE,
    MAX_TRUE_RANGE_MEDIAN_MULTIPLE, MIN_SQUEEZE_DAYS, RANGE_LOOKBACK,
    ROUND_TRIP_COST, STOP_ATR_MULTIPLIER, FAST_EMA_LENGTH, MIN_ADX,
    MIN_RELATIVE_VOLUME, TRAILING_STOP_ATR_MULTIPLIER, VOLUME_LOOKBACK,
)


@dataclass(frozen=True)
class Trade:
    signal_date: pd.Timestamp
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    exit_price: float
    stop_price: float
    exit_reason: str
    gross_return: float
    net_return: float
    squeeze_days: int
    signal_histogram: float
    signal_atr: float


def _linreg_last(values: np.ndarray) -> float:
    if np.isnan(values).any():
        return np.nan
    x = np.arange(len(values), dtype=float)
    slope, intercept = np.polyfit(x, values, 1)
    return float(intercept + slope * x[-1])


def add_indicators(prices: pd.DataFrame) -> pd.DataFrame:
    """Implement a LazyBear-inspired signal using daily closing prices only.

    Absolute close-to-close change is the documented proxy for true range and
    ATR. This is necessarily a close-only adaptation, not an OHLC reproduction.
    """
    if "Close" not in prices:
        raise ValueError("Missing Close column")
    frame = prices.loc[:, ["Close"]].dropna().copy()
    frame["true_range"] = frame["Close"].diff().abs()
    frame["atr"] = frame["true_range"].ewm(alpha=1 / ATR_LENGTH, adjust=False,
                                             min_periods=ATR_LENGTH).mean()
    basis = frame["Close"].rolling(BB_LENGTH, min_periods=BB_LENGTH).mean()
    deviation = frame["Close"].rolling(BB_LENGTH, min_periods=BB_LENGTH).std(ddof=0)
    bb_upper, bb_lower = basis + BB_MULTIPLIER * deviation, basis - BB_MULTIPLIER * deviation
    kc_range = frame["true_range"].rolling(KC_LENGTH, min_periods=KC_LENGTH).mean()
    kc_upper, kc_lower = basis + KC_MULTIPLIER * kc_range, basis - KC_MULTIPLIER * kc_range
    frame["squeeze_on"] = (bb_lower > kc_lower) & (bb_upper < kc_upper)
    frame["squeeze_off"] = (bb_lower < kc_lower) & (bb_upper > kc_upper)
    frame["ema_200"] = frame["Close"].ewm(span=EMA_LENGTH, adjust=False,
                                             min_periods=EMA_LENGTH).mean()
    high_close = frame["Close"].rolling(KC_LENGTH, min_periods=KC_LENGTH).max()
    low_close = frame["Close"].rolling(KC_LENGTH, min_periods=KC_LENGTH).min()
    midpoint = ((high_close + low_close) / 2 + basis) / 2
    frame["histogram"] = (frame["Close"] - midpoint).rolling(
        KC_LENGTH, min_periods=KC_LENGTH,
    ).apply(_linreg_last, raw=True)
    frame["histogram_rising"] = frame["histogram"] > frame["histogram"].shift(1)
    frame["positive_falling"] = (frame["histogram"] > 0) & (~frame["histogram_rising"])
    run = frame["squeeze_on"].astype(int).groupby((~frame["squeeze_on"]).cumsum()).cumsum()
    frame["prior_squeeze_days"] = run.shift(1).fillna(0).astype(int)
    frame["squeeze_release"] = frame["squeeze_off"] & frame["squeeze_on"].shift(1).fillna(False)
    rolling_range = frame["Close"].rolling(RANGE_LOOKBACK, min_periods=RANGE_LOOKBACK).max() - frame["Close"].rolling(RANGE_LOOKBACK, min_periods=RANGE_LOOKBACK).min()
    frame["range_confirmed"] = rolling_range <= MAX_RANGE_ATR_MULTIPLE * frame["atr"]
    median_range = frame["true_range"].shift(1).rolling(EXPANSION_LOOKBACK,
                                                           min_periods=EXPANSION_LOOKBACK).median()
    frame["no_expansion"] = frame["true_range"] <= MAX_TRUE_RANGE_MEDIAN_MULTIPLE * median_range
    frame["core_signal"] = (frame["squeeze_release"] & (frame["prior_squeeze_days"] >= MIN_SQUEEZE_DAYS)
                            & (frame["histogram"] > 0) & (frame["Close"] > frame["ema_200"]))
    return frame


def signals_for_variant(frame: pd.DataFrame, variant: str) -> pd.Series:
    core = frame["core_signal"].fillna(False)
    if variant == "baseline":
        return core
    if variant == "range_confirmed":
        return core & frame["range_confirmed"].fillna(False)
    if variant == "no_expansion":
        return core & frame["no_expansion"].fillna(False)
    raise ValueError(f"Unknown variant: {variant}")


def add_improved_indicators(prices: pd.DataFrame) -> pd.DataFrame:
    """Daily OHLCV version with trend, ADX and relative-volume confirmation."""
    required = {"Open", "High", "Low", "Close", "Volume"}
    missing = required - set(prices.columns)
    if missing:
        raise ValueError(f"Missing OHLCV columns: {', '.join(sorted(missing))}")
    frame = prices.loc[:, ["Open", "High", "Low", "Close", "Volume"]].dropna().copy()
    previous_close = frame["Close"].shift(1)
    frame["true_range"] = pd.concat([(frame["High"] - frame["Low"]),
        (frame["High"] - previous_close).abs(), (frame["Low"] - previous_close).abs()], axis=1).max(axis=1)
    frame["atr"] = frame["true_range"].ewm(alpha=1 / ATR_LENGTH, adjust=False, min_periods=ATR_LENGTH).mean()
    basis = frame["Close"].rolling(BB_LENGTH, min_periods=BB_LENGTH).mean()
    deviation = frame["Close"].rolling(BB_LENGTH, min_periods=BB_LENGTH).std(ddof=0)
    bb_upper, bb_lower = basis + BB_MULTIPLIER * deviation, basis - BB_MULTIPLIER * deviation
    kc_range = frame["true_range"].rolling(KC_LENGTH, min_periods=KC_LENGTH).mean()
    kc_upper, kc_lower = basis + KC_MULTIPLIER * kc_range, basis - KC_MULTIPLIER * kc_range
    frame["squeeze_on"] = (bb_lower > kc_lower) & (bb_upper < kc_upper)
    frame["squeeze_off"] = (bb_lower < kc_lower) & (bb_upper > kc_upper)
    run = frame["squeeze_on"].astype(int).groupby((~frame["squeeze_on"]).cumsum()).cumsum()
    frame["prior_squeeze_days"] = run.shift(1).fillna(0).astype(int)
    frame["squeeze_release"] = frame["squeeze_off"] & frame["squeeze_on"].shift(1).fillna(False)
    high = frame["High"].rolling(KC_LENGTH, min_periods=KC_LENGTH).max()
    low = frame["Low"].rolling(KC_LENGTH, min_periods=KC_LENGTH).min()
    midpoint = ((high + low) / 2 + basis) / 2
    frame["histogram"] = (frame["Close"] - midpoint).rolling(KC_LENGTH, min_periods=KC_LENGTH).apply(_linreg_last, raw=True)
    frame["ema_50"] = frame["Close"].ewm(span=FAST_EMA_LENGTH, adjust=False, min_periods=FAST_EMA_LENGTH).mean()
    frame["ema_200"] = frame["Close"].ewm(span=EMA_LENGTH, adjust=False, min_periods=EMA_LENGTH).mean()
    up, down = frame["High"].diff(), -frame["Low"].diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    plus_di = 100 * plus_dm.ewm(alpha=1 / ADX_LENGTH, adjust=False).mean() / frame["atr"]
    minus_di = 100 * minus_dm.ewm(alpha=1 / ADX_LENGTH, adjust=False).mean() / frame["atr"]
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    frame["adx"] = dx.ewm(alpha=1 / ADX_LENGTH, adjust=False, min_periods=ADX_LENGTH).mean()
    frame["relative_volume"] = frame["Volume"] / frame["Volume"].shift(1).rolling(VOLUME_LOOKBACK, min_periods=VOLUME_LOOKBACK).mean()
    frame["improved_signal"] = (
        frame["squeeze_release"] & (frame["prior_squeeze_days"] >= MIN_SQUEEZE_DAYS)
        & (frame["histogram"] > 0) & (frame["histogram"] > frame["histogram"].shift(1))
        & (frame["Close"] > frame["ema_50"]) & (frame["ema_50"] > frame["ema_200"])
        & (frame["adx"] >= MIN_ADX) & (frame["adx"] > frame["adx"].shift(1))
        & (frame["relative_volume"] >= MIN_RELATIVE_VOLUME)
    )
    return frame


def simulate_improved(frame: pd.DataFrame) -> list[Trade]:
    """Next-open entries with intraday initial/trailing ATR stops only."""
    trades: list[Trade] = []
    position: dict[str, object] | None = None
    pending_entry: int | None = None
    rows = frame.reset_index(names="date")
    for i, row in rows.iterrows():
        date = pd.Timestamp(row["date"])
        if pending_entry == i and position is not None:
            entry, atr = float(row["Open"]), float(position["signal_atr"])
            position.update({"entry_date": date, "entry_price": entry,
                             "stop_price": entry - TRAILING_STOP_ATR_MULTIPLIER * atr})
            pending_entry = None
        if position is not None:
            stop = float(position["stop_price"])
            if float(row["Low"]) <= stop:
                trades.append(_finish_trade(position, date, min(float(row["Open"]), stop), "atr_trailing_stop"))
                position = None
                continue
            position["stop_price"] = max(stop, float(row["Close"]) - TRAILING_STOP_ATR_MULTIPLIER * float(row["atr"]))
            continue
        if pending_entry is None and bool(row["improved_signal"]) and i + 1 < len(rows):
            position = {"signal_date": date, "signal_atr": float(row["atr"]),
                        "squeeze_days": int(row["prior_squeeze_days"]),
                        "signal_histogram": float(row["histogram"])}
            pending_entry = i + 1
    # Avoid survivor bias from silently omitting a live position at the fixed
    # sample end; this is a marked-to-market research exit, not a live rule.
    if position is not None and "entry_price" in position:
        last = rows.iloc[-1]
        trades.append(_finish_trade(position, pd.Timestamp(last["date"]), float(last["Close"]), "sample_end"))
    return trades


def simulate_long_only(frame: pd.DataFrame, signals: pd.Series) -> list[Trade]:
    """Use only close prices: next-close entry, close stop, and close exit."""
    trades: list[Trade] = []
    position: dict[str, object] | None = None
    pending_entry: int | None = None
    rows = frame.reset_index(names="date")
    for i, row in rows.iterrows():
        date, close = pd.Timestamp(row["date"]), float(row["Close"])
        if pending_entry == i and position is not None:
            atr = float(position["signal_atr"])
            position.update({"entry_date": date, "entry_price": close,
                             "stop_price": close - STOP_ATR_MULTIPLIER * atr,
                             "entry_index": i})
            pending_entry = None
        if position is not None and i > int(position["entry_index"]):
            if close <= float(position["stop_price"]):
                trades.append(_finish_trade(position, date, close, "close_stop"))
                position = None
                continue
            if bool(row["positive_falling"]):
                trades.append(_finish_trade(position, date, close, "momentum_faded"))
                position = None
                continue
        if position is None and pending_entry is None and bool(signals.iloc[i]) and i + 1 < len(rows):
            position = {"signal_date": date, "signal_atr": float(row["atr"]),
                        "squeeze_days": int(row["prior_squeeze_days"]),
                        "signal_histogram": float(row["histogram"])}
            pending_entry = i + 1
    return trades


def _finish_trade(position: dict[str, object], exit_date: pd.Timestamp, exit_price: float,
                  reason: str) -> Trade:
    entry = float(position["entry_price"])
    gross = exit_price / entry - 1
    return Trade(pd.Timestamp(position["signal_date"]), pd.Timestamp(position["entry_date"]), exit_date,
                 entry, exit_price, float(position["stop_price"]), reason, gross,
                 gross - ROUND_TRIP_COST, int(position["squeeze_days"]),
                 float(position["signal_histogram"]), float(position["signal_atr"]))


def trade_frame(trades: list[Trade], sectors: str, ticker: str, variant: str) -> pd.DataFrame:
    columns = ["sectors", "ticker", "variant", "signal_date", "entry_date", "exit_date", "entry_price",
               "exit_price", "stop_price", "exit_reason", "gross_return", "net_return", "squeeze_days",
               "signal_histogram", "signal_atr"]
    if not trades:
        return pd.DataFrame(columns=columns)
    result = pd.DataFrame([{**trade.__dict__, "sectors": sectors, "ticker": ticker, "variant": variant}
                           for trade in trades])
    return result.loc[:, columns]
