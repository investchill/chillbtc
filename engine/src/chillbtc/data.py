"""BTC daily fetcher (CryptoDataDownload Bitstamp) + monthly aggregation.

The CoinGecko free public API now caps history at 365 days, so we use
CryptoDataDownload's Bitstamp daily CSV, which is publicly accessible without
authentication and covers ~11 years of data (from 2014-11 to today).

Returns a tz-naive monthly DataFrame indexed by month-end date.
"""

from __future__ import annotations

from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Final

import pandas as pd
import requests

GENESIS: Final = pd.Timestamp("2009-01-03")
CDD_BITSTAMP_DAILY: Final = "https://www.cryptodatadownload.com/cdd/Bitstamp_BTCUSD_d.csv"
DEFAULT_TIMEOUT_S: Final = 30
CACHE_TTL_DAYS: Final = 25
HEADERS: Final = {"User-Agent": "Mozilla/5.0 (chillbtc research)"}


def fetch_bitstamp_daily() -> pd.DataFrame:
    """Fetch BTC/USD daily OHLCV from CryptoDataDownload (Bitstamp).

    Keeps volume columns when present (CDD typically exposes "Volume BTC"
    and "Volume USD"); they are renamed to volume_btc / volume_usd. If the
    source changes its schema, only OHLC is guaranteed.
    """
    response = requests.get(CDD_BITSTAMP_DAILY, headers=HEADERS, timeout=DEFAULT_TIMEOUT_S)
    response.raise_for_status()

    # CDD prepends a comment line "https://www.CryptoDataDownload.com" before the header
    text = response.text
    first_newline = text.index("\n")
    csv_body = text[first_newline + 1 :]

    df = pd.read_csv(StringIO(csv_body))
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()

    rename_map = {"close": "close_usd"}
    for col in df.columns:
        lower = col.lower().strip()
        if lower in {"volume btc", "volume_btc", "volumebtc"}:
            rename_map[col] = "volume_btc"
        elif lower in {"volume usd", "volume_usd", "volume usdt", "volumeusd"}:
            rename_map[col] = "volume_usd"
    df = df.rename(columns=rename_map)

    keep_cols = ["date", "open", "high", "low", "close_usd"]
    for vol_col in ("volume_btc", "volume_usd"):
        if vol_col in df.columns:
            keep_cols.append(vol_col)

    df = (
        df.loc[:, keep_cols]
        .set_index("date")
        .sort_index()
        .loc[lambda d: ~d.index.duplicated(keep="last")]
    )
    return df


def aggregate_monthly(daily: pd.DataFrame) -> pd.DataFrame:
    """Aggregate daily prices into a tz-naive monthly DataFrame.

    Columns:
    - close_usd: last daily close of the month
    - sma_200d: end-of-month snapshot of the 200-day rolling mean (canonical Mayer
      denominator). NaN for the first ~200 days of data.
    - days_since_genesis: int, days from 2009-01-03 to month-end
    - return_1m, return_12m: arithmetic returns vs 1, 12 months ago
    """
    enriched = daily.copy()
    enriched["sma_200d"] = enriched["close_usd"].rolling(window=200).mean()

    monthly = enriched[["close_usd", "sma_200d"]].resample("ME").last()
    monthly["days_since_genesis"] = (monthly.index - GENESIS).days.astype("int64")
    monthly["return_1m"] = monthly["close_usd"].pct_change(1)
    monthly["return_12m"] = monthly["close_usd"].pct_change(12)
    return monthly


def load_or_fetch(cache_csv: Path, force_refresh: bool = False) -> pd.DataFrame:
    """Load monthly BTC data from cache when fresh, else fetch from Bitstamp."""
    if cache_csv.exists() and not force_refresh:
        cached = pd.read_csv(cache_csv, parse_dates=["date"], index_col="date")
        last_date = cached.index.max()
        age_days = (datetime.utcnow() - last_date.to_pydatetime()).days
        if age_days < CACHE_TTL_DAYS:
            return cached

    daily = fetch_bitstamp_daily()
    monthly = aggregate_monthly(daily)
    cache_csv.parent.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(cache_csv)
    return monthly


def fetch_data_main() -> None:
    """CLI entrypoint: refresh the local cache and print summary."""
    cache = Path(__file__).resolve().parents[2] / "data" / "btc_monthly.csv"
    monthly = load_or_fetch(cache, force_refresh=True)
    print(
        f"OK | {len(monthly)} months | "
        f"{monthly.index.min().date()} -> {monthly.index.max().date()}"
    )
    print(monthly.head().to_string())
    print("...")
    print(monthly.tail().to_string())


if __name__ == "__main__":
    fetch_data_main()
