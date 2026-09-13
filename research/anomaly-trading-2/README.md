# Anomaly trading 2

A walk-forward seasonal research system for NSE sector indices. It examines
calendar entry dates and one-to-60 trading-day holding periods over the most
recent five **completed** years, deducts costs, and ranks only unseen-year
performance.

```bash
uv sync
uv run python run_research.py
```

Tune universe, costs, and thresholds in `config.py`. See [PLAN.md](PLAN.md) for
the methodology and its limitations.

The generated `output/BEST_PLAN.md` is a research report, not investment advice.

## Relationship to the web app

This folder is the standalone reference implementation. The web backend applies
the same five-completed-year, 1–60 trading-day, close-to-close walk-forward
rules when an admin runs **Compute V2 strategy**. It persists approved plans
and evidence instead of importing these generated CSV files. Use this command
to inspect or compare the reference research output.
