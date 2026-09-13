"""Persisted implementation of the walk-forward seasonal research rules."""
from __future__ import annotations

from calendar import monthrange
from math import ceil
from collections import defaultdict
from datetime import date, datetime, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from xml.etree import ElementTree

import numpy as np
import pandas as pd
import yfinance as yf
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.enums import EquityType, IntervalType
from app.db.models.anomaly import InstrumentMapping, PlanInstrument, StrategyPlan, StrategyRun
from app.db.models.equity import Equity
from app.db.models.price import Price
from app.data.sector_universe import SECTOR_UNIVERSE

STRATEGY_KEY = "anomaly-trading"
MIN_TRAIN_OBSERVATIONS, MIN_OOS_RETURN, MAX_DRAWDOWN, COST = 3, 0.03, -0.10, 0.002
WINDOW_BUFFER_DAYS = 10


def completed_years() -> list[int]:
    return list(range(date.today().year - 5, date.today().year))


def ensure_static_universe(db: Session) -> None:
    """Upsert the bundled snapshot; this never makes a web request."""
    sectors = db.scalars(select(Equity).where(Equity.type == EquityType.SECTOR)).all()
    sector_by_name = {sector.name: sector for sector in sectors}
    desired = [(sector_by_name[name], ticker, kind)
               for name, universe in SECTOR_UNIVERSE.items() if name in sector_by_name
               for kind, tickers in ((EquityType.STOCK, universe["stocks"]), (EquityType.ETF, universe["etfs"]))
               for ticker in tickers]
    tickers = {ticker for _, ticker, _ in desired}
    existing = {equity.ticker: equity for equity in db.scalars(select(Equity).where(Equity.ticker.in_(tickers))).all()} if tickers else {}
    for _, ticker, kind in desired:
        if ticker not in existing:
            equity = Equity(ticker=ticker, name=ticker.removesuffix(".NS"), type=kind)
            db.add(equity); existing[ticker] = equity
    db.flush()
    pairs = {(sector_id, instrument_id) for sector_id, instrument_id in db.execute(
        select(InstrumentMapping.sector_equity_id, InstrumentMapping.instrument_equity_id)
        .where(InstrumentMapping.sector_equity_id.in_([sector.pk_equity_id for sector, _, _ in desired]))
    )}
    for sector, ticker, _ in desired:
        pair = (sector.pk_equity_id, existing[ticker].pk_equity_id)
        if pair not in pairs:
            db.add(InstrumentMapping(sector_equity_id=pair[0], instrument_equity_id=pair[1], active=True))
    db.commit()


def first_session(index: pd.DatetimeIndex, year: int, month: int, day: int) -> int | None:
    if day > monthrange(year, month)[1]: return None
    pos = int(index.searchsorted(pd.Timestamp(year, month, day)))
    return pos if pos < len(index) and index[pos].year == year else None


def download_and_store(db: Session, equity: Equity, years: list[int], existing_dates: set[datetime] | None = None,
                       start: date | None = None, end: date | None = None) -> dict:
    """Upsert real daily sessions only; no holiday forward filling."""
    start = start or date(years[0], 1, 1)
    end = end or date.today()
    raw = yf.download(equity.ticker, start=start.isoformat(), end=(end + timedelta(days=1)).isoformat(),
                      auto_adjust=False, actions=False, progress=False)
    if raw.empty: raise ValueError("No daily data returned")
    if isinstance(raw.columns, pd.MultiIndex): raw.columns = raw.columns.get_level_values(0)
    raw = raw.dropna(subset=["Close"])
    existing = existing_dates if existing_dates is not None else {
        x[0] for x in db.query(Price.date_time).filter(Price.equity_id == equity.pk_equity_id,
        Price.interval == IntervalType.ONE_DAY).all()
    }
    inserted = 0
    for timestamp, row in raw.iterrows():
        timestamp = pd.Timestamp(timestamp).to_pydatetime().replace(tzinfo=None)
        if timestamp in existing: continue
        db.add(Price(equity_id=equity.pk_equity_id, date_time=timestamp, interval=IntervalType.ONE_DAY,
            open=float(row.get("Open", row["Close"])), high=float(row.get("High", row["Close"])),
            low=float(row.get("Low", row["Close"])), close=float(row["Close"]),
            volume=float(row.get("Volume", 0)), dividends=0, stock_splits=0, trades_count=0))
        inserted += 1
    return {"equity_id": equity.pk_equity_id, "ticker": equity.ticker, "rows": len(raw), "inserted": inserted}


def refresh_mapped_data(db: Session) -> list[dict]:
    years, quality = completed_years(), []
    mapped_ids = select(InstrumentMapping.instrument_equity_id).where(InstrumentMapping.active.is_(True))
    equities = db.query(Equity).filter((Equity.type == EquityType.SECTOR) | (Equity.pk_equity_id.in_(mapped_ids))).all()
    equity_ids = [equity.pk_equity_id for equity in equities]
    existing_by_equity: dict[int, set[datetime]] = defaultdict(set)
    if equity_ids:
        for equity_id, date_time in db.execute(select(Price.equity_id, Price.date_time).where(Price.interval == IntervalType.ONE_DAY, Price.equity_id.in_(equity_ids))):
            existing_by_equity[equity_id].add(date_time)
    for equity in equities:
        try: quality.append({**download_and_store(db, equity, years, existing_by_equity[equity.pk_equity_id]), "status": "ok"})
        except Exception as exc: quality.append({"equity_id": equity.pk_equity_id, "ticker": equity.ticker, "status": f"failed: {exc}"})
    db.commit()
    return quality


def load_sector_inputs(db: Session) -> tuple[list[Equity], dict[int, pd.Series]]:
    """Load the entire compute universe in three set-based reads, never in loops."""
    sectors = db.scalars(select(Equity).where(Equity.type == EquityType.SECTOR)).all()
    equity_ids = {sector.pk_equity_id for sector in sectors}
    if not equity_ids:
        return sectors, {}
    price_rows = db.execute(
        select(Price.equity_id, Price.date_time, Price.close)
        .where(Price.interval == IntervalType.ONE_DAY, Price.equity_id.in_(equity_ids))
        .order_by(Price.equity_id, Price.date_time)
    ).all()
    grouped: dict[int, list[tuple[datetime, float]]] = defaultdict(list)
    for equity_id, date_time, close in price_rows:
        grouped[equity_id].append((date_time, close))
    series_by_id = {
        equity_id: pd.Series([close for _, close in rows], index=pd.DatetimeIndex([date_time for date_time, _ in rows]), dtype=float)
        for equity_id, rows in grouped.items()
    }
    return sectors, series_by_id


def scan_sector(sector: Equity, close: pd.Series, years: list[int]) -> list[dict]:
    """V2 expanding-window scan; returns only candidates passing final strict OOS rules."""
    index, values = pd.DatetimeIndex(close.index), close.to_numpy(float)
    selected: dict[tuple[int, int, int], list[dict]] = {}
    for month in range(1, 13):
        for day in range(1, monthrange(2025, month)[1] + 1):
            starts = [first_session(index, year, month, day) for year in years]
            if any(x is None or x + 60 >= len(values) for x in starts): continue
            returns, drawdowns = np.empty((60, 5)), np.empty((60, 5))
            for yi, start in enumerate(starts):
                path = values[start:start + 61] / values[start]
                dd = np.minimum.accumulate(path / np.maximum.accumulate(path) - 1)
                returns[:, yi] = values[start + np.arange(1, 61)] / values[start] * (1 - COST) - 1
                drawdowns[:, yi] = dd[1:]
            for test in range(MIN_TRAIN_OBSERVATIONS, len(years)):
                train = returns[:, :test]
                lower = train.mean(1) - 1.96 * train.std(1, ddof=1) / np.sqrt(test)
                eligible = (train.mean(1) > 0) & ((train > 0).mean(1) >= .60) & (drawdowns[:, :test].min(1) >= MAX_DRAWDOWN) & (lower > 0)
                for offset in np.flatnonzero(eligible):
                    key = (month, day, int(offset + 1))
                    selected.setdefault(key, []).append({"year": years[test], "entry_date": str(index[starts[test]].date()),
                        "exit_date": str(index[starts[test] + offset + 1].date()), "net_return": float(returns[offset, test]),
                        "max_drawdown": float(drawdowns[offset, test])})
    output = []
    for (month, day, window), evidence in selected.items():
        rets = [x["net_return"] for x in evidence]
        if len(evidence) == len(years) - MIN_TRAIN_OBSERVATIONS and min(rets) > MIN_OOS_RETURN and min(x["max_drawdown"] for x in evidence) >= MAX_DRAWDOWN and all(x > 0 for x in rets):
            output.append({"sector_equity_id": sector.pk_equity_id, "month": month, "day": day, "window_days": window,
                "oos_observations": len(evidence), "oos_mean_return": float(np.mean(rets)), "oos_win_rate": 1.0,
                "oos_worst_return": min(rets), "oos_worst_drawdown": min(x["max_drawdown"] for x in evidence), "evidence": evidence})
    # Holiday/weekend dates can have exactly identical executions; retain one.
    seen, unique = set(), []
    for plan in sorted(output, key=lambda x: (x["oos_mean_return"], x["oos_worst_return"]), reverse=True):
        signature = tuple((x["entry_date"], x["exit_date"]) for x in plan["evidence"])
        if signature not in seen: seen.add(signature); unique.append(plan)
    return unique


def instrument_metric(sector_close: pd.Series, instrument_close: pd.Series, plan: StrategyPlan, years: list[int]) -> tuple[float, float, float, int, list] | None:
    daily_asset, daily_market, annual_returns, evidence = [], [], [], []
    for year in years:
        sidx, iidx = first_session(sector_close.index, year, plan.month, plan.day), first_session(instrument_close.index, year, plan.month, plan.day)
        if sidx is None or iidx is None or sidx + plan.window_days >= len(sector_close) or iidx + plan.window_days >= len(instrument_close): return None
        s, i = sector_close.iloc[sidx:sidx + plan.window_days + 1], instrument_close.iloc[iidx:iidx + plan.window_days + 1]
        common = pd.concat([s.rename("market"), i.rename("asset")], axis=1).dropna()
        # Yahoo can omit an index session while the ETF has traded (or vice
        # versa).  Keep the shared daily observations when at most one close
        # is lost; rejecting the whole five-year record for that feed quirk
        # incorrectly hid valid ETFs such as ITBEES.
        if len(common) < plan.window_days: return None
        returns = common.pct_change().dropna(); daily_market.extend(returns.market); daily_asset.extend(returns.asset)
        annual_returns.append(common.asset.iloc[-1] / common.asset.iloc[0] - 1)
        evidence.append({"year": year, "entry_date": str(common.index[0].date()), "exit_date": str(common.index[-1].date()), "return": annual_returns[-1]})
    x, y = np.array(daily_market), np.array(daily_asset)
    if len(x) < 2 or np.var(x) == 0: return None
    beta, alpha_daily = np.polyfit(x, y, 1)
    return float(np.mean(annual_returns)), float(alpha_daily * 252), float(beta), len(x), evidence


def download_live_closes(tickers: list[str], start: date, end: date) -> dict[str, pd.Series]:
    """Get detail-page inputs directly from Yahoo; never persist them to the DB."""
    raw = yf.download(tickers, start=start.isoformat(), end=(end + timedelta(days=1)).isoformat(),
                      auto_adjust=False, actions=False, progress=False, group_by="ticker", threads=True)
    if raw.empty: return {}
    closes: dict[str, pd.Series] = {}
    for ticker in tickers:
        try:
            frame = raw[ticker] if isinstance(raw.columns, pd.MultiIndex) and ticker in raw.columns.get_level_values(0) else raw
            close = frame["Close"].dropna()
            if not close.empty: closes[ticker] = pd.Series(close.to_numpy(float), index=pd.DatetimeIndex(close.index), dtype=float)
        except (KeyError, TypeError):
            continue
    return closes


def live_plan_instruments(db: Session, plan_id: int) -> list[dict]:
    """Calculate every mapped instrument live for one plan; only the page request pays this cost."""
    plan = db.get(StrategyPlan, plan_id)
    if not plan: raise ValueError("Plan not found")
    sector = db.get(Equity, plan.sector_equity_id)
    rows = db.execute(select(Equity).join(InstrumentMapping, InstrumentMapping.instrument_equity_id == Equity.pk_equity_id)
                      .where(InstrumentMapping.sector_equity_id == sector.pk_equity_id, InstrumentMapping.active.is_(True))
                      .order_by(Equity.type, Equity.ticker)).scalars().all()
    years = completed_years()
    starts = [date(year, plan.month, min(plan.day, monthrange(year, plan.month)[1])) for year in years]
    # ``window_days`` is trading sessions, not calendar days.  Allocate enough
    # calendar time for weekends plus a holiday margin; otherwise a 58-session
    # plan only downloads ~48 sessions and every instrument falsely fails.
    calendar_horizon = ceil(plan.window_days * 7 / 5) + WINDOW_BUFFER_DAYS
    start, end = min(starts) - timedelta(days=WINDOW_BUFFER_DAYS), max(starts) + timedelta(days=calendar_horizon)
    closes = download_live_closes([sector.ticker, *[item.ticker for item in rows]], start, end)
    benchmark = closes.get(sector.ticker)
    output = []
    for instrument in rows:
        metric = instrument_metric(benchmark, closes.get(instrument.ticker, pd.Series(dtype=float)), plan, years) if benchmark is not None else None
        if metric is None:
            output.append({"ticker": instrument.ticker, "name": instrument.name, "instrument_type": instrument.type.value, "eligible": False, "reason": "Incomplete Yahoo Finance coverage for the five seasonal windows"})
            continue
        seasonal_return, alpha, beta, observations, evidence = metric
        output.append({"ticker": instrument.ticker, "name": instrument.name, "instrument_type": instrument.type.value,
                       "seasonal_return": seasonal_return, "alpha": alpha, "beta": beta, "observation_count": observations,
                       "years": evidence, "eligible": alpha > 0 and beta <= 1.2,
                       "reason": None if alpha > 0 and beta <= 1.2 else "Does not meet positive-alpha and beta ≤ 1.2 criteria"})
    return output


def compute(db: Session, strategy_id: int) -> StrategyRun:
    years = completed_years()
    ensure_static_universe(db)
    sectors, series_by_id = load_sector_inputs(db)
    candidates, quality = [], []
    for sector in sectors:
        series = series_by_id.get(sector.pk_equity_id)
        if series is None:
            quality.append({"ticker": sector.ticker, "status": "failed: no daily price history"})
            continue
        try:
            candidates.extend(scan_sector(sector, series, years)); quality.append({"ticker": sector.ticker, "status": "ok", "rows": len(series)})
        except Exception as exc: quality.append({"ticker": sector.ticker, "status": f"failed: {exc}"})
    # This is the durable sector-to-window summary.  It is deliberately the
    # only result retained from the broad 1-60 day sector scan.
    candidates = sorted(candidates, key=lambda item: (item["oos_mean_return"], item["oos_worst_return"], item["oos_worst_drawdown"]), reverse=True)
    if not candidates:
        raise RuntimeError("No plan passed the final walk-forward filters; existing published results were preserved.")
    # Build the small publication set before touching prior published results.
    run = StrategyRun(strategy_id=strategy_id, configuration={"years": years, "window_days": [1, 60], "cost": COST}, data_quality=quality)
    db.add(run); db.flush()
    plans = [StrategyPlan(strategy_run_id=run.pk_strategy_run_id, **item) for item in candidates]
    db.add_all(plans); db.flush()
    # Latest-only publication: remove all prior result trees after replacement is ready.
    old_runs = select(StrategyRun.pk_strategy_run_id).where(StrategyRun.strategy_id == strategy_id, StrategyRun.pk_strategy_run_id != run.pk_strategy_run_id)
    old_plans = select(StrategyPlan.pk_strategy_plan_id).where(StrategyPlan.strategy_run_id.in_(old_runs))
    db.execute(delete(PlanInstrument).where(PlanInstrument.strategy_plan_id.in_(old_plans)))
    db.execute(delete(StrategyPlan).where(StrategyPlan.strategy_run_id.in_(old_runs)))
    db.execute(delete(StrategyRun).where(StrategyRun.pk_strategy_run_id.in_(old_runs)))
    # Raw sector history is an intermediate input.  The plan evidence above is
    # retained; benchmark sessions are re-fetched only for a selected sector's
    # narrow seasonal windows during its instrument stage.
    db.execute(delete(Price).where(Price.interval == IntervalType.ONE_DAY, Price.equity_id.in_([s.pk_equity_id for s in sectors])))
    db.commit(); db.refresh(run)
    return run


def track_sector_instruments(db: Session, strategy_id: int, sector_id: int) -> dict:
    """Fetch only selected sector windows (+ holiday buffer), publish winners, then purge inputs."""
    ensure_static_universe(db)
    plans = db.scalars(select(StrategyPlan).join(StrategyRun).where(
        StrategyRun.strategy_id == strategy_id, StrategyPlan.sector_equity_id == sector_id
    )).all()
    if not plans:
        raise ValueError("This sector has no qualified windows in the current research summary")
    sector = db.get(Equity, sector_id)
    mappings = db.execute(select(InstrumentMapping, Equity).join(Equity, Equity.pk_equity_id == InstrumentMapping.instrument_equity_id)
                          .where(InstrumentMapping.sector_equity_id == sector_id, InstrumentMapping.active.is_(True))).all()
    if not mappings:
        raise ValueError("No static stock/ETF universe is configured for this sector")
    # The OOS evidence contains only walk-forward test years.  Instrument
    # alpha/beta deliberately needs all five completed seasonal windows.
    dates = [date(year, plan.month, min(plan.day, monthrange(year, plan.month)[1]))
             for plan in plans for year in completed_years()]
    start, end = min(dates) - timedelta(days=WINDOW_BUFFER_DAYS), max(dates) + timedelta(days=WINDOW_BUFFER_DAYS)
    years, quality = completed_years(), []
    universe = [sector] + [instrument for _, instrument in mappings]
    for equity in universe:
        try:
            quality.append({**download_and_store(db, equity, years, start=start, end=end), "status": "ok"})
        except Exception as exc:
            quality.append({"ticker": equity.ticker, "status": f"failed: {exc}"})
    db.flush()
    ids = [item.pk_equity_id for item in universe]
    _, series = load_series_for_ids(db, ids)
    db.execute(delete(PlanInstrument).where(PlanInstrument.strategy_plan_id.in_([p.pk_strategy_plan_id for p in plans])))
    winners = 0
    for plan in plans:
        ranked: dict[str, list[tuple[PlanInstrument, float, float]]] = defaultdict(list)
        for _, instrument in mappings:
            metric = instrument_metric(series[sector_id], series.get(instrument.pk_equity_id, pd.Series(dtype=float)), plan, years)
            if metric is None: continue
            ret, alpha, beta, count, evidence = metric
            candidate = PlanInstrument(strategy_plan_id=plan.pk_strategy_plan_id, equity_id=instrument.pk_equity_id, instrument_type=instrument.type.value, seasonal_return=ret, alpha=alpha, beta=beta, observation_count=count, evidence=evidence)
            if alpha > 0 and beta <= 1.2: ranked[instrument.type.value].append((candidate, ret, alpha))
        for candidates in ranked.values():
            if candidates:
                winner = max(candidates, key=lambda item: (item[1], item[2]))[0]
                winner.is_recommended = True; db.add(winner); winners += 1
    db.execute(delete(Price).where(Price.interval == IntervalType.ONE_DAY, Price.equity_id.in_(ids)))
    db.commit()
    return {"sector": sector.name, "windows": len(plans), "recommended_instruments": winners, "data_quality": quality}


def load_series_for_ids(db: Session, ids: list[int]) -> tuple[list[int], dict[int, pd.Series]]:
    rows = db.execute(select(Price.equity_id, Price.date_time, Price.close).where(Price.interval == IntervalType.ONE_DAY, Price.equity_id.in_(ids)).order_by(Price.equity_id, Price.date_time)).all()
    grouped: dict[int, list[tuple[datetime, float]]] = defaultdict(list)
    for equity_id, date_time, close in rows: grouped[equity_id].append((date_time, close))
    return ids, {equity_id: pd.Series([value for _, value in values], index=pd.DatetimeIndex([when for when, _ in values]), dtype=float) for equity_id, values in grouped.items()}


def headlines(query: str) -> list[dict]:
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-IN&gl=IN&ceid=IN:en"
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 stock-backtester"})
    try:
        root = ElementTree.fromstring(urlopen(request, timeout=8).read())
        items = []
        for item in root.findall("./channel/item")[:8]:
            published = item.findtext("pubDate")
            items.append({"title": item.findtext("title") or "", "url": item.findtext("link") or "", "published_at": parsedate_to_datetime(published).isoformat() if published else None})
        return items
    except Exception:
        return []
