# Continuar despues

Estado guardado antes de cerrar el ordenador.

## Cambios implementados

- `config_trinchera.py`
  - Parametros de realismo del backtest:
    - `COMMISSION_PER_TRADE_USD`
    - `SLIPPAGE_POINTS`
    - `INTRABAR_POLICY`
    - `AVOID_OVERLAPPING_TRADES`
    - `LIMIT_EXIT_TO_SIGNAL_TIMEOUT`
  - Trigger de volumen relativo opcional:
    - `USE_RELATIVE_VOLUME_TRIGGER`
    - `RELATIVE_VOLUME_WINDOW`
    - `RELATIVE_VOLUME_MULTIPLIER`

- `find_big_volume.py`
  - Soporta trigger fijo o volumen relativo rolling.

- `strat_trinchera.py`
  - Descuenta comision y slippage.
  - Evita trades solapados si esta activado.
  - Limita la salida al timeout si esta activado.
  - Aplica politica conservadora cuando TP y SL se tocan en la misma vela.
  - Guarda auditoria de senales en `outputs/db_trinchera_signals_{DATE}.csv`.

- `summary_trinchera.py`
  - Muestra PnL bruto, costes, PnL neto y salidas por timeout.
  - Genera desglose en `outputs/db_trinchera_breakdown_{DATE}.csv`.

- `optimize_trinchera.py`
  - Prueba una grid basica de parametros y guarda resultados en `outputs/optimization_trinchera_{DATE}.csv`.

- `backtest_all_trinchera.py`
  - Ejecuta la estrategia sobre todos los CSV historicos.
  - Guarda avance incremental en `outputs/backtest_all_trinchera.csv`.
  - Restaura `config_trinchera.py` al terminar si no se interrumpe.

- `plot_backtest_all_trinchera.py`
  - Genera el dashboard agregado `charts/backtest_all_trinchera_report.html`.

## Estado actual

- No habia procesos `python` activos al guardar esta nota.
- `config_trinchera.py` apunta actualmente a:

```python
DATE = "20251016"
```

- Backtest agregado parcial guardado:

```text
outputs/backtest_all_trinchera.csv
```

- Informe HTML agregado generado:

```text
charts/backtest_all_trinchera_report.html
```

## Resultado parcial del backtest agregado

El CSV parcial contiene 21 fechas testeadas:

```text
20250915 a 20251013
```

Resumen calculado:

```text
Trades: 167
Eventos: 880
Senales: 294
PnL neto: +401.50 puntos
PnL neto USD: +$7,362.00
Winrate ponderado: 81.44%
Dias positivos: 19
Dias negativos: 2
BUY: +45.75 puntos
SELL: +355.75 puntos
```

## Para continuar

Desde la carpeta del proyecto:

```powershell
cd C:\Users\kakatua\OneDrive\Escritorio\ESTRATEGUIAS\trinchera-main2\trinchera-main
```

Para continuar el backtest completo:

```powershell
python -u backtest_all_trinchera.py
```

El script salta las fechas ya guardadas en `outputs/backtest_all_trinchera.csv`.

Para regenerar el dashboard:

```powershell
python plot_backtest_all_trinchera.py
```

Abrir informe:

```text
charts/backtest_all_trinchera_report.html
```
