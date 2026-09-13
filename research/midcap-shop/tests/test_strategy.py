from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[1]))
from charges import Charges, delivery_charges, grouped_sell_charges
from strategy import Lot, MidcapShopBacktest, StrategySettings, add_indicators, weakest_shortlist


def bars(closes: list[float], opens: list[float] | None = None) -> pd.DataFrame:
    index = pd.bdate_range("2024-01-01", periods=len(closes))
    return pd.DataFrame({"Open": opens or closes, "High": closes, "Low": closes,
                         "Close": closes, "Volume": [1000] * len(closes)}, index=index)


class MidcapShopTests(unittest.TestCase):
    def test_sma_and_weakest_shortlist(self) -> None:
        frames = {f"S{i}": add_indicators(bars([100] * 20 + [100 - i])) for i in range(6)}
        self.assertTrue(frames["S0"]["sma_20"].iloc[:19].isna().all())
        self.assertEqual(weakest_shortlist(frames, frames["S0"].index[-1]), ["S5", "S4", "S3", "S2", "S1"])

    def test_cost_formula_and_grouped_dp(self) -> None:
        buy = delivery_charges(100_000, "buy")
        self.assertAlmostEqual(buy.stt, 100.0)
        self.assertAlmostEqual(buy.stamp, 15.0)
        self.assertAlmostEqual(buy.gst, .18 * (3.07 + .1))
        sells = grouped_sell_charges([10_000, 30_000])
        self.assertAlmostEqual(sum(charge.dp for charge in sells), 15.34)
        self.assertAlmostEqual(sells[0].dp, 15.34 / 4)

    def test_next_open_fresh_entry_and_lot_target_exit(self) -> None:
        # Six symbols make a complete shortlist. AAA is weakest and enters on session 21 Open.
        base = [100.0] * 20 + [90.0, 91.0, 100.0, 100.0]
        frames = {"AAA": bars(base, [100.0] * 20 + [90.0, 92.0, 101.0, 101.0])}
        for number in range(5):
            frames[f"B{number}"] = bars([100.0] * 24)
        result = MidcapShopBacktest(frames).run(pd.Timestamp("2024-01-01"), pd.Timestamp("2024-02-01"))
        self.assertEqual(len(result.trades), 1)
        trade = result.trades.iloc[0]
        self.assertEqual(trade.ticker, "AAA")
        self.assertEqual(trade.entry_price, 90.0)
        self.assertEqual(trade.exit_price, 101.0)
        self.assertGreater(trade.buy_stt, 0)
        self.assertAlmostEqual(trade.sell_dp, 15.34)

    def test_cash_and_integer_share_limit(self) -> None:
        frames = {"AAA": bars([100.0] * 20 + [90.0, 100.0])}
        for number in range(5):
            frames[f"B{number}"] = bars([100.0] * 22)
        result = MidcapShopBacktest(frames, initial_cash=50).run(pd.Timestamp("2024-01-01"), pd.Timestamp("2024-02-01"))
        self.assertTrue((result.skipped["reason"] == "amount_below_one_share").any())

    def test_average_uses_most_declined_latest_lot_when_all_shortlisted_are_held(self) -> None:
        closes = {"A": 96.0, "B": 90.0, "C": 95.0, "D": 94.0, "E": 93.0}
        frames = {ticker: bars([100.0] * 20 + [close]) for ticker, close in closes.items()}
        engine = MidcapShopBacktest(frames)
        date = next(iter(frames.values())).index[-1]
        engine.lots = [Lot(i, ticker, date - pd.Timedelta(days=1), 100.0, 10, Charges(), 1)
                       for i, ticker in enumerate(closes, start=1)]
        engine._queue_orders(date)
        self.assertEqual(len(engine.pending_buys), 1)
        self.assertEqual(engine.pending_buys[0].ticker, "B")
        self.assertEqual(engine.pending_buys[0].kind, "average")

    def test_average_cap_blocks_a_fourth_average(self) -> None:
        frames = {"A": bars([100.0] * 20 + [90.0])}
        frames.update({ticker: bars([100.0] * 20 + [98.0]) for ticker in "BCDE"})
        engine = MidcapShopBacktest(frames)
        date = next(iter(frames.values())).index[-1]
        engine.lots = [Lot(i, "A", date - pd.Timedelta(days=i), 100.0, 10, Charges(), i)
                       for i in range(1, 5)]
        engine.lots.extend(Lot(i + 4, ticker, date, 100.0, 10, Charges(), 1)
                           for i, ticker in enumerate("BCDE", start=1))
        engine._queue_orders(date)
        self.assertEqual(engine.pending_buys, [])

    def test_rsi_and_trend_filters_are_buy_gates(self) -> None:
        frame = bars([100.0 - i * 0.1 for i in range(220)])
        date = frame.index[-1]
        rsi_engine = MidcapShopBacktest({"A": frame}, settings=StrategySettings(rsi_oversold=True))
        trend_engine = MidcapShopBacktest({"A": frame}, settings=StrategySettings(trend_sma=True))
        self.assertTrue(rsi_engine._passes_buy_filters("A", date))
        self.assertFalse(trend_engine._passes_buy_filters("A", date))

    def test_stock_level_target_exits_all_lots_at_weighted_average_target(self) -> None:
        frame = bars([100.0] * 20 + [105.0])
        date = frame.index[-1]
        engine = MidcapShopBacktest({"A": frame}, settings=StrategySettings(stock_level_target=True))
        engine.lots = [Lot(1, "A", date, 100.0, 10, Charges(), 1),
                       Lot(2, "A", date, 80.0, 10, Charges(), 1)]
        engine._queue_orders(date)
        self.assertEqual(engine.pending_sells, {1, 2})
        lot_engine = MidcapShopBacktest({"A": frame})
        lot_engine.lots = engine.lots
        lot_engine._queue_orders(date)
        self.assertEqual(lot_engine.pending_sells, {2})

    def test_dividend_and_split_preserve_open_lot_economics(self) -> None:
        frames = {"AAA": bars([100.0] * 20 + [90.0, 95.0, 47.5])}
        for number in range(5):
            frames[f"B{number}"] = bars([100.0] * 23)
        dates = frames["AAA"].index
        actions = {"AAA": pd.DataFrame({"Dividends": [0.0, 0.0, 1.0], "Stock Splits": [0.0, 0.0, 2.0]}, index=dates[-3:])}
        engine = MidcapShopBacktest(frames, actions)
        engine.run(pd.Timestamp("2024-01-01"), pd.Timestamp("2024-02-01"))
        lot = next(lot for lot in engine.lots if lot.ticker == "AAA")
        self.assertEqual(lot.quantity, 222)
        self.assertEqual(lot.entry_price, 45.0)
        self.assertGreater(engine.cash, 70_200)  # includes ₹1 × 222 post-split shares


if __name__ == "__main__":
    unittest.main()
