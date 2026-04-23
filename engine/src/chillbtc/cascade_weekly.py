"""Side experiment — Mode C cascade R1+R3 at weekly cadence.

100 % additive wrt the frozen monthly strategy: no mutation of ``cascade.py``,
``rules.py``, ``data.py``, or any monthly artifact. Paramètres figés repris de
la stratégie canonique :

- R1 TSMOM défensif : BUY si ``return_48w > 0`` (48 semaines ≈ 11 mois).
- R3 Power Law agressif : hysteresis sur ``close / fair_PL`` avec k_low=0.6,
  k_high=2.5, N_exponent=5.8. Constante A refit sur full série hebdo (script
  d'audit ; la cascade live mensuelle utilise A figé à -16.917 et n'est
  recalculée qu'à la revue annuelle, 1ᵉʳ janvier).
- Cascade ``strict_r1_def`` 100/50/0.

Friction : proportionnelle au turnover ``|Δposition|``, comme la cascade mensuelle.

Sunday-evening check : les signaux sont évalués sur le close du dimanche, la
position devient effective la semaine suivante (shift 1 semaine).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from chillbtc.data_weekly import load_or_fetch_weekly
from chillbtc.rules import _hysteresis_band, fit_power_law, power_law_fair_value

PERIODS_PER_YEAR_WEEKLY = 52

# Paramètres figés (valeurs canoniques)
N_TSMOM_WEEKS = 48
K_LOW_PL = 0.6
K_HIGH_PL = 2.5
N_EXPONENT_PL = 5.8


def signal_tsmom_weekly(weekly: pd.DataFrame, n: int = N_TSMOM_WEEKS) -> pd.Series:
    return_n = weekly["close_usd"].pct_change(n)
    sig = pd.Series(np.nan, index=weekly.index, name="signal_tsmom_weekly")
    valid = return_n.notna()
    sig.loc[valid] = (return_n.loc[valid] > 0).astype(float)
    return sig


def signal_power_law_weekly(
    weekly: pd.DataFrame,
    k_low: float = K_LOW_PL,
    k_high: float = K_HIGH_PL,
    n_exponent: float = N_EXPONENT_PL,
    a_constant: float | None = None,
) -> pd.Series:
    fair = power_law_fair_value(weekly, a_constant, n_exponent)
    plm = weekly["close_usd"] / fair
    return _hysteresis_band(plm, k_low, k_high).rename("signal_power_law_weekly")


def build_cascade_position_weekly(def_sig: pd.Series, agg_sig: pd.Series) -> pd.Series:
    """strict_r1_def : both BUY → 1.0 ; R1 CASH & R3 BUY → 0.5 ; sinon 0.0."""
    def_b = def_sig.fillna(0.0).astype(float)
    agg_b = agg_sig.fillna(0.0).astype(float)
    pos = pd.Series(0.0, index=def_b.index, name="position_cascade_weekly")
    pos[(def_b == 1) & (agg_b == 1)] = 1.0
    pos[(def_b == 0) & (agg_b == 1)] = 0.5
    return pos


def equity_from_cascade_weekly(
    weekly: pd.DataFrame,
    position: pd.Series,
    fee_per_switch: float,
    capital_init: float = 100.0,
) -> pd.Series:
    btc_returns = weekly["close_usd"].pct_change()
    pos = position.astype(float).fillna(0.0)
    effective_pos = pos.shift(1).fillna(0.0)
    prev_pos = effective_pos.shift(1).fillna(0.0)
    turnover = (effective_pos - prev_pos).abs()
    strat_returns = effective_pos * btc_returns - turnover * fee_per_switch
    strat_returns = strat_returns.fillna(0.0)
    equity = capital_init * (1 + strat_returns).cumprod()
    equity.name = "equity_cascade_weekly"
    return equity


def cagr_weekly(equity: pd.Series) -> float:
    if len(equity) < 2:
        return 0.0
    n_years = (len(equity) - 1) / PERIODS_PER_YEAR_WEEKLY
    if n_years <= 0:
        return 0.0
    ratio = equity.iloc[-1] / equity.iloc[0]
    if ratio <= 0:
        return 0.0
    return float(ratio ** (1 / n_years) - 1)


def max_drawdown_weekly(equity: pd.Series) -> float:
    if len(equity) == 0:
        return 0.0
    rolling_max = equity.cummax()
    drawdown = (equity - rolling_max) / rolling_max
    return float(drawdown.min())


def sharpe_weekly(returns: pd.Series) -> float:
    r = returns.dropna()
    if len(r) < 2 or r.std() == 0:
        return 0.0
    return float((r.mean() / r.std()) * np.sqrt(PERIODS_PER_YEAR_WEEKLY))


def _trim_common_warmup_weekly(weekly: pd.DataFrame) -> pd.DataFrame:
    """Drop leading weeks where R1 return_48w is NaN + drop current partial week."""
    trimmed = weekly.iloc[N_TSMOM_WEEKS:].copy()
    today = pd.Timestamp.utcnow().tz_localize(None).normalize()
    last = trimmed.index[-1]
    if (today - last).days < 4:
        trimmed = trimmed.iloc[:-1]
    return trimmed


def run_cascade_weekly(fee: float, save_outputs: bool = True) -> dict:
    repo = Path(__file__).resolve().parents[2]
    cache = repo / "data" / "btc_weekly.csv"
    weekly = _trim_common_warmup_weekly(load_or_fetch_weekly(cache))

    a_full, _ = fit_power_law(weekly, n_exponent=N_EXPONENT_PL)

    def_sig = signal_tsmom_weekly(weekly, n=N_TSMOM_WEEKS)
    agg_sig = signal_power_law_weekly(
        weekly,
        k_low=K_LOW_PL,
        k_high=K_HIGH_PL,
        n_exponent=N_EXPONENT_PL,
        a_constant=a_full,
    )
    position = build_cascade_position_weekly(def_sig, agg_sig)
    equity = equity_from_cascade_weekly(weekly, position, fee_per_switch=fee)
    returns = equity.pct_change()

    pos = position.astype(float).fillna(0.0)
    n_sw = int((pos.diff().abs() > 1e-9).sum())
    n_years = len(position) / PERIODS_PER_YEAR_WEEKLY
    total_turnover = float(pos.diff().abs().sum())

    hodl_equity = 100.0 * (weekly["close_usd"] / weekly["close_usd"].iloc[0])

    n_100 = int((position == 1.0).sum())
    n_050 = int((position == 0.5).sum())
    n_000 = int((position == 0.0).sum())
    total = int(len(position))

    summary = {
        "cadence": "weekly",
        "fee_per_switch": fee,
        "window_start": weekly.index.min().isoformat(),
        "window_end": weekly.index.max().isoformat(),
        "n_periods": total,
        "cagr_pct": round(cagr_weekly(equity) * 100, 2),
        "max_dd_pct": round(max_drawdown_weekly(equity) * 100, 2),
        "sharpe": round(sharpe_weekly(returns), 3),
        "final_equity": round(float(equity.iloc[-1]), 2),
        "n_switches": n_sw,
        "switches_per_year": round(n_sw / n_years, 2) if n_years > 0 else 0.0,
        "total_turnover": round(total_turnover, 3),
        "distribution": {
            "weeks_100pct": n_100,
            "weeks_50pct": n_050,
            "weeks_0pct": n_000,
            "pct_100pct": round(100 * n_100 / total, 1),
            "pct_50pct": round(100 * n_050 / total, 1),
            "pct_0pct": round(100 * n_000 / total, 1),
        },
        "hodl_cagr_pct": round(cagr_weekly(hodl_equity) * 100, 2),
        "hodl_max_dd_pct": round(max_drawdown_weekly(hodl_equity) * 100, 2),
        "hodl_final_equity": round(float(hodl_equity.iloc[-1]), 2),
        "a_constant_power_law": round(a_full, 4),
        "params": {
            "n_tsmom_weeks": N_TSMOM_WEEKS,
            "k_low_pl": K_LOW_PL,
            "k_high_pl": K_HIGH_PL,
            "n_exponent_pl": N_EXPONENT_PL,
        },
    }

    table = pd.DataFrame(
        {
            "btc_close": weekly["close_usd"],
            "def_signal": def_sig.fillna(0.0).astype(float),
            "agg_signal": agg_sig.fillna(0.0).astype(float),
            "position": position,
            "equity_cascade_weekly": equity,
            "hodl_equity": hodl_equity,
        }
    )

    if save_outputs:
        out_dir = repo / "output"
        out_dir.mkdir(parents=True, exist_ok=True)
        fee_tag = f"_fee{int(round(fee*1000)):03d}"
        table.to_csv(out_dir / f"cascade_position_weekly{fee_tag}.csv")
        with open(out_dir / f"cascade_summary_weekly{fee_tag}.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)

    return {
        "summary": summary,
        "table": table,
        "equity": equity,
        "hodl_equity": hodl_equity,
    }


def main() -> None:
    for fee in (0.002, 0.005):
        out = run_cascade_weekly(fee=fee)
        s = out["summary"]
        print(f"\n=== Weekly cascade — fee={fee*100:.1f} % ===")
        print(
            f"  Window  : {s['window_start'][:10]} → {s['window_end'][:10]} "
            f"({s['n_periods']} weeks)"
        )
        print(f"  CAGR    : {s['cagr_pct']:.2f} % (HODL {s['hodl_cagr_pct']:.2f} %)")
        print(f"  Max DD  : {s['max_dd_pct']:.2f} % (HODL {s['hodl_max_dd_pct']:.2f} %)")
        print(f"  Sharpe  : {s['sharpe']:.3f}")
        print(
            f"  Switches: {s['n_switches']} total ({s['switches_per_year']:.2f} /an)"
        )


if __name__ == "__main__":
    main()
