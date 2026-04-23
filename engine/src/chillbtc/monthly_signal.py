# SPDX-License-Identifier: CC-BY-NC-SA-4.0
# Copyright © 2026 ChillBTC
"""Phase E — Signal mensuel live de la stratégie BTC (gelée 2026-05-01).

Config figée (valeurs canoniques) :

- Mode C cascade R1+R3, convention ``strict_r1_def``.
- S2 défensif : R1 TSMOM, n = 11.
- S8 agressif : R3 Power Law band, k_low = 0.6, k_high = 2.5, N_exp = 5.8.
- Constante A du Power Law **figée à -16.917** jusqu'à la prochaine revue
  annuelle (1ᵉʳ janvier).

Exécution mensuelle (1ᵉʳ du mois, après clôture daily) :

    uv run chillbtc-monthly

Comportement :

1. Force le refresh du cache daily Bitstamp.
2. Drop le mois en cours s'il est partiel.
3. Calcule R1, R3, puis la cascade → position 0 / 0.5 / 1.
4. Affiche un rapport FR à l'écran, avec l'action Binance à faire.
5. Affiche la ligne CSV à copier-coller dans le Google Sheet live.
6. Append cette ligne à ``engine/output/live_journal.csv``.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import pandas as pd

from chillbtc.cascade import build_cascade_position
from chillbtc.data import load_or_fetch
from chillbtc.rules import (
    power_law_fair_value,
    signal_power_law,
    signal_tsmom,
)

# Config figée (valeurs canoniques)
N_TSMOM = 11
K_LOW_R3 = 0.6
K_HIGH_R3 = 2.5
N_EXP_R3 = 5.8
A_POWER_LAW = -16.917  # Figée 2026-04-18 jusqu'à la prochaine revue (1ᵉʳ janvier).
CONVENTION = "strict_r1_def"
FROZEN_SINCE = "2026-05-01"

LIVE_JOURNAL_HEADER = [
    "date",
    "close_btc_usd",
    "return_11m",
    "signal_r1",
    "ratio_price_fair_pl",
    "a_constant",
    "signal_r3",
    "position_pct",
    "diagnostic_fr",
    "source",
]

MOIS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril",
    5: "mai", 6: "juin", 7: "juillet", 8: "août",
    9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre",
}


def emoji_position(position: float) -> str:
    if position >= 0.99:
        return "🟢"
    if position >= 0.49:
        return "🟡"
    return "🔴"


def emoji_signal(sig: float) -> str:
    return "✅" if sig == 1.0 else "❌"


def _position_label(position: float) -> str:
    if position == 1.0:
        return "100 % BTC"
    if position == 0.5:
        return "50 % BTC + 50 % USDC"
    return "0 % BTC (100 % USDC)"


def _drop_partial_current_month(monthly: pd.DataFrame) -> pd.DataFrame:
    """Drop la dernière ligne si le mois n'est pas encore clos.

    Heuristique : si la dernière date index est à moins de 20 jours
    d'aujourd'hui, on considère qu'elle représente un mois partiel.
    Aligné sur ``backtest._trim_common_warmup``.
    """
    today = pd.Timestamp.utcnow().tz_localize(None).normalize()
    last = monthly.index[-1]
    if (today - last).days < 20:
        return monthly.iloc[:-1].copy()
    return monthly.copy()


def _sig_label(sig: float) -> str:
    if pd.isna(sig):
        return "N/A"
    return "BUY" if sig == 1 else "CASH"


def _build_diagnostic(sig_r1: float, sig_r3: float, ret_11: float,
                       ratio: float, position: float) -> str:
    r1_lbl = _sig_label(sig_r1)
    r3_lbl = _sig_label(sig_r3)
    return (
        f"R1 {r1_lbl} (rendement 11m = {ret_11:+.1%})"
        f" & R3 {r3_lbl} (prix/fair_PL = {ratio:.2f})"
        f" → {position * 100:.0f} % BTC"
    )


def _already_logged(csv_path: Path, date_iso: str) -> bool:
    if not csv_path.exists():
        return False
    with open(csv_path) as f:
        for line in f:
            if line.startswith(date_iso + ","):
                return True
    return False


def _append_to_journal(csv_path: Path, row: dict) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = csv_path.exists()
    with open(csv_path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LIVE_JOURNAL_HEADER)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def run_monthly_signal(dry_run: bool = False) -> dict:
    repo = Path(__file__).resolve().parents[2]
    cache = repo / "data" / "btc_monthly.csv"

    monthly_raw = load_or_fetch(cache, force_refresh=True)
    monthly = _drop_partial_current_month(monthly_raw)

    # A figé jusqu'à la revue annuelle ; pas de refit live.
    fair = power_law_fair_value(monthly, a_constant=A_POWER_LAW, n_exponent=N_EXP_R3)
    ratio_pl = monthly["close_usd"] / fair

    sig_r1_series = signal_tsmom(monthly, n=N_TSMOM)
    sig_r3_series = signal_power_law(
        monthly,
        k_low=K_LOW_R3,
        k_high=K_HIGH_R3,
        n_exponent=N_EXP_R3,
        a_constant=A_POWER_LAW,
    )
    position_series = build_cascade_position(
        sig_r1_series, sig_r3_series, convention=CONVENTION
    )

    last_date = monthly.index[-1]
    close = float(monthly["close_usd"].iloc[-1])
    ret_11 = float(monthly["close_usd"].pct_change(N_TSMOM).iloc[-1])
    sig_r1 = float(sig_r1_series.iloc[-1])
    sig_r3 = float(sig_r3_series.iloc[-1])
    ratio = float(ratio_pl.iloc[-1])
    position = float(position_series.iloc[-1])

    diagnostic = _build_diagnostic(sig_r1, sig_r3, ret_11, ratio, position)
    mois_label = f"{MOIS_FR[last_date.month]} {last_date.year}"
    pos_emoji = emoji_position(position)
    r1_emoji = emoji_signal(sig_r1)
    r3_emoji = emoji_signal(sig_r3)

    print()
    print(f"  📊  Signal BTC — fin {mois_label}")
    print()
    print(f"  {pos_emoji}   {_position_label(position)}")
    print()
    print("  ─ Signaux ─")
    print(f"    R1 TSMOM 11m : {ret_11:>+6.1%}  →  {r1_emoji} {_sig_label(sig_r1)}")
    print(f"    R3 Power Law : {ratio:>6.2f}  →  {r3_emoji} {_sig_label(sig_r3)}")
    print()

    row = {
        "date": last_date.date().isoformat(),
        "close_btc_usd": f"{close:.2f}",
        "return_11m": f"{ret_11:.6f}",
        "signal_r1": int(sig_r1) if not pd.isna(sig_r1) else "",
        "ratio_price_fair_pl": f"{ratio:.6f}",
        "a_constant": f"{A_POWER_LAW:.6f}",
        "signal_r3": int(sig_r3) if not pd.isna(sig_r3) else "",
        "position_pct": f"{position * 100:.0f}",
        "diagnostic_fr": diagnostic,
        "source": "live",
    }

    csv_line = ",".join(str(row[h]) for h in LIVE_JOURNAL_HEADER)

    journal_csv = repo / "output" / "live_journal.csv"
    if dry_run:
        print("  [dry-run] Pas d'append au journal.")
        print()
    elif not _already_logged(journal_csv, row["date"]):
        _append_to_journal(journal_csv, row)
        print("  📝 Journal mis à jour.")
        print()

    return {
        "date": last_date,
        "close_btc_usd": close,
        "signal_r1": sig_r1,
        "signal_r3": sig_r3,
        "position_pct": position * 100,
        "diagnostic": diagnostic,
        "csv_line": csv_line,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Signal mensuel BTC (stratégie gelée 2026-05-01, mode C cascade R1+R3).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche le rapport et la ligne CSV sans append au journal live.",
    )
    args = parser.parse_args()
    run_monthly_signal(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
