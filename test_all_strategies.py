import os
import sys
import random
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

# Add workspace root to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging to stdout
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

def generate_realistic_candles(symbol: str, timeframe: str, num_candles=300):
    """
    Kandel malumotlarini generatsiya qiladi (Trend + Wave + Noise).
    """
    now = datetime.now(timezone.utc).replace(microsecond=0)
    
    tf_minutes = 15
    if timeframe == 'M1': tf_minutes = 1
    elif timeframe == 'M5': tf_minutes = 5
    elif timeframe == 'M15': tf_minutes = 15
    elif timeframe == 'H1': tf_minutes = 60
    elif timeframe == 'H4': tf_minutes = 240
    elif timeframe == 'D1': tf_minutes = 1440
    
    # Base price setup based on symbol
    base_price = 1.0500
    if 'BTC' in symbol: base_price = 65000.0
    elif 'XAU' in symbol: base_price = 2300.0
    elif 'US30' in symbol: base_price = 39000.0
    elif 'JPY' in symbol: base_price = 150.0
    
    volatility = base_price * 0.002 # 0.2% volatility per candle
    
    times = []
    opens = []
    highs = []
    lows = []
    closes = []
    volumes = []
    
    current_price = base_price
    for i in range(num_candles):
        # Create a wavy trend so Harmonics/SMC can detect structure
        trend = np.sin(i / 15.0) * volatility * 2
        noise = random.uniform(-volatility, volatility)
        
        c_open = current_price
        c_close = current_price + trend + noise
        c_high = max(c_open, c_close) + random.uniform(0, volatility)
        c_low = min(c_open, c_close) - random.uniform(0, volatility)
        
        times.append(now - timedelta(minutes=tf_minutes * (num_candles - i - 1)))
        opens.append(c_open)
        highs.append(c_high)
        lows.append(c_low)
        closes.append(c_close)
        volumes.append(random.randint(100, 1500))
        
        current_price = c_close
        
    return pd.DataFrame({
        'time': times,
        'open': opens,
        'high': highs,
        'low': lows,
        'close': closes,
        'tick_volume': volumes
    })

def run_tests():
    from bot.main import TradingBot
    from bot.config import BotConfig
    
    # Init bot with mock config
    config = BotConfig(supabase_url="http://dummy", supabase_key="dummy_key")
    bot = TradingBot(config)
    # Hack the sync lock which is usually initialized inside start()
    import threading
    if not hasattr(bot, '_sync_lock'):
        bot._sync_lock = threading.Lock()
        
    # We will test 5 pairs and 5 timeframes
    symbols = ["EURUSD", "GBPUSD", "XAUUSD", "BTCUSD", "US30"]
    timeframes = ["M5", "M15", "H1", "H4", "D1"]
    
    success_count = 0
    error_count = 0
    
    for symbol in symbols:
        for tf in timeframes:
            df = generate_realistic_candles(symbol, tf)
            logging.info(f"Testing {symbol} {tf} ...")
            try:
                # _sync_chart internally calls the 5 strategy managers to get active patterns
                # But we need to first FEED the data to the engine so they have something to "get".
                
                # We can manually trigger the analysis for the 7 strategies here to populate the DB
                # 1. SMC
                smc_res = bot._get_smc_full_analysis(df)
                if smc_res:
                    bot._chart_zone_manager.save_zones(symbol, tf, smc_res)
                    
                # 2. Harmonics
                harm_res = bot._get_harmonic_patterns(df)
                if harm_res:
                    bot._chart_harmonic_manager.save_patterns(symbol, tf, harm_res)
                    
                # 3. Wyckoff
                from bot.strategy.wyckoff.engine import analyze_wyckoff
                wyc_res = analyze_wyckoff(df)
                if wyc_res:
                    bot._chart_wyckoff_manager.save_events(symbol, tf, wyc_res)
                    
                # 4. SR Volume
                sr_res = bot._get_sr_volume_analysis(df)
                if sr_res:
                    bot._chart_sr_volume_manager.save_zones(symbol, tf, sr_res)
                    
                # 5. Auto Patterns
                current_price = df['close'].iloc[-1]
                auto_res = bot._get_auto_patterns_analysis(df, current_price)
                if auto_res:
                    bot._chart_auto_pattern_manager.save_pattern(symbol, tf, auto_res)
                    
                # 6. Kill Zones
                bot._get_kill_zones_analysis(df)
                
                # 7. Trap Detector
                bot._get_trap_detection_analysis(df)
                
                # Now trigger _sync_chart to generate the local JSON
                bot._sync_chart(symbol, tf, df)
                
                # Check if JSON was created
                base_dir = os.path.dirname(os.path.abspath(__file__))
                json_path = os.path.join(base_dir, "public", "data", f"chart_{symbol}_{tf}.json")
                if os.path.exists(json_path):
                    success_count += 1
                else:
                    logging.error(f"Failed to generate JSON for {symbol} {tf}")
                    error_count += 1
                    
            except Exception as e:
                logging.exception(f"Error testing {symbol} {tf}: {e}")
                error_count += 1

    logging.info(f"Test summary: {success_count} SUCCESS, {error_count} ERRORS")

if __name__ == "__main__":
    run_tests()
