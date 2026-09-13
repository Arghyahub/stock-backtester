# Squeeze Momentum research plan

## Objective

Evaluate a daily Nifty 200 adaptation of the long breakout method in Trading Journal's [LazyBear Squeeze Momentum tutorial](https://www.youtube.com/watch?v=Xz3l0OSvrVE). The purpose is to test the rules, not to validate or recommend trading them.

## Fixed methodology

- Universe: the official current Nifty 200 constituent CSV from NSE. This is a current snapshot and therefore has survivorship bias in a 2021–2025 test.
- History: five fully completed calendar years; exclude the in-progress year.
- Control: the prior close-only implementation remains in the output for comparison.
- Improved model: standard daily OHLCV LazyBear squeeze, at least six squeeze sessions, true release, positive/rising histogram, Close above EMA(50) above EMA(200), ADX(14) at least 20 and rising, and volume at least 120% of the prior 20-session mean. Enter at the next Open and manage with a 2×ATR trailing stop.
- Costs: deduct the configured round-trip cost from every completed trade.

## Variants

`baseline` tests the rules above. `range_confirmed` additionally requires the preceding 20-session high/low range to be at most 8× ATR. `no_expansion` rejects a release whose true range exceeds 2.5× the prior 20-session median true range. These are objective stand-ins for the video's visual range and huge-candle checks, not claimed author settings.

## Limitations

Daily data cannot reproduce intraday order timing, discretionary support/resistance, liquidity, taxes, slippage, or broker-specific stop execution. No short positions are tested because the intended NSE stock/ETF use case is long-only. The improved filters are exploratory rather than validated, and must not be tuned against this same result set.

The all-sector compounded figure is a sequential trade-return diagnostic only;
it is not a portfolio result because simultaneous sector positions can overlap.
