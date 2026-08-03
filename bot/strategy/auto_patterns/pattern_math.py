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
    empty_res = {
        "pattern": "None",
        "signal": "HOLD",
        "confidence": 0,
        "reasoning": "Sufficient pivots not found",
        "slopes": {"res": 0.0, "sup": 0.0},
        "pattern_points": {}
    }

    if len(pivots) < 4:
        return empty_res

    # Oxirgi 5 ta yoki 4 ta pivotni olamiz
    recent = pivots[-5:]
    
    highs = [p for p in recent if p['type'] == 'High']
    lows = [p for p in recent if p['type'] == 'Low']
    
    if len(highs) < 2 or len(lows) < 2:
        return empty_res
        
    # Oxirgi 2 ta High
    h1, h2 = highs[-2], highs[-1]
    # Oxirgi 2 ta Low
    l1, l2 = lows[-2], lows[-1]
    
    # Resistance qiyaligi (Slope) = (y2 - y1) / (x2 - x1)
    # Normallashtirish: % o'zgarish 1 ta sham uchun * 1000
    if h2['index'] == h1['index'] or l2['index'] == l1['index']:
        return empty_res

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
    
    signal = "HOLD"
    confidence = 0
    reasoning = ""
    
    if pattern_name != "Unknown" and pattern_name != "None":
        delta = (atr * 0.5) if atr else 0.0
        is_breakout_up = current_price > h2['price'] + delta
        is_breakout_down = current_price < l2['price'] - delta
        
        if is_breakout_up:
            if pattern_dir == "Bullish" or pattern_dir == "Neutral":
                signal = "BUY"
                confidence = 80
                reasoning = f"{pattern_name} yuqoriga yorib o'tildi (Breakout Up)"
            else: # pattern_dir == "Bearish"
                # Ziddiyatli holat: pattern Bearish edi, lekin tepaga yorildi.
                signal = "HOLD"
                confidence = 0
                reasoning = f"{pattern_name} yuqoriga yorildi, lekin kutilgan Bearish bias bilan zid (No Trade)"
        elif is_breakout_down:
            if pattern_dir == "Bearish" or pattern_dir == "Neutral":
                signal = "SELL"
                confidence = 80
                reasoning = f"{pattern_name} pastga yorib o'tildi (Breakout Down)"
            else: # pattern_dir == "Bullish"
                # Ziddiyatli holat: pattern Bullish edi, lekin pastga yorildi.
                signal = "HOLD"
                confidence = 0
                reasoning = f"{pattern_name} pastga yorildi, lekin kutilgan Bullish bias bilan zid (No Trade)"
        else:
            # Hali breakout bo'lmagan, lekin figurani o'zi yo'nalish beradi (shakllanayotgan bias yoki yo'nalishsiz)
            if pattern_dir == "Bullish":
                signal = "BUY"
                confidence = 60
                reasoning = f"{pattern_name} shakllanmoqda (Bullish bias)"
            elif pattern_dir == "Bearish":
                signal = "SELL"
                confidence = 60
                reasoning = f"{pattern_name} shakllanmoqda (Bearish bias)"
            else: # Neutral
                signal = "HOLD"
                confidence = 40
                reasoning = f"{pattern_name} - shakllanmoqda (Yo'nalishsiz)"
                
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
