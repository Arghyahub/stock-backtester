"""Run a cost-aware, expanding-window seasonal research scan."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

from config import (
    MAX_TRAIN_DRAWDOWN, MAX_WINDOW_DAYS, MIN_TRAIN_MEAN_RETURN,
    MIN_TRAIN_OBSERVATIONS, MIN_TRAIN_WIN_RATE, MIN_WINDOW_DAYS,
    MAX_OOS_DRAWDOWN, MIN_OOS_WIN_RATE, MIN_OOS_WORST_RETURN,
    ROUND_TRIP_COST, SECTORS, TOP_PLANS, completed_years,
)

ROOT = Path(__file__).parent
OUTPUT = ROOT / "output"


@dataclass(frozen=True)
class Candidate:
    sector: str
    month: int
    day: int
    window_days: int

    @property
    def label(self) -> str:
        return f"{pd.Timestamp(2001, self.month, self.day):%b %d}"


def download_prices(ticker: str, years: list[int]) -> pd.DataFrame:
    """Fetch Close data, retaining only real market sessions."""
    raw = yf.download(
        ticker, start=f"{years[0]}-01-01", end=f"{years[-1] + 1}-01-10",
        auto_adjust=False, progress=False, actions=False,
    )
    if raw.empty:
        raise ValueError(f"No data returned for {ticker}")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)
    prices = raw[["Close"]].dropna().sort_index()
    prices.index = pd.to_datetime(prices.index).tz_localize(None)
    return prices


def entry_position(index: pd.DatetimeIndex, year: int, month: int, day: int) -> int | None:
    """First trading session on/after the calendar date, within the same year."""
    if day > monthrange(year, month)[1]:
        return None
    target = pd.Timestamp(year, month, day)
    pos = index.searchsorted(target)
    if pos == len(index) or index[pos].year != year:
        return None
    return int(pos)


def candidates() -> list[Candidate]:
    """Only include dates which exist in every non-leap calendar year."""
    return [Candidate(sector, month, day, window)
            for sector in SECTORS
            for month in range(1, 13)
            for day in range(1, monthrange(2025, month)[1] + 1)
            for window in range(MIN_WINDOW_DAYS, MAX_WINDOW_DAYS + 1)]


def prepare_positions(prices: pd.DataFrame, years: list[int]) -> dict[tuple[int, int, int], int]:
    """Precompute calendar-date entries once; the scan calls this hundreds of thousands of times."""
    index = prices.index
    positions = {}
    for year in years:
        for month in range(1, 13):
            for day in range(1, monthrange(year, month)[1] + 1):
                pos = entry_position(index, year, month, day)
                if pos is not None:
                    positions[(year, month, day)] = pos
    return positions


def qualify(train: list[dict]) -> bool:
    returns = np.array([x["net_return"] for x in train])
    drawdowns = np.array([x["max_drawdown"] for x in train])
    if len(returns) < MIN_TRAIN_OBSERVATIONS:
        return False
    # Conservative normal approximation: with three observations this is only a guardrail,
    # never a declaration of significance.
    lower_bound = returns.mean() - 1.96 * returns.std(ddof=1) / np.sqrt(len(returns)) if len(returns) > 1 else -np.inf
    return (returns.mean() > MIN_TRAIN_MEAN_RETURN and (returns > 0).mean() >= MIN_TRAIN_WIN_RATE
            and drawdowns.min() >= MAX_TRAIN_DRAWDOWN and lower_bound > 0)


def run() -> None:
    OUTPUT.mkdir(exist_ok=True)
    years = completed_years()
    universe = candidates()
    price_data: dict[str, pd.DataFrame] = {}
    quality = []
    for sector, ticker in SECTORS.items():
        try:
            prices = download_prices(ticker, years)
            price_data[sector] = prices
            quality.append({"sector": sector, "ticker": ticker, "rows": len(prices),
                            "first_date": prices.index.min().date(), "last_date": prices.index.max().date(), "status": "ok"})
        except Exception as exc:
            quality.append({"sector": sector, "ticker": ticker, "rows": 0, "first_date": None,
                            "last_date": None, "status": f"failed: {exc}"})
    pd.DataFrame(quality).to_csv(OUTPUT / "data_quality.csv", index=False)

    selected = []
    prepared = {
        sector: (prices.index, prices["Close"].to_numpy(dtype=float),
                 prepare_positions(prices, years))
        for sector, prices in price_data.items()
    }
    # Vectorize all 60 holding periods for a calendar day. This keeps the complete
    # 219k-candidate scan fast enough to be rerun, while preserving fold isolation.
    for sector, (index, closes, positions) in prepared.items():
        for month in range(1, 13):
            for day in range(1, monthrange(2025, month)[1] + 1):
                starts = np.array([positions.get((year, month, day), -1) for year in years])
                if np.any(starts < 0) or np.any(starts + MAX_WINDOW_DAYS >= len(closes)):
                    continue
                returns = np.empty((MAX_WINDOW_DAYS, len(years)))
                drawdowns = np.empty_like(returns)
                for year_index, start_pos in enumerate(starts):
                    path = closes[start_pos : start_pos + MAX_WINDOW_DAYS + 1] / closes[start_pos]
                    running_drawdown = path / np.maximum.accumulate(path) - 1
                    prefix_drawdown = np.minimum.accumulate(running_drawdown)
                    exits = closes[start_pos + np.arange(MIN_WINDOW_DAYS, MAX_WINDOW_DAYS + 1)]
                    returns[:, year_index] = (exits / closes[start_pos]) * (1 - ROUND_TRIP_COST) - 1
                    drawdowns[:, year_index] = prefix_drawdown[MIN_WINDOW_DAYS:]
                for test_index in range(MIN_TRAIN_OBSERVATIONS, len(years)):
                    train_returns = returns[:, :test_index]
                    train_drawdowns = drawdowns[:, :test_index]
                    mean = train_returns.mean(axis=1)
                    wins = (train_returns > 0).mean(axis=1)
                    lower = mean - 1.96 * train_returns.std(axis=1, ddof=1) / np.sqrt(test_index)
                    eligible = ((mean > MIN_TRAIN_MEAN_RETURN) & (wins >= MIN_TRAIN_WIN_RATE)
                                & (train_drawdowns.min(axis=1) >= MAX_TRAIN_DRAWDOWN) & (lower > 0))
                    for offset in np.flatnonzero(eligible):
                        exit_pos = starts[test_index] + offset + MIN_WINDOW_DAYS
                        selected.append({
                            "sector": sector, "month": month, "day": day,
                            "start": f"{pd.Timestamp(2025, month, day):%b %d}",
                            "window_days": int(offset + MIN_WINDOW_DAYS), "test_year": years[test_index],
                            "train_observations": test_index, "train_mean_net_return": mean[offset],
                            "year": years[test_index], "entry_date": index[starts[test_index]].date(),
                            "exit_date": index[exit_pos].date(), "net_return": returns[offset, test_index],
                            "max_drawdown": drawdowns[offset, test_index],
                        })

    walk = pd.DataFrame(selected)
    walk.to_csv(OUTPUT / "walk_forward_candidates.csv", index=False)
    if walk.empty:
        raise RuntimeError("No candidate passed the pre-committed training rules; do not relax them after seeing this result.")
    grouped = walk.groupby(["sector", "month", "day", "start", "window_days"], as_index=False).agg(
        oos_observations=("net_return", "count"), oos_mean_net_return=("net_return", "mean"),
        oos_win_rate=("net_return", lambda x: (x > 0).mean()),
        oos_worst_return=("net_return", "min"), oos_worst_drawdown=("max_drawdown", "min"),
        oos_entry_dates=("entry_date", lambda x: ", ".join(map(str, x))),
        oos_exit_dates=("exit_date", lambda x: ", ".join(map(str, x))),
        selected_folds=("test_year", lambda x: ", ".join(map(str, sorted(x)))),
    )
    # Weekend/holiday dates can map to the exact same entry and exit sessions in
    # every OOS fold. Keep one representative instead of presenting duplicates as
    # separate opportunities.
    key_columns = ["sector", "month", "day", "start", "window_days"]
    signature_rows = walk.assign(
        execution_signature=walk["entry_date"].astype(str) + ":" + walk["exit_date"].astype(str)
    ).sort_values("test_year")
    signatures = signature_rows.groupby(key_columns, as_index=False)["execution_signature"].agg("|".join)
    grouped = grouped.merge(signatures, on=key_columns, how="left")
    # Require selection and success in every available OOS fold; this avoids presenting
    # a window as robust when it was only eligible once.
    available_folds = len(years) - MIN_TRAIN_OBSERVATIONS
    plans = grouped[
        (grouped["oos_observations"] == available_folds)
        & (grouped["oos_win_rate"] >= MIN_OOS_WIN_RATE)
        & (grouped["oos_worst_return"] >= MIN_OOS_WORST_RETURN)
        & (grouped["oos_worst_drawdown"] >= MAX_OOS_DRAWDOWN)
    ].copy()
    plans = plans.sort_values(["oos_mean_net_return", "oos_worst_return", "oos_worst_drawdown"], ascending=False)
    plans = plans.drop_duplicates("execution_signature").drop(columns="execution_signature")
    plans.insert(0, "rank", range(1, len(plans) + 1))
    # Preserve numeric values for ranking/reporting, but show percentages in the
    # user-facing CSV instead of decimal fractions.
    export_plans = plans.copy()
    for column in ["oos_mean_net_return", "oos_win_rate", "oos_worst_return", "oos_worst_drawdown"]:
        export_plans[column] = export_plans[column].map(lambda value: f"{value:.2%}")
    export_plans.to_csv(OUTPUT / "best_plan.csv", index=False)

    report = ["# Best seasonal research plan", "", f"Completed-year sample: {years[0]}–{years[-1]}",
              f"Candidates searched: {len(universe):,}", f"Round-trip cost: {ROUND_TRIP_COST:.2%}", "",
              "These are out-of-sample walk-forward rankings, not trading instructions. With only "
              f"{available_folds} unseen annual observation(s), no result establishes a reliable edge.", "",
              f"Final-report filters: every OOS return above {MIN_OOS_WORST_RETURN:.0%}, 100% OOS win rate, and no OOS "
              f"drawdown below {MAX_OOS_DRAWDOWN:.0%}.", ""]
    if plans.empty:
        report += ["## Result", "", "No plan survived every walk-forward fold. This is a valid research outcome; do not force a trade."]
    else:
        report += ["## Top plans", "", "| Rank | Sector | Entry | Hold (trading days) | OOS mean net return | OOS win rate | Worst OOS return | Worst drawdown |", "|---:|---|---|---:|---:|---:|---:|---:|"]
        for row in plans.head(TOP_PLANS).itertuples():
            report.append(f"| {row.rank} | {row.sector} | {row.start} | {row.window_days} | {row.oos_mean_net_return:.2%} | {row.oos_win_rate:.0%} | {row.oos_worst_return:.2%} | {row.oos_worst_drawdown:.2%} |")
        report += ["", "## Execution convention", "", "For research, enter at the first session Close on/after the listed calendar date and exit at the Close after the stated number of trading days. The seasonal date is known in advance; confirm your broker's close/post-close order support for the instrument you actually trade. Revalidate liquidity, costs, taxes, and market conditions before any use."]
    (OUTPUT / "BEST_PLAN.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"Wrote results to {OUTPUT}")


if __name__ == "__main__":
    run()
