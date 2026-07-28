"""
bot/strategy/anti_manipulation/engine.py
======================================
Stop-Hunter Shield algoritmi (ATR + SMC).
Bu yordamchi strategiya AI ga xavfsiz Stop-Loss zonalarini taklif qiladi
va Retail treyderlarning "stoplari ovlanadigan" zonalardan (Liquidity Pools/Order Blocks) 
uzoqroq turishni maslahat beradi.
"""

import logging
import pandas as pd
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

def analyze_stop_hunting_risk(df: pd.DataFrame, smc_data: Dict[str, Any], current_price: float, atr: float) -> str:
    """
    AI uchun Stop-Hunting riskini tahlil qiladi va xavfsiz SL narxlarini taklif etadi.
    """
    if df is None or df.empty or atr <= 0:
        return "Stop-Hunter Shield: Tahlil uchun ma'lumot yetarli emas."
        
    try:
        zones = smc_data.get("zones", [])
        if not zones:
            return f"Stop-Hunter Shield: ATR asosidagi standart xavfsiz SL masofasi ~ {round(atr * 1.5, 5)} (Liquidity Pool'lar topilmadi)."

        # Standart ATR asosida taxminiy stoplar (masalan: 1.5 ATR)
        atr_multiplier = 1.5
        standard_long_sl = current_price - (atr * atr_multiplier)
        standard_short_sl = current_price + (atr * atr_multiplier)
        
        danger_long = False
        danger_short = False
        safe_long_sl = standard_long_sl
        safe_short_sl = standard_short_sl
        
        long_danger_zone = ""
        short_danger_zone = ""
        
        for z in zones:
            top = z.get('top', z.get('price', 0))
            bottom = z.get('bottom', z.get('price', 0))
            if top == 0 and bottom == 0:
                continue
                
            zone_type = z.get('type', 'Zone')
            
            # Long pozitsiyasi uchun stop zonani tekshirish
            if bottom <= standard_long_sl <= top:
                danger_long = True
                # Stoplarni ovchilardan himoya qilish uchun zonaning TAgidan yana biroz (masalan 0.2 ATR) tushamiz
                safe_long_sl = min(safe_long_sl, bottom - (atr * 0.2))
                long_danger_zone = f"{zone_type} ({bottom}-{top})"
                
            # Short pozitsiyasi uchun stop zonani tekshirish
            if bottom <= standard_short_sl <= top:
                danger_short = True
                # Stoplarni ovchilardan himoya qilish uchun zonaning TEPAsidan yana biroz chiqamiz
                safe_short_sl = max(safe_short_sl, top + (atr * 0.2))
                short_danger_zone = f"{zone_type} ({bottom}-{top})"
        
        messages = ["🛡️ STOP-HUNTER SHIELD (Anti-Manipulation):"]
        
        if danger_long:
            messages.append(f"- LONG uchun XAVF: Sening standart stopying {long_danger_zone} ichiga tushmoqda. Bu yerda yirik treyderlar seni \"ovlashi\" mumkin!")
            messages.append(f"  > Tavsiya etilgan eng xavfsiz LONG SL: {round(safe_long_sl, 5)} (zonadan tashqarida)")
        else:
            messages.append(f"- LONG uchun tavsiya etilgan (ATR) xavfsiz SL masofasi narxdan pastda: ~ {round(standard_long_sl, 5)}")
            
        if danger_short:
            messages.append(f"- SHORT uchun XAVF: Sening standart stopying {short_danger_zone} ichiga tushmoqda. Bu yerda yirik treyderlar seni \"ovlashi\" mumkin!")
            messages.append(f"  > Tavsiya etilgan eng xavfsiz SHORT SL: {round(safe_short_sl, 5)} (zonadan tashqarida)")
        else:
            messages.append(f"- SHORT uchun tavsiya etilgan (ATR) xavfsiz SL masofasi narxdan tepada: ~ {round(standard_short_sl, 5)}")

        return "\n".join(messages)

    except Exception as e:
        logger.error(f"Stop-Hunter Shield tahlil xatosi: {e}")
        return f"Stop-Hunter Shield: Xatolik - {e}"
