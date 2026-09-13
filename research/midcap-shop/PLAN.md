# Midcap SHOP methodology

- **Universe:** current Nifty Midcap 50 CSV from NSE. Historical constituent membership is not reconstructed; results therefore have survivorship bias.
- **Window:** 2021–2025, with November 2020 onward downloaded for SMA(20) warm-up.
- **Signals and execution:** daily close ranks `Close / SMA(20) - 1`; the five lowest form the shortlist. A fresh purchase uses equity ÷ 10. If all five are already held, the most-declined holding below its latest entry by more than 3% can receive one equity ÷ 40 average. Each stock is limited to three averaging buys after its initial lot (four open lots maximum). Qualifying lots close at 8% above their own entry. Every action executes at the next available Open, sales first.
- **Corporate actions:** unadjusted prices are used. Split ratios alter open-lot quantity and entry price; cash dividends credit open holdings on ex-date.
- **Costs:** current retail individual Zerodha NSE equity-delivery charges are uniformly applied; one DP fee is allocated across same-scrip, same-day sold lots.
- **Exclusions:** capital-gains tax, AMC, MTF, leverage, slippage, partial fills, and historical fee changes.
- **Confirmation study:** the report compares baseline rules against gates requiring RSI(14) < 30, Close > SMA(200), and both. Gates apply to fresh and averaging buys, never exits.
- **Exit-pattern study:** `baseline_stock_target` exits all open lots in a stock once its quantity-weighted average entry reaches the 8% target, rather than exiting individual qualifying lots.
