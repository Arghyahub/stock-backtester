# Squeeze Momentum research

Reproducible daily, long-only research of the LazyBear Squeeze Momentum breakout approach described in [Trading Journal's tutorial](https://www.youtube.com/watch?v=Xz3l0OSvrVE). It obtains the official current Nifty 200 constituent list and tests the five latest fully completed calendar years.

```bash
uv sync
uv run python run_research.py
```

Results are written to `output/`:

- `trades.csv` — each completed entry, exit, stop, and return;
- `strategy_summary.csv` — sector and aggregate metrics by variant;
- `data_quality.csv` — Yahoo download coverage and exclusions;
- `REPORT.md` — a readable methodology and results report.

The report compares the prior close-only adaptation with an exploratory daily-OHLCV model using trend, ADX, volume, and ATR-trailing-stop filters. See [PLAN.md](PLAN.md) for exact rules and limitations. This is research, not investment advice.

The aggregate return in the summary is a sequential trade-return diagnostic, not
a portfolio backtest: sector trades can overlap and no capital-allocation rule is modelled.
