import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

# MT5 ga ulanish
if not mt5.initialize():
    print("Ulanishda xatolik:", mt5.last_error())
    quit()

symbol = "EURUSD"

# So'nggi 100 ta H1 (1 soatlik) sham ma'lumotini olish
rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 100)

# So'nggi 100 ta M5 (5 daqiqalik) sham ma'lumotini olish
rates_m5 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 100)

# Pandas jadvaliga aylantirish (ishlash qulay bo'lishi uchun)
df_h1 = pd.DataFrame(rates_h1)
df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')

df_m5 = pd.DataFrame(rates_m5)
df_m5['time'] = pd.to_datetime(df_m5['time'], unit='s')

print("=== H1 (1 soatlik) so'nggi 5 ta sham ===")
print(df_h1[['time', 'open', 'high', 'low', 'close']].tail())

print("\n=== M5 (5 daqiqalik) so'nggi 5 ta sham ===")
print(df_m5[['time', 'open', 'high', 'low', 'close']].tail())

mt5.shutdown()