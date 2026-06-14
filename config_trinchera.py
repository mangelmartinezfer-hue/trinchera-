"""
Trinchera Configuration
Shared configuration for all trinchera scripts
"""

# ============================================================================
# DATA SOURCE
# ============================================================================
DATE = "20251104"  # Date for time_and_sales_nq_{DATE}.csv file

# ============================================================================
# BIG VOLUME DETECTION
# ============================================================================
BIG_VOLUME_TRIGGER = 250  # Minimum volume to detect as "big volume"
BIG_VOLUME_TIMEOUT = 10   # Timeout in minutes for big volume effect
USE_RELATIVE_VOLUME_TRIGGER = False  # Use rolling volume filter instead of fixed trigger
RELATIVE_VOLUME_WINDOW = 200         # Rolling bars used to calculate average volume
RELATIVE_VOLUME_MULTIPLIER = 3.0     # Event if volume > rolling average * multiplier

# ============================================================================
# INDICATORS
# ============================================================================
SMA_PERIOD = 200  # Simple Moving Average period
EMA_FAST_PERIOD = 50
EMA_SLOW_PERIOD = 200
ATR_PERIOD = 60
VWAP_PERIOD = 300
VOLUME_ZSCORE_WINDOW = 300
RANGE_POSITION_WINDOW = 300

# ============================================================================
# TRADING PARAMETERS
# ============================================================================
TP_POINTS = 5.0   # Take profit in points, usar 4 oara scalping and 20 for swing
SL_POINTS = 9.0  # Stop loss in points, usar 9 para scalping

# Backtest realism
# NQ futures cost model. CME NQ specs: $20/point, 0.25-point tick, $5/tick.
NQ_CONTRACTS = 1
NQ_POINT_VALUE_USD = 20.0
NQ_TICK_SIZE_POINTS = 0.25
NQ_TICK_VALUE_USD = NQ_POINT_VALUE_USD * NQ_TICK_SIZE_POINTS

# Edit these two if your broker statement shows a different all-in rate.
BROKER_COMMISSION_PER_CONTRACT_SIDE_USD = 0.85
EXCHANGE_AND_REGULATORY_FEES_PER_CONTRACT_SIDE_USD = 2.80
SLIPPAGE_TICKS_PER_SIDE = 1.0

COMMISSION_PER_TRADE_USD = (
    (BROKER_COMMISSION_PER_CONTRACT_SIDE_USD + EXCHANGE_AND_REGULATORY_FEES_PER_CONTRACT_SIDE_USD)
    * 2
    * NQ_CONTRACTS
)  # Round-turn commission + exchange/regulatory fees
SLIPPAGE_POINTS = SLIPPAGE_TICKS_PER_SIDE * NQ_TICK_SIZE_POINTS
SLIPPAGE_USD_PER_TRADE = SLIPPAGE_POINTS * 2 * NQ_POINT_VALUE_USD * NQ_CONTRACTS
TOTAL_COST_USD_PER_TRADE = COMMISSION_PER_TRADE_USD + SLIPPAGE_USD_PER_TRADE
INTRABAR_POLICY = "SL_FIRST"         # If TP and SL hit in same bar: SL_FIRST or TP_FIRST
AVOID_OVERLAPPING_TRADES = True      # If True, only one trade can be active at a time
LIMIT_EXIT_TO_SIGNAL_TIMEOUT = True  # If True, force close when signal timeout ends

MEAN_REVERS_EXPAND = 10          # Points to expand mean reversion levels up/down
MEAN_REVERSE_TIMEOUT_ORDER = 0.15   # Timeout in minutes for mean reversion order lines (red/green)

# ============================================================================
# FILTERS TRADING SYSTEM
# ============================================================================
FILTER_BY_SMA =   False  # Enable/disable SMA filter
# If True (checks orange dot position at big volume event):
#   - If orange dot < SMA: ONLY SELL (SHORT) orders allowed
#   - If orange dot > SMA: ONLY BUY (LONG) orders allowed

SMA_CASH_TRAILING_ENABLED = False  # Enable hybrid cash & trail strategy (only if SMA_TRAILING_STOP = False)
SMA_CASH_TRAILING = 25.0          # Points in favor to activate trailing stop (e.g., 15 points profit)
SMA_CASH_TRAILING_DISTANCE = 10.0  # Trailing stop distance after activation (e.g., 5 points from extreme)
# If SMA_CASH_TRAILING_ENABLED = True (and SMA_TRAILING_STOP = False):
#   - Initial SL: Fixed at SL_POINTS (10 points)
#   - When price moves SMA_CASH_TRAILING points in favor (e.g., 15 pts profit):
#     * Activate trailing stop at SMA_CASH_TRAILING_DISTANCE from extreme price
#     * Guarantees at least (SMA_CASH_TRAILING - SMA_CASH_TRAILING_DISTANCE) points profit
#     * Example: 15 - 5 = 10 points minimum profit locked in
#   - Final TP: Still at TP_POINTS (25 points)
#   - For LONG: When price rises 15pts â†’ trail at highest_price - 5pts (locks 10pts min)
#   - For SHORT: When price drops 15pts â†’ trail at lowest_price + 5pts (locks 10pts min)
#   - Exit reason: 'cash_trailing' if trailing stop hits, 'profit' if TP hits

SMA_TRAILING_STOP = False  # Enable/disable full trailing stop from entry (only works if FILTER_BY_SMA = True)
TRAILING_STOP_ATR_MULT = 2.0    # Distance in points from price for trailing stop (volatility buffer)
# If SMA_TRAILING_STOP = True (only when FILTER_BY_SMA is also True):
#   - DISABLES fixed TP - lets profits run with dynamic trailing stop
#   - For LONG trades: SL = highest_price - TRAILING_STOP_ATR_MULT, moves UP only (never down)
#   - For SHORT trades: SL = lowest_price + TRAILING_STOP_ATR_MULT, moves DOWN only (never up)
#   - Trailing stop follows price movement with a volatility buffer (TRAILING_STOP_ATR_MULT points)
#   - Exit when price hits the trailing SL
#   - Exit reason will be 'trailing_stop' instead of 'stop'
#   - NO fixed TP is used when trailing stop is active (let profits run)
#   - NOTE: SMA is ONLY used for trade direction filtering, NOT for trailing stop calculation
#   - IMPORTANT: Trailing Stop OVERRIDES GRID_TP_POINTS when both GRID and Trailing Stop are enabled
#                When SMA_TRAILING_STOP=True, GRID_TP_POINTS is IGNORED and only GRID_SL_POINTS is used

# ============================================================================
# TOF FILTER - TIME OF DAY FILTER
# ============================================================================

FILTER_TIME_OF_DAY = False  # Enable/disable time-of-day filter
START_TRADING_TIME = "18:50:00"  # Start trading from this time (HH:MM:SS)
END_TRADING_TIME = "22:50:00"    # Stop trading after this time (HH:MM:SS)
# If True: Only trades with entry_time between START and END are allowed

# ============================================================================
# GRID SYSTEM
# ============================================================================
FILTER_USE_GRID = False  # Enable/disable GRID system (second entry)
GRID_MEAN_REVERS_EXPAND = 5.0  # Distance in points for second entry from first entry
GRID_TP_POINTS = 4.0  # Take profit distance from average entry price when GRID is active (ignored if trailing stop is ON)
GRID_SL_POINTS = 3.0   # Stop loss distance BEYOND second entry level when GRID is active
# If FILTER_USE_GRID = True:
#   - SELL: First entry at MEAN_REVERS_EXPAND, second entry at MEAN_REVERS_EXPAND + GRID_MEAN_REVERS_EXPAND
#   - BUY: First entry at MEAN_REVERS_EXPAND, second entry at MEAN_REVERS_EXPAND + GRID_MEAN_REVERS_EXPAND
#
#   WITHOUT Trailing Stop (SMA_TRAILING_STOP = False):
#     - If first entry reaches TP_POINTS before second entry triggers â†’ close immediately at profit
#     - If second entry triggers â†’ use GRID_TP_POINTS from average price, GRID_SL_POINTS beyond second entry
#
#   WITH Trailing Stop (SMA_TRAILING_STOP = True):
#     - Fixed TP is DISABLED for both first entry only AND second entry scenarios
#     - Only trailing stop is used (GRID_TP_POINTS is IGNORED)
#     - If only first entry fills â†’ trailing stop manages exit (no fixed TP/SL)
#     - If second entry fills â†’ trailing stop still manages exit (GRID_TP_POINTS ignored)
#
#   - Filled zones drawn at MEAN_REVERS_EXPAND + GRID_MEAN_REVERS_EXPAND (where second entry would be)
















