import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from smc_structure import SMCStructure

def generate_mock_data(n_bars=500):
    """SMC BoS/ChoCh sinovlari uchun trend va tebranishlarga ega mock narx ma'lumotlarini yaratadi"""
    np.random.seed(42)
    times = [datetime.now() - timedelta(hours=i) for i in range(n_bars)][::-1]
    
    # Trend va tsiklik o'zgarishlar bilan narx oqimini simulyatsiya qilamiz
    x = np.linspace(0, 10 * np.pi, n_bars)
    # Katta to'lqinlar (major trend) + kichik to'lqinlar (minor trend) + shovqin
    base_price = 1.1000 + 0.015 * np.sin(x) + 0.005 * np.sin(3 * x) - 0.00005 * np.arange(n_bars)
    
    # High, Low, Open, Close larni shakllantirish
    noise = np.random.normal(0, 0.001, n_bars)
    close_prices = base_price + noise
    open_prices = np.roll(close_prices, 1)
    open_prices[0] = close_prices[0] - 0.0005
    
    highs = []
    lows = []
    for o, c in zip(open_prices, close_prices):
        h = max(o, c) + np.abs(np.random.normal(0.0005, 0.0002))
        l = min(o, c) - np.abs(np.random.normal(0.0005, 0.0002))
        highs.append(h)
        lows.append(l)
        
    df = pd.DataFrame({
        'time': times,
        'open': open_prices,
        'high': highs,
        'low': lows,
        'close': close_prices
    })
    return df

def main():
    # 1. MT5 ga ulanish
    rates = None
    if mt5.initialize():
        print("MT5 terminaliga ulanish muvaffaqiyatli.")
        symbol = "EURUSD"
        # So'nggi 500 ta H1 sham ma'lumotini olamiz
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 500)
        mt5.shutdown()
    else:
        print("MT5 ulanishda xatolik (IPC timeout yoki terminal yopiq).")
        print("SMCStructure'ni tekshirish uchun mock (simulyatsiya qilingan) narxlardan foydalanamiz...")

    if rates is not None and len(rates) > 0:
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        print(f"=== MT5'dan EURUSD H1 ma'lumotlari yuklandi. Jami: {len(df)} ta bar ===")
    else:
        df = generate_mock_data(500)
        print(f"=== Mock ma'lumotlar yaratildi. Jami: {len(df)} ta bar ===")
    
    # 2. SMCStructure ni ishga tushirish
    # Pivot periodni 5 deb belgilaymiz
    smc = SMCStructure(pivot_period=5)
    
    highs = df['high'].tolist()
    lows = df['low'].tolist()
    closes = df['close'].tolist()
    
    events = smc.run(highs, lows, closes)
    
    # 3. Natijalarni chiqarish
    print(f"\nSMC hisoblandi. Jami sving nuqtalar: {len(smc.swings)}")
    print(f"Jami aniqlangan trend sinishlari (BoS/ChoCh): {len(events)}\n")
    
    # Oxirgi 15 ta hodisani ko'rsatish
    print("=== OXIRGI 15 TA BOS/CHOCH HODISALARI ===")
    for ev in events[-15:]:
        # original bar vaqtini topamiz
        bar_time = df.loc[ev.bar_index, 'time']
        print(f"Bar: {ev.bar_index} ({bar_time}) | {ev.level} | {ev.direction} {ev.kind} | Price: {ev.price:.5f}")

    # Oxirgi holat/kontekst
    print("\n=== OXIRGI SMC KONTEKSTI (AI uchun) ===")
    context = smc.latest_context()
    for k, v in context.items():
        print(f"{k}: {v}")

if __name__ == "__main__":
    main()
