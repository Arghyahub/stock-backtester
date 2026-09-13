# Nifty Midcap SHOP research

Reproducible, long-only daily research for the Midcap SHOP adaptation of the Nifty SHOP idea. It uses the current official Nifty Midcap 50 constituent snapshot, ₹1,00,000 starting cash, next-open execution, per-lot 8% targets, three averaging buys maximum per stock, and current Zerodha equity-delivery charges.

This is the Midcap 50 adaptation documented by Fabtrader, which credits the original Nifty SHOP concept to Mahesh Chandra Kaushik; it is not a verified direct publication by him. See [PLAN.md](PLAN.md) for fixed methodology and limitations.

## Run

```bash
cd research/midcap-shop
uv run python run_research.py
```

The generated `output/` folder contains trades, equity curve, summary, skipped orders, data quality, and a cited report. It is research only, not investment advice.

The default run compares the capped lot-wise baseline with a stock-level weighted-average-cost 8% exit, RSI(14) < 30, Close > SMA(200), and combined confirmation variants. These filters gate purchases only; they never block a qualifying exit.
