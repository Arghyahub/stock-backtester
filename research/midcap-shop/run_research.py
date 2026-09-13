"""Fetch data and run the Nifty Midcap SHOP portfolio backtest."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
import yfinance as yf

from config import NIFTY_MIDCAP_50_CSV_URL, completed_years
from strategy import MidcapShopBacktest, StrategySettings

ROOT = Path(__file__).parent
OUTPUT = ROOT / "output"


def universe() -> dict[str, str]:
    request = Request(NIFTY_MIDCAP_50_CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=60) as response:
        table = pd.read_csv(StringIO(response.read().decode("utf-8")))
    if "Symbol" not in table:
        raise ValueError("official constituent CSV did not contain Symbol")
    industry = "Industry" if "Industry" in table else None
    return {f"{row.Symbol}.NS": str(getattr(row, industry)) if industry else "Unknown"
            for row in table.itertuples(index=False)}


def fetch(ticker: str, start: str, end: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = yf.Ticker(ticker).history(start=start, end=end, auto_adjust=False, actions=True)
    if data.empty:
        raise ValueError("no Yahoo Finance history")
    data.index = pd.to_datetime(data.index).tz_localize(None)
    bars = data.loc[:, ["Open", "High", "Low", "Close", "Volume"]].dropna()
    actions = data.loc[:, ["Dividends", "Stock Splits"]].fillna(0.0)
    return bars, actions


def export_percentage(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for field in ["gross_return", "net_return", "max_drawdown", "xirr"]:
        if field in result:
            result[field] = result[field].map(lambda value: "" if pd.isna(value) else f"{value:.2%}")
    return result


def xirr(cashflows: list[tuple[pd.Timestamp, float]]) -> float:
    """Small dependency-free XIRR solver; returns NaN when no sign-changing flows exist."""
    if not cashflows or not (any(amount < 0 for _, amount in cashflows) and any(amount > 0 for _, amount in cashflows)):
        return float("nan")
    start = cashflows[0][0]
    def npv(rate: float) -> float:
        return sum(amount / (1 + rate) ** ((date - start).days / 365.25) for date, amount in cashflows)
    low, high = -0.999, 10.0
    for _ in range(200):
        middle = (low + high) / 2
        if npv(middle) > 0:
            low = middle
        else:
            high = middle
    return (low + high) / 2


def summary(result, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    curve, trades = result.equity_curve, result.trades
    if curve.empty:
        raise RuntimeError("no market sessions in requested period")
    ending = float(curve.iloc[-1].equity)
    drawdown = curve["equity"].div(curve["equity"].cummax()).sub(1).min()
    charge = result.charge_totals
    gross_pnl = float(trades["gross_pnl"].sum()) if not trades.empty else 0.0
    return pd.DataFrame([{
        "start": start.date(), "end": end.date(), "starting_cash": 100_000.0,
        "ending_equity": ending, "net_return": ending / 100_000.0 - 1,
        "gross_pnl_closed_lots": gross_pnl, "net_pnl_closed_lots": float(trades["net_pnl"].sum()) if not trades.empty else 0.0,
        "trade_lots": len(trades), "win_rate": float((trades["net_pnl"] > 0).mean()) if not trades.empty else np.nan,
        "max_drawdown": drawdown, "xirr": xirr([(start, -100_000.0), (end, ending)]),
        "max_deployed": float((curve["equity"] - curve["cash"]).max()),
        "turnover": float((trades["quantity"] * (trades["entry_price"] + trades["exit_price"])).sum()) if not trades.empty else 0.0,
        "skipped_orders": len(result.skipped), **{f"charges_{key}": value for key, value in charge.__dict__.items()},
        "charges_total": charge.total,
    }])


def report(years: list[int], members: dict[str, str], quality: pd.DataFrame, totals: pd.DataFrame) -> str:
    return "\n".join([
        "# Nifty Midcap SHOP research", "",
        f"Sample: {years[0]}–{years[-1]}; current official Nifty Midcap 50 snapshot: {len(members)} stocks.", "",
        "## Rules", "",
        "All variants rank the 50 members by Close/SMA(20) − 1, use the five weakest, buy equity ÷ 10, average equity ÷ 40 only after a 3% fall from the latest lot, cap averages at three, and sell each lot after an 8% close-based target. Orders execute next Open. `baseline_stock_target` instead exits every open lot in a stock after its weighted-average entry cost reaches 8%. `rsi_oversold` additionally requires RSI(14) < 30 for every buy; `trend_sma_200` requires Close > SMA(200); `rsi_and_trend` requires both. Exits are never filtered.", "",
        "## Costs", "",
        "Current Zerodha retail NSE equity-delivery fees are applied uniformly to the historical sample: zero brokerage; 0.1% STT on each side; 0.00307% NSE transaction charge; ₹10/crore SEBI charge; 18% GST on transaction and SEBI fees; 0.015% buy stamp duty; and one ₹15.34 DP charge per sold scrip per day. Capital-gains tax, AMC, MTF, leverage, and slippage are excluded.", "",
        "## Results", "", export_percentage(totals).to_markdown(index=False), "",
        "## Limitations", "",
        "The constituent list is a current snapshot, so 2021–2025 results have survivorship and look-ahead bias. Daily OHLC cannot reproduce a 3:20 PM quote; signals execute at the next open. Yahoo Finance data and corporate-action records can contain errors. This is research, not investment advice.", "",
        "## Sources", "",
        "- [Fabtrader, MCK Midcap SHOP Swing Strategy Backtested Results](https://fabtrader.in/videos/mahesh-chander-kaushik-midcap-shop-swing-strategy-backtested-results)",
        "- [NSE, Nifty Midcap 50 Index](https://www.nseindia.com/static/products-services/indices-niftymidcap50-index)",
        "- [Zerodha, charges](https://zerodha.com/charges)", "",
        "## Data quality", "", quality.to_markdown(index=False), "",
    ])


def run() -> None:
    OUTPUT.mkdir(exist_ok=True)
    years = completed_years()
    members = universe()
    frames: dict[str, pd.DataFrame] = {}
    actions: dict[str, pd.DataFrame] = {}
    quality: list[dict[str, object]] = []
    with ThreadPoolExecutor(max_workers=10) as pool:
        pending = {pool.submit(fetch, ticker, f"{years[0] - 1}-11-01", f"{years[-1] + 1}-01-10"): (ticker, industry)
                   for ticker, industry in members.items()}
        for task in as_completed(pending):
            ticker, industry = pending[task]
            try:
                bars, corporate_actions = task.result()
                frames[ticker], actions[ticker] = bars, corporate_actions
                quality.append({"ticker": ticker, "industry": industry, "rows": len(bars), "status": "ok"})
            except Exception as exc:
                quality.append({"ticker": ticker, "industry": industry, "rows": 0, "status": f"failed: {exc}"})
    start, end = pd.Timestamp(years[0], 1, 1), pd.Timestamp(years[-1], 12, 31)
    variants = {
        "baseline": StrategySettings(),
        "baseline_stock_target": StrategySettings(stock_level_target=True),
        "rsi_oversold": StrategySettings(rsi_oversold=True),
        "trend_sma_200": StrategySettings(trend_sma=True),
        "rsi_and_trend": StrategySettings(rsi_oversold=True, trend_sma=True),
    }
    results = {name: MidcapShopBacktest(frames, actions, settings=settings).run(start, end)
               for name, settings in variants.items()}
    totals = pd.concat([summary(result, start, end).assign(variant=name)
                        for name, result in results.items()], ignore_index=True)
    trade_export = pd.concat([result.trades.assign(variant=name) for name, result in results.items()], ignore_index=True)
    curve_export = pd.concat([result.equity_curve.assign(variant=name) for name, result in results.items()], ignore_index=True)
    skipped_export = pd.concat([result.skipped.assign(variant=name) for name, result in results.items()], ignore_index=True)
    trade_export.to_csv(OUTPUT / "trades.csv", index=False)
    curve_export.to_csv(OUTPUT / "equity_curve.csv", index=False)
    skipped_export.to_csv(OUTPUT / "skipped_orders.csv", index=False)
    export_percentage(totals).to_csv(OUTPUT / "strategy_summary.csv", index=False)
    quality_frame = pd.DataFrame(quality).sort_values("ticker")
    quality_frame.to_csv(OUTPUT / "data_quality.csv", index=False)
    (OUTPUT / "REPORT.md").write_text(report(years, members, quality_frame, totals), encoding="utf-8")
    print(f"Wrote Midcap SHOP results to {OUTPUT}")


if __name__ == "__main__":
    run()
