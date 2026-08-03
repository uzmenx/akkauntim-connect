"""
bot/strategy/kill_zones/engine.py
=================================
Savdo sessiyalari va Kill Zonelarni (Ochilish vaqti) aniqlaydigan dvigatel.
"""

import logging
import pandas as pd
from datetime import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

def analyze_kill_zones(df: pd.DataFrame) -> Dict[str, Any]:
    """
    So'nggi sham vaqti (UTC) ga asosan qaysi sessiyada ekanligimizni 
    va Kill Zone'ga to'g'ri kelish-kelmasligini aniqlaydi.
    """
    if df is None or df.empty or 'time' not in df.columns:
        return _empty_result("Bozor vaqti topilmadi (time ustuni yo'q)")
        
    try:
        last_time = pd.to_datetime(df['time'].iloc[-1])
        # Vaqtni soat va daqiqada olamiz
        current_time = last_time.time()
        
        # UTC da sessiya vaqtlari
        # Asian: 00:00 - 09:00
        # London: 07:00 - 16:00
        # NY: 12:00 - 21:00
        
        asian_active = time(0, 0) <= current_time <= time(9, 0)
        london_active = time(7, 0) <= current_time <= time(16, 0)
        ny_active = time(12, 0) <= current_time <= time(21, 0)
        
        # Kill Zones (Ochilishdagi yuqori volatillik vaqtlari)
        asian_kz = time(0, 0) <= current_time <= time(2, 0)
        london_kz = time(7, 0) <= current_time <= time(9, 0)
        ny_kz = time(12, 0) <= current_time <= time(14, 0)
        
        active_sessions = []
        if ny_active: active_sessions.append("New York")
        if london_active: active_sessions.append("London")
        if asian_active: active_sessions.append("Asian")
        
        is_kill_zone = asian_kz or london_kz or ny_kz
        is_dead_zone = not (asian_active or london_active or ny_active)
        is_overlap = london_active and ny_active
        
        active_kz = []
        if ny_kz: active_kz.append("New York KZ")
        if london_kz: active_kz.append("London KZ")
        if asian_kz: active_kz.append("Asian KZ")
        
        # Volatillikni belgilash
        if is_kill_zone:
            volatility = "High"
        elif is_overlap:
            volatility = "High"
        elif not active_sessions:
            volatility = "Low"
        elif active_sessions == ["Asian"]:
            volatility = "Medium-Low"
        else:
            volatility = "Medium"
            
        reasoning = []
        if active_sessions:
            reasoning.append(f"Ochiq: {', '.join(active_sessions)}")
        else:
            reasoning.append("Sessiyalar yopiq (Dead Zone)")
            
        if active_kz:
            reasoning.append(f"Kill Zone: {', '.join(active_kz)}")
        if is_overlap:
            reasoning.append("London & NY Overlap")
            
        return {
            "active_sessions": active_sessions,
            "is_kill_zone": is_kill_zone,
            "is_dead_zone": is_dead_zone,
            "is_overlap": is_overlap,
            "volatility_expected": volatility,
            "reasoning": " | ".join(reasoning)
        }
        
    except Exception as e:
        logger.error(f"Kill Zones tahlil xatosi: {e}")
        return _empty_result(f"Xatolik: {e}")


def _empty_result(reason: str) -> Dict[str, Any]:
    return {
        "active_sessions": [],
        "is_kill_zone": False,
        "is_dead_zone": False,
        "is_overlap": False,
        "volatility_expected": "Unknown",
        "reasoning": reason
    }
