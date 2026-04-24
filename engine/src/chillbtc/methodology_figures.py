# SPDX-License-Identifier: CC-BY-NC-SA-4.0
# Copyright © 2026 ChillBTC
"""Annotated figures for docs/methodologie.md.

Generates three PNGs in docs/assets/methodology/ using the frozen live
parameters of the strategy (N_TSMOM=11, k_low=0.6, k_high=2.5, N=5.8,
A=-16.917):

- signaux_history.png   tendance and valorisation signals versus BTC price,
                        with CASH zones shaded.
- powerlaw_band.png     BTC price versus the Power Law fair-value line,
                        with the hysteresis band k_low .. k_high shaded.
- cascade_position_history.png
                        Cascade position (0 / 50 / 100 percent) over time,
                        overlaid on BTC price with pivotal-cycle annotations.

Run:

    cd engine
    uv run chillbtc-methodology-figures
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from chillbtc.cascade import build_cascade_position
from chillbtc.monthly_signal import (
    A_POWER_LAW,
    CONVENTION,
    K_HIGH_R3,
    K_LOW_R3,
    N_EXP_R3,
    N_TSMOM,
)
from chillbtc.rules import power_law_fair_value, signal_power_law, signal_tsmom

BTC_ORANGE = "#F7931A"
CASH_GREY = "#9AA0A6"
BUY_GREEN = "#2E7D32"
BAND_BLUE = "#1565C0"
ANNOT_BG = "#FFF8E1"

# Three mutually-exclusive CASH states (tendance, valorisation, both)
COLOR_TEND_ONLY = "#BDBDBD"   # grey, momentum weak, price still reasonable
COLOR_VALO_ONLY = "#90CAF9"   # light blue, price overheated, trend still up
COLOR_BOTH_CASH = "#EF9A9A"   # light red, bear confirmed


def _load_monthly() -> pd.DataFrame:
    repo = Path(__file__).resolve().parents[2]
    cache = repo / "data" / "btc_monthly.csv"
    return pd.read_csv(cache, parse_dates=["date"], index_col="date")


def _shade_three_states(ax, sig_tend: pd.Series, sig_valo: pd.Series) -> None:
    """Shade the three mutually-exclusive CASH states with distinct colors.

    Each month falls into exactly one of four buckets (BUY+BUY, tendance CASH
    only, valorisation CASH only, both CASH). BUY+BUY is left unshaded; the
    three CASH states each get a dedicated color and a single legend entry.
    """
    tend = sig_tend.fillna(1.0).astype(float).to_numpy()
    valo = sig_valo.fillna(1.0).astype(float).to_numpy()
    dates = sig_tend.index.to_numpy()

    state_defs = [
        ("tend_only", (tend == 0) & (valo == 1), COLOR_TEND_ONLY,
         "Tendance CASH uniquement"),
        ("valo_only", (tend == 1) & (valo == 0), COLOR_VALO_ONLY,
         "Valorisation CASH uniquement"),
        ("both_cash", (tend == 0) & (valo == 0), COLOR_BOTH_CASH,
         "Les 2 signaux CASH (bear confirmé)"),
    ]
    alpha = 0.50
    for _, mask, color, label in state_defs:
        in_zone = False
        start = None
        first = True
        for i, on in enumerate(mask):
            if on and not in_zone:
                start = dates[i]
                in_zone = True
            elif not on and in_zone:
                ax.axvspan(start, dates[i], color=color, alpha=alpha,
                           label=label if first else None)
                first = False
                in_zone = False
        if in_zone:
            ax.axvspan(start, dates[-1], color=color, alpha=alpha,
                       label=label if first else None)


def plot_signaux_history(monthly: pd.DataFrame, out: Path) -> None:
    sig_tend = signal_tsmom(monthly, n=N_TSMOM)
    sig_valo = signal_power_law(
        monthly, k_low=K_LOW_R3, k_high=K_HIGH_R3,
        n_exponent=N_EXP_R3, a_constant=A_POWER_LAW,
    )

    fig, ax = plt.subplots(figsize=(13.33, 6.0), dpi=120)
    _shade_three_states(ax, sig_tend, sig_valo)
    ax.semilogy(monthly.index, monthly["close_usd"], color=BTC_ORANGE,
                linewidth=1.8, label="Prix BTC (USD, log)")

    ax.set_title("Signaux tendance et valorisation — historique 2015-2026",
                 fontsize=14, loc="left")
    ax.set_ylabel("Prix BTC en USD (échelle log)")
    ax.set_xlabel("")
    ax.grid(True, which="both", alpha=0.2)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax.legend(loc="lower right", framealpha=0.9)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)


def plot_powerlaw_band(monthly: pd.DataFrame, out: Path) -> None:
    fair = power_law_fair_value(monthly, a_constant=A_POWER_LAW, n_exponent=N_EXP_R3)
    band_low = fair * K_LOW_R3
    band_high = fair * K_HIGH_R3

    fig, ax = plt.subplots(figsize=(13.33, 6.0), dpi=120)
    ax.fill_between(monthly.index, band_low, band_high,
                    color=BAND_BLUE, alpha=0.10,
                    label=f"Bande de tolérance [{K_LOW_R3} × fair, {K_HIGH_R3} × fair]")
    ax.semilogy(monthly.index, fair, color=BAND_BLUE, linestyle="--",
                linewidth=1.5, label=f"Droite Power Law (A={A_POWER_LAW}, N={N_EXP_R3})")
    ax.semilogy(monthly.index, monthly["close_usd"], color=BTC_ORANGE,
                linewidth=1.8, label="Prix BTC (USD, log)")

    ax.set_title("Valorisation — prix BTC contre la droite Power Law",
                 fontsize=14, loc="left")
    ax.set_ylabel("Prix BTC en USD (échelle log)")
    ax.set_xlabel("")
    ax.grid(True, which="both", alpha=0.2)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax.legend(loc="lower right", framealpha=0.9)
    fig.tight_layout()
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)


def plot_cascade_position_history(monthly: pd.DataFrame, out: Path) -> None:
    sig_tend = signal_tsmom(monthly, n=N_TSMOM)
    sig_valo = signal_power_law(
        monthly, k_low=K_LOW_R3, k_high=K_HIGH_R3,
        n_exponent=N_EXP_R3, a_constant=A_POWER_LAW,
    )
    position = build_cascade_position(sig_tend, sig_valo, convention=CONVENTION)

    fig, (ax_price, ax_pos) = plt.subplots(
        nrows=2, ncols=1, figsize=(13.33, 7.5), dpi=120,
        sharex=True, gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05},
    )

    ax_price.semilogy(monthly.index, monthly["close_usd"], color=BTC_ORANGE,
                      linewidth=1.8, label="Prix BTC (USD, log)")
    ax_price.set_ylabel("Prix BTC (USD, log)")
    ax_price.grid(True, which="both", alpha=0.2)
    ax_price.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax_price.set_title(
        "Cascade — position recommandée vs prix BTC sur 4 cycles",
        fontsize=14, loc="left",
    )

    annotations = [
        ("2017-12-31", "Top 2017 : valorisation CASH → 50 %"),
        ("2018-12-31", "Bear 2018 : 0 % toute l'année"),
        ("2021-11-30", "Top 2021 : valorisation CASH → 50 %"),
        ("2022-11-30", "FTX : 0 % à l'effondrement"),
    ]
    for date_str, text in annotations:
        d = pd.Timestamp(date_str)
        if d not in monthly.index:
            continue
        y = float(monthly.loc[d, "close_usd"])
        ax_price.annotate(
            text, xy=(d, y),
            xytext=(0, 40), textcoords="offset points",
            fontsize=9, ha="center",
            bbox=dict(boxstyle="round,pad=0.3", fc=ANNOT_BG, ec=CASH_GREY, alpha=0.9),
            arrowprops=dict(arrowstyle="->", color=CASH_GREY, lw=0.8),
        )

    pos_values = position.fillna(0.0).to_numpy()
    visual_heights = np.where(pos_values == 0.0, 8.0, pos_values * 100.0)
    colors = np.where(pos_values == 1.0, BUY_GREEN,
                      np.where(pos_values == 0.5, BTC_ORANGE, CASH_GREY))
    ax_pos.bar(position.index, visual_heights, width=30,
               color=colors, edgecolor="none")
    ax_pos.set_ylabel("% BTC")
    ax_pos.set_yticks([0, 50, 100])
    ax_pos.set_ylim(0, 110)
    ax_pos.grid(True, axis="y", alpha=0.2)
    ax_pos.set_xlabel("")

    from matplotlib.patches import Patch
    legend_handles = [
        Patch(facecolor=BUY_GREEN, label="100 % BTC"),
        Patch(facecolor=BTC_ORANGE, label="50 % BTC + 50 % USDC"),
        Patch(facecolor=CASH_GREY, label="0 % BTC (CASH)"),
    ]
    ax_pos.legend(handles=legend_handles, loc="upper left",
                  ncol=3, fontsize=8, framealpha=0.9)

    fig.subplots_adjust(hspace=0.05, top=0.92, bottom=0.08, left=0.07, right=0.98)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    repo = Path(__file__).resolve().parents[3]
    out_dir = repo / "docs" / "assets" / "methodology"
    out_dir.mkdir(parents=True, exist_ok=True)

    monthly = _load_monthly()

    plot_signaux_history(monthly, out_dir / "signaux_history.png")
    print(f"  wrote {out_dir / 'signaux_history.png'}")
    plot_powerlaw_band(monthly, out_dir / "powerlaw_band.png")
    print(f"  wrote {out_dir / 'powerlaw_band.png'}")
    plot_cascade_position_history(monthly, out_dir / "cascade_position_history.png")
    print(f"  wrote {out_dir / 'cascade_position_history.png'}")


if __name__ == "__main__":
    main()
