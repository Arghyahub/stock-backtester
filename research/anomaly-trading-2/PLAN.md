# Seasonal anomaly research plan

## Objective

Find **sector-index seasonal holding windows** that are promising after an honest
walk-forward evaluation. This is research, not an instruction to trade.

## Scope

- Universe: liquid NSE sector indices supplied by Yahoo Finance.
- History: the most recent five completed calendar years. The current partial
  year is deliberately excluded so every observation is a complete seasonal
  opportunity.
- Candidates: every valid calendar start day and every holding period from one
  through 60 **trading days**.
- Execution convention: buy at the first available **Close** on/after the
  calendar date and sell at the Close after the selected number of trading days.
  A round-trip cost is deducted from every return.

## Validation design

The script performs expanding-window walk-forward testing. For each eligible
test year, it uses only prior years to select candidates, then records their
return in that unseen test year. With five completed years this produces two
out-of-sample years (after the first three training years), so results must be
treated as preliminary rather than proof of an edge.

Selection happens separately inside each training fold. The final ranking uses
only the resulting out-of-sample returns. This prevents the original failure
mode of choosing a window after looking at the same outcomes used to judge it.

For the final `best_plan.csv`, a plan must be selected in every available
out-of-sample fold, have a positive return in every one, and have no
out-of-sample return below 3% or drawdown worse than 10%. These thresholds are in `config.py` and
must be changed before—not after—reviewing a run.

## Selection rules

A candidate must meet all of these **in its training fold**:

- at least three annual observations;
- positive mean net return;
- at least 60% winning years;
- no worse than the configured maximum drawdown;
- a positive lower confidence bound for the mean return, where possible.

The script also records how many overlapping candidate windows were searched.
It does not claim statistical significance from a small number of annual
observations; users should prefer stable neighbouring windows and re-run after
each completed year.

## Outputs

Running `uv run python run_research.py` writes:

- `output/walk_forward_candidates.csv` — every selected candidate and its
  unseen-year result;
- `output/best_plan.csv` — ranked, deduplicated candidates with only
  out-of-sample metrics;
- `output/BEST_PLAN.md` — a readable report of the best current plan and the
  research limitations;
- `output/data_quality.csv` — downloaded date ranges and row counts.

## Before real-money use

Validate with a longer history, a current investable instrument (ETF/futures),
its real transaction costs and taxes, capacity/liquidity limits, and a
pre-committed execution process. For NSE cash instruments, confirm that the
chosen broker supports the relevant close/post-close workflow. Do not treat an
index result as an executable single-stock recommendation.
