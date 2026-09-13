"""Compare close-only control and improved daily OHLCV Squeeze Momentum on Nifty 200."""
from __future__ import annotations

from io import StringIO
from pathlib import Path
from urllib.request import Request, urlopen

import pandas as pd
import yfinance as yf

from config import NIFTY200_CSV_URL, completed_years
from strategy import (add_improved_indicators, add_indicators, signals_for_variant,
                      simulate_improved, simulate_long_only, trade_frame)

ROOT, OUTPUT = Path(__file__).parent, Path(__file__).parent / "output"


def nifty200() -> dict[str, str]:
    request = Request(NIFTY200_CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=60) as response:
        table = pd.read_csv(StringIO(response.read().decode("utf-8")))
    return {f"{row.Symbol}.NS": str(row.Industry) for row in table.itertuples(index=False)}


def history(tickers: list[str], years: list[int]) -> pd.DataFrame:
    # Yahoo can silently abandon very large multi-ticker requests. Small batches
    # retain a bulk-download design without making the result depend on one request.
    chunks = [tickers[offset:offset + 40] for offset in range(0, len(tickers), 40)]
    parts = [yf.download(chunk, start=f"{years[0] - 1}-01-01", end=f"{years[-1] + 1}-01-10",
                         auto_adjust=False, progress=False, actions=False, group_by="ticker", threads=True)
             for chunk in chunks]
    data = pd.concat(parts, axis=1)
    if data.empty:
        raise RuntimeError("Yahoo Finance returned no data")
    return data


def instrument(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    try:
        frame = raw[ticker] if isinstance(raw.columns, pd.MultiIndex) else raw
    except KeyError as exc:
        raise ValueError("ticker was absent from Yahoo response") from exc
    columns = ["Open", "High", "Low", "Close", "Volume"]
    frame = frame.loc[:, columns].dropna().sort_index()
    frame.index = pd.to_datetime(frame.index).tz_localize(None)
    if frame.empty:
        raise ValueError("no complete OHLCV observations")
    return frame


def summarize(trades: pd.DataFrame) -> pd.DataFrame:
    fields = ["industry", "ticker", "variant", "trade_count", "win_rate", "mean_net_return",
              "median_net_return", "total_compounded_return", "worst_trade"]
    rows = []
    for (industry, ticker, variant), group in trades.groupby(["industry", "ticker", "variant"]):
        returns = group.sort_values("exit_date")["net_return"]
        rows.append({"industry": industry, "ticker": ticker, "variant": variant, "trade_count": len(group),
                     "win_rate": (returns > 0).mean(), "mean_net_return": returns.mean(),
                     "median_net_return": returns.median(), "total_compounded_return": (1 + returns).prod() - 1,
                     "worst_trade": returns.min()})
    return pd.DataFrame(rows, columns=fields).sort_values(["variant", "mean_net_return"], ascending=[True, False]) if rows else pd.DataFrame(columns=fields)


def format_report(years: list[int], universe: dict[str, str], quality: pd.DataFrame,
                  trades: pd.DataFrame, summary: pd.DataFrame) -> str:
    lines = ["# Nifty 200 Squeeze Momentum research", "", f"Sample: {years[0]}–{years[-1]}; official current Nifty 200 snapshot: {len(universe)} stocks.", "",
             "## Models", "", "- `close_only_control`: prior close-only adaptation; it is retained as a control.", "- `improved_ohlcv`: standard daily OHLCV LazyBear/TTM squeeze plus 50 EMA > 200 EMA, positive/rising histogram, ADX(14) ≥ 20 and rising, release-day volume ≥ 120% of prior 20-day average, and a 2×ATR trailing stop.", "", "These additions are exploratory and were fixed before this Nifty 200 run from documented TTM/Squeeze practice; they are not evidence of a validated edge.", "", "## Results", ""]
    if trades.empty:
        lines.append("No completed trades.")
    else:
        aggregate = trades.groupby("variant")["net_return"].agg(trade_count="count", win_rate=lambda x: (x > 0).mean(), mean_net_return="mean", median_net_return="median").reset_index()
        for field in ["win_rate", "mean_net_return", "median_net_return"]:
            aggregate[field] = aggregate[field].map(lambda value: f"{value:.2%}")
        lines += [aggregate.to_markdown(index=False), "", "## Stock results", ""]
        shown = summary.copy()
        for field in ["win_rate", "mean_net_return", "median_net_return", "total_compounded_return", "worst_trade"]:
            shown[field] = shown[field].map(lambda value: f"{value:.2%}")
        lines.append(shown.to_markdown(index=False))
    lines += ["", "## Limitations", "", "Current Nifty 200 membership introduces survivorship bias for a 2021–2025 test. This is not a portfolio backtest and excludes sizing, taxes, liquidity, and slippage. Results are research only, not investment advice.", "", "## Data quality", "", quality.to_markdown(index=False)]
    return "\n".join(lines) + "\n"


def percentage_export(frame: pd.DataFrame, fields: list[str]) -> pd.DataFrame:
    """Format user-facing percentage fields without changing internal metrics."""
    exported = frame.copy()
    for field in fields:
        if field in exported:
            exported[field] = exported[field].map(lambda value: f"{value:.2%}")
    return exported


def run() -> None:
    OUTPUT.mkdir(exist_ok=True)
    years, universe = completed_years(), nifty200()
    raw = history(list(universe), years)
    start, end, quality, all_trades = pd.Timestamp(years[0], 1, 1), pd.Timestamp(years[-1], 12, 31), [], []
    for ticker, industry in universe.items():
        try:
            prices = instrument(raw, ticker)
            if len(prices.loc[(prices.index >= start) & (prices.index <= end)]) < 200:
                raise ValueError("insufficient history")
            control = add_indicators(prices[["Close"]]).loc[start:end]
            improved = add_improved_indicators(prices).loc[start:end]
            all_trades += [trade_frame(simulate_long_only(control, signals_for_variant(control, "baseline")), industry, ticker, "close_only_control"),
                           trade_frame(simulate_improved(improved), industry, ticker, "improved_ohlcv")]
            quality.append({"ticker": ticker, "industry": industry, "rows": len(improved), "status": "ok"})
        except Exception as exc:
            quality.append({"ticker": ticker, "industry": industry, "rows": 0, "status": f"failed: {exc}"})
    quality_frame = pd.DataFrame(quality)
    trades = pd.concat(all_trades, ignore_index=True) if all_trades else pd.DataFrame()
    trades = trades.rename(columns={"sectors": "industry"})
    summary = summarize(trades) if not trades.empty else pd.DataFrame()
    quality_frame.to_csv(OUTPUT / "data_quality.csv", index=False)
    percentage_export(trades, ["gross_return", "net_return"]).to_csv(OUTPUT / "trades.csv", index=False)
    percentage_export(summary, ["win_rate", "mean_net_return", "median_net_return",
                                "total_compounded_return", "worst_trade"]).to_csv(
        OUTPUT / "strategy_summary.csv", index=False,
    )
    (OUTPUT / "REPORT.md").write_text(format_report(years, universe, quality_frame, trades, summary), encoding="utf-8")
    print(f"Wrote Nifty 200 research outputs to {OUTPUT}")


if __name__ == "__main__":
    run()
