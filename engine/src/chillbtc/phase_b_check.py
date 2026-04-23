"""Phase B sanity check: run R1, R2, R3 with default params and print perf vs HODL.

This is throwaway code (replaced by ``backtest.py`` in Phase C) but lets us
visually validate that the rules behave sensibly before plugging the optimiser
on top.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from chillbtc.data import load_or_fetch
from chillbtc.metrics import equity_from_signals, summarize
from chillbtc.rules import signal_mayer, signal_power_law, signal_tsmom


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    cache = repo / "data" / "btc_monthly.csv"
    monthly = load_or_fetch(cache)

    print(f"Window: {monthly.index.min().date()} -> {monthly.index.max().date()} "
          f"({len(monthly)} months)\n")

    # HODL baseline (always BUY, no fees)
    hodl_signals = pd.Series(1.0, index=monthly.index, name="hodl")
    hodl_equity = equity_from_signals(monthly, hodl_signals, fee_per_switch=0.0)

    # R1 — Time-Series Momentum, N=12
    r1_signals = signal_tsmom(monthly, n=12)
    r1_equity = equity_from_signals(monthly, r1_signals, fee_per_switch=0.005)

    # R2 — Mayer Multiple band with canonical SMA200d
    # Default k_high=2.4 (Mayer's historical optimum) is never breached on 2014+ data
    # (max MM = 2.389 in Nov 2017), so we also show k_high=2.0 to demonstrate hysteresis works.
    r2a_signals = signal_mayer(monthly, k_low=1.0, k_high=2.4)
    r2a_equity = equity_from_signals(monthly, r2a_signals, fee_per_switch=0.005)

    r2b_signals = signal_mayer(monthly, k_low=1.0, k_high=2.0)
    r2b_equity = equity_from_signals(monthly, r2b_signals, fee_per_switch=0.005)

    # R3 — Power Law band, k_low=0.7 k_high=2.0 (A fitted on full series, in-sample bias)
    r3_signals = signal_power_law(monthly, k_low=0.7, k_high=2.0)
    r3_equity = equity_from_signals(monthly, r3_signals, fee_per_switch=0.005)

    rows = [
        summarize(hodl_equity, hodl_signals, "HODL"),
        summarize(r1_equity, r1_signals, "R1 TSMOM (N=12)"),
        summarize(r2a_equity, r2a_signals, "R2 Mayer SMA200d (k_low=1.0, k_high=2.4)"),
        summarize(r2b_equity, r2b_signals, "R2 Mayer SMA200d (k_low=1.0, k_high=2.0)"),
        summarize(r3_equity, r3_signals, "R3 PowerLaw (k_low=0.7, k_high=2.0)"),
    ]
    df = pd.DataFrame(rows).set_index("name")
    print(df.to_string())


if __name__ == "__main__":
    main()
