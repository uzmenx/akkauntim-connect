"""
bot/strategy/auto_patterns/engine.py
====================================
Auto Chart Patterns strategiyasi uchun asosiy dvigatel.
Zigzag orqali pivotlarni topadi va qaysi figura shakllanganini aniqlaydi.
"""

import logging
import pandas as pd
from typing import Dict, Any, Optional

from .zigzag import find_pivots
from .pattern_math import identify_pattern

logger = logging.getLogger(__name__)

def analyze_auto_patterns(df: pd.DataFrame, current_price: Optional[float] = None, atr: float = 0.0) -> Dict[str, Any]:
    """
    Auto Chart Patterns tahlili.
    
    Qaytaradi:
    {
        "signal": "BUY" | "SELL" | "HOLD" | "NEUTRAL",
        "confidence": int,
        "reasoning": str,
        "pattern_name": str,
        "pivots_found": int
    }
    """
    if df is None or df.empty or len(df) < 50:
        return _empty_result("Ma'lumot yetarli emas")
        
    try:
        if current_price is None:
            current_price = float(df['close'].iloc[-1])
            
        # 1. Zigzag orqali pivotlarni topamiz. Bizga oxirgi pivotlar yetarli.
        # Order 8 - bu Pine Script dagi zigzagLength1 = 8 ga mos.
        pivots = find_pivots(df, order=8)
        
        if len(pivots) < 4:
            return _empty_result("Figurani aniqlash uchun pivotlar yetishmaydi")
            
        # 2. Patternni hisoblash
        result = identify_pattern(pivots, current_price, atr)
        
        return {
            "signal": result["signal"],
            "confidence": result["confidence"],
            "reasoning": result["reasoning"],
            "pattern_name": result["pattern"],
            "pivots_found": len(pivots),
            "slopes": result["slopes"]
        }
        
    except Exception as e:
        logger.error(f"Auto Patterns tahlil xatosi: {e}")
        return _empty_result(f"Xatolik: {e}")

def _empty_result(reason: str) -> Dict[str, Any]:
    return {
        "signal": "NEUTRAL",
        "confidence": 0,
        "reasoning": reason,
        "pattern_name": "None",
        "pivots_found": 0,
        "slopes": {}
    }
