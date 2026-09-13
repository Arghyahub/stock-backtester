from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[1]))
from strategy import add_indicators, signals_for_variant, simulate_long_only
from universe import stock_universe


def prices(rows: int = 260) -> pd.DataFrame:
    return pd.DataFrame({"Close": np.linspace(100, 160, rows)},
                        index=pd.bdate_range("2024-01-01", periods=rows))


class SqueezeMomentumTests(unittest.TestCase):
    def test_close_only_warmup_and_release(self) -> None:
        frame = add_indicators(prices())
        self.assertTrue(frame["ema_200"].iloc[:199].isna().all())
        self.assertTrue(frame["histogram"].iloc[:19].isna().all())
        self.assertTrue((frame.loc[frame["squeeze_release"], "squeeze_off"]).all())

    def test_missing_close_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Close"):
            add_indicators(pd.DataFrame({"Open": [100]}))

    def test_stock_universe_is_unique_but_keeps_membership(self) -> None:
        universe = stock_universe()
        self.assertIn("TCS.NS", universe)
        self.assertIn("Nifty Bank", universe["HDFCBANK.NS"])
        self.assertIn("Nifty Financial Services", universe["HDFCBANK.NS"])

    def test_variant_filter(self) -> None:
        frame = add_indicators(prices())
        i = 230
        frame.loc[:, "core_signal"] = False
        frame.loc[frame.index[i], "core_signal"] = True
        frame.loc[frame.index[i], "range_confirmed"] = False
        self.assertTrue(signals_for_variant(frame, "baseline").iloc[i])
        self.assertFalse(signals_for_variant(frame, "range_confirmed").iloc[i])

    def test_next_close_entry_close_stop_and_cost(self) -> None:
        index = pd.bdate_range("2025-01-01", periods=4)
        frame = pd.DataFrame({"Close": [100, 100, 90, 90], "atr": [1, 1, 1, 1],
                              "positive_falling": [False] * 4, "prior_squeeze_days": [6] * 4,
                              "histogram": [1] * 4}, index=index)
        trades = simulate_long_only(frame, pd.Series([True, False, False, False], index=index))
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].entry_date, index[1])
        self.assertEqual(trades[0].exit_date, index[2])
        self.assertEqual(trades[0].exit_price, 90.0)
        self.assertEqual(trades[0].exit_reason, "close_stop")
        self.assertAlmostEqual(trades[0].net_return, trades[0].gross_return - 0.002)

    def test_no_signal_has_no_trade(self) -> None:
        frame = pd.DataFrame({"Close": [100, 101], "atr": [1, 1],
                              "positive_falling": [False, False], "prior_squeeze_days": [0, 0],
                              "histogram": [0, 0]}, index=pd.bdate_range("2025-01-01", periods=2))
        self.assertEqual(simulate_long_only(frame, pd.Series([False, False], index=frame.index)), [])


if __name__ == "__main__":
    unittest.main()
