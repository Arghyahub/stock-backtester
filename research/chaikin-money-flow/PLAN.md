# Chaikin Money Flow research methodology

- **Universe:** current official Nifty 200 constituent CSV. Historical results have survivorship bias.
- **Windows:** latest completed calendar year and latest five completed calendar years, with one prior calendar year downloaded for indicator warm-up.
- **Signals:** `cmf_baseline` is CMF(40) strictly crossing above +0.05 with signal Close above EMA(200). `cmf_rsi_ema_confirmed` additionally requires Close above EMA(50), EMA(50) above EMA(200), and RSI(14) from 50 through 70. CMF is rolling money-flow volume divided by rolling volume; zero high-low ranges contribute zero money flow.
- **Execution:** enter next Open, unless it is at/below the precomputed `signal Close − 2×ATR(14)` stop. Target is 2× actual entry-to-stop risk. Only one open long per ticker.
- **Exit:** a stop gap exits at Open; a non-gap stop exits at stop price; target exits at target price. If a daily bar touches both stop and target, stop is assumed first. Remaining positions exit at the window's final Close and are marked `sample_end`.
- **Metrics:** returns deduct 20 bps round-trip costs. Summary distinguishes signals, executed trades, gap skips, and signals skipped while a position is open. Aggregate results concatenate stock trade returns by exit date and are not investable portfolio performance.
