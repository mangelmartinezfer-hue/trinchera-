import pandas as pd
from datetime import timedelta, datetime
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
UTILS_DIR = CURRENT_DIR / "utils"
if str(UTILS_DIR) not in sys.path:
    sys.path.append(str(UTILS_DIR))

from rolling_profile import RollingMarketProfile
from config_trinchera import (
    ATR_PERIOD,
    DATE,
    EMA_FAST_PERIOD,
    EMA_SLOW_PERIOD,
    RANGE_POSITION_WINDOW,
    SMA_PERIOD,
    VOLUME_ZSCORE_WINDOW,
    VWAP_PERIOD,
)

# ============ CONFIGURATION ============
FRAME_FREQUENCY = "1s"  # Frequency for frame updates (1 second)
PROFILE_FREQUENCY = 1   # Frequency for Market Profile in seconds
TICK_SIZE = 0.25        # Price tick size for grouping levels
# =======================================

# Load data
csv_path = CURRENT_DIR / "data" / "historic" / f"time_and_sales_nq_{DATE}.csv"

print("=" * 60)
print("TRINCHERA DATA PROCESSOR")
print("=" * 60)
print(f"\nLoading data from: {csv_path}")
print(f"File exists: {csv_path.exists()}")

df = pd.read_csv(csv_path, sep=";", decimal=",")
df["Timestamp"] = pd.to_datetime(df["Timestamp"])

print(f"Loaded {len(df)} ticks")
print(f"Date range: {df['Timestamp'].min()} to {df['Timestamp'].max()}")

# Pre-compute market profiles with 1-second aggregation
print("\n" + "=" * 60)
print("PROCESSING MARKET PROFILES (1-second frames)...")
print("=" * 60)

profiles_data = []

# Generate timestamps every 1 second for aggregation
start_time = df["Timestamp"].min()
end_time = df["Timestamp"].max()
timestamps = pd.date_range(start=start_time, end=end_time, freq=FRAME_FREQUENCY)

print(f"Total frames to process: {len(timestamps)}")

# Create a SINGLE RollingMarketProfile instance
mp = RollingMarketProfile(
    window=timedelta(seconds=PROFILE_FREQUENCY),
    price_tick=TICK_SIZE,
)

total_ticks = len(df)
tick_idx = 0
last_known_price = None

ts_values = df["Timestamp"].values  # numpy array for fast comparison in while condition

for i, ts in enumerate(timestamps):
    if i % 5000 == 0 and i > 0:
        print(f"  Processing frame {i}/{len(timestamps)}... (tick {tick_idx}/{total_ticks})")

    frame_tick_start = tick_idx  # start index for this frame's ticks

    # Process all ticks up to this timestamp
    while tick_idx < total_ticks and ts_values[tick_idx] <= ts:
        row = df.iloc[tick_idx]
        mp.update(row["Timestamp"], row["Precio"], row["Volumen"], row["Lado"])
        last_known_price = row["Precio"]  # Track last known price
        tick_idx += 1

    # Get closing price (last known price up to this timestamp)
    closing_price = last_known_price

    # Get the current profile (rolling window automatically maintained)
    profile = mp.profile()
    profiles_data.append((ts, profile, closing_price, frame_tick_start, tick_idx))

print(f"\n[OK] Pre-computed {len(profiles_data)} profiles (processed {tick_idx} ticks)")

# Extract ALL frames data with OHLCV aggregation
print("\n" + "=" * 60)
print("EXTRACTING FRAME DATA (OHLCV + Market Profile metrics)...")
print("=" * 60)

all_frames = []

for i, (timestamp, profile, closing_price, tick_start, tick_end) in enumerate(profiles_data):
    if i % 5000 == 0 and i > 0:
        print(f"  Extracting frame data {i}/{len(profiles_data)}...")

    # Get previous close for price change calculation
    previous_close = None
    previous_profile = None
    if i > 0 and i - 1 < len(profiles_data):
        _, previous_profile, previous_close, _, _ = profiles_data[i - 1]

    # Calculate price change
    price_change = closing_price - previous_close if previous_close is not None else 0
    price_change_pct = (price_change / previous_close * 100) if previous_close is not None and previous_close != 0 else 0

    # Ticks for this frame, using pre-computed index range (O(1) vs O(n) boolean mask)
    frame_ticks = df.iloc[tick_start:tick_end]

    # Calculate OHLC from frame ticks
    if len(frame_ticks) > 0:
        frame_open = frame_ticks.iloc[0]['Precio']
        frame_high = frame_ticks['Precio'].max()
        frame_low = frame_ticks['Precio'].min()
        frame_close = frame_ticks.iloc[-1]['Precio']
        tick_count = len(frame_ticks)

        # Calculate BID/ASK volumes from frame ticks
        bid_ticks = frame_ticks[frame_ticks['Lado'] == 'BID']
        ask_ticks = frame_ticks[frame_ticks['Lado'] == 'ASK']
        total_bid = bid_ticks['Volumen'].sum() if len(bid_ticks) > 0 else 0
        total_ask = ask_ticks['Volumen'].sum() if len(ask_ticks) > 0 else 0
        total_volume = total_bid + total_ask
        bid_ask_ratio = total_bid / total_ask if total_ask > 0 else 0
    else:
        frame_open = frame_high = frame_low = frame_close = closing_price
        tick_count = 0
        total_bid = total_ask = total_volume = bid_ask_ratio = 0

    # Count active price levels from profile
    num_price_levels = 0
    profile_bid_volume = 0
    profile_ask_volume = 0
    profile_total_volume = 0
    min_price = None
    max_price = None
    price_range = 0
    poc_price = None  # Point of Control
    poc_volume = 0

    if profile:
        active_prices = [p for p in profile.keys() if profile[p].get('BID', 0) > 0 or profile[p].get('ASK', 0) > 0]
        num_price_levels = len(active_prices)

        if active_prices:
            min_price = min(active_prices)
            max_price = max(active_prices)
            price_range = max_price - min_price

            # Calculate total volumes from profile
            profile_bid_volume = sum(profile[p].get('BID', 0) for p in active_prices)
            profile_ask_volume = sum(profile[p].get('ASK', 0) for p in active_prices)
            profile_total_volume = profile_bid_volume + profile_ask_volume

            # Find Point of Control (price level with most volume)
            for p in active_prices:
                level_volume = profile[p].get('BID', 0) + profile[p].get('ASK', 0)
                if level_volume > poc_volume:
                    poc_volume = level_volume
                    poc_price = p

    # Calculate number of price levels moved (price change in ticks)
    num_levels_moved = 0
    if previous_close is not None and TICK_SIZE > 0:
        num_levels_moved = round(price_change / TICK_SIZE)

    # Calculate profile BID/ASK ratio
    profile_bid_ask_ratio = profile_bid_volume / profile_ask_volume if profile_ask_volume > 0 else 0

    # Build frame data dictionary
    frame_data = {
        'timestamp': timestamp,

        # OHLC data
        'open': frame_open,
        'high': frame_high,
        'low': frame_low,
        'close': frame_close,
        'previous_close': previous_close,

        # Price changes
        'price_change': price_change,
        'price_change_pct': price_change_pct,
        'num_levels_moved': num_levels_moved,

        # Volume from ticks (aggregated for this 1-second window)
        'total_bid': total_bid,
        'total_ask': total_ask,
        'total_volume': total_volume,
        'bid_ask_ratio': bid_ask_ratio,

        # Market Profile volumes (rolling window)
        'profile_bid_volume': profile_bid_volume,
        'profile_ask_volume': profile_ask_volume,
        'profile_total_volume': profile_total_volume,
        'profile_bid_ask_ratio': profile_bid_ask_ratio,

        # Market Profile structure
        'num_price_levels': num_price_levels,
        'price_range': price_range,
        'min_price': min_price,
        'max_price': max_price,
        'poc_price': poc_price,  # Point of Control
        'poc_volume': poc_volume,

        # Other metrics
        'tick_count': tick_count,
    }

    all_frames.append(frame_data)

print(f"\n[OK] Extracted {len(all_frames)} frames")

# Create DataFrame
df_all_frames = pd.DataFrame(all_frames)

# Calculate SMA
print(f"\n[INFO] Calculating SMA-{SMA_PERIOD}...")
df_all_frames['sma'] = df_all_frames['close'].rolling(window=SMA_PERIOD, min_periods=1).mean()
print(f"[OK] SMA-{SMA_PERIOD} calculated")

print("[INFO] Calculating context indicators...")
df_all_frames['ema_fast'] = df_all_frames['close'].ewm(span=EMA_FAST_PERIOD, adjust=False).mean()
df_all_frames['ema_slow'] = df_all_frames['close'].ewm(span=EMA_SLOW_PERIOD, adjust=False).mean()
df_all_frames['ema_spread'] = df_all_frames['ema_fast'] - df_all_frames['ema_slow']
df_all_frames['sma_distance'] = df_all_frames['close'] - df_all_frames['sma']

true_range_parts = pd.concat([
    df_all_frames['high'] - df_all_frames['low'],
    (df_all_frames['high'] - df_all_frames['previous_close']).abs(),
    (df_all_frames['low'] - df_all_frames['previous_close']).abs(),
], axis=1)
df_all_frames['true_range'] = true_range_parts.max(axis=1).fillna(0)
df_all_frames['atr'] = df_all_frames['true_range'].rolling(window=ATR_PERIOD, min_periods=1).mean()

volume_price = df_all_frames['close'] * df_all_frames['total_volume']
rolling_volume = df_all_frames['total_volume'].rolling(window=VWAP_PERIOD, min_periods=1).sum()
rolling_volume_price = volume_price.rolling(window=VWAP_PERIOD, min_periods=1).sum()
df_all_frames['vwap'] = (rolling_volume_price / rolling_volume.replace(0, float('nan'))).ffill().fillna(df_all_frames['close'])
df_all_frames['vwap_distance'] = df_all_frames['close'] - df_all_frames['vwap']

volume_mean = df_all_frames['total_volume'].rolling(window=VOLUME_ZSCORE_WINDOW, min_periods=2).mean()
volume_std = df_all_frames['total_volume'].rolling(window=VOLUME_ZSCORE_WINDOW, min_periods=2).std()
df_all_frames['volume_zscore'] = ((df_all_frames['total_volume'] - volume_mean) / volume_std.replace(0, float('nan'))).fillna(0)

df_all_frames['orderflow_delta'] = df_all_frames['total_ask'] - df_all_frames['total_bid']
df_all_frames['cumulative_delta'] = df_all_frames['orderflow_delta'].cumsum()
df_all_frames['orderflow_imbalance'] = (
    df_all_frames['orderflow_delta'] / df_all_frames['total_volume'].replace(0, float('nan'))
).fillna(0)

rolling_low = df_all_frames['low'].rolling(window=RANGE_POSITION_WINDOW, min_periods=1).min()
rolling_high = df_all_frames['high'].rolling(window=RANGE_POSITION_WINDOW, min_periods=1).max()
range_width = rolling_high - rolling_low
df_all_frames['range_position'] = ((df_all_frames['close'] - rolling_low) / range_width.replace(0, float('nan'))).fillna(0.5)

df_all_frames['trend_state'] = 'NEUTRAL'
df_all_frames.loc[df_all_frames['ema_spread'] > df_all_frames['atr'] * 0.25, 'trend_state'] = 'UP'
df_all_frames.loc[df_all_frames['ema_spread'] < -df_all_frames['atr'] * 0.25, 'trend_state'] = 'DOWN'
print("[OK] Context indicators calculated")

# Save to CSV in strat_trinchera/outputs folder with date from source file
OUTPUTS_DIR = CURRENT_DIR / "outputs"
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
# Extract date from source filename (e.g., time_and_sales_nq_20251022.csv -> 20251022)
import re
date_match = re.search(r'_(\d{8})\.csv', csv_path.name)
date_str = date_match.group(1) if date_match else datetime.now().strftime("%Y%m%d")
output_csv = OUTPUTS_DIR / f"db_trinchera_all_data_{date_str}.csv"
df_all_frames.to_csv(output_csv, index=False, sep=';', decimal=',')

print("\n" + "=" * 60)
print("RESULTS SUMMARY")
print("=" * 60)
print(f"Total frames processed: {len(df_all_frames)}")
print(f"Output file: {output_csv}")
print(f"File size: {output_csv.stat().st_size / (1024*1024):.2f} MB")
print("\nColumns included:")
for col in df_all_frames.columns:
    print(f"  - {col}")

print("\n" + "=" * 60)
print("Sample statistics:")
print("=" * 60)
print(f"Average volume per frame: {df_all_frames['total_volume'].mean():.2f}")
print(f"Average BID/ASK ratio: {df_all_frames['bid_ask_ratio'].mean():.2f}")
print(f"Average price levels: {df_all_frames['num_price_levels'].mean():.2f}")
print(f"Max price range in frame: {df_all_frames['price_range'].max():.2f}")
print(f"Total price changes > 0: {len(df_all_frames[df_all_frames['price_change'] > 0])}")
print(f"Total price changes < 0: {len(df_all_frames[df_all_frames['price_change'] < 0])}")

print("\n" + "=" * 60)
print("[SUCCESS] Processing completed!")
print("=" * 60)
