"""Prototype dashboard generator: standalone HTML + PNG + CSV from monthly BTC data.

This module produces a HODL-only dashboard so the user can validate the
visual approach BEFORE the 9 strategies are coded. It is throwaway prototype
code: a real dashboard module will replace it once Phase D lands.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

BTC_ORANGE = "#f7931a"
DD_RED = "#e74c3c"


def compute_hodl_equity(monthly: pd.DataFrame, capital_init: float = 100.0) -> pd.DataFrame:
    """Compute HODL equity curve, drawdown, and rolling stats."""
    out = monthly[["close_usd"]].copy()
    out["hodl_equity"] = capital_init * out["close_usd"] / out["close_usd"].iloc[0]
    rolling_max = out["hodl_equity"].cummax()
    out["hodl_drawdown"] = (out["hodl_equity"] - rolling_max) / rolling_max
    out["return_1m"] = out["hodl_equity"].pct_change()
    return out


def _summary_stats(df: pd.DataFrame) -> dict:
    n_months = len(df)
    n_years = n_months / 12.0
    total_return = df["hodl_equity"].iloc[-1] / df["hodl_equity"].iloc[0] - 1
    cagr = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0.0
    monthly_returns = df["return_1m"].dropna()
    sharpe = (
        (monthly_returns.mean() / monthly_returns.std()) * (12**0.5)
        if monthly_returns.std() > 0
        else 0.0
    )
    max_dd = df["hodl_drawdown"].min()
    return {
        "n_months": n_months,
        "n_years": round(n_years, 1),
        "start": df.index.min().strftime("%Y-%m"),
        "end": df.index.max().strftime("%Y-%m"),
        "first_close": float(df["close_usd"].iloc[0]),
        "last_close": float(df["close_usd"].iloc[-1]),
        "total_return_pct": float(total_return * 100),
        "cagr_pct": float(cagr * 100),
        "sharpe": float(sharpe),
        "max_dd_pct": float(max_dd * 100),
    }


def _plot_equity(df: pd.DataFrame, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5), dpi=110)
    ax.plot(df.index, df["hodl_equity"], color=BTC_ORANGE, linewidth=1.6, label="HODL")
    ax.set_yscale("log")
    ax.set_title("BTC HODL — equity curve (log)", fontsize=12)
    ax.set_ylabel("Equity (base 100)")
    ax.grid(True, which="both", alpha=0.25)
    ax.legend(loc="upper left", frameon=False)
    fig.tight_layout()
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def _plot_drawdown(df: pd.DataFrame, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 3.4), dpi=110)
    dd_pct = df["hodl_drawdown"] * 100
    ax.fill_between(df.index, dd_pct, 0, color=DD_RED, alpha=0.65, linewidth=0)
    ax.set_title("BTC HODL — drawdown (%)", fontsize=12)
    ax.set_ylabel("Drawdown (%)")
    ax.grid(True, alpha=0.25)
    ax.set_ylim(top=2)
    fig.tight_layout()
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


def _plot_yearly_returns(df: pd.DataFrame, output: Path) -> None:
    yearly = df["hodl_equity"].resample("YE").last().pct_change().dropna() * 100
    fig, ax = plt.subplots(figsize=(10, 3.6), dpi=110)
    colors = [BTC_ORANGE if r >= 0 else DD_RED for r in yearly]
    ax.bar(yearly.index.year, yearly.values, color=colors, edgecolor="none")
    ax.axhline(0, color="#444", linewidth=0.7)
    ax.set_title("BTC HODL — return annuel (%)", fontsize=12)
    ax.set_ylabel("Return annuel (%)")
    ax.grid(True, alpha=0.2, axis="y")
    fig.tight_layout()
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>BTC dashboard — prototype</title>
<style>
  :root {{
    --bg: #1a1a1a; --panel: #242424; --text: #e8e8e8; --muted: #888;
    --orange: #f7931a; --red: #e74c3c; --green: #27ae60; --border: #333;
  }}
  * {{ box-sizing: border-box; }}
  body {{ background: var(--bg); color: var(--text);
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
          margin: 0; padding: 2rem 1.5rem; max-width: 1200px; margin: 0 auto; line-height: 1.5; }}
  h1 {{ color: var(--orange); font-weight: 500; border-bottom: 1px solid var(--border);
        padding-bottom: 0.5rem; margin-top: 0; }}
  h2 {{ color: var(--orange); font-weight: 500; margin-top: 2.5rem; }}
  .meta {{ color: var(--muted); font-size: 0.85rem; }}
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
            gap: 0.8rem; margin: 1.5rem 0; }}
  .stat {{ background: var(--panel); padding: 1rem; border-radius: 6px;
           border-left: 3px solid var(--orange); }}
  .stat .label {{ color: var(--muted); font-size: 0.75rem; text-transform: uppercase;
                  letter-spacing: 0.06em; }}
  .stat .value {{ font-size: 1.5rem; font-weight: 600; color: #fff; margin-top: 0.3rem; }}
  .stat.dd .value {{ color: var(--red); }}
  img {{ max-width: 100%; height: auto; background: white; border-radius: 4px;
         margin: 0.5rem 0 1.5rem; display: block; }}
  table {{ width: 100%; border-collapse: collapse; margin-top: 0.5rem; font-size: 0.9rem; }}
  th, td {{ text-align: left; padding: 0.45rem 0.6rem; border-bottom: 1px solid var(--border); }}
  th {{ color: var(--orange); font-weight: 500; background: var(--panel); }}
  tr:hover td {{ background: var(--panel); }}
  .footer {{ margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border);
             color: var(--muted); font-size: 0.8rem; }}
  .warn {{ background: #2a2010; border-left: 3px solid var(--orange);
           padding: 0.8rem 1rem; border-radius: 4px; margin: 1.5rem 0; }}
</style>
</head>
<body>
<h1>BTC dashboard — prototype</h1>
<p class="meta">Généré le {generated_at} · Données CoinGecko · {n_months} mois ({start} → {end})</p>

<div class="warn">
  <strong>Prototype HODL only.</strong> Les 9 stratégies (R1 TSMOM, R2 Mayer, R3 Power Law
  × O1 Plateau, O2 Walk-fwd, O3 Leave-cycle) n'apparaîtront qu'à la fin de la phase D
  du backtest. Ce dashboard est là pour valider le look-and-feel.
</div>

<div class="stats">
  <div class="stat"><div class="label">CAGR HODL</div><div class="value">{cagr_pct:.1f}%</div></div>
  <div class="stat dd"><div class="label">Max drawdown</div><div class="value">{max_dd_pct:.1f}%</div></div>
  <div class="stat"><div class="label">Sharpe annualisé</div><div class="value">{sharpe:.2f}</div></div>
  <div class="stat"><div class="label">Total return</div><div class="value">×{total_return_x:.0f}</div></div>
  <div class="stat"><div class="label">Premier close</div><div class="value">${first_close:,.0f}</div></div>
  <div class="stat"><div class="label">Dernier close</div><div class="value">${last_close:,.0f}</div></div>
</div>

<h2>Equity curve (log)</h2>
<img src="equity.png" alt="Equity curve HODL">

<h2>Drawdown</h2>
<img src="drawdown.png" alt="Drawdown HODL">

<h2>Return annuel</h2>
<img src="yearly_returns.png" alt="Yearly returns HODL">

<h2>10 dernières observations mensuelles</h2>
{recent_table}

<div class="footer">
  Fichiers générés : <code>dashboard.html</code>, <code>equity.png</code>,
  <code>drawdown.png</code>, <code>yearly_returns.png</code>,
  <code>monthly_hodl.csv</code> · projet
  <a href="https://www.coingecko.com/" style="color:var(--orange)">CoinGecko</a>
</div>
</body>
</html>
"""


def generate(monthly: pd.DataFrame, output_dir: Path) -> dict:
    """Produce HTML, PNGs and CSV. Returns dict of artifact paths."""
    output_dir.mkdir(parents=True, exist_ok=True)

    df = compute_hodl_equity(monthly)
    stats = _summary_stats(df)

    _plot_equity(df, output_dir / "equity.png")
    _plot_drawdown(df, output_dir / "drawdown.png")
    _plot_yearly_returns(df, output_dir / "yearly_returns.png")

    df.to_csv(output_dir / "monthly_hodl.csv")

    recent = (
        df.tail(10)
        .reset_index()
        .assign(date=lambda d: d["date"].dt.strftime("%Y-%m-%d"))
        .assign(
            close_usd=lambda d: d["close_usd"].map(lambda x: f"${x:,.0f}"),
            hodl_equity=lambda d: d["hodl_equity"].map(lambda x: f"{x:,.0f}"),
            hodl_drawdown=lambda d: d["hodl_drawdown"].map(lambda x: f"{x*100:.1f}%"),
            return_1m=lambda d: d["return_1m"].map(lambda x: f"{x*100:+.1f}%"),
        )
    )
    recent_html = recent.to_html(index=False, border=0, classes="recent")

    html = HTML_TEMPLATE.format(
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        recent_table=recent_html,
        total_return_x=stats["total_return_pct"] / 100 + 1,
        **stats,
    )
    (output_dir / "dashboard.html").write_text(html, encoding="utf-8")

    return {
        "html": output_dir / "dashboard.html",
        "equity_png": output_dir / "equity.png",
        "drawdown_png": output_dir / "drawdown.png",
        "yearly_png": output_dir / "yearly_returns.png",
        "csv": output_dir / "monthly_hodl.csv",
        "stats": stats,
    }


def proto_dashboard_main() -> None:
    """CLI entrypoint: load monthly data and generate the prototype dashboard."""
    from chillbtc.data import load_or_fetch

    repo = Path(__file__).resolve().parents[2]
    cache = repo / "data" / "btc_monthly.csv"
    output = repo / "output"

    monthly = load_or_fetch(cache)
    print(
        f"Loaded {len(monthly)} months "
        f"({monthly.index.min().date()} -> {monthly.index.max().date()})"
    )

    artifacts = generate(monthly, output)
    print("\nArtifacts générés :")
    for key, path in artifacts.items():
        if isinstance(path, Path):
            print(f"  {key:14} -> {path}")
    print(f"\nOuvre {artifacts['html']} dans un navigateur pour voir le rendu.")


if __name__ == "__main__":
    proto_dashboard_main()
