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
    spring_upthrust = _detect_spring_upthrust(df_recent, tr_data)
    
    # 4. SOS (Sign of Strength) / SOW (Sign of Weakness) momentumini aniqlash
    momentum_sign = _detect_sos_sow(df_recent)
    
    return {
        "phase": phase,
        "trading_range": tr_data,
        "spring_upthrust": spring_upthrust,
        "momentum_sign": momentum_sign,
        "current_price": current_price
    }

def _empty_wyckoff_result() -> Dict[str, Any]:
    return {
        "phase": "Unknown",
        "trading_range": {"is_ranging": False},
        "spring_upthrust": "None",
        "momentum_sign": "None",
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
    
    # Agar narx oxirgi 50 sham davomida ATR * 10 dan kichik koridorda qolib ketgan bo'lsa, bu TR.
    # Lekin juda tor ham bo'lmasligi kerak (ATR * 1.5 dan katta)
    is_ranging = False
    if atr_approx * 1.5 < range_size < atr_approx * 10:
        # Endi narx shu oraliqda necha marta tepaga/pastga urilganini tekshiramiz (ADR qismi)
        # O'rta chiziq atrofida kesishmalar soni
        mid_price = (max_h + min_l) / 2
        # np.diff bool arrayda ishlatilganda o'zgarishlarni topadi
        bool_array = (closes[-50:] > mid_price).astype(int)
        crosses = np.sum(np.abs(np.diff(bool_array)))
        if crosses >= 3: # Kamida 3 marta o'rtani kesib o'tgan bo'lsa
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
    Accumulation / Distribution esa TR va undan oldingi trendga qaraydi.
    """
    closes = df['close'].values
    ema50 = df['close'].ewm(span=50).mean().iloc[-1]
    ema20 = df['close'].ewm(span=20).mean().iloc[-1]
    current = closes[-1]
    
    if tr_data["is_ranging"]:
        # Agar narx EMA lardan pastdan kelib TR ga kirgan bo'lsa = Accumulation
        # Agar narx EMA lardan tepadan kelib TR ga kirgan bo'lsa = Distribution
        start_price = closes[0]
        if start_price > tr_data["top"]: # Tushib kelib fletga kirdi
            return "Accumulation"
        elif start_price < tr_data["bottom"]: # O'sib kelib fletga kirdi
            return "Distribution"
        else:
            return "Consolidation"
    else:
        # Flet emas, yo'nalishli trend
        if current > ema20 > ema50:
            return "Markup"
        elif current < ema20 < ema50:
            return "Markdown"
        
    return "Unknown"

def _detect_spring_upthrust(df: pd.DataFrame, tr_data: Dict[str, Any]) -> str:
    """
    Spring = Support ni yorib pastga ketdi, lekin tezda Range ichiga qaytdi (Liquidity Sweep).
    Upthrust = Resistance ni yorib tepaga chiqdi, lekin tezda Range ichiga qaytdi.
    """
    if not tr_data["is_ranging"]:
        return "None"
        
    top = tr_data["top"]
    bottom = tr_data["bottom"]
    
    # Oxirgi 10-15 sham ichida hodisa bo'lganini qaraymiz
    recent = df.iloc[-15:]
    
    spring_detected = False
    upthrust_detected = False
    
    for i, row in recent.iterrows():
        # Pastga soxta yorilish
        if row['low'] < bottom and row['close'] > bottom:
            spring_detected = True
        
        # Tepaga soxta yorilish
        if row['high'] > top and row['close'] < top:
            upthrust_detected = True
            
    # Agar oxirgi sham range ni ichida yoki tepasida/pastida bo'lsa
    current_close = df['close'].iloc[-1]
    
    if spring_detected and current_close > bottom:
        return "Spring"
        
    if upthrust_detected and current_close < top:
        return "Upthrust"
        
    return "None"

def _detect_sos_sow(df: pd.DataFrame) -> str:
    """
    Sign of Strength (SOS): Juda katta bullish sham (qolgan o'rtacha shamlardan ancha katta),
                            ko'pincha volume ham baland bo'ladi.
    Sign of Weakness (SOW): Katta bearish sham.
    """
    recent_5 = df.iloc[-5:]
    
    atr = np.mean(df['high'].iloc[-14:] - df['low'].iloc[-14:])
    
    has_sos = False
    has_sow = False
    
    for _, row in recent_5.iterrows():
        candle_body = row['close'] - row['open']
        candle_size = row['high'] - row['low']
        
        # O'sish kuchli (SOS) - Tana ATR dan ham katta
        if candle_body > atr * 1.2:
            # Volume ham tekshirilishi mumkin (agar tick_volume bo'lsa)
            if 'tick_volume' in row and row['tick_volume'] > df['tick_volume'].mean() * 1.2:
                has_sos = True
            elif 'tick_volume' not in row:
                has_sos = True
                
        # Tushish kuchli (SOW)
        if candle_body < -atr * 1.2:
            if 'tick_volume' in row and row['tick_volume'] > df['tick_volume'].mean() * 1.2:
                has_sow = True
            elif 'tick_volume' not in row:
                has_sow = True
                
    if has_sos and not has_sow:
        return "SOS"
    if has_sow and not has_sos:
        return "SOW"
        
    return "None"
