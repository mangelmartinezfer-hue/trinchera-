"""
Run the Trinchera strategy across every historic data file.

This script updates DATE in config_trinchera.py for each available
data/historic/time_and_sales_nq_YYYYMMDD.csv file, runs the required pipeline
steps without opening charts, saves one row per date to outputs/backtest_all_trinchera.csv,
and restores the original config when finished.
"""

import re
import subprocess
import sys
from pathlib import Path

import pandas as pd


CURRENT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = CURRENT_DIR / "config_trinchera.py"
DATA_DIR = CURRENT_DIR / "data" / "historic"
OUTPUTS_DIR = CURRENT_DIR / "outputs"
SUMMARY_FILE = OUTPUTS_DIR / "backtest_all_trinchera.csv"


def set_config_date(config_text, date):
    return re.sub(
        r'^DATE\s*=\s*".*?"',
        f'DATE = "{date}"',
        config_text,
        flags=re.MULTILINE,
    )


def run_script(script, *args):
    result = subprocess.run(
        [sys.executable, str(CURRENT_DIR / script), *map(str, args)],
        cwd=str(CURRENT_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())


def summarize_date(date):
    trades_file = OUTPUTS_DIR / f"db_trinchera_TR_{date}.csv"
    bins_file = OUTPUTS_DIR / f"db_trinchera_bins_{date}.csv"
    signals_file = OUTPUTS_DIR / f"db_trinchera_signals_{date}.csv"

    bins = pd.read_csv(bins_file, sep=";", decimal=",") if bins_file.exists() else pd.DataFrame()
    signals = pd.read_csv(signals_file, sep=";", decimal=",") if signals_file.exists() else pd.DataFrame()

    if not trades_file.exists():
        return {
            "date": date,
            "events": len(bins),
            "signals": len(signals),
            "trades": 0,
            "pnl": 0.0,
            "pnl_usd": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "buy_pnl": 0.0,
            "sell_pnl": 0.0,
            "max_loss": 0.0,
        }

    trades = pd.read_csv(trades_file, sep=";", decimal=",")
    if trades.empty:
        return {
            "date": date,
            "events": len(bins),
            "signals": len(signals),
            "trades": 0,
            "pnl": 0.0,
            "pnl_usd": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "buy_pnl": 0.0,
            "sell_pnl": 0.0,
            "max_loss": 0.0,
        }

    winners = trades[trades["pnl"] > 0]
    losers = trades[trades["pnl"] <= 0]
    gross_profit = winners["pnl"].sum()
    gross_loss = abs(losers["pnl"].sum())
    profit_factor = gross_profit / gross_loss if gross_loss else float("inf")

    return {
        "date": date,
        "events": len(bins),
        "signals": len(signals),
        "trades": len(trades),
        "pnl": trades["pnl"].sum(),
        "pnl_usd": trades["pnl_usd"].sum(),
        "win_rate": len(winners) / len(trades) * 100,
        "profit_factor": profit_factor,
        "buy_pnl": trades.loc[trades["direction"] == "BUY", "pnl"].sum(),
        "sell_pnl": trades.loc[trades["direction"] == "SELL", "pnl"].sum(),
        "max_loss": trades["pnl"].min(),
    }


def main():
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(DATA_DIR.glob("time_and_sales_nq_*.csv"))
    dates = [path.stem.rsplit("_", 1)[-1] for path in files]

    original_config = CONFIG_FILE.read_text(encoding="utf-8")
    if SUMMARY_FILE.exists():
        existing = pd.read_csv(SUMMARY_FILE, sep=";", decimal=",")
        rows = existing.to_dict("records")
        completed_dates = set(existing["date"].astype(str))
    else:
        rows = []
        completed_dates = set()

    try:
        for index, date in enumerate(dates, start=1):
            if date in completed_dates:
                print(f"[{index}/{len(dates)}] Skipping {date} (already summarized)", flush=True)
                continue

            print(f"[{index}/{len(dates)}] Backtesting {date}", flush=True)
            CONFIG_FILE.write_text(set_config_date(original_config, date), encoding="utf-8")

            processed_file = OUTPUTS_DIR / f"db_trinchera_all_data_{date}.csv"
            if not processed_file.exists():
                run_script("util_trinchera.py")

            run_script("find_big_volume.py")
            run_script("strat_trinchera.py")
            row = summarize_date(date)
            rows.append(row)
            pd.DataFrame(rows).to_csv(SUMMARY_FILE, index=False, sep=";", decimal=",")
            print(
                f"  trades={row['trades']} pnl={row['pnl']:.2f} "
                f"usd={row['pnl_usd']:.2f} win={row['win_rate']:.1f}%"
                f" saved={SUMMARY_FILE.name}",
                flush=True,
            )
    finally:
        CONFIG_FILE.write_text(original_config, encoding="utf-8")

    summary = pd.DataFrame(rows)
    summary.to_csv(SUMMARY_FILE, index=False, sep=";", decimal=",")

    total_trades = summary["trades"].sum()
    total_pnl = summary["pnl"].sum()
    total_pnl_usd = summary["pnl_usd"].sum()
    weighted_win_rate = (
        (summary["win_rate"] * summary["trades"]).sum() / total_trades
        if total_trades
        else 0
    )

    print("\n" + "=" * 80)
    print("ALL-DATA BACKTEST SUMMARY")
    print("=" * 80)
    print(f"Dates tested: {len(summary)}")
    print(f"Total trades: {total_trades}")
    print(f"Total P&L: {total_pnl:.2f} points (${total_pnl_usd:,.2f})")
    print(f"Weighted win rate: {weighted_win_rate:.1f}%")
    print(f"Best day: {summary.loc[summary['pnl_usd'].idxmax(), 'date']}")
    print(f"Worst day: {summary.loc[summary['pnl_usd'].idxmin(), 'date']}")
    print(f"Saved: {SUMMARY_FILE}")


if __name__ == "__main__":
    main()
