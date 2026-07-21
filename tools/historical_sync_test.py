"""
historical_sync_test.py
=======================
Ushbu skript MT5 dan katta hajmdagi tarixiy ma'lumotni oladi, 
SMC Engine orqali tahlil qilib, natijani ZoneManager orqali SQLite 
bazasiga yozadi. Keyin AI ga qanday prompt yuborilishini simulyatsiya qiladi.
"""

import sys
import json
import MetaTrader5 as mt5
import pandas as pd

# Windows cp1251 encoding fix
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from smc_engine import analyze_market_structure
from zone_manager import ZoneManager

def get_mt5_data(symbol: str, timeframe, bars: int) -> pd.DataFrame:
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"Data olib bo'lmadi: {mt5.last_error()}")
    
    df = pd.DataFrame(rates)
    df["timestamp"] = pd.to_datetime(df["time"], unit="s")
    df = df[["timestamp", "open", "high", "low", "close", "tick_volume"]].rename(
        columns={"tick_volume": "volume"}
    )
    return df

def simulate_ai_prompt(symbol: str, current_price: float, nearby_zones: list):
    """AI ga yuboriladigan xabarni shakllantiradi."""
    print(f"\n{'='*60}")
    print(f"🤖 AI PROMPT SIMULATION")
    print(f"{'='*60}")
    print(f"Joriy narx: {current_price}")
    
    if not nearby_zones:
        print("💡 Tizim Xabari: Joriy narx atrofida kuchli tarixiy zonalar yo'q.")
        return
        
    print(f"💡 Tizim Xabari: DIQQAT! Joriy narx ({current_price}) quyidagi {len(nearby_zones)} ta "
          f"tarixiy zonaga yaqinlashmoqda (0.5% masofada):\n")
          
    for z in nearby_zones:
        emoji = "🟩" if z["direction"] == "demand" else "🟥"
        z_type = "Order Block" if z["zone_type"] == "ob" else "Fair Value Gap"
        print(f"  {emoji} {z['direction'].upper()} {z_type}")
        print(f"      Narx zonasi:  {z['bottom_price']} -> {z['top_price']}")
        print(f"      Masofa:       {z['distance_pct']}%")
        print(f"      Yaratilgan:   {z['creation_time']}")
        print(f"      Holati:       {z['status'].upper()} (Hali ochilmagan)")
        if z.get("origin"):
            print(f"      Kelib chiqishi: {z['origin']} ({z['level']})")
        print()
        
    print("AI uchun ko'rsatma: Ushbu zonalardan narxning kuchli qaytish (rejection) ehtimoli yuqori. "
          "Trend va joriy bozor holatini hisobga olib savdo qiling.")

def main():
    if not mt5.initialize():
        print(f"MT5 ulanishda xatolik: {mt5.last_error()}")
        sys.exit(1)

    symbol = "EURUSD"
    # H1 da 5000 bar = taxminan 200 ish kuni (qariyb 9 oy)
    bars_to_fetch = 5000
    tf = mt5.TIMEFRAME_H1
    tf_str = "H1"

    print(f"📊 1. MT5 dan ma'lumot olinmoqda... ({symbol} {tf_str}, {bars_to_fetch} bar)")
    try:
        df = get_mt5_data(symbol, tf, bars_to_fetch)
    except Exception as e:
        print(e)
        mt5.shutdown()
        sys.exit(1)
        
    print(f"   => Olingan oraliq: {df['timestamp'].iloc[0]} dan {df['timestamp'].iloc[-1]} gacha")

    print(f"\n⚙️ 2. SMC Engine orqali tahlil qilinmoqda...")
    # config da ob_validity_bars ni juda katta qilamiz, toki eski OB lar ham hisobga olinsin
    config = {
        "ob_validity_bars": 10000, 
        "ob_refine": True,
        "fvg_filter": True,
        "fvg_filter_type": "Defensive"
    }
    result = analyze_market_structure(df, config)
    
    current_price = result["current_price"]
    print(f"   => Tahlil yakunlandi. Joriy narx: {current_price}")

    print(f"\n💾 3. ZoneManager orqali SQLite bazaga saqlanmoqda...")
    zm = ZoneManager("smc_history.db")
    
    # Yangi zonalarni yozish
    new_zones = zm.save_zones(symbol, tf_str, result)
    print(f"   => Bazaga yozilgan yangi zonalar soni: {new_zones}")
    
    # Joriy narx bo'yicha mitigatsiyalarni tekshirish (oxirgi sham asosida)
    # Eslatma: smc_engine o'zi ham mitigatsiyalarni hisoblaydi, lekin bu method 
    # jonli savdoda har bir tick (yoki M1 bar) da chaqirilishi kerak bo'lgan logika.
    current_high = float(df["high"].iloc[-1])
    current_low = float(df["low"].iloc[-1])
    mitigated = zm.update_mitigations(symbol, tf_str, current_high, current_low)
    print(f"   => Yangi mitigatsiya qilingan zonalar: {mitigated}")

    print(f"\n📈 4. Bazadagi jami statistika ({symbol} {tf_str}):")
    stats = zm.get_stats(symbol, tf_str)
    print(json.dumps(stats, indent=2))

    # AI Prompt simulyatsiyasi (0.5% atrofidagi zonalarni izlash)
    nearby = zm.get_nearby_zones(symbol, tf_str, current_price, threshold_pct=0.5)
    simulate_ai_prompt(symbol, current_price, nearby)

    mt5.shutdown()

if __name__ == "__main__":
    main()
