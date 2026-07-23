"""
mtf_confirm.py
==============
Multi-Timeframe Confirmation moduli.
Asosiy taymfreymdagi (masalan, H1) signalni kichik taymfreym (M5) dagi
harakat bilan tasdiqlaydi.

Mantiq:
1. H1 dan signal keldi (masalan, BUY).
2. M5 dagi oxirgi 15-20 ta sham tahlil qilinadi.
3. Tasdiqlash shartlari (BUY uchun):
   - M5 da ChoCh yoki BoS Bullish bo'lganmi?
   - M5 da fresh demand OB/FVG hosil bo'lganmi?
   - M5 momentum (oxirgi 3-5 sham) yuqoriga qaraganmi?
"""

import logging
import pandas as pd
from typing import Dict, Any, Tuple

logger = logging.getLogger(__name__)

def check_mtf_confirmation(
    signal: str, 
    df_minor: pd.DataFrame, 
    smc_minor: Dict[str, Any],
    lookback_bars: int = 15
) -> Tuple[bool, str]:
    """
    Kichik taymfreymda (M5) signalni tasdiqlaydi.
    
    Args:
        signal: Asosiy taymfreym signali ("BUY" yoki "SELL")
        df_minor: Kichik taymfreym OHLC ma'lumotlari (M5)
        smc_minor: Kichik taymfreym SMC tahlili
        lookback_bars: Qancha orqaga qarash
        
    Returns:
        (tasdiqlandi: bool, sabab: str)
    """
    if signal not in ["BUY", "SELL"]:
        return True, "Signal HOLD - MTF tasdiq shart emas"
        
    if df_minor is None or df_minor.empty or len(df_minor) < lookback_bars:
        logger.warning("MTF tasdiq uchun M5 ma'lumotlari yetarli emas.")
        return True, "Ma'lumot yetarli emas, tasdiq o'tkazib yuborildi."
        
    if smc_minor is None:
        smc_minor = {}

    target_direction = "demand" if signal == "BUY" else "supply"
    
    # 1. Momentum tekshiruvi (oxirgi 3 sham)
    recent_candles = df_minor.iloc[-3:]
    bullish_candles = sum(1 for i, row in recent_candles.iterrows() if row['close'] > row['open'])
    bearish_candles = sum(1 for i, row in recent_candles.iterrows() if row['close'] < row['open'])
    
    momentum_aligned = False
    if signal == "BUY" and bullish_candles >= 2:
        momentum_aligned = True
    elif signal == "SELL" and bearish_candles >= 2:
        momentum_aligned = True

    # 2. M5 dagi Structure Break tekshiruvi (oxirgi 15-20 sham ichida)
    structure_aligned = False
    last_bos = smc_minor.get("last_bos", {})
    last_choch = smc_minor.get("last_choch", {})
    
    current_index = len(df_minor) - 1
    
    # Agar ChoCh yoki BoS yaqinda bo'lgan bo'lsa va yo'nalishi to'g'ri bo'lsa
    if last_choch:
        bars_since_choch = current_index - last_choch.get("bar_index", 0)
        if bars_since_choch <= lookback_bars:
            choch_type = last_choch.get("type", "")
            if signal == "BUY" and "Bullish" in choch_type:
                structure_aligned = True
            elif signal == "SELL" and "Bearish" in choch_type:
                structure_aligned = True
                
    if not structure_aligned and last_bos:
        bars_since_bos = current_index - last_bos.get("bar_index", 0)
        if bars_since_bos <= lookback_bars:
            bos_type = last_bos.get("type", "")
            if signal == "BUY" and "Bullish" in bos_type:
                structure_aligned = True
            elif signal == "SELL" and "Bearish" in bos_type:
                structure_aligned = True

    # 3. M5 dagi Fresh zonalar tekshiruvi (yo'nalishni tasdiqlovchi zona bormi?)
    zones_aligned = False
    obs = smc_minor.get("order_blocks", {}).get(target_direction, [])
    fvgs = smc_minor.get("fvg", {}).get(target_direction, [])
    
    # Yaqinda shakllangan fresh zonalar borligini tekshirish
    for ob in obs:
        if ob.get("status") == "fresh":
            bars_since = current_index - ob.get("bar_index", 0)
            if bars_since <= lookback_bars:
                zones_aligned = True
                break
                
    if not zones_aligned:
        for fvg in fvgs:
            if fvg.get("status") == "fresh":
                bars_since = current_index - fvg.get("bar_index", 0)
                if bars_since <= lookback_bars:
                    zones_aligned = True
                    break

    # Qaror chiqarish: Tasdiq uchun kamida 2 ta omil mos kelishi kerak
    score = 0
    reasons = []
    
    if momentum_aligned:
        score += 1
        reasons.append("M5 Momentum")
    if structure_aligned:
        score += 2  # Structure eng muhimi
        reasons.append("M5 Structure Break")
    if zones_aligned:
        score += 1
        reasons.append("M5 Fresh Zone")
        
    if score >= 2:
        return True, f"MTF tasdiqlandi: {', '.join(reasons)}"
    else:
        return False, "Kichik taymfreym tasdiqlamadi (qarshi trend)."
