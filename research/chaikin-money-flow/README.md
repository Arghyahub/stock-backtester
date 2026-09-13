# Nifty 200 Chaikin Money Flow research

Reproducible daily, long-only research of the CMF strategy in the attached [tutorial](https://www.youtube.com/watch?v=RNJvhPASNU0). It uses the current official Nifty 200 constituent list and the five latest fully completed calendar years.

```bash
uv sync
uv run python run_research.py
```

The summary compares a CMF-only baseline with a confirmed model: CMF(40) crossing above +0.05 with Close above EMA(200), plus Close above EMA(50), EMA(50) above EMA(200), and RSI(14) from 50 through 70. Both use next-session-open entry, signal-close minus 2×ATR(14) stop, and a 2R target. It tests no short positions or optimized variants.

`output/` contains `trades.csv`, `strategy_summary.csv`, `data_quality.csv`, and `REPORT.md`. The summary has stock and Nifty 200 aggregate rows for the latest completed year and five completed years. Aggregate compounding and drawdown are sequential-trade diagnostics, not portfolio results.

The Nifty 200 list is current membership and therefore introduces survivorship bias in the historical test. Results omit sizing, taxes, liquidity, and slippage beyond the fixed 20 bps round-trip cost. Research only; not investment advice.

Sources: [NSE Nifty 200](https://www.nseindia.com/static/products-services/indices-nifty200-index); [CMF formula](https://help.ctrader.com/indicators/built-in/volume/chaikin-money-flow/).
