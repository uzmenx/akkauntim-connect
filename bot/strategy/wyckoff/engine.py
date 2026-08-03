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
    
    # 5. Dynamic Confluence Calculations
    confluences = _calculate_confluences(df_recent, phase, spring_upthrust, event_details, momentum_sign, momentum_details, current_price)
    
    return {
        "phase": phase,
        "trading_range": tr_data,
        "spring_upthrust": spring_upthrust,
        "event_details": event_details,
        "event_bar_index": event_details.get("event_bar_index"),
        "event_time": event_details.get("event_time"),
        "momentum_sign": momentum_sign,
        "momentum_details": momentum_details,
        "current_price": current_price,
        "confluences": confluences
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
        "current_price": 0.0,
        "confluences": {
            "volume_ratio": 1.0,
            "trend_score": 0.0,
            "sweep_ratio": 0.0,
            "phase_aligned": False,
            "momentum_aligned": False
        }
    }

def _detect_trading_range(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Narx ma'lum bir koridorda (Trading Range) qolib ketganligini aniqlaydi.
    Institutional darajadagi dinamik va adaptiv tahlil orqali tor fletlardan tortib,
    keng tarqalgan konsolidatsiyalargacha aniq ajratib beradi.
    """
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    
    n = len(df)
    if n < 65:
        recent_highs = highs
        recent_lows = lows
        recent_closes = closes
    else:
        # TR chegaralarini topishda oxirgi 15 ta shamni (Spring/Upthrust ehtimoli bor joyni) hisobga olmaymiz
        recent_highs = highs[-65:-15]
        recent_lows = lows[-65:-15]
        recent_closes = closes[-65:-15]
        
    max_h = np.max(recent_highs)
    min_l = np.min(recent_lows)
    range_size = max_h - min_l
    
    # ATR oraliq kengligi (14 periodli)
    atr_approx = np.mean(highs[-14:] - lows[-14:])
    if atr_approx < 1e-8:
        atr_approx = 1e-8
        
    # Kvant tahliliga ko'ra, koridor kengligi ATR ning 0.3 baravaridan
    # tortib 20.0 baravarigacha bo'lishi mumkin.
    min_multiplier = 0.3
    max_multiplier = 20.0
    
    is_ranging = False
    
    if atr_approx * min_multiplier <= range_size <= atr_approx * max_multiplier:
        mid_price = (max_h + min_l) / 2.0
        
        # O'rta chiziq (mid_price) atrofidagi kesishmalar soni
        bool_array = (recent_closes > mid_price).astype(int)
        crosses = int(np.sum(np.abs(np.diff(bool_array))))
        
        # Trend kuchini aniqlash: Linear regression slope
        try:
            x = np.arange(len(recent_closes))
            slope, _ = np.polyfit(x, recent_closes, 1)
            normalized_slope = abs(slope * len(recent_closes) / atr_approx)
        except Exception:
            normalized_slope = 0.0
            
        # Narx o'zgaruvchanligi (Standard Deviation of closes) koridorga nisbatan
        close_std = np.std(recent_closes)
        std_to_range_ratio = close_std / range_size if range_size > 0 else 0
        
        # Shartlar:
        # - crosses >= 2 (kamida 2 marta o'rta chiziq kesib o'tilgan bo'lishi kerak)
        # - normalized_slope < 4.0 (kuchli yo'nalishli trend bo'lmasligi kerak)
        # - std_to_range_ratio < 0.45 (fletlik testi)
        if crosses >= 2 and normalized_slope < 4.0 and std_to_range_ratio < 0.45:
            is_ranging = True
        elif crosses >= 4 and normalized_slope < 6.0:
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

def _calculate_confluences(
    df_recent: pd.DataFrame,
    phase: str,
    spring_upthrust: str,
    event_details: dict,
    momentum_sign: str,
    momentum_details: dict,
    current_price: float
) -> Dict[str, Any]:
    """
    Wyckoff hodisalari va fazalariga doir bozor konfluensiyalarini hisoblaydi.
    """
    confluences = {
        "volume_ratio": 1.0,
        "trend_score": 0.0,
        "sweep_ratio": 0.0,
        "phase_aligned": False,
        "momentum_aligned": False
    }

    # 1. Volume Ratio (Hajm Confluence)
    vol_col = 'tick_volume' if 'tick_volume' in df_recent.columns else 'volume' if 'volume' in df_recent.columns else None
    if vol_col:
        try:
            recent_vols = df_recent[vol_col].values
            avg_vol = float(np.mean(recent_vols[-20:])) if len(recent_vols) >= 20 else float(np.mean(recent_vols))
            if avg_vol < 1e-8:
                avg_vol = 1e-8
                
            event_time = event_details.get("time") if spring_upthrust != "None" else momentum_details.get("time")
            if event_time is not None and event_time in df_recent.index:
                trigger_vol = float(df_recent.loc[event_time, vol_col])
            else:
                trigger_vol = float(df_recent[vol_col].iloc[-1])
                
            confluences["volume_ratio"] = float(trigger_vol / avg_vol)
        except Exception:
            confluences["volume_ratio"] = 1.0

    # 2. Trend Score (-1.0 dan +1.0 gacha)
    try:
        ema20_series = df_recent['close'].ewm(span=20).mean()
        ema50_series = df_recent['close'].ewm(span=50).mean()
        ema20 = float(ema20_series.iloc[-1])
        ema50 = float(ema50_series.iloc[-1])

        if current_price > ema20 > ema50:
            confluences["trend_score"] = 1.0
        elif current_price > ema50 and ema20 > ema50:
            confluences["trend_score"] = 0.5
        elif current_price < ema20 < ema50:
            confluences["trend_score"] = -1.0
        elif current_price < ema50 and ema20 < ema50:
            confluences["trend_score"] = -0.5
        else:
            confluences["trend_score"] = 0.0
    except Exception:
        confluences["trend_score"] = 0.0

    # 3. Sweep Ratio (Faqat Spring/Upthrust uchun)
    if spring_upthrust in ["Spring", "Upthrust"] and event_details.get("price") is not None and event_details.get("level_broken") is not None:
        try:
            atr = float(np.mean(df_recent['high'].iloc[-14:] - df_recent['low'].iloc[-14:]))
            if atr < 1e-8:
                atr = 1e-8
            sweep_depth = abs(event_details["price"] - event_details["level_broken"])
            confluences["sweep_ratio"] = float(sweep_depth / atr)
        except Exception:
            confluences["sweep_ratio"] = 0.0

    # 4. Phase Alignment (Faza mosligi)
    if spring_upthrust == "Spring" and phase == "Accumulation":
        confluences["phase_aligned"] = True
    elif spring_upthrust == "Upthrust" and phase == "Distribution":
        confluences["phase_aligned"] = True

    # 5. Momentum Alignment (Momentum mosligi)
    if spring_upthrust == "Spring" and momentum_sign == "SOS":
        confluences["momentum_aligned"] = True
    elif spring_upthrust == "Upthrust" and momentum_sign == "SOW":
        confluences["momentum_aligned"] = True
    elif phase == "Markup" and momentum_sign == "SOS":
        confluences["momentum_aligned"] = True
    elif phase == "Markdown" and momentum_sign == "SOW":
        confluences["momentum_aligned"] = True

    return confluences

def to_voting_signal(result: dict) -> dict:
    """
    Wyckoff natijalaridan ovoz berish moduli uchun BUY/SELL/HOLD signali chiqaradi.
    Dinamik ravishda bozor konfluensiyalarini (Volume, Trend, Sweep chuqurligi, 
    Faza va Momentum mosligi) hisobga olib confidence hisoblaydi.
    """
    if not result:
        return {"signal": "HOLD", "confidence": 0}
        
    spring_upthrust = result.get("spring_upthrust", "None")
    phase = result.get("phase", "Unknown")
    momentum_sign = result.get("momentum_sign", "None")
    confluences = result.get("confluences", {})
    
    # 1. Baza signal va dastlabki confidence
    signal = "HOLD"
    base_confidence = 0
    
    if spring_upthrust == "Spring":
        signal = "BUY"
        base_confidence = 65
    elif spring_upthrust == "Upthrust":
        signal = "SELL"
        base_confidence = 65
    elif phase == "Markup" and momentum_sign == "SOS":
        signal = "BUY"
        base_confidence = 50
    elif phase == "Markdown" and momentum_sign == "SOW":
        signal = "SELL"
        base_confidence = 50
        
    if signal == "HOLD":
        return {"signal": "HOLD", "confidence": 0}
        
    # 2. Konfluensiya bo'yicha hisob-kitoblar (Dinamik)
    confidence = base_confidence
    
    # A. Volume Confluence (+12 bonusgacha yoki -10 jarimagacha)
    vol_ratio = confluences.get("volume_ratio", 1.0)
    if vol_ratio > 1.2:
        # Katta hajm o'sishi signal ishonchliligini oshiradi
        vol_bonus = min(12, int((vol_ratio - 1.0) * 10))
        confidence += vol_bonus
    elif vol_ratio < 0.8:
        # Kichik hajm feykout (soxta yorilish) ehtimolini oshiradi, confidence kamayadi
        vol_penalty = min(10, int((1.0 - vol_ratio) * 10))
        confidence -= vol_penalty
        
    # B. Phase Alignment Confluence (+12 bonusgacha)
    if confluences.get("phase_aligned", False):
        confidence += 12
        
    # C. Momentum Alignment Confluence (+10 bonusgacha)
    if confluences.get("momentum_aligned", False):
        confidence += 10
        
    # D. Trend Alignment Confluence (+10 bonusgacha yoki -8 jarimagacha)
    trend_score = confluences.get("trend_score", 0.0)
    if signal == "BUY" and trend_score > 0:
        confidence += int(trend_score * 10)
    elif signal == "SELL" and trend_score < 0:
        confidence += int(abs(trend_score) * 10)
    elif signal == "BUY" and trend_score < 0:
        confidence -= int(abs(trend_score) * 8)
    elif signal == "SELL" and trend_score > 0:
        confidence -= int(trend_score * 8)
        
    # E. Sweep Quality Confluence (+8 bonus yoki -10 jarimagacha, faqat Spring/Upthrust)
    if spring_upthrust in ["Spring", "Upthrust"]:
        sweep_ratio = confluences.get("sweep_ratio", 0.0)
        if 0.2 <= sweep_ratio <= 1.2:
            confidence += 8
        elif sweep_ratio > 1.8:
            # Haddan tashqari katta yorilish real yorib o'tish bo'lishi mumkin, soxta emas
            confidence -= 10
        elif sweep_ratio < 0.1:
            confidence -= 5
            
    # 3. Institutional darajadagi xavfsiz diapazon: [15, 95]
    confidence = max(15, min(95, confidence))
    
    return {"signal": signal, "confidence": int(confidence)}
