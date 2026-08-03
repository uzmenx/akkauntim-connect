"""
wyckoff/engine.py
=================
Wyckoff Method bo'yicha bozor fazalari va hodisalarini (Spring/Upthrust, SOS/SOW)
aniqlaydigan mantiqiy modul.

Fazalar:
- Accumulation (Yig'ilish): Narx pastda TR (Trading Range) da harakatlanadi.
- Distribution (Tarqatish): Narx yuqorida TR da harakatlanadi.
- Markup (O'sish): Trend yuqoriga.
- Markdown (Qulash): Trend pastga.

Hodisalar:
- Spring: Accumulation zonasidan pastga soxta yorib o'tish (Liquidity Sweep) va qaytish.
- Upthrust (UTAD): Distribution zonasidan yuqoriga soxta yorib o'tish va qaytish.
- SOS (Sign of Strength): Katta hajmli o'sish shamlar.
- SOW (Sign of Weakness): Katta hajmli pasayish shamlar.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List

def analyze_wyckoff(df: pd.DataFrame, lookback: int = 100) -> Dict[str, Any]:
    """
    Berilgan DataFrame (OHLCV) asosida Wyckoff fazasi va hodisalarini aniqlaydi.
    """
    if df.empty or len(df) < lookback:
        return _empty_wyckoff_result()

    # So'nggi 'lookback' ta shamni kesib olamiz
    df_recent = df.iloc[-lookback:].copy()
    current_price = float(df_recent['close'].iloc[-1])
    
    # 1. Trading Range (TR) ni aniqlash
    # Bozor fletdami yoki trenddami?
    tr_data = _detect_trading_range(df_recent)
    
    # 2. Fazani aniqlash (Accumulation, Distribution, Markup, Markdown)
    phase = _determine_phase(df_recent, tr_data)
    
    # 3. Spring yoki Upthrust ni izlash (soxta yorib o'tishlar)
    spring_upthrust, event_details = _detect_spring_upthrust(df_recent, tr_data)
    
    # 4. SOS (Sign of Strength) / SOW (Sign of Weakness) momentumini aniqlash
    momentum_sign, momentum_details = _detect_sos_sow(df_recent)
    
    return {
        "phase": phase,
        "trading_range": tr_data,
        "spring_upthrust": spring_upthrust,
        "event_details": event_details,
        "event_bar_index": event_details.get("event_bar_index"),
        "event_time": event_details.get("event_time"),
        "momentum_sign": momentum_sign,
        "momentum_details": momentum_details,
        "current_price": current_price
    }

def _empty_wyckoff_result() -> Dict[str, Any]:
    return {
        "phase": "Unknown",
        "trading_range": {"is_ranging": False},
        "spring_upthrust": "None",
        "event_details": {"type": "None", "bar_index": None, "event_bar_index": None, "time": None, "event_time": None, "price": None},
        "event_bar_index": None,
        "event_time": None,
        "momentum_sign": "None",
        "momentum_details": {"type": "None", "bar_index": None, "event_bar_index": None, "time": None, "event_time": None, "price": None},
        "current_price": 0.0
    }

def _detect_trading_range(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Narx ma'lum bir koridorda (Trading Range) qolib ketganligini aniqlaydi.
    """
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    
    # TR chegaralarini topishda oxirgi 15 ta shamni (Spring/Upthrust ehtimoli bor joyni) hisobga olmaymiz
    recent_highs = highs[-65:-15]
    recent_lows = lows[-65:-15]
    
    max_h = np.max(recent_highs)
    min_l = np.min(recent_lows)
    
    # TR kengligi (ATR bilan solishtiramiz)
    atr_approx = np.mean(highs[-14:] - lows[-14:])
    range_size = max_h - min_l
    
    # Kengaytirilgan ATR koridori: 0.8 * ATR dan 15.0 * ATR gacha.
    # Bu tor fletlarni va yuqori volatilli bozorlardagi keng trading range'larni qamrab oladi.
    is_ranging = False
    if atr_approx * 0.8 < range_size < atr_approx * 15.0:
        # Endi narx shu oraliqda necha marta tepaga/pastga urilganini tekshiramiz (ADR qismi)
        # O'rta chiziq atrofida kesishmalar soni
        mid_price = (max_h + min_l) / 2
        # np.diff bool arrayda ishlatilganda o'zgarishlarni topadi
        bool_array = (closes[-50:] > mid_price).astype(int)
        crosses = np.sum(np.abs(np.diff(bool_array)))
        if crosses >= 2: # Kamida 2 marta o'rtani kesib o'tgan bo'lsa
            is_ranging = True
            
    return {
        "is_ranging": is_ranging,
        "top": float(max_h),
        "bottom": float(min_l),
        "mid": float((max_h + min_l) / 2),
        "range_size": float(range_size)
    }

def _determine_phase(df: pd.DataFrame, tr_data: Dict[str, Any]) -> str:
    """
    Narx qaysi bosqichda ekanini topadi.
    Markup / Markdown trendga asoslanadi.
    Accumulation / Distribution esa TR va undan oldingi trend/kirish traektoriyasiga qaraydi.
    """
    closes = df['close'].values
    ema50 = df['close'].ewm(span=50).mean().iloc[-1]
    ema20 = df['close'].ewm(span=20).mean().iloc[-1]
    current = closes[-1]
    
    if tr_data["is_ranging"]:
        start_price = closes[0]
        # Narx trading range'ga yuqoridan/o'rtadan balanddan kelib kirdi = Accumulation
        # Narx trading range'ga pastdan/o'rtadan pastdan kelib kirdi = Distribution
        if start_price > tr_data["top"]:
            return "Accumulation"
        elif start_price < tr_data["bottom"]:
            return "Distribution"
        elif start_price >= tr_data["mid"]:
            return "Accumulation"
        else:
            return "Distribution"
    else:
        # Flet emas, yo'nalishli trend
        if current > ema20 > ema50:
            return "Markup"
        elif current < ema20 < ema50:
            return "Markdown"
        
    return "Unknown"

def _detect_spring_upthrust(df: pd.DataFrame, tr_data: Dict[str, Any]) -> tuple:
    """
    Spring = Support ni yorib pastga ketdi, lekin tezda Range ichiga qaytdi (Liquidity Sweep).
    Upthrust = Resistance ni yorib tepaga chiqdi, lekin tezda Range ichiga qaytdi.
    """
    empty_details = {"type": "None", "bar_index": None, "event_bar_index": None, "time": None, "event_time": None, "price": None, "level_broken": None}
    if not tr_data["is_ranging"]:
        return "None", empty_details
        
    top = tr_data["top"]
    bottom = tr_data["bottom"]
    
    recent = df.iloc[-15:]
    
    spring_info = None
    upthrust_info = None
    
    for idx, row in recent.iterrows():
        bar_loc = int(df.index.get_loc(idx)) if idx in df.index else None
        bar_time = str(idx)
        
        # Pastga soxta yorilish (Spring)
        if row['low'] < bottom and row['close'] > bottom:
            spring_info = {
                "type": "Spring",
                "bar_index": bar_loc,
                "event_bar_index": bar_loc,
                "time": bar_time,
                "event_time": bar_time,
                "price": float(row['low']),
                "level_broken": float(bottom)
            }
        
        # Tepaga soxta yorilish (Upthrust)
        if row['high'] > top and row['close'] < top:
            upthrust_info = {
                "type": "Upthrust",
                "bar_index": bar_loc,
                "event_bar_index": bar_loc,
                "time": bar_time,
                "event_time": bar_time,
                "price": float(row['high']),
                "level_broken": float(top)
            }
            
    current_close = float(df['close'].iloc[-1])
    
    if spring_info and current_close > bottom:
        return "Spring", spring_info
        
    if upthrust_info and current_close < top:
        return "Upthrust", upthrust_info
        
    return "None", empty_details

def _detect_sos_sow(df: pd.DataFrame) -> tuple:
    """
    Sign of Strength (SOS): Juda katta bullish sham (qolgan o'rtacha shamlardan ancha katta),
                            ko'pincha volume ham baland bo'ladi.
    Sign of Weakness (SOW): Katta bearish sham.
    """
    empty_details = {"type": "None", "bar_index": None, "event_bar_index": None, "time": None, "event_time": None, "price": None}
    recent_5 = df.iloc[-5:]
    
    atr = float(np.mean(df['high'].iloc[-14:] - df['low'].iloc[-14:]))
    
    sos_info = None
    sow_info = None
    
    for idx, row in recent_5.iterrows():
        bar_loc = int(df.index.get_loc(idx)) if idx in df.index else None
        bar_time = str(idx)
        candle_body = row['close'] - row['open']
        
        # O'sish kuchli (SOS) - Tana ATR dan ham katta
        if candle_body > atr * 1.2:
            if 'tick_volume' in row and row['tick_volume'] > df['tick_volume'].mean() * 1.2:
                sos_info = {"type": "SOS", "bar_index": bar_loc, "event_bar_index": bar_loc, "time": bar_time, "event_time": bar_time, "price": float(row['close'])}
            elif 'tick_volume' not in row:
                sos_info = {"type": "SOS", "bar_index": bar_loc, "event_bar_index": bar_loc, "time": bar_time, "event_time": bar_time, "price": float(row['close'])}
                
        # Tushish kuchli (SOW)
        if candle_body < -atr * 1.2:
            if 'tick_volume' in row and row['tick_volume'] > df['tick_volume'].mean() * 1.2:
                sow_info = {"type": "SOW", "bar_index": bar_loc, "event_bar_index": bar_loc, "time": bar_time, "event_time": bar_time, "price": float(row['close'])}
            elif 'tick_volume' not in row:
                sow_info = {"type": "SOW", "bar_index": bar_loc, "event_bar_index": bar_loc, "time": bar_time, "event_time": bar_time, "price": float(row['close'])}
                
    if sos_info and not sow_info:
        return "SOS", sos_info
    if sow_info and not sos_info:
        return "SOW", sow_info
        
    return "None", empty_details

def to_voting_signal(result: dict) -> dict:
    """
    Wyckoff natijalaridan ovoz berish moduli uchun BUY/SELL/HOLD signali chiqaradi.
    """
    if not result:
        return {"signal": "HOLD", "confidence": 0}
        
    spring_upthrust = result.get("spring_upthrust", "None")
    phase = result.get("phase", "Unknown")
    momentum_sign = result.get("momentum_sign", "None")
    
    if spring_upthrust == "Spring":
        return {"signal": "BUY", "confidence": 70}
    elif spring_upthrust == "Upthrust":
        return {"signal": "SELL", "confidence": 70}
        
    if phase == "Markup" and momentum_sign == "SOS":
        return {"signal": "BUY", "confidence": 55}
    elif phase == "Markdown" and momentum_sign == "SOW":
        return {"signal": "SELL", "confidence": 55}
        
    return {"signal": "HOLD", "confidence": 0}
