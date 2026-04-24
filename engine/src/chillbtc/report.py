"""Phase D — report visuel PNG pour consolidation des résultats de backtest.

Génère 4 figures dans ``engine/output/figures/`` :

1. ``equity_curves.png``   : HODL + Mode A (S8) + Mode B (K=4) + Mode C (cascade),
   échelle log, même fenêtre 2016-05 → 2026-03.
2. ``drawdown.png``        : drawdowns des 4 mêmes séries, overlay sur la cible -50 %.
3. ``heatmaps_o1.png``     : S1 (R1 CAGR, barplot sur n), S4 (R2 DD, heatmap
   k_low × k_high), S7 (R3 Sharpe, heatmap k_low × k_high). Visualise le
   plateau de stabilité de chaque règle sous O1.
4. ``theta_o2.png``        : distribution des paramètres θ choisis par fenêtre
   walk-forward pour S2 (R1 n), S5 (R2 k_low/k_high), S8 (R3 k_low/k_high).

Sortie complémentaire : ``figures_index.md`` listant les 4 PNG avec légendes,
à intégrer dans la documentation de résultats.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from chillbtc.backtest import (
    FEE_CONSERVATIVE,
    _trim_common_warmup,
)
from chillbtc.cascade import run_cascade
from chillbtc.compare_modes import K_ENSEMBLE, _mode_a_signal, _mode_b_signal
from chillbtc.data import load_or_fetch
from chillbtc.metrics import equity_from_signals


def _compute_series(monthly: pd.DataFrame, fee: float, phase_c: pd.DataFrame):
    hodl_sig = pd.Series(1.0, index=monthly.index)
    eq_hodl = equity_from_signals(monthly, hodl_sig, fee_per_switch=0.0)

    cell_id_a, sig_a = _mode_a_signal(monthly, fee, phase_c)
    eq_a = equity_from_signals(monthly, sig_a, fee_per_switch=fee)

    sig_b = _mode_b_signal(monthly, fee, K=K_ENSEMBLE)
    eq_b = equity_from_signals(monthly, sig_b, fee_per_switch=fee)

    cascade = run_cascade(fee=fee, save_outputs=False, convention="strict_r1_def")
    eq_c = cascade["equity"]

    return {
        "HODL": eq_hodl,
        f"Mode A ({cell_id_a})": eq_a,
        f"Mode B (K={K_ENSEMBLE})": eq_b,
        "Mode C (cascade)": eq_c,
    }


def _drawdown_series(equity: pd.Series) -> pd.Series:
    rolling_max = equity.cummax()
    return (equity - rolling_max) / rolling_max


def _plot_equity(series: dict[str, pd.Series], out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = {"HODL": "gray"}
    styles = {"HODL": "--"}
    for label, eq in series.items():
        ls = styles.get(label, "-")
        color = colors.get(label)
        ax.plot(eq.index, eq.values, label=label, linestyle=ls, color=color, linewidth=1.6)
    ax.set_yscale("log")
    ax.set_title("Courbes d'équité — fenêtre 2016-05 → 2026-03 (capital initial 100, log)")
    ax.set_ylabel("Équité (log)")
    ax.set_xlabel("Date")
    ax.grid(True, which="both", ls=":", alpha=0.5)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def _plot_drawdown(series: dict[str, pd.Series], out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    for label, eq in series.items():
        dd = _drawdown_series(eq) * 100
        ax.plot(dd.index, dd.values, label=label, linewidth=1.4)
    ax.axhline(-50, color="red", linestyle=":", linewidth=1.2, label="Cible DD -50 %")
    ax.set_title("Drawdowns — overlay cible bon père de famille (-50 %)")
    ax.set_ylabel("Drawdown (%)")
    ax.set_xlabel("Date")
    ax.grid(True, ls=":", alpha=0.5)
    ax.legend(loc="lower left")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def _heatmap_2d(ax, grid_df: pd.DataFrame, x_col: str, y_col: str, z_col: str, title: str, cmap: str = "viridis"):
    pivot = grid_df.pivot(index=y_col, columns=x_col, values=z_col)
    im = ax.imshow(pivot.values, aspect="auto", origin="lower", cmap=cmap,
                   extent=[pivot.columns.min(), pivot.columns.max(),
                           pivot.index.min(), pivot.index.max()])
    ax.set_title(title)
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    plt.colorbar(im, ax=ax, fraction=0.046)
    # Marker sur le max (ou min pour DD qui est négatif)
    if z_col == "max_dd":
        idx = pivot.values.argmax()  # max = DD le moins profond = le meilleur
    else:
        idx = pivot.values.argmax()
    row, col = np.unravel_index(idx, pivot.values.shape)
    ax.plot(pivot.columns[col], pivot.index[row], marker="*", color="red", markersize=14)


def _plot_heatmaps_o1(phase_c_raw: dict, out_path: Path) -> None:
    cells = {c["cell_id"]: c for c in phase_c_raw["cells"]}

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # S1 (R1 × O1, CAGR) — barplot sur n
    s1 = pd.DataFrame(cells["S1"]["grid"])
    axes[0].bar(s1["n"].astype(int), s1["cagr"] * 100, color="steelblue", alpha=0.8)
    best_n = int(s1.loc[s1["cagr"].idxmax(), "n"])
    axes[0].axvline(best_n, color="red", linestyle="--", label=f"argmax CAGR : n={best_n}")
    axes[0].set_title("S1 R1×O1 — CAGR(n) TSMOM\nplateau étroit")
    axes[0].set_xlabel("n (mois)")
    axes[0].set_ylabel("CAGR (%)")
    axes[0].legend()
    axes[0].grid(True, ls=":", alpha=0.5, axis="y")

    # S4 (R2 × O1, DD) — heatmap k_low × k_high sur max_dd
    s4 = pd.DataFrame(cells["S4"]["grid"])
    _heatmap_2d(axes[1], s4, "k_high", "k_low", "max_dd",
                "S4 R2×O1 — max DD Mayer\n(rouge = optimum, DD le moins profond)")

    # S7 (R3 × O1, Sharpe) — heatmap k_low × k_high sur sharpe
    s7 = pd.DataFrame(cells["S7"]["grid"])
    _heatmap_2d(axes[2], s7, "k_high", "k_low", "sharpe",
                "S7 R3×O1 — Sharpe Power Law\n(rouge = optimum)")

    fig.suptitle("Heatmaps O1 — plateau de stabilité par règle", fontsize=13)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def _plot_theta_o2(phase_c_raw: dict, out_path: Path) -> None:
    cells = {c["cell_id"]: c for c in phase_c_raw["cells"]}

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    # S2 (R1 × O2 DD) — distribution θ_n par fenêtre
    s2 = pd.DataFrame(cells["S2"]["grid"])
    s2["label"] = s2["train_start"].str[:7] + " → " + s2["test_end"].str[:7]
    axes[0].bar(s2["label"], s2["theta_n"], color="steelblue", alpha=0.8)
    axes[0].set_title(f"S2 R1×O2 DD — θ_n par fenêtre ({len(s2)} fenêtres)")
    axes[0].set_ylabel("n choisi (mois)")
    axes[0].tick_params(axis="x", rotation=30)
    axes[0].grid(True, ls=":", alpha=0.5, axis="y")

    # S5 (R2 × O2 Sharpe) — θ_k_low et θ_k_high par fenêtre
    s5 = pd.DataFrame(cells["S5"]["grid"])
    s5["label"] = s5["train_start"].str[:7] + "\n→ " + s5["test_end"].str[:7]
    x = np.arange(len(s5))
    width = 0.35
    axes[1].bar(x - width/2, s5["theta_k_low"], width, label="k_low", color="steelblue")
    axes[1].bar(x + width/2, s5["theta_k_high"], width, label="k_high", color="orange")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(s5["label"], rotation=20)
    axes[1].set_title(f"S5 R2×O2 Sharpe — θ par fenêtre ({len(s5)} fenêtres)")
    axes[1].set_ylabel("k")
    axes[1].legend()
    axes[1].grid(True, ls=":", alpha=0.5, axis="y")

    # S8 (R3 × O2 CAGR) — θ_k_low et θ_k_high par fenêtre
    s8 = pd.DataFrame(cells["S8"]["grid"])
    s8["label"] = s8["train_start"].str[:7] + "\n→ " + s8["test_end"].str[:7]
    x = np.arange(len(s8))
    axes[2].bar(x - width/2, s8["theta_k_low"], width, label="k_low", color="steelblue")
    axes[2].bar(x + width/2, s8["theta_k_high"], width, label="k_high", color="orange")
    axes[2].set_xticks(x)
    axes[2].set_xticklabels(s8["label"], rotation=20)
    axes[2].set_title(f"S8 R3×O2 CAGR — θ par fenêtre ({len(s8)} fenêtres)")
    axes[2].set_ylabel("k")
    axes[2].legend()
    axes[2].grid(True, ls=":", alpha=0.5, axis="y")

    fig.suptitle("Distribution θ — paramètres choisis par fenêtre walk-forward O2", fontsize=13)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


def _render_figures_index_md(fig_paths: dict[str, Path]) -> str:
    lines = [
        "## §15 — Figures (post-Phase D)",
        "",
        "Figures générées par `engine/src/chillbtc/report.py`. Inlined depuis",
        "`engine/output/figures/`. Régénérer après tout rerun de Phase C / D.",
        "",
    ]
    captions = {
        "equity": ("Courbes d'équité", "HODL + 3 modes candidats, échelle log, 2016-05 → 2026-03."),
        "drawdown": ("Drawdowns", "Superposition avec la cible bon père de famille -50 %."),
        "heatmaps_o1": ("Heatmaps O1", "Plateaux de stabilité — S1 (R1 CAGR), S4 (R2 DD), S7 (R3 Sharpe)."),
        "theta_o2": ("Distribution θ O2", "Paramètres retenus par fenêtre walk-forward pour S2, S5, S8."),
    }
    for key, path in fig_paths.items():
        title, caption = captions[key]
        lines.append(f"### {title}")
        lines.append("")
        lines.append(f"![{title}](backtest/output/figures/{path.name})")
        lines.append("")
        lines.append(f"_{caption}_")
        lines.append("")
    return "\n".join(lines)


def run_report(fee: float = FEE_CONSERVATIVE) -> dict[str, Path]:
    repo = Path(__file__).resolve().parents[2]
    out_dir = repo / "output" / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)

    cache = repo / "data" / "btc_monthly.csv"
    monthly = _trim_common_warmup(load_or_fetch(cache))
    phase_c = pd.read_csv(repo / "output" / "phase_c_results.csv").set_index("cell_id")
    with open(repo / "output" / "phase_c_raw.json") as f:
        phase_c_raw = json.load(f)

    series = _compute_series(monthly, fee, phase_c)

    fig_paths: dict[str, Path] = {}
    fig_paths["equity"] = out_dir / "equity_curves.png"
    _plot_equity(series, fig_paths["equity"])
    print(f"[1/4] {fig_paths['equity'].name}")

    fig_paths["drawdown"] = out_dir / "drawdown.png"
    _plot_drawdown(series, fig_paths["drawdown"])
    print(f"[2/4] {fig_paths['drawdown'].name}")

    fig_paths["heatmaps_o1"] = out_dir / "heatmaps_o1.png"
    _plot_heatmaps_o1(phase_c_raw, fig_paths["heatmaps_o1"])
    print(f"[3/4] {fig_paths['heatmaps_o1'].name}")

    fig_paths["theta_o2"] = out_dir / "theta_o2.png"
    _plot_theta_o2(phase_c_raw, fig_paths["theta_o2"])
    print(f"[4/4] {fig_paths['theta_o2'].name}")

    md = _render_figures_index_md(fig_paths)
    md_path = repo / "output" / "figures_index.md"
    md_path.write_text(md)
    print(f"\nMarkdown index saved to {md_path}")

    return fig_paths


def main() -> None:
    paths = run_report()
    print("\n=== Figures générées ===")
    for key, p in paths.items():
        print(f"  {key:12s} → {p}")


if __name__ == "__main__":
    main()
