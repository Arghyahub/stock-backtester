from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[1]))
from strategy import add_indicators, simulate


def ohlcv(rows: int = 260) -> pd.DataFrame:
    close = np.linspace(100, 160, rows)
    return pd.DataFrame({"Open": close, "High": close + 2, "Low": close - 2,
                         "Close": close, "Volume": np.full(rows, 1000)},
                        index=pd.bdate_range("2024-01-01", periods=rows))


class ChaikinMoneyFlowTests(unittest.TestCase):
    def test_warmup_zero_range_and_strict_cross(self) -> None:
        frame = ohlcv()
        frame.loc[frame.index[0], ["High", "Low", "Close"]] = 100
        indicators = add_indicators(frame)
        self.assertTrue(indicators["cmf"].iloc[:39].isna().all())
        self.assertTrue(indicators["ema_200"].iloc[:199].isna().all())
        self.assertEqual(indicators["cmf"].iloc[39], 0.0)
        indicators.loc[:, "cmf"] = 0.05
        indicators.loc[:, "ema_200"] = 100
        indicators.loc[:, "Close"] = 110
        indicators["cmf_cross_up"] = (indicators["cmf"] > 0.05) & (indicators["cmf"].shift(1) <= 0.05)
        self.assertFalse(indicators["cmf_cross_up"].any())

    def test_rsi_ema_confirmation_requires_all_filters(self) -> None:
        frame = add_indicators(ohlcv())
        i = frame.index[-1]
        frame.loc[i, ["signal", "Close", "ema_50", "ema_200", "rsi_14"]] = [True, 120, 110, 100, 60]
        frame.loc[i, "rsi_ema_signal"] = (frame.loc[i, "signal"] and frame.loc[i, "Close"] > frame.loc[i, "ema_50"]
                                             and frame.loc[i, "ema_50"] > frame.loc[i, "ema_200"]
                                             and 50 <= frame.loc[i, "rsi_14"] <= 70)
        self.assertTrue(frame.loc[i, "rsi_ema_signal"])
        frame.loc[i, "rsi_14"] = 72
        self.assertFalse(50 <= frame.loc[i, "rsi_14"] <= 70)

    def test_gap_skip_stop_target_collision_and_sample_end(self) -> None:
        index = pd.bdate_range("2025-01-01", periods=6)
        frame = pd.DataFrame({
            "Open": [100, 89, 100, 100, 100, 100], "High": [101, 91, 101, 121, 110, 108],
            "Low": [99, 88, 99, 89, 90, 99], "Close": [100, 90, 100, 105, 105, 106],
            "atr": [5] * 6, "signal": [True, False, True, False, True, False],
        }, index=index)
        result = simulate(frame)
        self.assertEqual(result.skipped_gap_entries, 1)
        self.assertEqual(len(result.trades), 2)
        self.assertEqual(result.trades[0].exit_reason, "stop")  # collision is conservative
        self.assertEqual(result.trades[0].exit_price, 90.0)
        self.assertEqual(result.trades[1].exit_reason, "sample_end")
        self.assertAlmostEqual(result.trades[1].net_return, 0.06 - 0.002)

    def test_stop_gap_and_target(self) -> None:
        index = pd.bdate_range("2025-01-01", periods=5)
        frame = pd.DataFrame({
            "Open": [100, 100, 85, 110, 110], "High": [101, 101, 90, 121, 140],
            "Low": [99, 99, 80, 99, 109], "Close": [100, 100, 85, 110, 130],
            "atr": [5] * 5, "signal": [True, False, False, True, False],
        }, index=index)
        result = simulate(frame)
        self.assertEqual(result.trades[0].exit_reason, "stop_gap")
        self.assertEqual(result.trades[0].exit_price, 85)
        self.assertEqual(result.trades[1].exit_reason, "target")


if __name__ == "__main__":
    unittest.main()
