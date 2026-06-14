"""
Generate an aggregate HTML dashboard for outputs/backtest_all_trinchera.csv.
"""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


CURRENT_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = CURRENT_DIR / "outputs"
CHARTS_DIR = CURRENT_DIR / "charts"
INPUT_FILE = OUTPUTS_DIR / "backtest_all_trinchera.csv"
OUTPUT_FILE = CHARTS_DIR / "backtest_all_trinchera_report.html"


def money(value):
    return f"${value:,.2f}"


def number(value):
    return f"{value:,.2f}"


def main():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Backtest summary not found: {INPUT_FILE}")

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT_FILE, sep=";", decimal=",")
    df["date"] = df["date"].astype(str)
    df["equity_usd"] = df["pnl_usd"].cumsum()
    df["equity_points"] = df["pnl"].cumsum()
    df["running_max_usd"] = df["equity_usd"].cummax()
    df["drawdown_usd"] = df["equity_usd"] - df["running_max_usd"]

    total_trades = int(df["trades"].sum())
    total_events = int(df["events"].sum())
    total_signals = int(df["signals"].sum())
    total_pnl = df["pnl"].sum()
    total_pnl_usd = df["pnl_usd"].sum()
    avg_daily_usd = df["pnl_usd"].mean()
    median_daily_usd = df["pnl_usd"].median()
    positive_days = int((df["pnl_usd"] > 0).sum())
    negative_days = int((df["pnl_usd"] <= 0).sum())
    weighted_win_rate = (df["win_rate"] * df["trades"]).sum() / total_trades if total_trades else 0
    max_drawdown = df["drawdown_usd"].min()
    buy_pnl = df["buy_pnl"].sum()
    sell_pnl = df["sell_pnl"].sum()

    fig = make_subplots(
        rows=3,
        cols=2,
        subplot_titles=(
            "Equity Curve USD",
            "Daily P&L USD",
            "Drawdown USD",
            "Trades Per Day",
            "BUY vs SELL Points",
            "Win Rate by Day",
        ),
        specs=[
            [{"type": "scatter"}, {"type": "bar"}],
            [{"type": "scatter"}, {"type": "bar"}],
            [{"type": "bar"}, {"type": "bar"}],
        ],
        vertical_spacing=0.12,
    )

    fig.add_trace(go.Scatter(x=df["date"], y=df["equity_usd"], mode="lines+markers", name="Equity"), row=1, col=1)
    fig.add_trace(go.Bar(x=df["date"], y=df["pnl_usd"], name="Daily P&L"), row=1, col=2)
    fig.add_trace(go.Scatter(x=df["date"], y=df["drawdown_usd"], mode="lines+markers", name="Drawdown"), row=2, col=1)
    fig.add_trace(go.Bar(x=df["date"], y=df["trades"], name="Trades"), row=2, col=2)
    fig.add_trace(go.Bar(x=["BUY", "SELL"], y=[buy_pnl, sell_pnl], name="Direction P&L"), row=3, col=1)
    fig.add_trace(go.Bar(x=df["date"], y=df["win_rate"], name="Win Rate"), row=3, col=2)

    fig.update_layout(
        height=1150,
        title="Trinchera Aggregate Backtest Report",
        showlegend=False,
        template="plotly_white",
        margin=dict(l=50, r=30, t=80, b=50),
    )
    fig.update_xaxes(tickangle=45)

    best = df.sort_values("pnl_usd", ascending=False).head(5)
    worst = df.sort_values("pnl_usd", ascending=True).head(5)

    def table_html(data):
        cols = ["date", "events", "signals", "trades", "pnl", "pnl_usd", "win_rate", "buy_pnl", "sell_pnl"]
        out = ["<table>", "<thead><tr>"]
        out.extend(f"<th>{col}</th>" for col in cols)
        out.append("</tr></thead><tbody>")
        for _, row in data[cols].iterrows():
            out.append("<tr>")
            for col in cols:
                value = row[col]
                if col == "pnl_usd":
                    value = money(value)
                elif col in {"pnl", "win_rate", "buy_pnl", "sell_pnl"}:
                    value = number(value)
                out.append(f"<td>{value}</td>")
            out.append("</tr>")
        out.append("</tbody></table>")
        return "".join(out)

    html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Trinchera Backtest All Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f6f7f8; color: #151515; }}
    .wrap {{ max-width: 1280px; margin: 0 auto; }}
    .header, .card {{ background: white; border: 1px solid #e3e5e8; border-radius: 6px; padding: 18px; margin-bottom: 16px; }}
    h1 {{ margin: 0 0 8px; font-size: 26px; }}
    h2 {{ margin: 0 0 12px; font-size: 18px; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }}
    .metric {{ background: #f9fafb; border: 1px solid #e4e7eb; border-radius: 4px; padding: 12px; }}
    .metric span {{ display: block; color: #666; font-size: 12px; }}
    .metric strong {{ display: block; margin-top: 6px; font-size: 20px; }}
    .positive {{ color: #16803c; }}
    .negative {{ color: #b42318; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border-bottom: 1px solid #eee; padding: 8px; text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
    th {{ background: #f2f4f7; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <h1>Trinchera Backtest Agregado</h1>
      <p>Basado en {len(df)} fechas procesadas desde <code>{INPUT_FILE.name}</code>.</p>
      <div class="grid">
        <div class="metric"><span>Trades</span><strong>{total_trades}</strong></div>
        <div class="metric"><span>Eventos / Señales</span><strong>{total_events} / {total_signals}</strong></div>
        <div class="metric"><span>P&L Neto</span><strong class="{'positive' if total_pnl_usd >= 0 else 'negative'}">{money(total_pnl_usd)}</strong></div>
        <div class="metric"><span>Puntos</span><strong>{number(total_pnl)}</strong></div>
        <div class="metric"><span>Winrate Ponderado</span><strong>{weighted_win_rate:.2f}%</strong></div>
        <div class="metric"><span>Días Positivos / Negativos</span><strong>{positive_days} / {negative_days}</strong></div>
        <div class="metric"><span>Media Diaria</span><strong>{money(avg_daily_usd)}</strong></div>
        <div class="metric"><span>Max Drawdown</span><strong class="negative">{money(max_drawdown)}</strong></div>
      </div>
    </div>

    <div class="card">
      {fig.to_html(full_html=False, include_plotlyjs="cdn")}
    </div>

    <div class="card">
      <h2>Mejores días</h2>
      {table_html(best)}
    </div>

    <div class="card">
      <h2>Peores días</h2>
      {table_html(worst)}
    </div>
  </div>
</body>
</html>
"""

    OUTPUT_FILE.write_text(html, encoding="utf-8")
    print(f"[OK] Report saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
