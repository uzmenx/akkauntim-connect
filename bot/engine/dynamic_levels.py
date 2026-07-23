"""
dynamic_levels.py
=================
Bozor strukturasi (OB, FVG) va ATR asosida Dinamik SL (Stop Loss) va TP (Take Profit)
darajalarini hisoblaydigan maxsus modul.

Qoidalar:
- SL = Eng yaqin zona (OB/FVG) + ATR * 0.3 (qopqon/buffer). Minimal SL = ATR * 1.5.
- TP1 (70% yopish uchun) = Eng yaqin qarama-qarshi zona.
- TP2 (30% trailing) = Harmonic fib darajasi yoki keyingi zona.
- Minimal Risk:Reward (R:R) = 1:1.5. Aks holda bitim bekor qilinadi.
"""

from typing import Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

def calculate_dynamic_levels(
    signal: str,
    current_price: float,
    smc_data: Dict[str, Any],
    harmonic_data: Dict[str, Any],
    atr_pips: float,
    pip_divisor: float
) -> Dict[str, Any]:
    """
    Dinamik SL, TP1, TP2 va RR ni hisoblaydi.
    """
    # Xavfsizlik tekshiruvlari
    if not signal or signal == "HOLD":
        return _invalid_result("Signal HOLD yoki yo'q.")
        
    atr_pips = max(atr_pips, 10.0) # Minimal ATR
    atr_price_val = atr_pips * pip_divisor
    min_sl_price_val = (atr_pips * 1.5) * pip_divisor
    buffer_val = (atr_pips * 0.3) * pip_divisor
    
    sl_price = 0.0
    tp1_price = 0.0
    tp2_price = 0.0
    
    # Zonalarni yig'ish
    obs = smc_data.get("order_blocks", {})
    fvgs = smc_data.get("fvg", {})
    
    demand_zones = obs.get("demand", []) + fvgs.get("demand", [])
    supply_zones = obs.get("supply", []) + fvgs.get("supply", [])
    
    # Faqat fresh zonalarni qoldirish va narxga nisbatan saralash
    demand_zones = [z for z in demand_zones if z.get("status") == "fresh" and z.get("top", 0) < current_price]
    demand_zones.sort(key=lambda x: x.get("top", 0), reverse=True) # Eng yaqini birinchi
    
    supply_zones = [z for z in supply_zones if z.get("status") == "fresh" and z.get("bottom", 0) > current_price]
    supply_zones.sort(key=lambda x: x.get("bottom", 0)) # Eng yaqini birinchi

    # =========================================================
    # 1. SL HISOBLASH (Qopqon himoyasi bilan)
    # =========================================================
    if signal == "BUY":
        if demand_zones:
            nearest_demand = demand_zones[0]
            zone_bottom = nearest_demand.get("bottom", current_price - min_sl_price_val)
            sl_price = zone_bottom - buffer_val
        else:
            sl_price = current_price - min_sl_price_val
            
        # Minimal SL qoidasi (ATR * 1.5 dan kichik bo'lmasin)
        if (current_price - sl_price) < min_sl_price_val:
            sl_price = current_price - min_sl_price_val
            
    elif signal == "SELL":
        if supply_zones:
            nearest_supply = supply_zones[0]
            zone_top = nearest_supply.get("top", current_price + min_sl_price_val)
            sl_price = zone_top + buffer_val
        else:
            sl_price = current_price + min_sl_price_val
            
        if (sl_price - current_price) < min_sl_price_val:
            sl_price = current_price + min_sl_price_val
            
    sl_pips = abs(current_price - sl_price) / pip_divisor
    sl_pips = round(max(sl_pips, 10.0)) # kamida 10 pip

    # =========================================================
    # 2. TP1 HISOBLASH (Eng yaqin qarama-qarshi zona)
    # =========================================================
    if signal == "BUY":
        if supply_zones:
            tp1_price = supply_zones[0].get("bottom", current_price + (sl_pips * 2 * pip_divisor))
        else:
            tp1_price = current_price + (sl_pips * 2.0 * pip_divisor) # Standart 1:2
            
    elif signal == "SELL":
        if demand_zones:
            tp1_price = demand_zones[0].get("top", current_price - (sl_pips * 2 * pip_divisor))
        else:
            tp1_price = current_price - (sl_pips * 2.0 * pip_divisor) # Standart 1:2
            
    tp1_pips = abs(tp1_price - current_price) / pip_divisor
    
    # R:R 1.5 dan kichik bo'lsa, TP1 ni biroz uzoqlashtirish (majburiy target)
    if tp1_pips < sl_pips * 1.5:
        tp1_pips = sl_pips * 1.5
        if signal == "BUY":
            tp1_price = current_price + (tp1_pips * pip_divisor)
        else:
            tp1_price = current_price - (tp1_pips * pip_divisor)

    tp1_pips = round(tp1_pips)

    # =========================================================
    # 3. TP2 HISOBLASH (Harmonic Fib yoki TP1 * 1.5)
    # =========================================================
    fib_tp = harmonic_data.get("fib_tp")
    if fib_tp:
        tp2_price = fib_tp
    else:
        # Keyingi zonani qidirish
        if signal == "BUY":
            if len(supply_zones) > 1:
                tp2_price = supply_zones[1].get("bottom", current_price + (tp1_pips * 1.5 * pip_divisor))
            else:
                tp2_price = current_price + (tp1_pips * 1.5 * pip_divisor)
        elif signal == "SELL":
            if len(demand_zones) > 1:
                tp2_price = demand_zones[1].get("top", current_price - (tp1_pips * 1.5 * pip_divisor))
            else:
                tp2_price = current_price - (tp1_pips * 1.5 * pip_divisor)
                
    tp2_pips = abs(tp2_price - current_price) / pip_divisor
    
    # TP2 har doim TP1 dan katta bo'lishi shart
    if tp2_pips <= tp1_pips:
        tp2_pips = tp1_pips * 1.5
        if signal == "BUY":
            tp2_price = current_price + (tp2_pips * pip_divisor)
        else:
            tp2_price = current_price - (tp2_pips * pip_divisor)
            
    tp2_pips = round(tp2_pips)

    # =========================================================
    # 4. YAKUNIY R:R VA TASDIQ
    # =========================================================
    # Asosiy qaror TP1 ga qarab olinadi (chunki hajmining 70% shunda yopiladi)
    rr = round(tp1_pips / sl_pips, 2)
    
    is_valid = rr >= 1.5
    
    reason = "Valid" if is_valid else f"R:R juda past ({rr} < 1.5). TP1 zonasiga masofa yetarli emas."
    
    return {
        "is_valid": is_valid,
        "reason": reason,
        "sl_pips": sl_pips,
        "sl_price": sl_price,
        "tp1_pips": tp1_pips,
        "tp1_price": tp1_price,
        "tp2_pips": tp2_pips,
        "tp2_price": tp2_price,
        "rr": rr
    }

def _invalid_result(reason: str) -> Dict[str, Any]:
    return {
        "is_valid": False,
        "reason": reason,
        "sl_pips": 0,
        "sl_price": 0.0,
        "tp1_pips": 0,
        "tp1_price": 0.0,
        "tp2_pips": 0,
        "tp2_price": 0.0,
        "rr": 0.0
    }
