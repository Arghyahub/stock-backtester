# Improvements over anomaly-trading v1

This document compares the original `anomaly-trading` notebooks with the
walk-forward system in `anomaly-trading-2`.

| Area | Version 1 | Version 2 | How this helps |
|---|---|---|---|
| Evaluation period | Roughly ten years were scanned and filtered in one pass. | Uses the five most recent **completed** calendar years. | A fixed, complete sample avoids mixing an unfinished current-year trade with historical evidence. |
| Window search | Scanned dates and 1–60 day windows, then ranked them using those same results. | Scans the same 1–60 trading-day range, but selects candidates using only prior years before evaluating the next year. | Reduces look-ahead bias: the test-year return did not influence its own selection. |
| Validation | In-sample metrics were used as evidence of an anomaly. | Uses expanding walk-forward folds: 2021–2023 selects 2024; 2021–2024 selects 2025. | Produces genuinely unseen-year results, which are much more informative than an in-sample ranking. |
| Sample-size treatment | Could accept as few as four observations. | Requires three prior observations before a fold, reports the small two-year OOS sample explicitly, and refuses to claim a proven edge. | Makes uncertainty visible instead of presenting a short history as confidence. |
| Entry/exit convention | Return was measured Close-to-Close without a documented execution process. | Uses first available Close on/after the calendar date and the Close after the selected number of trading days; the seasonal date is pre-committed. | Matches an after-office routine while avoiding a signal that depends on an unknown same-day close. |
| Trading costs | No transaction costs in window returns. | Deducts a configurable 0.20% round-trip cost from every trade. | Prevents small apparent anomalies from surviving only because friction was ignored. |
| Drawdown | Measured the lowest price relative to entry. This misses losses after a position first rises. | Computes close-based peak-to-trough drawdown during each holding window. | Measures path risk more accurately and supports a meaningful drawdown filter. |
| Candidate qualification | Thresholds ranked windows after the full scan. | Training-fold qualification requires positive mean net return, at least 60% wins, drawdown control, and a positive approximate lower confidence bound. | Makes selection rules explicit and applies them before the unseen test result is observed. |
| Duplicate windows | Weekend/holiday calendar dates could point to identical market sessions and appear as separate ideas. | Detects and removes plans with identical OOS entry/exit sessions. | Avoids overstating the number of independent opportunities. |
| Data quality | Missing observations were forward-filled. | Uses only actual downloaded market sessions and records data range, row count, and download status. | Avoids artificial prices/returns and makes source coverage auditable. |
| Reproducibility | Notebook cells depended on execution order and local state. | A single command runs the entire pipeline and writes CSV and Markdown outputs. | Makes reruns and parameter review substantially easier. |
| Reporting | Excel-focused output ranked many overlapping anomalies. | Creates `BEST_PLAN.md`, `best_plan.csv`, raw walk-forward candidates, and a data-quality report. | Separates the readable conclusion from the audit trail needed to review it. |

## What version 2 still does not solve

Version 2 is a stricter research prototype, not a validated trading system.
Five years gives only two out-of-sample annual folds under this design. Before
acting on a result, extend the history, use the exact instrument that would be
traded, include its taxes/slippage/liquidity constraints, and test a
pre-committed live or paper-trading process.

The system studies sector indices, not historical constituent-level portfolios.
It therefore avoids the stock-survivorship issue from version 1's stock screen,
but it also does not select individual stocks. That should be a separate,
point-in-time-universe walk-forward project.
