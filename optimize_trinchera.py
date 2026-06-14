"""
Basic parameter optimizer for the Trinchera strategy.

It tests a small grid on the current DATE from config_trinchera.py, writes
outputs/optimization_trinchera_{DATE}.csv, and restores config_trinchera.py
when finished.
"""

import itertools
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd

from config_trinchera import DATE


CURRENT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = CURRENT_DIR / "config_trinchera.py"
OUTPUTS_DIR = CURRENT_DIR / "outputs"
RESULTS_FILE = OUTPUTS_DIR / f"optimization_trinchera_{DATE}.csv"

PARAM_GRID = {
    "BIG_VOLUME_TRIGGER": [200, 250, 300],
    "TP_POINTS": [4.0, 5.0, 6.0],
    "SL_POINTS": [7.0, 9.0, 11.0],
    "MEAN_REVERS_EXPAND": [8, 10, 12],
}


def update_config(original_text, params):
    updated = original_text
    for name, value in params.items():
        if isinstance(value, str):
            replacement = f'{name} = "{value}"'
        else:
            replacement = f"{name} = {value}"
        pattern = rf"^{name}\s*=\s*.+$"
        updated = re.sub(pattern, replacement, updated, flags=re.MULTILINE)
    return updated


def run_step(script, *args):
    result = subprocess.run(
        [sys.executable, str(CURRENT_DIR / script), *map(str, args)],
        cwd=str(CURRENT_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())


def evaluate_trades(params):
    trades_file = OUTPUTS_DIR / f"db_trinchera_TR_{DATE}.csv"
    if not trades_file.exists():
        return {**params, "trades": 0, "pnl": 0, "pnl_usd": 0, "win_rate": 0, "profit_factor": 0}

    df = pd.read_csv(trades_file, sep=";", decimal=",")
    if len(df) == 0:
        return {**params, "trades": 0, "pnl": 0, "pnl_usd": 0, "win_rate": 0, "profit_factor": 0}

    winners = df[df["pnl"] > 0]
    losers = df[df["pnl"] <= 0]
    gross_profit = winners["pnl"].sum()
    gross_loss = abs(losers["pnl"].sum())
    profit_factor = gross_profit / gross_loss if gross_loss else float("inf")

    return {
        **params,
        "trades": len(df),
        "pnl": df["pnl"].sum(),
        "pnl_usd": df["pnl_usd"].sum(),
        "win_rate": len(winners) / len(df) * 100,
        "profit_factor": profit_factor,
        "max_loss": df["pnl"].min(),
    }


def main():
    original_config = CONFIG_FILE.read_text(encoding="utf-8")
    results = []

    keys = list(PARAM_GRID.keys())
    combos = [dict(zip(keys, values)) for values in itertools.product(*(PARAM_GRID[k] for k in keys))]

    try:
        for i, params in enumerate(combos, start=1):
            print(f"[{i}/{len(combos)}] Testing {params}")
            CONFIG_FILE.write_text(update_config(original_config, params), encoding="utf-8")
            run_step("find_big_volume.py", params["BIG_VOLUME_TRIGGER"])
            run_step("strat_trinchera.py")
            results.append(evaluate_trades(params))
    finally:
        CONFIG_FILE.write_text(original_config, encoding="utf-8")

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values(["profit_factor", "pnl_usd"], ascending=[False, False])
    df_results.to_csv(RESULTS_FILE, index=False, sep=";", decimal=",")

    print(f"\n[OK] Optimization saved to: {RESULTS_FILE}")
    print(df_results.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
