"""Phase D — Mode C cascade : 2 signaux R1+R3 avec dosage 100/50/0.

Architecture cascade 2 signaux (défensif + agressif), classique en trend-following.
Paire retenue après arbitrage Q1/Q2/Q3 (2026-04-18) :

- **Défensif** : S2 = R1 × O2 (objectif DD, n=11). Sort tôt, DD le plus bas dans l'axe R1.
- **Agressif** : S8 = R3 × O2 (objectif CAGR, walk-forward). Reste long plus longtemps,
  CAGR élevé sans le biais in-sample de S7 (R3×O1, A fitté sur full data).

Dosage (100/50/0 strict) :

- défensif BUY  & agressif BUY  → 1.00  (tout va bien)
- défensif CASH & agressif BUY  → 0.50  (pré-alerte, on allège)
- agressif CASH                 → 0.00  (bear confirmé, sortie totale)

Edge case (défensif BUY & agressif CASH) : agressif CASH prime → 0 %. Rare
par construction (R3 Power Law band sort plus tard que R1 TSMOM court horizon),
tracé dans le diagnostic.

Friction : frais proportionnels à `abs(Δposition)`. Passer de 1.00 à 0.50 paie
0.5 × 0.5 % = 0.25 % de friction (seule la fraction tradée est facturée),
pas le fee binaire plein comme dans `equity_from_signals`. Plus fidèle à la
réalité Binance.

Sorties :

- ``engine/output/cascade_position.csv`` : série temporelle {date, def_signal,
  agg_signal, position, crân}.
- ``engine/output/cascade_summary.json`` : KPIs + distribution des crans +
  edge cases + paramètres des 2 cellules.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from chillbtc.backtest import (
    FEE_CONSERVATIVE,
    LATIN_SQUARE,
    OPTIM_FNS,
    SPECS,
    _trim_common_warmup,
)
from chillbtc.data import load_or_fetch
from chillbtc.metrics import (
    PERIODS_PER_YEAR,
    cagr,
    max_drawdown,
    sharpe,
)

DEF_CELL_ID = "S2"   # R1 × O2 — objectif DD, défensif
AGG_CELL_ID = "S8"   # R3 × O2 — objectif CAGR, agressif (walk-forward)


def _get_cell(cell_id: str):
    for c in LATIN_SQUARE:
        if c.cell_id == cell_id:
            return c
    raise ValueError(f"unknown cell_id {cell_id}")


def _cell_signal(cell, monthly: pd.DataFrame, fee: float) -> tuple[pd.Series, dict]:
    """Reprend le pattern de ``ensemble._cell_signal`` : relance l'optim de la cellule,
    puis régénère le signal binaire sur la fenêtre complète avec les params trouvés
    + refit des extras (A de R3) sur toute la série pour la perf finale."""
    spec = SPECS[cell.rule_name]
    fn = OPTIM_FNS[cell.optim_name]
    result = fn(spec, monthly, cell.objective, fee)
    extras = spec.fit_on_train(monthly) if spec.fit_on_train is not None else {}
    signal = spec.rule_fn(monthly, **{**result["params"], **extras})
    signal.name = cell.cell_id
    return signal, {
        "cell_id": cell.cell_id,
        "rule": cell.rule_name,
        "optim": cell.optim_name,
        "objective": cell.objective,
        "params": {k: float(v) if isinstance(v, (np.floating, np.integer)) else v
                   for k, v in result["params"].items()},
        "extras": {k: float(v) if isinstance(v, (np.floating, np.integer)) else v
                   for k, v in extras.items()},
    }


def build_cascade_position(
    def_sig: pd.Series,
    agg_sig: pd.Series,
    convention: str = "strict_r1_def",
) -> pd.Series:
    """Produit la position cascade (0.0 / 0.5 / 1.0) à partir de 2 signaux binaires.

    3 conventions supportées, qui diffèrent sur le traitement des désaccords entre
    les 2 signaux (S2 R1 défensif théorique vs S8 R3 agressif théorique).

    - ``strict_r1_def`` (actuel) : cascade stricte avec R1 défensif, R3 agressif.
      Edge case (R1 BUY & R3 CASH) traité comme 0 % (R3 CASH prime).

    - ``symmetric`` : chaque désaccord = 50 %. Renonce au framing asymétrique
      mais reflète le fait que sur BTC, aucune des 2 règles n'est univoquement
      "plus stricte" — R3 sort parfois AVANT R1 en zone euphorique (valorisation),
      R1 sort parfois AVANT R3 en fin de bear (momentum).

    - ``strict_r3_def`` : cascade stricte avec R3 défensif, R1 agressif. Edge case
      nouveau (R3 BUY & R1 CASH) traité comme 0 % (R1 CASH prime).
    """
    def_b = def_sig.fillna(0.0).astype(float)
    agg_b = agg_sig.fillna(0.0).astype(float)
    position = pd.Series(0.0, index=def_b.index, name="position_cascade")

    both_buy = (def_b == 1) & (agg_b == 1)
    both_cash = (def_b == 0) & (agg_b == 0)
    only_agg_buy = (def_b == 0) & (agg_b == 1)   # R1 CASH, R3 BUY
    only_def_buy = (def_b == 1) & (agg_b == 0)   # R1 BUY, R3 CASH (edge actuel)

    position[both_buy] = 1.0

    if convention == "strict_r1_def":
        position[only_agg_buy] = 0.5
        # only_def_buy → 0 (déjà), both_cash → 0 (déjà)
    elif convention == "symmetric":
        position[only_agg_buy] = 0.5
        position[only_def_buy] = 0.5
    elif convention == "strict_r3_def":
        # Swap : R3 devient défensif, R1 agressif
        # R3 BUY & R1 CASH = def BUY & agg CASH (nouvel edge, R1 SELL prime) → 0
        # R3 CASH & R1 BUY = def CASH & agg BUY (pré-alerte R3) → 0.5 (ex-edge)
        position[only_def_buy] = 0.5  # R1 BUY & R3 CASH
        # only_agg_buy (R1 CASH & R3 BUY) → 0 (déjà)
    else:
        raise ValueError(f"unknown convention: {convention}")
    return position


def equity_from_cascade(
    monthly: pd.DataFrame,
    position: pd.Series,
    fee_per_switch: float = FEE_CONSERVATIVE,
    capital_init: float = 100.0,
) -> pd.Series:
    """Equity avec friction proportionnelle au turnover.

    - ``position[t]`` = dosage signalé fin de mois t (∈ {0, 0.5, 1}).
    - Position effective sur le mois t+1 = ``position[t]`` (shift 1, CASH avant le
      premier signal).
    - Turnover[t+1] = ``abs(position[t] - position[t-1])`` → frais facturés sur la
      seule fraction tradée (passer 1.00 → 0.50 coûte 0.5 × fee).
    """
    btc_returns = monthly["close_usd"].pct_change()
    pos = position.astype(float).fillna(0.0)
    effective_pos = pos.shift(1).fillna(0.0)
    prev_pos = effective_pos.shift(1).fillna(0.0)
    turnover = (effective_pos - prev_pos).abs()
    strat_returns = effective_pos * btc_returns - turnover * fee_per_switch
    strat_returns = strat_returns.fillna(0.0)
    equity = capital_init * (1 + strat_returns).cumprod()
    equity.name = "equity_cascade"
    return equity


def _count_switches_cascade(position: pd.Series) -> int:
    """Nombre de changements de cran (n'importe lequel), peu importe l'amplitude."""
    pos = position.astype(float).fillna(0.0)
    return int((pos.diff().abs() > 1e-9).sum())


def _total_turnover(position: pd.Series) -> float:
    """Somme des |Δposition| — utile pour juger du churn effectif (0.5 + 0.5 pour
    un aller-retour partiel, 1.0 pour un aller-retour binaire).
    """
    pos = position.astype(float).fillna(0.0)
    return float(pos.diff().abs().sum())


def run_cascade(
    fee: float = FEE_CONSERVATIVE,
    save_outputs: bool = True,
    convention: str = "strict_r1_def",
) -> dict:
    repo = Path(__file__).resolve().parents[2]
    cache = repo / "data" / "btc_monthly.csv"
    monthly = _trim_common_warmup(load_or_fetch(cache))

    def_cell = _get_cell(DEF_CELL_ID)
    agg_cell = _get_cell(AGG_CELL_ID)

    print(f"[défensif] {def_cell.cell_id} = {def_cell.rule_name} × {def_cell.optim_name} (obj={def_cell.objective})")
    def_sig, def_meta = _cell_signal(def_cell, monthly, fee)
    print(f"  params: {def_meta['params']}")

    print(f"[agressif] {agg_cell.cell_id} = {agg_cell.rule_name} × {agg_cell.optim_name} (obj={agg_cell.objective})")
    agg_sig, agg_meta = _cell_signal(agg_cell, monthly, fee)
    print(f"  params: {agg_meta['params']}")
    if agg_meta["extras"]:
        print(f"  extras (full-history refit): {agg_meta['extras']}")

    position = build_cascade_position(def_sig, agg_sig, convention=convention)
    equity = equity_from_cascade(monthly, position, fee_per_switch=fee)
    returns = equity.pct_change()

    def_b = def_sig.fillna(0.0).astype(float)
    agg_b = agg_sig.fillna(0.0).astype(float)
    total_months = int(len(position))
    # Distribution = position effective après application de la convention.
    n_100 = int((position == 1.0).sum())
    n_050 = int((position == 0.5).sum())
    n_000 = int((position == 0.0).sum())
    n_edge_def_only = int(((def_b == 1) & (agg_b == 0)).sum())

    n_sw = _count_switches_cascade(position)
    total_turnover = _total_turnover(position)
    n_years = total_months / PERIODS_PER_YEAR

    summary = {
        "mode": "C_cascade_R1_R3",
        "convention": convention,
        "def_cell": def_meta,
        "agg_cell": agg_meta,
        "fee_per_switch": fee,
        "window_start": monthly.index.min().isoformat(),
        "window_end": monthly.index.max().isoformat(),
        "total_months": total_months,
        "cagr_pct": round(cagr(equity) * 100, 2),
        "max_dd_pct": round(max_drawdown(equity) * 100, 2),
        "sharpe": round(sharpe(returns), 3),
        "n_switches": n_sw,
        "switches_per_year": round(n_sw / n_years, 3) if n_years > 0 else 0.0,
        "total_turnover": round(total_turnover, 3),
        "distribution": {
            "months_100pct": n_100,
            "months_50pct": n_050,
            "months_0pct": n_000,
            "pct_100pct": round(100 * n_100 / total_months, 1),
            "pct_50pct": round(100 * n_050 / total_months, 1),
            "pct_0pct": round(100 * n_000 / total_months, 1),
        },
        "edge_cases": {
            "months_def_BUY_and_agg_CASH": n_edge_def_only,
            "note": "Edge case traité comme 0 % (agressif SELL prime). Doit rester rare.",
        },
    }

    # Table mensuelle pour audit
    table = pd.DataFrame({
        "btc_close": monthly["close_usd"],
        "def_signal": def_b,
        "agg_signal": agg_b,
        "position": position,
        "equity_cascade": equity,
    })

    if save_outputs:
        out_dir = repo / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        suffix = f"_{convention}" if convention != "strict_r1_def" else ""
        table.to_csv(out_dir / f"cascade_position{suffix}.csv")
        with open(out_dir / f"cascade_summary{suffix}.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"\nTable mensuelle saved to {out_dir / f'cascade_position{suffix}.csv'}")
        print(f"Summary saved to {out_dir / f'cascade_summary{suffix}.json'}")

    return {"summary": summary, "table": table, "position": position, "equity": equity}


def _print_summary(s: dict) -> None:
    print(f"\n=== Mode C cascade R1+R3 — convention={s['convention']} ===")
    print(f"  Fenêtre         : {s['window_start'][:10]} → {s['window_end'][:10]} ({s['total_months']} mois)")
    print(f"  CAGR            : {s['cagr_pct']:.2f} %")
    print(f"  Max DD          : {s['max_dd_pct']:.2f} %")
    print(f"  Sharpe          : {s['sharpe']:.3f}")
    print(f"  Switches        : {s['n_switches']} ({s['switches_per_year']:.2f} /an)")
    print(f"  Turnover total  : {s['total_turnover']:.2f} (somme |Δposition|)")
    d = s["distribution"]
    print(f"  Distribution    : 100 % = {d['months_100pct']} ({d['pct_100pct']} %), "
          f"50 % = {d['months_50pct']} ({d['pct_50pct']} %), "
          f"0 % = {d['months_0pct']} ({d['pct_0pct']} %)")


def main() -> None:
    # Lance les 3 conventions pour comparaison (voies A/B/C).
    for conv in ("strict_r1_def", "symmetric", "strict_r3_def"):
        out = run_cascade(convention=conv)
        _print_summary(out["summary"])


if __name__ == "__main__":
    main()
