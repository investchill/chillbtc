"""Phase C sanity check.

Runs the 9 cells of the Latin square, prints the result table next to HODL,
and flags any cell that fails its acceptance criterion
(optim protocol §2/3/4):

- O1: plateau width ratio >= 30 %
- O2: WFE >= 60 %
- O3: cycle-retention >= 70 %
"""

from __future__ import annotations

from chillbtc.backtest import FEE_CONSERVATIVE, run_phase_c


def main() -> None:
    df = run_phase_c(fee=FEE_CONSERVATIVE, save_outputs=True)

    print("\n=== Phase C — résultats (frais 0.5 % par switch) ===\n")
    cols = [
        "rule", "optim", "objective", "params",
        "cagr_pct", "max_dd_pct", "sharpe", "switches_per_year",
        "wfe", "plateau_width", "retention_cycle",
    ]
    print(df[cols].to_string())

    print("\n=== Critères d'acceptation ===\n")
    flags = []
    for cell_id, row in df.iterrows():
        if cell_id == "HODL":
            continue
        optim = row["optim"]
        if optim == "O1":
            ok = row["width_ok"]
            metric = f"plateau_width={row['plateau_width']}"
            target = "≥ 0.30"
        elif optim == "O2":
            ok = row["wfe_ok"]
            metric = f"WFE={row['wfe']}"
            target = "≥ 0.60"
        elif optim == "O3":
            ok = row["retention_ok"]
            metric = f"retention={row['retention_cycle']}"
            target = "≥ 0.70"
        else:
            continue
        mark = "OK " if ok else "KO "
        flags.append(f"  [{mark}] {cell_id} {row['rule']} × {optim} : {metric} (cible {target})")
    print("\n".join(flags))

    # HODL baseline for quick visual comparison
    hodl = df.loc["HODL"]
    print(f"\n=== HODL baseline : CAGR={hodl['cagr_pct']}%, DD={hodl['max_dd_pct']}%, Sharpe={hodl['sharpe']} ===")


if __name__ == "__main__":
    main()
