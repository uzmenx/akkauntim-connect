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
        """Testing uchun dummy ma'lumotlar."""
        # Sodda trend
        periods = int((end.timestamp() - start.timestamp()) / 3600)
        dates = pd.date_range(start=start, end=end, periods=max(10, periods))
        
        df = pd.DataFrame({
            'time': dates,
            'open': [1.0 + (i * 0.001) for i in range(len(dates))],
            'high': [1.0 + (i * 0.001) + 0.002 for i in range(len(dates))],
            'low': [1.0 + (i * 0.001) - 0.002 for i in range(len(dates))],
            'close': [1.0 + (i * 0.001) + 0.001 for i in range(len(dates))],
            'tick_volume': [100 for _ in range(len(dates))],
            'spread': [2 for _ in range(len(dates))]
        })
        return df
