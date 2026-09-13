"""Run the reproducible daily long-only CMF study on current Nifty 200 members."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd
import yfinance as yf

from config import NIFTY200_CSV_URL, completed_years
from strategy import SimulationResult, add_indicators, metrics, simulate, trade_frame

ROOT = Path(__file__).parent
OUTPUT = ROOT / "output"
PERCENT_FIELDS = ["win_rate", "mean_net_return", "median_net_return", "total_compounded_return",
                  "worst_trade", "max_sequential_drawdown"]


def nifty200() -> dict[str, str]:
    request = Request(NIFTY200_CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=60) as response:
        table = pd.read_csv(StringIO(response.read().decode("utf-8")))
    return {f"{row.Symbol}.NS": str(row.Industry) for row in table.itertuples(index=False)}


def history(tickers: list[str], years: list[int]) -> pd.DataFrame:
    chunks = [tickers[i:i + 40] for i in range(0, len(tickers), 40)]
    parts = [yf.download(chunk, start=f"{years[0] - 1}-01-01", end=f"{years[-1] + 1}-01-10",
                         auto_adjust=False, progress=False, actions=False, group_by="ticker", threads=True)
             for chunk in chunks]
    result = pd.concat(parts, axis=1)
    if result.empty:
        raise RuntimeError("Yahoo Finance returned no data")
    return result


def instrument(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    try:
        frame = raw[ticker] if isinstance(raw.columns, pd.MultiIndex) else raw
    except KeyError as exc:
        raise ValueError("ticker was absent from Yahoo response") from exc
    frame = frame.loc[:, ["Open", "High", "Low", "Close", "Volume"]].dropna().sort_index()
    frame.index = pd.to_datetime(frame.index).tz_localize(None)
    if frame.empty:
        raise ValueError("no complete OHLCV observations")
    return frame


def horizon_frame(indicators: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    return indicators.loc[(indicators.index >= start) & (indicators.index <= end)].copy()


def summary_row(scope: str, variant: str, ticker: str, industry: str, horizon: str, result,
                data_status: str = "ok") -> dict[str, object]:
    return {"scope": scope, "variant": variant, "horizon": horizon, "ticker": ticker, "industry": industry,
            "data_status": data_status,
            **metrics(trade_frame(result.trades, ticker, industry, horizon, variant), result.signal_count,
                      result.skipped_gap_entries, result.skipped_while_open)}


def aggregate_row(rows: list[dict[str, object]], trades: pd.DataFrame, horizon: str,
                  variant: str) -> dict[str, object]:
    ordered_trades = trades.sort_values(["exit_date", "ticker", "entry_date"]) if not trades.empty else trades
    return {"scope": "aggregate", "variant": variant, "horizon": horizon,
            "ticker": "NIFTY200_AGGREGATE", "industry": "All",
            "data_status": "aggregate",
            **metrics(ordered_trades, sum(int(row["signal_count"]) for row in rows),
                      sum(int(row["skipped_gap_entries"]) for row in rows),
                      sum(int(row["skipped_while_open"]) for row in rows))}


def percentage_export(frame: pd.DataFrame) -> pd.DataFrame:
    exported = frame.copy()
    for field in PERCENT_FIELDS:
        if field in exported:
            exported[field] = exported[field].map(
                lambda value: "" if pd.isna(value) else ("∞" if np.isinf(value) else f"{value:.2%}"))
    for field in ["gross_return", "net_return"]:
        if field in exported:
            exported[field] = exported[field].map(lambda value: f"{value:.2%}")
    return exported


def report(years: list[int], universe: dict[str, str], quality: pd.DataFrame, summary: pd.DataFrame) -> str:
    display = percentage_export(summary)
    return "\n".join([
        "# Nifty 200 Chaikin Money Flow research", "",
        f"Sample: {years[0]}–{years[-1]}; latest completed year: {years[-1]}. Current official Nifty 200 snapshot: {len(universe)} stocks.", "",
        "## Fixed rules", "",
        "`cmf_baseline`: CMF(40) crosses strictly above +0.05 and Close > EMA(200). `cmf_rsi_ema_confirmed`: baseline plus Close > EMA(50), EMA(50) > EMA(200), and RSI(14) in [50, 70]. Both enter next Open, use a signal-Close − 2×ATR(14) stop, and target 2R. Stop wins same-bar target/stop collisions. A gap at/below the precomputed stop skips the trade.", "",
        "## Results", "", display.to_markdown(index=False), "",
        "## Limitations", "",
        "Current Nifty 200 membership creates survivorship bias for historical results. Aggregated compounded return and drawdown are sequential-trade diagnostics, not a portfolio backtest: positions can overlap across stocks and no sizing, cash constraint, taxes, liquidity, or slippage beyond the 20 bps round-trip cost is modelled. This is research, not investment advice.", "",
        "## Sources", "",
        "- Attached transcript: *Chaikin Money Flow strategy made 316% Profit! (Full Tutorial)*, https://www.youtube.com/watch?v=RNJvhPASNU0", "- [NSE Nifty 200 Index](https://www.nseindia.com/static/products-services/indices-nifty200-index)", "- [cTrader: Chaikin Money Flow calculation](https://help.ctrader.com/indicators/built-in/volume/chaikin-money-flow/)", "",
        "## Data quality", "", quality.to_markdown(index=False), "",
    ])


def run() -> None:
    OUTPUT.mkdir(exist_ok=True)
    years, universe = completed_years(), nifty200()
    raw = history(list(universe), years)
    horizons = {"1_year": (pd.Timestamp(years[-1], 1, 1), pd.Timestamp(years[-1], 12, 31)),
                "5_year": (pd.Timestamp(years[0], 1, 1), pd.Timestamp(years[-1], 12, 31))}
    variants = {"cmf_baseline": "signal", "cmf_rsi_ema_confirmed": "rsi_ema_signal"}
    summaries: list[dict[str, object]] = []
    all_trades: list[pd.DataFrame] = []
    quality: list[dict[str, object]] = []
    for ticker, industry in universe.items():
        try:
            indicators = add_indicators(instrument(raw, ticker))
            rows = []
            for name, (start, end) in horizons.items():
                study = horizon_frame(indicators, start, end)
                if study.empty or study["ema_200"].notna().sum() == 0:
                    raise ValueError("insufficient warm history")
                for variant, signal_column in variants.items():
                    result = simulate(study, signal_column)
                    rows.append(summary_row("stock", variant, ticker, industry, name, result))
                    all_trades.append(trade_frame(result.trades, ticker, industry, name, variant))
            summaries.extend(rows)
            quality.append({"ticker": ticker, "industry": industry, "rows": len(indicators), "status": "ok"})
        except Exception as exc:
            status = f"failed: {exc}"
            quality.append({"ticker": ticker, "industry": industry, "rows": 0, "status": status})
            empty = SimulationResult([], 0, 0, 0)
            summaries.extend(summary_row("stock", variant, ticker, industry, name, empty, status)
                             for name in horizons for variant in variants)
    trades = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame(
        columns=["variant", "horizon", "industry", "ticker"])
    for name in horizons:
        for variant in variants:
            stock_rows = [row for row in summaries if row["horizon"] == name and row["variant"] == variant]
            horizon_trades = trades.loc[(trades["horizon"] == name) & (trades["variant"] == variant)]
            summaries.append(aggregate_row(stock_rows, horizon_trades, name, variant))
    summary = pd.DataFrame(summaries).sort_values(["horizon", "variant", "scope", "ticker"])
    quality_frame = pd.DataFrame(quality).sort_values("ticker")
    percentage_export(trades).to_csv(OUTPUT / "trades.csv", index=False)
    percentage_export(summary).to_csv(OUTPUT / "strategy_summary.csv", index=False)
    quality_frame.to_csv(OUTPUT / "data_quality.csv", index=False)
    (OUTPUT / "REPORT.md").write_text(report(years, universe, quality_frame, summary), encoding="utf-8")
    print(f"Wrote Nifty 200 CMF research outputs to {OUTPUT}")


if __name__ == "__main__":
    run()
