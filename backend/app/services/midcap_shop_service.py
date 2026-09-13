"""Public, database-free daily scanner for the capped Midcap SHOP strategy."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from io import StringIO
from threading import Lock
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

NIFTY_MIDCAP_50_CSV_URL = "https://nsearchives.nseindia.com/content/indices/ind_niftymidcap50list.csv"
CACHE_SECONDS = 15 * 60
_cache: dict | None = None
_cache_at: datetime | None = None
_lock = Lock()


def india_today() -> date:
    return datetime.now(ZoneInfo("Asia/Kolkata")).date()


def fetch_universe() -> dict[str, str]:
    request = Request(NIFTY_MIDCAP_50_CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=20) as response:
        table = pd.read_csv(StringIO(response.read().decode("utf-8")))
    if "Symbol" not in table:
        raise ValueError("Official Midcap 50 file did not contain Symbol")
    name_column = "Company Name" if "Company Name" in table.columns else "Symbol"
    return {f"{row['Symbol']}.NS": str(row[name_column]) for _, row in table.iterrows()}


def fetch_prices(tickers: list[str], start: date, end: date) -> dict[str, pd.DataFrame]:
    raw = yf.download(tickers, start=start.isoformat(), end=end.isoformat(), auto_adjust=False,
                      actions=False, progress=False, group_by="ticker", threads=True)
    if raw.empty:
        raise ValueError("Yahoo Finance returned no daily data")
    output: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        try:
            frame = raw[ticker] if isinstance(raw.columns, pd.MultiIndex) else raw
            frame = frame.loc[:, ["Close"]].dropna().copy()
            frame.index = pd.DatetimeIndex(frame.index).tz_localize(None)
            if len(frame) >= 20:
                output[ticker] = frame
        except (KeyError, TypeError):
            continue
    return output


def build_scan(today: date | None = None) -> dict:
    """Build a scan using only sessions before the current India calendar day."""
    session_today = today or india_today()
    universe = fetch_universe()
    # ``end`` is exclusive in yfinance; this deliberately excludes a partial current session.
    frames = fetch_prices(list(universe), session_today - timedelta(days=90), session_today)
    candidates: list[dict] = []
    for ticker, frame in frames.items():
        frame["sma_20"] = frame["Close"].rolling(20, min_periods=20).mean()
        row = frame.iloc[-1]
        if pd.isna(row.sma_20):
            continue
        candidates.append({"ticker": ticker, "name": universe[ticker],
                           "close": round(float(row.Close), 2), "sma_20": round(float(row.sma_20), 2),
                           "distance_below_sma": float(row.Close / row.sma_20 - 1),
                           "as_of_date": str(frame.index[-1].date())})
    if len(candidates) < 5:
        raise ValueError("Fewer than five Midcap 50 stocks had sufficient completed daily history")
    candidates.sort(key=lambda item: (item["distance_below_sma"], item["ticker"]))
    shortlist = candidates[:5]
    as_of = min(item["as_of_date"] for item in shortlist)
    for rank, item in enumerate(shortlist, start=1):
        item["shortlist_rank"] = rank
    return {"as_of_date": as_of, "generated_at": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
            "stale": False, "universe_size": len(universe), "candidates": shortlist}


def scan() -> dict:
    global _cache, _cache_at
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    with _lock:
        if _cache is not None and _cache_at is not None and (now - _cache_at).total_seconds() < CACHE_SECONDS:
            return _cache
    try:
        result = build_scan()
    except Exception:
        with _lock:
            if _cache is not None:
                return {**_cache, "stale": True}
        raise
    with _lock:
        _cache, _cache_at = result, now
    return result


def clear_cache() -> None:
    """Test-only cache reset."""
    global _cache, _cache_at
    with _lock:
        _cache = _cache_at = None
