import MetaTrader5 as mt5
import pandas as pd
from harmonic_engine import analyze_harmonic_patterns

def main():
    if not mt5.initialize():
        print("Ulanishda xatolik:", mt5.last_error())
        return

    symbol = "EURUSD"
    # So'nggi 200 ta H1 sham ma'lumotini olish
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 200)
    mt5.shutdown()

    if rates is None:
        print("Ma'lumot olinmadi")
        return

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # Engine requires 'open', 'high', 'low', 'close'
    # df already has these. We can set index to time
    df.set_index('time', inplace=True)
    
    print(f"Boshlang'ich tekshiruv: EURUSD H1 ({len(df)} ta bar)")
    
    # Config bilan ishlatish
    config = {
        'entry_window_rate': 0.236,
        'tp_rate': 0.618,
        'sl_rate': -0.236
    }
    
    result = analyze_harmonic_patterns(df, config)
    
    print(f"\nJoriy Narx: {result['current_price']}")
    print(f"Joriy Signal: {result['signal']}")
    print("\n=== Oxirgi Topilgan Barcha Patternlar ===")
    
    patterns = result['all_detected_patterns']
    if not patterns:
        print("Hech qanday pattern topilmadi.")
    else:
        print(f"{'Nom':<25} | {'Yo\'nalish':<10} | {'D Narx':<10} | {'Bar Index'}")
        print("-" * 65)
        for p in patterns:
            print(f"{p['name']:<25} | {p['direction']:<10} | {p['d_price']:<10.5f} | {p['bar_index']}")

    print("\n=== Kutilayotgan Patternlar (PRZ) ===")
    emerging = result.get('emerging_patterns', [])
    if not emerging:
        print("Ayni paytda kutilayotgan (emerging) patternlar yo'q.")
    else:
        print(f"{'Nom':<25} | {'Yo\'nalish':<10} | {'PRZ Min':<10} | {'PRZ Max':<10}")
        print("-" * 65)
        for p in emerging:
            print(f"{p['name']:<25} | {p['direction']:<10} | {p['prz_min']:<10.5f} | {p['prz_max']:<10.5f}")

if __name__ == "__main__":
    main()
