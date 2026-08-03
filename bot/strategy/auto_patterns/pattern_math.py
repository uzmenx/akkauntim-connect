"""
bot/strategy/auto_patterns/pattern_math.py
==========================================
Grafik figuralarini (Channels, Wedges, Triangles) topish uchun matematik mantiq.
Oxirgi pivotlardan foydalanib Resistance va Support chiziqlarining og'ishini (slope) hisoblaydi.
"""

from typing import List, Dict, Any, Optional

def identify_pattern(pivots: List[Dict[str, Any]], current_price: float, atr: float = 0.0) -> Dict[str, Any]:
    """
    Pivotlar ro'yxatidan eng oxirgi figurani aniqlaydi.
    Kamida 4 ta pivot kerak (2 ta High, 2 ta Low).
    """
    if len(pivots) < 4:
        return {"pattern": "None", "direction": "Neutral", "quality": 0}

    # Oxirgi 5 ta yoki 4 ta pivotni olamiz
    recent = pivots[-5:]
    
    highs = [p for p in recent if p['type'] == 'High']
    lows = [p for p in recent if p['type'] == 'Low']
    
    if len(highs) < 2 or len(lows) < 2:
        return {"pattern": "None", "direction": "Neutral", "quality": 0}
        
    # Oxirgi 2 ta High
    h1, h2 = highs[-2], highs[-1]
    # Oxirgi 2 ta Low
    l1, l2 = lows[-2], lows[-1]
    
    # Resistance qiyaligi (Slope) = (y2 - y1) / (x2 - x1)
    # Normallashtirish: % o'zgarish 1 ta sham uchun * 1000
    if h2['index'] == h1['index']: return {"pattern": "None", "direction": "Neutral", "quality": 0}
    if l2['index'] == l1['index']: return {"pattern": "None", "direction": "Neutral", "quality": 0}

    m_res = ((h2['price'] - h1['price']) / h1['price']) / (h2['index'] - h1['index']) * 1000
    m_sup = ((l2['price'] - l1['price']) / l1['price']) / (l2['index'] - l1['index']) * 1000
    
    flat_threshold = 0.05
    diff_threshold = 0.08
    
    # Patternni aniqlash
    pattern_name = "Unknown"
    pattern_dir = "Neutral"
    
    is_res_flat = abs(m_res) < flat_threshold
    is_sup_flat = abs(m_sup) < flat_threshold
    
    is_res_up = m_res > flat_threshold
    is_res_down = m_res < -flat_threshold
    
    is_sup_up = m_sup > flat_threshold
    is_sup_down = m_sup < -flat_threshold
    
    are_parallel = abs(m_res - m_sup) < diff_threshold
    
    if is_res_up and is_sup_up:
        # Ikkalasi ham tepaga
        if are_parallel:
            pattern_name = "Ascending Channel"
            pattern_dir = "Bearish" # Odatda o'suvchi kanal pastga yoriladi
        elif m_res > m_sup:
            pattern_name = "Rising Wedge (Expanding)"
            pattern_dir = "Bearish"
        else:
            pattern_name = "Rising Wedge (Contracting)"
            pattern_dir = "Bearish"
            
    elif is_res_down and is_sup_down:
        # Ikkalasi ham pastga
        if are_parallel:
            pattern_name = "Descending Channel"
            pattern_dir = "Bullish" # Odatda tushuvchi kanal tepaga yoriladi
        elif m_res < m_sup:
            pattern_name = "Falling Wedge (Contracting)"
            pattern_dir = "Bullish"
        else:
            pattern_name = "Falling Wedge (Expanding)"
            pattern_dir = "Bullish"
            
    elif is_res_flat and is_sup_flat:
        pattern_name = "Ranging Channel"
        pattern_dir = "Neutral"
        
    elif is_res_down and is_sup_up:
        pattern_name = "Converging Triangle" # Symmetrical Triangle
        pattern_dir = "Neutral" # Yorib o'tish tomonga qarab
        
    elif is_res_up and is_sup_down:
        pattern_name = "Diverging Triangle" # Kengayuvchi
        pattern_dir = "Neutral"
        
    elif is_res_flat and is_sup_up:
        pattern_name = "Ascending Triangle"
        pattern_dir = "Bullish"
        
    elif is_res_down and is_sup_flat:
        pattern_name = "Descending Triangle"
        pattern_dir = "Bearish"
        
    # Breakout tekshiruvi (agar pattern allaqachon aniqlangan bo'lsa)
    # Joriy narx h2 dan baland bo'lsa -> Breakout UP
    # Joriy narx l2 dan past bo'lsa -> Breakout DOWN
    
    signal = "NEUTRAL"
    confidence = 0
    reasoning = ""
    
    if pattern_name != "Unknown" and pattern_name != "None":
        # Chiziqlarning hozirgi bardagi proyeksiyasi
        last_index = max(h2['index'], l2['index'])
        # Aytaylik hozirgi index oxirgi pivotdan 5-10 bar uzoqlikda
        # Biz aniq bar indexini bilmaymiz, chunki current_price berilgan.
        # Breakout oddiygina oxirgi pivotlar orqali tekshiriladi
        
        if current_price > h2['price'] + (atr * 0.5 if atr else 0):
            signal = "BUY"
            # Pattern direction va breakout signalini muvofiqlashtirish:
            # Agar pattern_dir == "Bullish" bo'lsa (masalan Descending Channel, Falling Wedge) -> aligned breakout (confidence = 85)
            # Agar pattern_dir == "Bearish" bo'lsa (masalan Ascending Channel, Rising Wedge) -> counter-bias breakout (susaytirildi, confidence = 55)
            # Agar pattern_dir == "Neutral" bo'lsa -> standard breakout (confidence = 75)
            if pattern_dir == "Bullish":
                confidence = 85
                reasoning = f"{pattern_name} yuqoriga yorib o'tildi (Bullish aligned Breakout Up)"
            elif pattern_dir == "Bearish":
                confidence = 55  # Counter-bias breakout signal: susaytirildi
                reasoning = f"{pattern_name} yuqoriga yorib o'tildi (Counter-bias Breakout Up - ehtiyotkorlik bilan)"
            else:
                confidence = 75
                reasoning = f"{pattern_name} yuqoriga yorib o'tildi (Breakout Up)"
        elif current_price < l2['price'] - (atr * 0.5 if atr else 0):
            signal = "SELL"
            # Pattern direction va breakout signalini muvofiqlashtirish:
            # Agar pattern_dir == "Bearish" bo'lsa (masalan Ascending Channel, Rising Wedge) -> aligned breakout (confidence = 85)
            # Agar pattern_dir == "Bullish" bo'lsa (masalan Descending Channel, Falling Wedge) -> counter-bias breakout (susaytirildi, confidence = 55)
            # Agar pattern_dir == "Neutral" bo'lsa -> standard breakout (confidence = 75)
            if pattern_dir == "Bearish":
                confidence = 85
                reasoning = f"{pattern_name} pastga yorib o'tildi (Bearish aligned Breakout Down)"
            elif pattern_dir == "Bullish":
                confidence = 55  # Counter-bias breakout signal: susaytirildi
                reasoning = f"{pattern_name} pastga yorib o'tildi (Counter-bias Breakout Down - ehtiyotkorlik bilan)"
            else:
                confidence = 75
                reasoning = f"{pattern_name} pastga yorib o'tildi (Breakout Down)"
        else:
            # Hali breakout bo'lmagan, lekin figurani o'zi yo'nalish beradi
            if pattern_dir == "Bullish":
                signal = "BUY"
                confidence = 60
                reasoning = f"{pattern_name} shakllanmoqda (Bullish bias)"
            elif pattern_dir == "Bearish":
                signal = "SELL"
                confidence = 60
                reasoning = f"{pattern_name} shakllanmoqda (Bearish bias)"
            else:
                signal = "HOLD"
                confidence = 40
                reasoning = f"{pattern_name} - yo'nalish kutilyapti"
                
    return {
        "pattern": pattern_name,
        "signal": signal,
        "confidence": confidence,
        "reasoning": reasoning,
        "slopes": {"res": round(m_res, 3), "sup": round(m_sup, 3)},
        "pattern_points": {
            "h1": h1,
            "h2": h2,
            "l1": l1,
            "l2": l2
        }
    }
