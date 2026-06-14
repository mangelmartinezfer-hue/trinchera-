"""
Trinchera Mean Reversion Strategy
Trades based on price touching mean reversion levels (red/green lines)
- SELL at red line (mean_level_up) with TP=5, SL=10
- BUY at green line (mean_level_down) with TP=5, SL=10
"""

import pandas as pd
from pathlib import Path
from datetime import datetime, time
from config_trinchera import MEAN_REVERS_EXPAND, TP_POINTS, SL_POINTS, FILTER_BY_SMA, FILTER_TIME_OF_DAY, START_TRADING_TIME, END_TRADING_TIME, FILTER_USE_GRID, GRID_MEAN_REVERS_EXPAND, GRID_TP_POINTS, GRID_SL_POINTS, SMA_TRAILING_STOP, TRAILING_STOP_ATR_MULT, SMA_CASH_TRAILING_ENABLED, SMA_CASH_TRAILING, SMA_CASH_TRAILING_DISTANCE, DATE, NQ_CONTRACTS, NQ_POINT_VALUE_USD, NQ_TICK_SIZE_POINTS, NQ_TICK_VALUE_USD, BROKER_COMMISSION_PER_CONTRACT_SIDE_USD, EXCHANGE_AND_REGULATORY_FEES_PER_CONTRACT_SIDE_USD, SLIPPAGE_TICKS_PER_SIDE, COMMISSION_PER_TRADE_USD, SLIPPAGE_POINTS, SLIPPAGE_USD_PER_TRADE, TOTAL_COST_USD_PER_TRADE, INTRABAR_POLICY, AVOID_OVERLAPPING_TRADES, LIMIT_EXIT_TO_SIGNAL_TIMEOUT

# ============================================================================
# STRATEGY CONFIGURATION
# ============================================================================
CURRENT_DIR = Path(__file__).resolve().parent
OUTPUTS_DIR = CURRENT_DIR / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
CHARTS_DIR = CURRENT_DIR / "charts"
CHARTS_DIR.mkdir(parents=True, exist_ok=True)

# Use DATE from config to find the specific files
BINS_FILE = OUTPUTS_DIR / f"db_trinchera_bins_{DATE}.csv"
if not BINS_FILE.exists():
    raise FileNotFoundError(f"Bins file not found: {BINS_FILE}")

ALL_DATA_FILE = OUTPUTS_DIR / f"db_trinchera_all_data_{DATE}.csv"
if not ALL_DATA_FILE.exists():
    raise FileNotFoundError(f"Data file not found: {ALL_DATA_FILE}")

OUTPUT_FILE = OUTPUTS_DIR / f"db_trinchera_TR_{DATE}.csv"
SIGNALS_FILE = OUTPUTS_DIR / f"db_trinchera_signals_{DATE}.csv"

POINT_VALUE = NQ_POINT_VALUE_USD * NQ_CONTRACTS

# Parse trading time range
if FILTER_TIME_OF_DAY:
    start_time = datetime.strptime(START_TRADING_TIME, "%H:%M:%S").time()
    end_time = datetime.strptime(END_TRADING_TIME, "%H:%M:%S").time()

print("="*80)
print("TRINCHERA MEAN REVERSION STRATEGY")
print("="*80)
print(f"\nConfiguration:")
print(f"  - Take Profit: {TP_POINTS} points (${TP_POINTS * POINT_VALUE:.0f})")
print(f"  - Stop Loss: {SL_POINTS} points (${SL_POINTS * POINT_VALUE:.0f})")
print(f"  - Mean Reversion Expand: {MEAN_REVERS_EXPAND} points")
print(f"  - NQ Contracts: {NQ_CONTRACTS}")
print(f"  - NQ Point Value: ${NQ_POINT_VALUE_USD:.2f} per point/contract")
print(f"  - NQ Tick: {NQ_TICK_SIZE_POINTS} points (${NQ_TICK_VALUE_USD:.2f}/contract)")
print(f"  - Broker Commission: ${BROKER_COMMISSION_PER_CONTRACT_SIDE_USD:.2f}/contract/side")
print(f"  - Exchange + Regulatory Fees: ${EXCHANGE_AND_REGULATORY_FEES_PER_CONTRACT_SIDE_USD:.2f}/contract/side")
print(f"  - Round-turn Fees: ${COMMISSION_PER_TRADE_USD:.2f} per completed trade")
print(f"  - Slippage: {SLIPPAGE_TICKS_PER_SIDE} ticks/side = {SLIPPAGE_POINTS} points/side (${SLIPPAGE_USD_PER_TRADE:.2f} round-turn)")
print(f"  - Total Modeled Cost: ${TOTAL_COST_USD_PER_TRADE:.2f} per completed trade")
print(f"  - Intrabar Policy: {INTRABAR_POLICY}")
print(f"  - Avoid Overlapping Trades: {'ENABLED' if AVOID_OVERLAPPING_TRADES else 'DISABLED'}")
print(f"  - Limit Exit To Signal Timeout: {'ENABLED' if LIMIT_EXIT_TO_SIGNAL_TIMEOUT else 'DISABLED'}")
print(f"  - SMA Filter: {'ENABLED' if FILTER_BY_SMA else 'DISABLED'}")
if FILTER_BY_SMA:
    print(f"    * Orange dot < SMA at event: ONLY SELL orders")
    print(f"    * Orange dot > SMA at event: ONLY BUY orders")
    if SMA_TRAILING_STOP:
        print(f"    * SMA Trailing Stop: ENABLED (follows SMA)")
    else:
        print(f"    * SMA Trailing Stop: DISABLED")
        # Add Cash & Trail status when trailing stop is disabled
        if SMA_CASH_TRAILING_ENABLED:
            min_profit = SMA_CASH_TRAILING - SMA_CASH_TRAILING_DISTANCE
            print(f"    * Cash & Trail: ENABLED ({SMA_CASH_TRAILING}p->{SMA_CASH_TRAILING_DISTANCE}p, locks {min_profit}p min)")
        else:
            print(f"    * Cash & Trail: DISABLED")
print(f"  - Time Filter: {'ENABLED' if FILTER_TIME_OF_DAY else 'DISABLED'}")
if FILTER_TIME_OF_DAY:
    print(f"    * Trading hours: {START_TRADING_TIME} to {END_TRADING_TIME}")
print(f"  - GRID System: {'ENABLED' if FILTER_USE_GRID else 'DISABLED'}")
if FILTER_USE_GRID:
    print(f"    * Second entry distance: {GRID_MEAN_REVERS_EXPAND} points")
    print(f"    * GRID TP: {GRID_TP_POINTS} points (${GRID_TP_POINTS * POINT_VALUE:.0f}) from average entry")
    print(f"    * GRID SL: {GRID_SL_POINTS} points (${GRID_SL_POINTS * POINT_VALUE:.0f}) beyond second entry")
    print(f"    * TP from average, SL from second entry + {GRID_SL_POINTS} pts")

# Load big volume events (bins)
print(f"\n[INFO] Loading big volume events from: {BINS_FILE.name}")
df_bins = pd.read_csv(BINS_FILE, sep=';', decimal=',', low_memory=False)
df_bins.columns = df_bins.columns.str.strip()
df_bins['timestamp'] = pd.to_datetime(df_bins['timestamp'])
df_bins['start_timestamp'] = pd.to_datetime(df_bins['start_timestamp'])
df_bins['end_timeout_mean_reversion'] = pd.to_datetime(df_bins['end_timeout_mean_reversion'])

print(f"[OK] Loaded {len(df_bins)} big volume events")

# Load all tick data
print(f"\n[INFO] Loading price data from: {ALL_DATA_FILE.name}")
df_data = pd.read_csv(ALL_DATA_FILE, sep=';', decimal=',', low_memory=False)
df_data.columns = df_data.columns.str.strip()
df_data['timestamp'] = pd.to_datetime(df_data['timestamp'])
df_data = df_data.sort_values('timestamp')

print(f"[OK] Loaded {len(df_data):,} frames")

# ============================================================================
# STRATEGY EXECUTION
# ============================================================================
trades = []
signals = []
active_trade_until = pd.Timestamp.min


def get_exit_data(df, exit_search_start, end_ts):
    if LIMIT_EXIT_TO_SIGNAL_TIMEOUT:
        return df[(df['timestamp'] > exit_search_start) & (df['timestamp'] <= end_ts)].copy()
    return df[df['timestamp'] > exit_search_start].copy()


def finalize_trade(direction, avg_entry_price, exit_price):
    gross_pnl = avg_entry_price - exit_price if direction == 'SELL' else exit_price - avg_entry_price
    net_pnl = gross_pnl - (SLIPPAGE_POINTS * 2)
    gross_pnl_usd = gross_pnl * POINT_VALUE
    slippage_usd = SLIPPAGE_POINTS * 2 * POINT_VALUE
    net_pnl_usd = gross_pnl_usd - slippage_usd - COMMISSION_PER_TRADE_USD
    return gross_pnl, net_pnl, gross_pnl_usd, slippage_usd, net_pnl_usd


def choose_fixed_exit(direction, bar, tp_price, sl_price):
    if direction == 'SELL':
        tp_hit = bar['low'] <= tp_price
        sl_hit = bar['high'] >= sl_price
    else:
        tp_hit = bar['high'] >= tp_price
        sl_hit = bar['low'] <= sl_price

    if tp_hit and sl_hit:
        if INTRABAR_POLICY == "TP_FIRST":
            return 'profit', tp_price
        return 'stop', sl_price
    if tp_hit:
        return 'profit', tp_price
    if sl_hit:
        return 'stop', sl_price
    return None, None


def force_timeout_exit(exit_data, direction):
    if len(exit_data) == 0:
        return None, None, None
    last_bar = exit_data.iloc[-1]
    exit_price = last_bar['close']
    return 'timeout', last_bar['timestamp'], exit_price


ENTRY_CONTEXT_COLUMNS = [
    'ema_fast',
    'ema_slow',
    'ema_spread',
    'sma_distance',
    'atr',
    'vwap',
    'vwap_distance',
    'volume_zscore',
    'orderflow_delta',
    'cumulative_delta',
    'orderflow_imbalance',
    'range_position',
    'trend_state',
]


def entry_context(row):
    return {f'entry_{col}': row[col] if col in row.index else None for col in ENTRY_CONTEXT_COLUMNS}

print(f"\n[INFO] Processing mean reversion opportunities...")

for idx, event in df_bins.iterrows():
    start_ts = event['start_timestamp']
    end_ts = event['end_timeout_mean_reversion']
    mean_level_up = event['mean_level_up']
    mean_level_down = event['mean_level_down']

    if AVOID_OVERLAPPING_TRADES and start_ts <= active_trade_until:
        signals.append({
            'event_timestamp': event['timestamp'],
            'direction': 'SKIPPED',
            'reason': 'overlapping_trade',
            'filter_passed': False
        })
        continue

    # Get orange dot (close price) and SMA at big volume event timestamp
    event_close = event['close']  # Orange dot price
    event_sma = event['sma']      # SMA at big volume event

    # Get price data within the timeout window
    mask = (df_data['timestamp'] >= start_ts) & (df_data['timestamp'] <= end_ts)
    window_data = df_data[mask].copy()

    if len(window_data) == 0:
        continue

    # Check for SELL opportunity (price touches red line - mean_level_up)
    # If FILTER_USE_GRID, first entry at MEAN_REVERS_EXPAND, second at MEAN_REVERS_EXPAND + GRID_MEAN_REVERS_EXPAND
    if FILTER_USE_GRID:
        first_entry_level = event_close + MEAN_REVERS_EXPAND
        second_entry_level = event_close + MEAN_REVERS_EXPAND + GRID_MEAN_REVERS_EXPAND
    else:
        first_entry_level = mean_level_up
        second_entry_level = None

    sell_touches = window_data[window_data['high'] >= first_entry_level]
    if len(sell_touches) > 0:
        entry_row = sell_touches.iloc[0]
        entry_time = entry_row['timestamp']
        entry_price = first_entry_level
        entry_sma = entry_row['sma']

        # Check filters (both are independent)
        sma_filter_passed = True
        time_filter_passed = True

        # SMA filter: SELL only if orange dot was BELOW SMA at event
        if FILTER_BY_SMA:
            sma_filter_passed = event_close < event_sma

        # Time filter: Check if entry time is within trading hours
        if FILTER_TIME_OF_DAY:
            entry_time_only = entry_time.time()
            time_filter_passed = start_time <= entry_time_only <= end_time

        # Both filters must pass (if enabled)
        filter_passed = sma_filter_passed and time_filter_passed

        # GRID: Look for second entry OR TP from first entry (whichever comes first)
        second_entry_time = None
        second_entry_price = None
        has_second_entry = False
        early_tp_exit = False

        # Calculate TP from first entry
        first_entry_tp = entry_price - TP_POINTS  # SELL: TP is below entry
        first_entry_sl = entry_price + SL_POINTS  # SELL: SL is above entry

        if FILTER_USE_GRID and second_entry_level is not None:
            # Search for second entry OR TP/SL from first entry (whichever comes first)
            # BUT: If trailing stop is enabled, ONLY check for second entry (skip fixed TP/SL)
            trailing_enabled = FILTER_BY_SMA and SMA_TRAILING_STOP
            second_entry_data = df_data[(df_data['timestamp'] > entry_time) & (df_data['timestamp'] <= end_ts)].copy()

            for _, bar in second_entry_data.iterrows():
                fixed_exit_reason, fixed_exit_price = (None, None)
                if not trailing_enabled:
                    fixed_exit_reason, fixed_exit_price = choose_fixed_exit('SELL', bar, first_entry_tp, first_entry_sl)

                # Check if first entry TP/SL is reached BEFORE second entry (only if NO trailing stop)
                if fixed_exit_reason:
                    early_tp_exit = True
                    exit_reason = fixed_exit_reason
                    exit_time = bar['timestamp']
                    exit_price = fixed_exit_price
                    exit_sma = bar['sma']
                    avg_entry_price = entry_price
                    tp_price = first_entry_tp
                    sl_price = first_entry_sl
                    break
                # Check if second entry is triggered
                elif bar['high'] >= second_entry_level:
                    second_entry_time = bar['timestamp']
                    second_entry_price = second_entry_level
                    has_second_entry = True
                    # Calculate average entry price for TP/SL
                    avg_entry_price = (entry_price + second_entry_price) / 2
                    break

            # If no early exit and no second entry, use first entry price
            if not early_tp_exit and not has_second_entry:
                avg_entry_price = entry_price
        else:
            avg_entry_price = entry_price

        # Calculate TP and SL for SELL (only if not early exit)
        if not early_tp_exit:
            trailing_enabled = FILTER_BY_SMA and SMA_TRAILING_STOP
            if FILTER_USE_GRID and has_second_entry:
                # GRID second entry filled - use GRID TP/SL (unless trailing stop overrides TP)
                tp_price = avg_entry_price - GRID_TP_POINTS if not trailing_enabled else None
                sl_price = event_close + MEAN_REVERS_EXPAND + GRID_MEAN_REVERS_EXPAND + GRID_SL_POINTS
            else:
                # Only first entry (or GRID disabled) - use normal TP/SL (unless trailing stop overrides TP)
                tp_price = avg_entry_price - TP_POINTS if not trailing_enabled else None
                sl_price = avg_entry_price + SL_POINTS

            # Find exit from entry time (or second entry if exists) onwards
            exit_search_start = second_entry_time if has_second_entry else entry_time
            exit_data = get_exit_data(df_data, exit_search_start, end_ts)

            exit_reason = None
            exit_time = None
            exit_price = None
            exit_sma = None

            # Trailing stop tracking
            trailing_enabled = FILTER_BY_SMA and SMA_TRAILING_STOP
            cash_trailing_enabled = FILTER_BY_SMA and SMA_CASH_TRAILING_ENABLED and not trailing_enabled

            trailing_distance = TRAILING_STOP_ATR_MULT  # Distance for full trailing stop
            initial_sl = sl_price  # Store initial stop loss
            trailing_has_moved = False  # Track if trailing stop actually moved
            lowest_price = None  # Track lowest price reached for SHORT trailing

            # Cash & Trail specific variables
            cash_trailing_activated = False  # Track if cash trailing threshold was reached
            best_profit = 0.0  # Track best profit achieved (for SELL: entry - current)

            for _, bar in exit_data.iterrows():
                current_price = bar['low']  # Use low for SHORT (worst case for us)

                # Calculate current profit for SELL (entry - current)
                current_profit = avg_entry_price - current_price

                # FULL TRAILING STOP (from entry)
                if trailing_enabled:
                    # Track lowest price for SHORT
                    if lowest_price is None or current_price < lowest_price:
                        lowest_price = current_price
                        # For SHORT: SL is above lowest price by trailing_distance
                        new_sl = lowest_price + trailing_distance
                        # Only move SL down (never up for SHORT)
                        if new_sl < sl_price:
                            sl_price = new_sl
                            trailing_has_moved = True  # Mark that trailing has taken over

                # CASH & TRAIL HYBRID (activate trail after threshold)
                elif cash_trailing_enabled:
                    # Track best profit achieved
                    if current_profit > best_profit:
                        best_profit = current_profit

                    # Check if we've reached the cash trailing threshold
                    if best_profit >= SMA_CASH_TRAILING and not cash_trailing_activated:
                        cash_trailing_activated = True
                        lowest_price = current_price  # Initialize lowest price from activation point

                    # If cash trailing is activated, apply trailing stop
                    if cash_trailing_activated:
                        if current_price < lowest_price:
                            lowest_price = current_price
                        # For SHORT: SL is above lowest price by cash trailing distance
                        new_sl = lowest_price + SMA_CASH_TRAILING_DISTANCE
                        # Only move SL down (never up for SHORT), and don't go below initial SL
                        if new_sl < sl_price and new_sl < initial_sl:
                            sl_price = new_sl
                            trailing_has_moved = True

                # Check fixed TP/SL with explicit intrabar policy.
                if not trailing_enabled:
                    fixed_exit_reason, fixed_exit_price = choose_fixed_exit('SELL', bar, tp_price, sl_price)
                    if fixed_exit_reason:
                        if fixed_exit_reason == 'stop' and cash_trailing_enabled and trailing_has_moved:
                            fixed_exit_reason = 'cash_trailing'
                        exit_reason = fixed_exit_reason
                        exit_time = bar['timestamp']
                        exit_price = fixed_exit_price
                        exit_sma = bar['sma']
                        break
                # Check SL (price goes up to SL)
                if bar['high'] >= sl_price:
                    # Determine exit reason based on trailing type
                    if trailing_enabled and trailing_has_moved:
                        exit_reason = 'trailing_stop'
                    elif cash_trailing_enabled and trailing_has_moved:
                        exit_reason = 'cash_trailing'
                    else:
                        exit_reason = 'stop'
                    exit_time = bar['timestamp']
                    exit_price = sl_price
                    exit_sma = bar['sma']
                    break

            if exit_reason is None and LIMIT_EXIT_TO_SIGNAL_TIMEOUT:
                timeout_reason, timeout_time, timeout_price = force_timeout_exit(exit_data, 'SELL')
                if timeout_reason:
                    exit_reason = timeout_reason
                    exit_time = timeout_time
                    exit_price = timeout_price
                    exit_sma = exit_data.iloc[-1]['sma']

        if exit_reason:
            signals.append({
                'event_timestamp': event['timestamp'],
                'entry_time': entry_time,
                'exit_time': exit_time,
                'direction': 'SELL',
                'exit_reason': exit_reason,
                'filter_passed': filter_passed,
                'reject_reason': None if filter_passed else 'filter_rejected'
            })

        if exit_reason and filter_passed:
            gross_pnl, pnl, gross_pnl_usd, slippage_usd, pnl_usd = finalize_trade('SELL', avg_entry_price, exit_price)
            trade = {
                'entry_time': entry_time,
                'entry_time_2': second_entry_time if has_second_entry else None,
                'exit_time': exit_time,
                'direction': 'SELL',
                'entry_price': entry_price,
                'entry_price_2': second_entry_price if has_second_entry else None,
                'avg_entry_price': avg_entry_price,
                'exit_price': exit_price,
                'entry_sma': entry_sma,
                'exit_sma': exit_sma,
                'event_close': event_close,
                'event_sma': event_sma,
                'tp_price': tp_price,
                'sl_price': sl_price,
                'exit_reason': exit_reason,
                'gross_pnl': gross_pnl,
                'pnl': pnl,
                'gross_pnl_usd': gross_pnl_usd,
                'pnl_usd': pnl_usd,
                'commission_usd': COMMISSION_PER_TRADE_USD,
                'slippage_points': SLIPPAGE_POINTS * 2,
                'slippage_usd': slippage_usd,
                'total_cost_usd': COMMISSION_PER_TRADE_USD + slippage_usd,
                'contracts': NQ_CONTRACTS,
                'point_value_usd': POINT_VALUE,
                'tick_size_points': NQ_TICK_SIZE_POINTS,
                'tick_value_usd': NQ_TICK_VALUE_USD * NQ_CONTRACTS,
                'filter_passed': filter_passed,
                'event_timestamp': event['timestamp'],
                'has_grid_entry': has_second_entry
            }
            trade.update(entry_context(entry_row))
            trades.append(trade)
            active_trade_until = max(active_trade_until, exit_time)

    if AVOID_OVERLAPPING_TRADES and start_ts <= active_trade_until:
        continue

    # Check for BUY opportunity (price touches green line - mean_level_down)
    # If FILTER_USE_GRID, first entry at MEAN_REVERS_EXPAND, second at MEAN_REVERS_EXPAND + GRID_MEAN_REVERS_EXPAND
    if FILTER_USE_GRID:
        first_entry_level = event_close - MEAN_REVERS_EXPAND
        second_entry_level = event_close - MEAN_REVERS_EXPAND - GRID_MEAN_REVERS_EXPAND
    else:
        first_entry_level = mean_level_down
        second_entry_level = None

    buy_touches = window_data[window_data['low'] <= first_entry_level]
    if len(buy_touches) > 0:
        entry_row = buy_touches.iloc[0]
        entry_time = entry_row['timestamp']
        entry_price = first_entry_level
        entry_sma = entry_row['sma']

        # Check filters (both are independent)
        sma_filter_passed = True
        time_filter_passed = True

        # SMA filter: BUY only if orange dot was ABOVE SMA at event
        if FILTER_BY_SMA:
            sma_filter_passed = event_close > event_sma

        # Time filter: Check if entry time is within trading hours
        if FILTER_TIME_OF_DAY:
            entry_time_only = entry_time.time()
            time_filter_passed = start_time <= entry_time_only <= end_time

        # Both filters must pass (if enabled)
        filter_passed = sma_filter_passed and time_filter_passed

        # GRID: Look for second entry OR TP from first entry (whichever comes first)
        second_entry_time = None
        second_entry_price = None
        has_second_entry = False
        early_tp_exit = False

        # Calculate TP from first entry
        first_entry_tp = entry_price + TP_POINTS  # BUY: TP is above entry
        first_entry_sl = entry_price - SL_POINTS  # BUY: SL is below entry

        if FILTER_USE_GRID and second_entry_level is not None:
            # Search for second entry OR TP/SL from first entry (whichever comes first)
            # BUT: If trailing stop is enabled, ONLY check for second entry (skip fixed TP/SL)
            trailing_enabled = FILTER_BY_SMA and SMA_TRAILING_STOP
            second_entry_data = df_data[(df_data['timestamp'] > entry_time) & (df_data['timestamp'] <= end_ts)].copy()

            for _, bar in second_entry_data.iterrows():
                fixed_exit_reason, fixed_exit_price = (None, None)
                if not trailing_enabled:
                    fixed_exit_reason, fixed_exit_price = choose_fixed_exit('BUY', bar, first_entry_tp, first_entry_sl)

                # Check if first entry TP/SL is reached BEFORE second entry (only if NO trailing stop)
                if fixed_exit_reason:
                    early_tp_exit = True
                    exit_reason = fixed_exit_reason
                    exit_time = bar['timestamp']
                    exit_price = fixed_exit_price
                    exit_sma = bar['sma']
                    avg_entry_price = entry_price
                    tp_price = first_entry_tp
                    sl_price = first_entry_sl
                    break
                # Check if second entry is triggered
                elif bar['low'] <= second_entry_level:
                    second_entry_time = bar['timestamp']
                    second_entry_price = second_entry_level
                    has_second_entry = True
                    # Calculate average entry price for TP/SL
                    avg_entry_price = (entry_price + second_entry_price) / 2
                    break

            # If no early exit and no second entry, use first entry price
            if not early_tp_exit and not has_second_entry:
                avg_entry_price = entry_price
        else:
            avg_entry_price = entry_price

        # Calculate TP and SL for BUY (only if not early exit)
        if not early_tp_exit:
            trailing_enabled = FILTER_BY_SMA and SMA_TRAILING_STOP
            if FILTER_USE_GRID and has_second_entry:
                # GRID second entry filled - use GRID TP/SL (unless trailing stop overrides TP)
                tp_price = avg_entry_price + GRID_TP_POINTS if not trailing_enabled else None
                sl_price = event_close - MEAN_REVERS_EXPAND - GRID_MEAN_REVERS_EXPAND - GRID_SL_POINTS
            else:
                # Only first entry (or GRID disabled) - use normal TP/SL (unless trailing stop overrides TP)
                tp_price = avg_entry_price + TP_POINTS if not trailing_enabled else None
                sl_price = avg_entry_price - SL_POINTS

            # Find exit from entry time (or second entry if exists) onwards
            exit_search_start = second_entry_time if has_second_entry else entry_time
            exit_data = get_exit_data(df_data, exit_search_start, end_ts)

            exit_reason = None
            exit_time = None
            exit_price = None
            exit_sma = None

            # Trailing stop tracking
            trailing_enabled = FILTER_BY_SMA and SMA_TRAILING_STOP
            cash_trailing_enabled = FILTER_BY_SMA and SMA_CASH_TRAILING_ENABLED and not trailing_enabled

            trailing_distance = TRAILING_STOP_ATR_MULT  # Distance for full trailing stop
            initial_sl = sl_price  # Store initial stop loss
            trailing_has_moved = False  # Track if trailing stop actually moved
            highest_price = None  # Track highest price reached for LONG trailing

            # Cash & Trail specific variables
            cash_trailing_activated = False  # Track if cash trailing threshold was reached
            best_profit = 0.0  # Track best profit achieved (for BUY: current - entry)

            for _, bar in exit_data.iterrows():
                current_price = bar['high']  # Use high for LONG (worst case for us)

                # Calculate current profit for BUY (current - entry)
                current_profit = current_price - avg_entry_price

                # FULL TRAILING STOP (from entry)
                if trailing_enabled:
                    # Track highest price for LONG
                    if highest_price is None or current_price > highest_price:
                        highest_price = current_price
                        # For LONG: SL is below highest price by trailing_distance
                        new_sl = highest_price - trailing_distance
                        # Only move SL up (never down for LONG)
                        if new_sl > sl_price:
                            sl_price = new_sl
                            trailing_has_moved = True  # Mark that trailing has taken over

                # CASH & TRAIL HYBRID (activate trail after threshold)
                elif cash_trailing_enabled:
                    # Track best profit achieved
                    if current_profit > best_profit:
                        best_profit = current_profit

                    # Check if we've reached the cash trailing threshold
                    if best_profit >= SMA_CASH_TRAILING and not cash_trailing_activated:
                        cash_trailing_activated = True
                        highest_price = current_price  # Initialize highest price from activation point

                    # If cash trailing is activated, apply trailing stop
                    if cash_trailing_activated:
                        if current_price > highest_price:
                            highest_price = current_price
                        # For LONG: SL is below highest price by cash trailing distance
                        new_sl = highest_price - SMA_CASH_TRAILING_DISTANCE
                        # Only move SL up (never down for LONG), and don't go above initial SL
                        if new_sl > sl_price and new_sl > initial_sl:
                            sl_price = new_sl
                            trailing_has_moved = True

                # Check fixed TP/SL with explicit intrabar policy.
                if not trailing_enabled:
                    fixed_exit_reason, fixed_exit_price = choose_fixed_exit('BUY', bar, tp_price, sl_price)
                    if fixed_exit_reason:
                        if fixed_exit_reason == 'stop' and cash_trailing_enabled and trailing_has_moved:
                            fixed_exit_reason = 'cash_trailing'
                        exit_reason = fixed_exit_reason
                        exit_time = bar['timestamp']
                        exit_price = fixed_exit_price
                        exit_sma = bar['sma']
                        break
                # Check SL (price goes down to SL)
                if bar['low'] <= sl_price:
                    # Determine exit reason based on trailing type
                    if trailing_enabled and trailing_has_moved:
                        exit_reason = 'trailing_stop'
                    elif cash_trailing_enabled and trailing_has_moved:
                        exit_reason = 'cash_trailing'
                    else:
                        exit_reason = 'stop'
                    exit_time = bar['timestamp']
                    exit_price = sl_price
                    exit_sma = bar['sma']
                    break

            if exit_reason is None and LIMIT_EXIT_TO_SIGNAL_TIMEOUT:
                timeout_reason, timeout_time, timeout_price = force_timeout_exit(exit_data, 'BUY')
                if timeout_reason:
                    exit_reason = timeout_reason
                    exit_time = timeout_time
                    exit_price = timeout_price
                    exit_sma = exit_data.iloc[-1]['sma']

        if exit_reason:
            signals.append({
                'event_timestamp': event['timestamp'],
                'entry_time': entry_time,
                'exit_time': exit_time,
                'direction': 'BUY',
                'exit_reason': exit_reason,
                'filter_passed': filter_passed,
                'reject_reason': None if filter_passed else 'filter_rejected'
            })

        if exit_reason and filter_passed:
            gross_pnl, pnl, gross_pnl_usd, slippage_usd, pnl_usd = finalize_trade('BUY', avg_entry_price, exit_price)
            trade = {
                'entry_time': entry_time,
                'entry_time_2': second_entry_time if has_second_entry else None,
                'exit_time': exit_time,
                'direction': 'BUY',
                'entry_price': entry_price,
                'entry_price_2': second_entry_price if has_second_entry else None,
                'avg_entry_price': avg_entry_price,
                'exit_price': exit_price,
                'entry_sma': entry_sma,
                'exit_sma': exit_sma,
                'event_close': event_close,
                'event_sma': event_sma,
                'tp_price': tp_price,
                'sl_price': sl_price,
                'exit_reason': exit_reason,
                'gross_pnl': gross_pnl,
                'pnl': pnl,
                'gross_pnl_usd': gross_pnl_usd,
                'pnl_usd': pnl_usd,
                'commission_usd': COMMISSION_PER_TRADE_USD,
                'slippage_points': SLIPPAGE_POINTS * 2,
                'slippage_usd': slippage_usd,
                'total_cost_usd': COMMISSION_PER_TRADE_USD + slippage_usd,
                'contracts': NQ_CONTRACTS,
                'point_value_usd': POINT_VALUE,
                'tick_size_points': NQ_TICK_SIZE_POINTS,
                'tick_value_usd': NQ_TICK_VALUE_USD * NQ_CONTRACTS,
                'filter_passed': filter_passed,
                'event_timestamp': event['timestamp'],
                'has_grid_entry': has_second_entry
            }
            trade.update(entry_context(entry_row))
            trades.append(trade)
            active_trade_until = max(active_trade_until, exit_time)

# ============================================================================
# SAVE RESULTS
# ============================================================================
if len(signals) > 0:
    df_signals = pd.DataFrame(signals)
    df_signals.to_csv(SIGNALS_FILE, index=False, sep=';', decimal=',')
    print(f"\n[OK] Signals audit saved to: {SIGNALS_FILE.name}")

if len(trades) > 0:
    df_trades = pd.DataFrame(trades)

    # Add sequential trade ID (starting from 1)
    df_trades.insert(0, 'trade_id', range(1, len(df_trades) + 1))

    # Save to CSV
    df_trades.to_csv(OUTPUT_FILE, index=False, sep=';', decimal=',')

    print(f"\n[OK] Strategy completed: {len(trades)} trades executed")
    print(f"[OK] Trades saved to: {OUTPUT_FILE.name}")

    # Statistics
    profit_trades = df_trades[df_trades['exit_reason'] == 'profit']
    stop_trades = df_trades[df_trades['exit_reason'] == 'stop']
    trailing_stop_trades = df_trades[df_trades['exit_reason'] == 'trailing_stop']
    cash_trailing_trades = df_trades[df_trades['exit_reason'] == 'cash_trailing']
    timeout_trades = df_trades[df_trades['exit_reason'] == 'timeout']

    total_pnl = df_trades['pnl'].sum()
    total_pnl_usd = df_trades['pnl_usd'].sum()

    print("\n" + "="*80)
    print("STRATEGY STATISTICS")
    print("="*80)
    print(f"Total trades: {len(df_trades)}")
    print(f"  - PROFIT exits: {len(profit_trades)} ({len(profit_trades)/len(df_trades)*100:.1f}%)")
    print(f"  - STOP exits: {len(stop_trades)} ({len(stop_trades)/len(df_trades)*100:.1f}%)")
    if len(trailing_stop_trades) > 0:
        print(f"  - TRAILING STOP exits: {len(trailing_stop_trades)} ({len(trailing_stop_trades)/len(df_trades)*100:.1f}%)")
    if len(cash_trailing_trades) > 0:
        print(f"  - CASH TRAILING exits: {len(cash_trailing_trades)} ({len(cash_trailing_trades)/len(df_trades)*100:.1f}%)")
    if len(timeout_trades) > 0:
        print(f"  - TIMEOUT exits: {len(timeout_trades)} ({len(timeout_trades)/len(df_trades)*100:.1f}%)")

    if FILTER_BY_SMA:
        filtered_trades = df_trades[df_trades['filter_passed'] == True]
        rejected_trades = df_signals[df_signals['filter_passed'] == False] if len(signals) > 0 else pd.DataFrame()
        print(f"\nSMA Filter:")
        print(f"  - Passed filter: {len(filtered_trades)} ({len(filtered_trades)/len(df_trades)*100:.1f}%)")
        print(f"  - Rejected/Skipped signals: {len(rejected_trades)}")

    print(f"\nTotal P&L: {total_pnl:.2f} points (${total_pnl_usd:,.2f})")
    print(f"Average P&L per trade: {total_pnl/len(df_trades):.2f} points (${total_pnl_usd/len(df_trades):,.2f})")

    # Breakdown by direction
    buy_trades = df_trades[df_trades['direction'] == 'BUY']
    sell_trades = df_trades[df_trades['direction'] == 'SELL']

    print(f"\nBUY trades: {len(buy_trades)}")
    if len(buy_trades) > 0:
        buy_pnl = buy_trades['pnl'].sum()
        buy_pnl_usd = buy_trades['pnl_usd'].sum()
        print(f"  - P&L: {buy_pnl:.2f} points (${buy_pnl_usd:,.2f})")
        print(f"  - Profit exits: {len(buy_trades[buy_trades['exit_reason']=='profit'])}")
        print(f"  - Stop exits: {len(buy_trades[buy_trades['exit_reason']=='stop'])}")
        if len(buy_trades[buy_trades['exit_reason']=='trailing_stop']) > 0:
            print(f"  - Trailing stop exits: {len(buy_trades[buy_trades['exit_reason']=='trailing_stop'])}")
        if len(buy_trades[buy_trades['exit_reason']=='cash_trailing']) > 0:
            print(f"  - Cash trailing exits: {len(buy_trades[buy_trades['exit_reason']=='cash_trailing'])}")

    print(f"\nSELL trades: {len(sell_trades)}")
    if len(sell_trades) > 0:
        sell_pnl = sell_trades['pnl'].sum()
        sell_pnl_usd = sell_trades['pnl_usd'].sum()
        print(f"  - P&L: {sell_pnl:.2f} points (${sell_pnl_usd:,.2f})")
        print(f"  - Profit exits: {len(sell_trades[sell_trades['exit_reason']=='profit'])}")
        print(f"  - Stop exits: {len(sell_trades[sell_trades['exit_reason']=='stop'])}")
        if len(sell_trades[sell_trades['exit_reason']=='trailing_stop']) > 0:
            print(f"  - Trailing stop exits: {len(sell_trades[sell_trades['exit_reason']=='trailing_stop'])}")
        if len(sell_trades[sell_trades['exit_reason']=='cash_trailing']) > 0:
            print(f"  - Cash trailing exits: {len(sell_trades[sell_trades['exit_reason']=='cash_trailing'])}")

else:
    print("\n[WARN] No trades executed")

print("\n" + "="*80)
print("[SUCCESS] Strategy execution completed!")
print("="*80)
