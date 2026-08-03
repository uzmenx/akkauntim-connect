"""
EURUSD H1 uchun to'liq SMC tahlil — TradingView bilan solishtirish uchun.
Barcha OB, FVG, BoS/ChoCh, trend va liquidity ma'lumotlarini chiqaradi.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import MetaTrader5 as mt5
import pandas as pd
import json
from datetime import datetime
from smc_engine import analyze_market_structure

if not mt5.initialize():
    print(f"MT5 xatolik: {mt5.last_error()}")
    sys.exit(1)

symbol = "EURUSD"
rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 200)
mt5.shutdown()

if rates is None or len(rates) == 0:
    print("Data olib bo'lmadi")
    sys.exit(1)

df = pd.DataFrame(rates)
df["timestamp"] = pd.to_datetime(df["time"], unit="s")
df = df[["timestamp", "open", "high", "low", "close", "tick_volume"]].rename(
    columns={"tick_volume": "volume"}
)

print(f"{'='*80}")
print(f"  EURUSD H1 — SMC ENGINE TO'LIQ TAHLIL")
print(f"  Data: {df['timestamp'].iloc[0]} -> {df['timestamp'].iloc[-1]}")
print(f"  Barlar soni: {len(df)}")
print(f"  Pivot Period: 5 | OB Validity: 500 | Refine: Defensive")
print(f"{'='*80}")

result = analyze_market_structure(df, {
    "pivot_period": 5,
    "ob_validity_bars": 500,
    "ob_refine": True,
    "ob_refine_method": "Defensive",
    "fvg_filter": True,
    "fvg_filter_type": "Defensive",
    "static_pivot_period": 8,
    "dynamic_pivot_period": 3,
    "static_liquidity_sensitivity": 0.30,
    "dynamic_liquidity_sensitivity": 1.00,
})

# ========== 1. TREND va NARX ==========
print(f"\n{'─'*80}")
print(f"  1. TREND VA JORIY NARX")
print(f"{'─'*80}")
print(f"  Joriy narx:     {result['current_price']}")
print(f"  Tashqi (Major): {result['trend']['external']}")
print(f"  Ichki (Minor):  {result['trend']['internal']}")

# ========== 2. BARCHA BoS / ChoCh HODISALARI ==========
print(f"\n{'─'*80}")
print(f"  2. BARCHA BoS / ChoCh HODISALARI (TradingView chiziqlar bilan solishtiring)")
print(f"{'─'*80}")

# SMCStructure dan to'liq event ro'yxatini olish
from smc_structure import SMCStructure
smc = SMCStructure(pivot_period=5)
smc.run(df["high"].tolist(), df["low"].tolist(), df["close"].tolist())

print(f"  {'#':<4} {'Bar':<6} {'Vaqt':<22} {'Daraja':<8} {'Turi':<8} {'Yonalish':<10} {'Narx':<12}")
print(f"  {'─'*4} {'─'*6} {'─'*22} {'─'*8} {'─'*8} {'─'*10} {'─'*12}")

for i, ev in enumerate(smc.events):
    ts = str(df['timestamp'].iloc[ev.bar_index]) if ev.bar_index < len(df) else "N/A"
    print(f"  {i+1:<4} {ev.bar_index:<6} {ts:<22} {ev.level:<8} {ev.kind:<8} {ev.direction:<10} {ev.price:<12.5f}")

print(f"\n  Jami: {len(smc.events)} ta hodisa")
print(f"  Oxirgi BoS:   {result['last_bos']}")
print(f"  Oxirgi ChoCh: {result['last_choch']}")

# ========== 3. BARCHA ORDER BLOCK'LAR ==========
print(f"\n{'─'*80}")
print(f"  3. BARCHA ORDER BLOCK'LAR (TradingView box'lar bilan solishtiring)")
print(f"{'─'*80}")

print(f"\n  --- DEMAND (Bullish) Order Blocks ---")
print(f"  {'#':<4} {'Bar':<6} {'Vaqt':<22} {'Bottom':<12} {'Top':<12} {'Origin':<14} {'Level':<8} {'Status':<10} {'Dist%':<8}")
print(f"  {'─'*4} {'─'*6} {'─'*22} {'─'*12} {'─'*12} {'─'*14} {'─'*8} {'─'*10} {'─'*8}")

for i, ob in enumerate(result["order_blocks"]["demand"]):
    ts = ob.get("timestamp", "N/A")
    if ts and ts != "None":
        ts = str(ts)[:19]
    else:
        ts = "N/A"
    print(f"  {i+1:<4} {ob['bar_index']:<6} {ts:<22} {ob['bottom']:<12.5f} {ob['top']:<12.5f} {ob['origin']:<14} {ob['level']:<8} {ob['status']:<10} {ob['distance_pct']:<8.3f}")

print(f"\n  --- SUPPLY (Bearish) Order Blocks ---")
print(f"  {'#':<4} {'Bar':<6} {'Vaqt':<22} {'Bottom':<12} {'Top':<12} {'Origin':<14} {'Level':<8} {'Status':<10} {'Dist%':<8}")
print(f"  {'─'*4} {'─'*6} {'─'*22} {'─'*12} {'─'*12} {'─'*14} {'─'*8} {'─'*10} {'─'*8}")

for i, ob in enumerate(result["order_blocks"]["supply"]):
    ts = ob.get("timestamp", "N/A")
    if ts and ts != "None":
        ts = str(ts)[:19]
    else:
        ts = "N/A"
    print(f"  {i+1:<4} {ob['bar_index']:<6} {ts:<22} {ob['bottom']:<12.5f} {ob['top']:<12.5f} {ob['origin']:<14} {ob['level']:<8} {ob['status']:<10} {ob['distance_pct']:<8.3f}")

total_d = len(result["order_blocks"]["demand"])
total_s = len(result["order_blocks"]["supply"])
fresh_d = sum(1 for ob in result["order_blocks"]["demand"] if ob["status"] == "fresh")
fresh_s = sum(1 for ob in result["order_blocks"]["supply"] if ob["status"] == "fresh")
print(f"\n  Jami Demand OB: {total_d} ({fresh_d} fresh)")
print(f"  Jami Supply OB: {total_s} ({fresh_s} fresh)")

# ========== 4. BARCHA FVG'LAR ==========
print(f"\n{'─'*80}")
print(f"  4. BARCHA FVG'LAR (TradingView FVG zonalari bilan solishtiring)")
print(f"{'─'*80}")

print(f"\n  --- DEMAND FVG (Bullish gap) ---")
print(f"  {'#':<4} {'Bar':<6} {'Vaqt':<22} {'Bottom':<12} {'Top':<12} {'Gap Size':<12} {'Status':<10}")
print(f"  {'─'*4} {'─'*6} {'─'*22} {'─'*12} {'─'*12} {'─'*12} {'─'*10}")

for i, fvg in enumerate(result["fvg"]["demand"]):
    ts = fvg.get("timestamp", "N/A")
    if ts and ts != "None":
        ts = str(ts)[:19]
    else:
        ts = "N/A"
    print(f"  {i+1:<4} {fvg['bar_index']:<6} {ts:<22} {fvg['bottom']:<12.5f} {fvg['top']:<12.5f} {fvg['gap_size']:<12.5f} {fvg['status']:<10}")

print(f"\n  --- SUPPLY FVG (Bearish gap) ---")
print(f"  {'#':<4} {'Bar':<6} {'Vaqt':<22} {'Bottom':<12} {'Top':<12} {'Gap Size':<12} {'Status':<10}")
print(f"  {'─'*4} {'─'*6} {'─'*22} {'─'*12} {'─'*12} {'─'*12} {'─'*10}")

for i, fvg in enumerate(result["fvg"]["supply"]):
    ts = fvg.get("timestamp", "N/A")
    if ts and ts != "None":
        ts = str(ts)[:19]
    else:
        ts = "N/A"
    print(f"  {i+1:<4} {fvg['bar_index']:<6} {ts:<22} {fvg['bottom']:<12.5f} {fvg['top']:<12.5f} {fvg['gap_size']:<12.5f} {fvg['status']:<10}")

total_fd = len(result["fvg"]["demand"])
total_fs = len(result["fvg"]["supply"])
fresh_fd = sum(1 for f in result["fvg"]["demand"] if f["status"] == "fresh")
fresh_fs = sum(1 for f in result["fvg"]["supply"] if f["status"] == "fresh")
print(f"\n  Jami Demand FVG: {total_fd} ({fresh_fd} fresh)")
print(f"  Jami Supply FVG: {total_fs} ({fresh_fs} fresh)")

# ========== 5. LIQUIDITY ==========
print(f"\n{'─'*80}")
print(f"  5. LIQUIDITY DARAJALARI")
print(f"{'─'*80}")
liq = result["liquidity"]
print(f"  Statik High (SPP=8):   {liq['static_high']}")
print(f"  Statik Low (SPP=8):    {liq['static_low']}")
print(f"  Dinamik High (DPP=3):  {liq['dynamic_high']}")
print(f"  Dinamik Low (DPP=3):   {liq['dynamic_low']}")

# ========== 6. PIVOT / SWING NUQTALAR ==========
print(f"\n{'─'*80}")
print(f"  6. MAJOR / MINOR PIVOT NUQTALAR (oxirgi 20 ta)")
print(f"{'─'*80}")
print(f"  {'#':<4} {'Bar':<6} {'Vaqt':<22} {'Turi':<8} {'Narx':<12}")
print(f"  {'─'*4} {'─'*6} {'─'*22} {'─'*8} {'─'*12}")

# adv_type/adv_value/adv_index dan oxirgi 20 tasini chiqarish
show_count = min(20, len(smc.adv_type))
start_idx = len(smc.adv_type) - show_count
for j in range(start_idx, len(smc.adv_type)):
    bar_i = smc.adv_index[j]
    ts = str(df['timestamp'].iloc[bar_i])[:19] if bar_i < len(df) else "N/A"
    print(f"  {j+1:<4} {bar_i:<6} {ts:<22} {smc.adv_type[j]:<8} {smc.adv_value[j]:<12.5f}")

print(f"\n  Major High: {smc.major_high} (bar {smc.major_high_idx})")
print(f"  Major Low:  {smc.major_low} (bar {smc.major_low_idx})")
print(f"  Minor High: {smc.minor_high} (bar {smc.minor_high_idx})")
print(f"  Minor Low:  {smc.minor_low} (bar {smc.minor_low_idx})")

# ========== 7. TO'LIQ JSON ==========
print(f"\n{'─'*80}")
print(f"  7. TO'LIQ JSON OUTPUT")
print(f"{'─'*80}")
print(json.dumps(result, indent=2, default=str))

print(f"\n{'='*80}")
print(f"  TAHLIL TUGADI — yuqoridagi natijalarni TradingView bilan solishtiring")
print(f"{'='*80}")
