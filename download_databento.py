"""
Descarga tick data de NQ futuros desde Databento y lo convierte
al formato que espera util_trinchera.py:

    data/historic/time_and_sales_nq_{YYYYMMDD}.csv
    Columnas: Timestamp;Precio;Volumen;Lado
    Separador: ;  Decimal: ,

Uso:
    python download_databento.py

Configuracion:
    Edita las variables de la seccion CONFIGURACION antes de ejecutar.
"""

import subprocess
import sys

# ── Instalar databento si no está disponible ──────────────────────────────────
try:
    import databento as db
except ModuleNotFoundError:
    print("[INFO] Instalando databento...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "databento"])
    import databento as db

import pandas as pd
from datetime import date, timedelta
from pathlib import Path
import time

# ============================================================================
# CONFIGURACION — edita aqui
# ============================================================================
DATABENTO_API_KEY = "TU_API_KEY_AQUI"   # <-- bloqueado, ver portal Databento

DATE_START = date(2025, 1, 2)           # primer dia a descargar
DATE_END   = date(2025, 6, 30)          # ultimo dia a descargar (inclusive)

DATASET   = "GLBX.MDP3"                 # CME Globex MDP 3.0
SYMBOL    = "NQ.v.0"                    # frente continuo NQ, precios reales sin ajustar
SCHEMA    = "trades"                    # ticks individuales (time & sales)
# ============================================================================

CURRENT_DIR  = Path(__file__).resolve().parent
OUTPUT_DIR   = CURRENT_DIR / "data" / "historic"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Mapeo de lado Databento → formato Trinchera
# A = Ask side (agressor comprador) → ASK
# B = Bid side (agressor vendedor) → BID
# N = ninguno → lo dejamos como BID por defecto
SIDE_MAP = {"A": "ASK", "B": "BID", "N": "BID"}


def date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def download_day(client: db.Historical, day: date) -> int:
    """Descarga los ticks de un dia. Devuelve numero de ticks guardados."""
    output_path = OUTPUT_DIR / f"time_and_sales_nq_{day.strftime('%Y%m%d')}.csv"

    if output_path.exists():
        print(f"  [SKIP] {day} — ya existe {output_path.name}")
        return 0

    # Databento usa rangos semiabiertos [start, end)
    ts_start = f"{day}T00:00:00"
    ts_end   = f"{day + timedelta(days=1)}T00:00:00"

    try:
        data = client.timeseries.get_range(
            dataset=DATASET,
            symbols=[SYMBOL],
            stype_in="continuous",
            schema=SCHEMA,
            start=ts_start,
            end=ts_end,
        )
    except Exception as e:
        print(f"  [WARN] {day} — error al descargar: {e}")
        return 0

    df = data.to_df()

    if df.empty:
        print(f"  [SKIP] {day} — sin datos (festivo o mercado cerrado)")
        return 0

    # ── Convertir al formato Trinchera ────────────────────────────────────────
    # ts_event en Databento = nanosegundos desde epoch UTC → datetime
    df["Timestamp"] = pd.to_datetime(df["ts_event"], unit="ns", utc=True)
    df["Timestamp"] = df["Timestamp"].dt.tz_convert("UTC").dt.tz_localize(None)
    df["Timestamp"] = df["Timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S.%f")

    # Precio: la librería databento ya convierte a float con el scale correcto
    df["Precio"] = df["price"].round(2)

    # Volumen
    df["Volumen"] = df["size"].astype(int)

    # Lado
    df["Lado"] = df["side"].map(SIDE_MAP).fillna("BID")

    # Solo columnas necesarias, orden correcto
    out = df[["Timestamp", "Precio", "Volumen", "Lado"]].copy()

    # Guardar con separador ; y decimal ,
    out.to_csv(
        output_path,
        sep=";",
        decimal=",",
        index=False,
        encoding="utf-8",
    )

    n = len(out)
    print(f"  [OK]   {day} - {n:,} ticks -> {output_path.name}")
    return n


def main():
    print("=" * 70)
    print("TRINCHERA - Descarga de tick data desde Databento")
    print("=" * 70)
    print(f"Dataset : {DATASET}")
    print(f"Simbolo : {SYMBOL}")
    print(f"Periodo : {DATE_START} -> {DATE_END}")
    print(f"Destino : {OUTPUT_DIR}")
    print()

    if DATABENTO_API_KEY == "TU_API_KEY_AQUI":
        print("[ERROR] Edita DATABENTO_API_KEY en este script antes de ejecutar.")
        sys.exit(1)

    client = db.Historical(DATABENTO_API_KEY)

    # Estimar coste antes de descargar
    try:
        cost = client.metadata.get_cost(
            dataset=DATASET,
            symbols=[SYMBOL],
            stype_in="continuous",
            schema=SCHEMA,
            start=str(DATE_START),
            end=str(DATE_END + timedelta(days=1)),
        )
        print(f"[INFO] Coste estimado: ${cost:.4f} USD")
    except Exception as e:
        print(f"[WARN] No se pudo estimar el coste: {e}")

    print()
    total_ticks = 0
    days_downloaded = 0

    for day in date_range(DATE_START, DATE_END):
        # Saltar fines de semana (NQ no opera Sat/Sun)
        if day.weekday() >= 5:
            continue

        ticks = download_day(client, day)
        if ticks > 0:
            total_ticks += ticks
            days_downloaded += 1
            time.sleep(0.3)  # respetar rate limit de Databento

    print()
    print("=" * 70)
    print(f"Descarga completa: {days_downloaded} dias, {total_ticks:,} ticks totales")
    print(f"Archivos en: {OUTPUT_DIR}")
    print()
    print("Siguiente paso: ejecuta el backtest completo con:")
    print("  python backtest_all_trinchera.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
