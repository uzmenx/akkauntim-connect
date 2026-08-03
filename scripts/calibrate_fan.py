import os
import sys
import sqlite3
import pandas as pd
import numpy as np

# Loyiha papkasini sys.path ga qo'shish (bot importlari ishlashi uchun)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.prediction.fan_simulator import FanConfig, simulate_fan

def calibrate_fan():
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot_learning.db')
    
    # Tarixiy ma'lumotlarni yuklash
    if not os.path.exists(db_path):
        print(f"Baza topilmadi: {db_path}. Fake data generatsiya qilinmoqda...")
        # 5000 ta tasodifiy narx ketma-ketligi (random walk)
        closes_all = np.cumprod(1 + np.random.normal(0, 0.001, 5000)) * 100
    else:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query("SELECT price_close FROM shadow_states ORDER BY timestamp ASC", conn)
        conn.close()
        
        if len(df) < 500:
            print("Yetarli ma'lumot yo'q, fake data ishlatilmoqda...")
            closes_all = np.cumprod(1 + np.random.normal(0, 0.001, 5000)) * 100
        else:
            closes_all = df['price_close'].values
            print(f"Bazadan {len(closes_all)} ta qator o'qildi.")

    lookback = 100      # Qancha orqaga qarash (volatillikni hisoblash uchun)
    n_steps = 15        # Qancha oldinga bashorat qilish
    
    if len(closes_all) < lookback + n_steps:
        print("Data yetarli emas!")
        return

    # Tekshiriladigan drift kuchaytirgichlar
    multipliers = [0.1, 0.3, 0.5, 0.8, 1.0, 1.5, 2.0]
    
    print("\n" + "="*55)
    print(f"FAN SIMULATOR KALIBRATSIYASI")
    print(f"Target Coverage: ~80% (10-90 percentiles)")
    print(f"{'Multiplier':<12} | {'Coverage (10-90)':<18} | {'Status'}")
    print("-" * 55)
    
    best_mult = None
    best_diff = 100.0
    best_cov = 0.0
    
    for mult in multipliers:
        config = FanConfig(n_paths=100, n_steps=n_steps, seed=42, drift_multiplier=mult)
        hits = 0
        total_tests = 0
        
        # Sliding window orqali tekshirish (har 5 qadamda 1 marta hisoblaymiz, tezroq ishlashi uchun)
        for i in range(lookback, len(closes_all) - n_steps, 5):
            window_closes = closes_all[i - lookback : i]
            actual_future_price = closes_all[i + n_steps - 1]
            
            # Kalibratsiya maqsadida mock signal beramiz
            # Agar oxirgi 10 sham o'sgan bo'lsa BUY, aks holda SELL (Mock Voting Engine)
            if window_closes[-1] > window_closes[-10]:
                direction = "BUY"
            else:
                direction = "SELL"
            
            confidence = 0.8 # Mock confidence
            
            paths = simulate_fan(window_closes, direction, confidence, config)
            
            # paths shape: (n_paths, n_steps). Bizga oxirgi qadamdagi narxlar kerak
            final_prices = paths[:, -1]
            
            p10 = np.percentile(final_prices, 10)
            p90 = np.percentile(final_prices, 90)
            
            if p10 <= actual_future_price <= p90:
                hits += 1
            total_tests += 1
            
        coverage = hits / total_tests if total_tests > 0 else 0
        
        diff_from_target = abs(coverage - 0.80)
        status = "Optimal" if diff_from_target < 0.05 else ("Narrow" if coverage < 0.70 else "Wide")
        
        if diff_from_target < best_diff:
            best_diff = diff_from_target
            best_mult = mult
            best_cov = coverage
            
        print(f"{mult:<12.1f} | {coverage:<18.1%} | {status}")

    print("=" * 55)
    print(f"XULOSA: Eng optimal max_drift_multiplier = {best_mult} (Coverage: {best_cov:.1%})")
    print("Iltimos, ushbu qiymatni bot/prediction/fan_simulator.py faylida asosiy qiymat qilib o'rnating.")
    print("=" * 55)

if __name__ == "__main__":
    calibrate_fan()
