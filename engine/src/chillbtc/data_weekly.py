"""BTC weekly loader — side experiment for the monthly-vs-weekly comparison.

Built on top of ``data.py``: imports ``fetch_bitstamp_daily`` unchanged and only
adds a weekly aggregator (close-on-Sunday, W-SUN). The Sunday evening check sees
the close of the week that just ended.

Read-only with respect to the frozen monthly strategy. Nothing in this file
affects ``btc_monthly.csv`` or any monthly output.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from chillbtc.data import CACHE_TTL_DAYS, GENESIS, fetch_bitstamp_daily


def aggregate_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily prices into a weekly DataFrame indexed by Sunday close.

    Columns:
    - close_usd: last daily close of the week (Sunday or nearest prior close)
    - sma_200d: end-of-week snapshot of the 200-day daily rolling mean
    - days_since_genesis: days from 2009-01-03 to the week-end date
    - return_1w, return_48w, return_52w: returns vs 1/48/52 weeks ago
    """
    enriched = daily.copy()
    enriched["sma_200d"] = enriched["close_usd"].rolling(window=200).mean()

    weekly = enriched[["close_usd", "sma_200d"]].resample("W-SUN").last()
    weekly["days_since_genesis"] = (weekly.index - GENESIS).days.astype("int64")
    weekly["return_1w"] = weekly["close_usd"].pct_change(1)
    weekly["return_48w"] = weekly["close_usd"].pct_change(48)
    weekly["return_52w"] = weekly["close_usd"].pct_change(52)
    return weekly


def load_or_fetch_weekly(cache_csv: Path, force_refresh: bool = False) -> pd.DataFrame:
    if cache_csv.exists() and not force_refresh:
        cached = pd.read_csv(cache_csv, parse_dates=["date"], index_col="date")
        last_date = cached.index.max()
        age_days = (datetime.utcnow() - last_date.to_pydatetime()).days
        if age_days < CACHE_TTL_DAYS:
            return cached

    daily = fetch_bitstamp_daily()
    weekly = aggregate_weekly(daily)
    cache_csv.parent.mkdir(parents=True, exist_ok=True)
    weekly.to_csv(cache_csv)
    return weekly


def fetch_weekly_main() -> None:
    cache = Path(__file__).resolve().parents[2] / "data" / "btc_weekly.csv"
    weekly = load_or_fetch_weekly(cache, force_refresh=True)
    print(
        f"OK | {len(weekly)} weeks | "
        f"{weekly.index.min().date()} -> {weekly.index.max().date()}"
    )
    print(weekly.head().to_string())
    print("...")
    print(weekly.tail().to_string())


if __name__ == "__main__":
    fetch_weekly_main()
