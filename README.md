# Trinchera — Estrategia de Mean Reversion en NQ Futuros

```bash
git clone https://github.com/ferranfont/trinchera.git && cd trinchera && pip install pandas plotly
```

Estrategia avanzada de mean reversion para futuros NQ (Nasdaq-100 E-mini) basada en detección de volumen alto y análisis de perfil de mercado.

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![Licencia](https://img.shields.io/badge/licencia-Propietario-red)](LICENSE)
[![Estado](https://img.shields.io/badge/estado-Activo-success)](https://github.com/ferranfont/trinchera)

---

## Descripción general

La estrategia Trinchera identifica picos de volumen alto (>200 contratos) y crea niveles de mean reversion alrededor del precio de cierre. Opera cuando el precio toca esos niveles extremos (±10 puntos desde el pico de volumen), esperando que el precio revierta hacia la media.

### Características principales

- **Totalmente portable**: Autónomo con carpeta local `utils/` (sin dependencias externas)
- **Pipeline automatizado**: Un solo comando ejecuta todo el flujo de backtest
- **Configuración por fecha**: Parámetro DATE centralizado para procesamiento por lotes
- **Visualizaciones interactivas**: Gráficos HTML con Plotly mostrando operaciones, equity y rendimiento
- **Análisis de perfil de mercado**: Perfil de volumen rolling con precisión de 1 segundo
- **Sistema de filtros múltiples**: SMA, Horario, GRID, Stop Trailing
- **Informes detallados**: Métricas de rendimiento y análisis de riesgo completos

---

## Inicio rápido

### 1. Configurar la fecha

Edita `config_trinchera.py`:

```python
DATE = "20251104"  # Fecha del archivo time_and_sales_nq_{DATE}.csv
```

### 2. Añadir datos

Coloca el archivo de tick data en:
```
data/historic/time_and_sales_nq_20251104.csv
```

### 3. Ejecutar el pipeline

```bash
python main_trinchera.py
```

Esto hace automáticamente:
- Comprueba si los datos están procesados (ejecuta `util_trinchera.py` si es necesario)
- Detecta eventos de volumen alto
- Ejecuta la estrategia de trading
- Genera gráficos interactivos
- Crea informes resumen

---

## Lógica de la estrategia

### 1. Detección de volumen alto

Identifica barras donde `total_volume > BIG_VOLUME_TRIGGER` (por defecto: 200 contratos)

### 2. Niveles de mean reversion

Calcula niveles alrededor del precio de cierre del volumen alto:
- **Nivel superior** (ROJO): `precio_cierre + MEAN_REVERS_EXPAND` → zona de VENTA
- **Nivel inferior** (VERDE): `precio_cierre - MEAN_REVERS_EXPAND` → zona de COMPRA

### 3. Ejecución de operaciones

- **Señal VENTA**: El precio toca la línea roja → se espera bajada
- **Señal COMPRA**: El precio toca la línea verde → se espera subida

### 4. Gestión de riesgo

- **Take Profit**: 5 puntos ($100)
- **Stop Loss**: 9 puntos ($180)
- **Timeout**: Los niveles expiran tras la duración configurada

---

## Estructura del proyecto

```
trinchera_strategy/
├── README.md                          # Este archivo
├── config_trinchera.py               # Configuración centralizada (DATE, TP/SL, filtros)
├── main_trinchera.py                 # Orquestador principal del pipeline
│
├── utils/                            # Utilidades portables (autónomas)
│   ├── __init__.py
│   ├── rolling_profile.py           # Calculadora de Perfil de Mercado
│   ├── tick.py                      # Estructura de datos de tick
│   └── parse_utils.py               # Parsers de timestamp y número
│
├── util_trinchera.py                # PASO 0: Procesador Tick → Frame
├── find_big_volume.py               # PASO 1: Detector de volumen alto
├── strat_trinchera.py               # PASO 2: Estrategia de trading
├── plot_trinchera_trades.py         # PASO 3: Visualización de operaciones
├── summary_trinchera.py             # PASO 4: Informe resumen
└── plot_equity_trinchera.py         # PASO 5: Curva de equity
│
├── data/                            # Datos de entrada
│   └── historic/
│       └── time_and_sales_nq_{DATE}.csv
│
├── outputs/                         # Datos procesados
│   ├── db_trinchera_all_data_{DATE}.csv    # OHLCV + Perfil de Mercado
│   ├── db_trinchera_bins_{DATE}.csv        # Eventos de volumen alto
│   └── db_trinchera_TR_{DATE}.csv          # Operaciones ejecutadas
│
└── charts/                          # Visualizaciones HTML
    ├── chart_trinchera_trades_{DATE}.html  # Marcadores de operaciones
    ├── summary_trinchera_{DATE}.html       # Métricas de rendimiento
    └── equity_trinchera_{DATE}.html        # Curva de equity
```

---

## Instalación

### Requisitos previos

```bash
pip install pandas plotly
```

### Clonar el repositorio

```bash
git clone https://github.com/ferranfont/trinchera.git
cd trinchera
```

---

## Configuración

### Parámetro DATE (IMPORTANTE)

**El parámetro `DATE` es el ÚNICO lugar donde se especifica la fecha a procesar.**

Todos los scripts usan automáticamente este DATE centralizado:
- `util_trinchera.py` → busca `time_and_sales_nq_{DATE}.csv`
- `find_big_volume.py` → carga y crea archivos con `{DATE}`
- `strat_trinchera.py` → carga bins y datos con DATE
- `plot_trinchera_trades.py` → carga todos los archivos con DATE
- `summary_trinchera.py` → incluye DATE en el título HTML
- `plot_equity_trinchera.py` → carga operaciones con DATE

**Importante**: NUNCA escribas fechas fijas en los scripts individuales. Siempre importa y usa `DATE` desde `config_trinchera.py`.

### Parámetros principales (`config_trinchera.py`)

```python
# ============================================================================
# FUENTE DE DATOS
# ============================================================================
DATE = "20251104"  # Fecha del archivo time_and_sales_nq_{DATE}.csv

# ============================================================================
# DETECCIÓN DE VOLUMEN ALTO
# ============================================================================
BIG_VOLUME_TRIGGER = 200           # Volumen mínimo a detectar (contratos)
BIG_VOLUME_TIMEOUT = 10            # Duración del efecto de volumen alto (minutos)

# ============================================================================
# PARÁMETROS DE TRADING
# ============================================================================
TP_POINTS = 5.0                    # Take profit (puntos) → $100
SL_POINTS = 9.0                    # Stop loss (puntos) → $180
MEAN_REVERS_EXPAND = 10            # Distancia desde precio de cierre (puntos)
MEAN_REVERSE_TIMEOUT_ORDER = 3    # Timeout de mean reversion (minutos)

# ============================================================================
# FILTROS
# ============================================================================
FILTER_BY_SMA = False              # Activar filtro direccional SMA-200
FILTER_TIME_OF_DAY = False         # Activar filtro horario
FILTER_USE_GRID = False            # Activar segunda entrada (sistema GRID)

# ============================================================================
# FUNCIONES AVANZADAS
# ============================================================================
# Stop Trailing con SMA
SMA_TRAILING_STOP = False          # Stop trailing dinámico (desactiva TP fijo)
TRAILING_STOP_ATR_MULT = 0.75      # Distancia desde precio extremo (puntos)

# Híbrido Cash & Trail
SMA_CASH_TRAILING_ENABLED = False  # Híbrido: SL fijo → Trailing tras beneficio
SMA_CASH_TRAILING = 25.0           # Umbral de activación (puntos a favor)
SMA_CASH_TRAILING_DISTANCE = 10.0  # Distancia trailing tras activación

# Sistema GRID (Segunda Entrada)
GRID_MEAN_REVERS_EXPAND = 5.0      # Distancia adicional para 2ª entrada
GRID_TP_POINTS = 4.0               # TP desde precio medio de entrada
GRID_SL_POINTS = 3.0               # SL más allá de la segunda entrada
```

---

## Formato de datos

### Archivo de entrada

**Ubicación**: `data/historic/time_and_sales_nq_{DATE}.csv`

**Formato** (CSV europeo):
```csv
Timestamp;Precio;Volumen;Lado
2025-11-04 06:00:00.404;20425.25;1;BID
2025-11-04 06:00:00.512;20425.50;2;ASK
```

**Requisitos**:
- Separador: `;` (punto y coma)
- Decimal: `,` (coma)
- Columnas: `Timestamp`, `Precio`, `Volumen`, `Lado`
- Valores de `Lado`: `"BID"` o `"ASK"`

---

## Ejecución del pipeline

### Modo automático (recomendado)

```bash
python main_trinchera.py
```

**Pasos ejecutados**:
1. Comprueba si existe `db_trinchera_all_data_{DATE}.csv`
2. Si no existe → ejecuta `util_trinchera.py` automáticamente
3. Detecta eventos de volumen alto → `db_trinchera_bins_{DATE}.csv`
4. Ejecuta estrategia → `db_trinchera_TR_{DATE}.csv`
5. Genera gráfico de operaciones → `chart_trinchera_trades_{DATE}.html`
6. Genera resumen → `summary_trinchera_{DATE}.html`
7. Genera curva de equity → `equity_trinchera_{DATE}.html`

### Modo manual (paso a paso)

```bash
# PASO 0: Procesar tick data (ejecutar una vez por fecha)
python util_trinchera.py

# PASO 1: Detectar volumen alto
python find_big_volume.py

# PASO 2: Ejecutar estrategia
python strat_trinchera.py

# PASO 3: Generar gráfico de operaciones
python plot_trinchera_trades.py

# PASO 4: Generar resumen
python summary_trinchera.py

# PASO 5: Generar curva de equity
python plot_equity_trinchera.py
```

---

## Archivos de salida

### Datos procesados (`outputs/`)

| Archivo | Descripción | Tamaño (típico) |
|---------|-------------|-----------------|
| `db_trinchera_all_data_{DATE}.csv` | OHLCV de 1 segundo + Perfil de Mercado | ~10-15 MB |
| `db_trinchera_bins_{DATE}.csv` | Eventos de volumen alto con niveles | ~6-30 KB |
| `db_trinchera_TR_{DATE}.csv` | Operaciones ejecutadas con P&L | ~4-30 KB |

### Gráficos HTML (`charts/`)

| Archivo | Descripción | Características |
|---------|-------------|-----------------|
| `chart_trinchera_trades_{DATE}.html` | Visualización de operaciones | Marcadores interactivos, niveles, volumen |
| `summary_trinchera_{DATE}.html` | Informe de rendimiento | Tabla de métricas con fecha en cabecera |
| `equity_trinchera_{DATE}.html` | Curva de equity | Gráfico 3 paneles (equity, P&L, drawdown) |

---

## Métricas de rendimiento

### Resultados típicos (backtest 1 día)

```
Total operaciones: 95
Tasa de acierto:   78.9%
P&L total:         +$3.900 (195 puntos)
Factor de beneficio: 2.08
Drawdown máximo:   -$1.420

Ganadoras: 75 operaciones (media: +$100)
Perdedoras: 20 operaciones (media: -$180)

Operaciones COMPRA: 44 (46.3%) → +$1.600
Operaciones VENTA:  51 (53.7%) → +$2.300
```

### Velocidad de procesamiento

- **Procesamiento de ticks**: ~193K ticks → ~61K frames en 2-3 minutos
- **Detección de volumen alto**: ~61K frames → ~22-103 eventos en <10 segundos
- **Backtest de estrategia**: ~22-103 eventos → ~20-95 operaciones en <30 segundos
- **Generación de gráficos**: 3 archivos HTML en <20 segundos
- **Pipeline completo**: 3-4 minutos de principio a fin

---

## Funciones avanzadas

### Filtro SMA

```python
FILTER_BY_SMA = True
```

**Lógica**:
- Precio < SMA-200 → SOLO órdenes de VENTA
- Precio > SMA-200 → SOLO órdenes de COMPRA

### Filtro horario

```python
FILTER_TIME_OF_DAY = True
START_TRADING_TIME = "18:50:00"
END_TRADING_TIME = "22:50:00"
```

**Lógica**: Solo opera dentro del horario especificado

### Sistema GRID (Segunda entrada)

```python
FILTER_USE_GRID = True
GRID_MEAN_REVERS_EXPAND = 5.0
```

**Lógica**:
- 1ª entrada: `MEAN_REVERS_EXPAND` (10 pts)
- 2ª entrada: `MEAN_REVERS_EXPAND + GRID_MEAN_REVERS_EXPAND` (15 pts)
- TP/SL calculados desde precio medio de entrada

### Stop Trailing

```python
SMA_TRAILING_STOP = True
TRAILING_STOP_ATR_MULT = 0.75
```

**Lógica**:
- **Desactiva** el TP fijo (deja correr los beneficios)
- LARGO: SL = `precio_máximo - TRAILING_STOP_ATR_MULT` (solo sube)
- CORTO: SL = `precio_mínimo + TRAILING_STOP_ATR_MULT` (solo baja)

---

## Solución de problemas

### Error: No se encuentra el archivo de datos

```
FileNotFoundError: Data file not found: db_trinchera_all_data_20251104.csv
```

**Solución**:
```bash
# main_trinchera.py ejecuta util_trinchera.py automáticamente si falta
python main_trinchera.py
```

### Error: No se detectan eventos de volumen alto

**Solución**: Bajar el umbral de volumen
```python
BIG_VOLUME_TRIGGER = 150  # Bajar desde 200
```

### Error: No se ejecutan operaciones

**Solución**: Aumentar la distancia de mean reversion
```python
MEAN_REVERS_EXPAND = 15  # Aumentar desde 10
```

### Error: Los gráficos no se abren

**Solución**: Abrirlos manualmente desde la carpeta `charts/`
```bash
# Windows
explorer charts\chart_trinchera_trades_20251104.html
```

### Error: Desalineación del eje X en gráficos

**Síntoma**: El gráfico muestra datos de dos fechas distintas en el mismo eje X

**Causa**: Distintas fuentes de datos cargando desde fechas diferentes

**Solución**: Asegúrate de que todos los scripts usan `DATE` de `config_trinchera.py`:
```python
# Correcto (usa DATE de config)
BINS_FILE = OUTPUTS_DIR / f"db_trinchera_bins_{DATE}.csv"

# Incorrecto (busca el archivo más reciente — puede cargar fecha incorrecta)
bins_files = sorted(OUTPUTS_DIR.glob("db_trinchera_bins_*.csv"))
BINS_FILE = bins_files[-1]
```

---

## Procesamiento por lotes de múltiples fechas

```python
# batch_process.py
from pathlib import Path
import subprocess

fechas = ["20251103", "20251104", "20251105"]

for fecha in fechas:
    config = Path("config_trinchera.py").read_text()
    config = config.replace(f'DATE = "{fechas[0]}"', f'DATE = "{fecha}"')
    Path("config_trinchera.py").write_text(config)
    subprocess.run(["python", "main_trinchera.py"])
```

---

## Optimización de la estrategia

### Sensibilidad de parámetros

| Parámetro | Efecto | Recomendación |
|-----------|--------|---------------|
| `BIG_VOLUME_TRIGGER` | Más bajo = más operaciones | Empieza en 200, prueba 150-300 |
| `MEAN_REVERS_EXPAND` | Más alto = más toques | Prueba 8-15 puntos |
| `TP_POINTS` | Más alto = mejor ratio R:R | Prueba 4-10 puntos |
| `SL_POINTS` | Más bajo = menos riesgo | Prueba 7-12 puntos |

### Flujo de optimización

1. Ejecuta la línea base con parámetros por defecto
2. Modifica UN parámetro a la vez
3. Compara métricas (Factor de beneficio, Sharpe, Drawdown)
4. Documenta resultados en `optimization_log.csv`

---

## Licencia

Propietario — Solo uso interno

---

## Soporte

Para preguntas o problemas:
1. Consulta la sección [Solución de problemas](#solución-de-problemas)
2. Revisa los comentarios en los archivos Python
3. Contacto: [GitHub Issues](https://github.com/ferranfont/trinchera/issues)

---

**Versión**: 2.0
**Última actualización**: 2025-11-22
**Estado**: Listo para producción

**Mejoras clave en v2.0**:
- Totalmente portable con carpeta local `utils/`
- Configuración DATE centralizada (todos los archivos usan config_trinchera.py)
- Procesamiento automático de datos en el pipeline
- Fecha mostrada en todos los títulos HTML y nombres de archivo
- Autónomo (sin dependencias externas)
- Alineación de eje X corregida en gráficos
- Código de filtro horario unificado en config
