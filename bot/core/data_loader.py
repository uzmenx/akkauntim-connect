import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime
import time

class BacktestDataLoader:
    def __init__(self):
        pass
        
    def fetch_history(self, symbol: str, timeframe: int, date_from: datetime, date_to: datetime) -> pd.DataFrame:
        """
        MetaTrader5 orqali tarixiy kandelstik ma'lumotlarni yuklab oladi.
        Agar MT5 ishlamayotgan bo'lsa, dummy (soxta) ma'lumot qaytaradi.
        """
        if not mt5.initialize():
            print("MT5 bilan ulanib bo'lmadi, dummy ma'lumot yaratilmoqda...")
            return self._generate_dummy_data(date_from, date_to)

        rates = mt5.copy_rates_range(symbol, timeframe, date_from, date_to)
        
        if rates is None or len(rates) == 0:
            print(f"{symbol} bo'yicha ma'lumot topilmadi, dummy ma'lumot yaratilmoqda...")
            return self._generate_dummy_data(date_from, date_to)
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df
        
    def _generate_dummy_data(self, start: datetime, end: datetime) -> pd.DataFrame:
        """Testing uchun tasodifiy (tebranuvchan) dummy ma'lumotlar."""
        import random
        import math
        
        periods = int((end.timestamp() - start.timestamp()) / 3600)
        dates = pd.date_range(start=start, end=end, periods=max(10, periods))
        
        current_price = 1.1000
        opens, highs, lows, closes = [], [], [], []
        
        # Sine wave + random noise to create realistic swings
        for i in range(len(dates)):
            trend = math.sin(i / 20.0) * 0.005  # Macro trend wave
            noise = (random.random() - 0.5) * 0.004 # Micro noise
            
            step = trend + noise
            
            op = current_price
            cl = current_price + step
            hi = max(op, cl) + (random.random() * 0.002)
            lo = min(op, cl) - (random.random() * 0.002)
            
            opens.append(op)
            highs.append(hi)
            lows.append(lo)
            closes.append(cl)
            
            current_price = cl
            
        df = pd.DataFrame({
            'time': dates,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'tick_volume': [random.randint(100, 500) for _ in range(len(dates))],
            'spread': [random.randint(1, 3) for _ in range(len(dates))]
        })
        return df
