"""
bot/strategy/sr_volume/engine.py
================================
TradingView'ning "Support and Resistance (High Volume Boxes)" indikatorining Python versiyasi.
SMC strategiyasi kabi Confluence Engine'ga uzatish uchun mo'ljallangan.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any

def analyze_sr_volume(df: pd.DataFrame, lookbackPeriod: int = 20, vol_len: int = 2, box_withd: float = 1.0) -> Dict[str, Any]:
    """
    Support and Resistance (High Volume Boxes) mantiqini hisoblaydi.
    """
    if df.empty or len(df) < lookbackPeriod * 2:
        return _empty_result()

    df_calc = df.copy()
    n = len(df_calc)

    # 1. Delta Volume hisoblash
    is_buy_volume = np.ones(n, dtype=bool) # Default True
    
    closes = df_calc['close'].values
    opens = df_calc['open'].values
    volumes = df_calc['tick_volume'].values if 'tick_volume' in df_calc.columns else (df_calc['volume'].values if 'volume' in df_calc.columns else np.zeros(n))
    
    current_buy_state = True
    for i in range(n):
        if closes[i] > opens[i]:
            current_buy_state = True
        elif closes[i] < opens[i]:
            current_buy_state = False
        is_buy_volume[i] = current_buy_state
        
    vol_delta = np.where(is_buy_volume, volumes, -volumes)
    df_calc['Vol'] = vol_delta
    
    # 2. Volume filter (highest/lowest over vol_len)
    vol_div = df_calc['Vol'] / 2.5
    df_calc['vol_hi'] = vol_div.rolling(window=vol_len, min_periods=1).max()
    df_calc['vol_lo'] = vol_div.rolling(window=vol_len, min_periods=1).min()
    
    # 3. Pivot Points
    highs = df_calc['high'].values
    lows = df_calc['low'].values
    
    pivot_highs = np.full(n, np.nan)
    pivot_lows = np.full(n, np.nan)
    
    for i in range(lookbackPeriod, n - lookbackPeriod):
        window_h = highs[i - lookbackPeriod : i + lookbackPeriod + 1]
        if highs[i] == np.max(window_h):
            # Pivot confirmed at i + lookbackPeriod
            pivot_highs[i + lookbackPeriod] = highs[i]
            
        window_l = lows[i - lookbackPeriod : i + lookbackPeriod + 1]
        if lows[i] == np.min(window_l):
            pivot_lows[i + lookbackPeriod] = lows[i]
            
    df_calc['pivot_high'] = pivot_highs
    df_calc['pivot_low'] = pivot_lows
    
    # 4. Box Width (ATR 200 * box_withd)
    tr = np.maximum(
        highs - lows,
        np.maximum(
            np.abs(highs - np.roll(closes, 1)),
            np.abs(lows - np.roll(closes, 1))
        )
    )
    tr[0] = highs[0] - lows[0]
    
    df_calc['TR'] = tr
    df_calc['ATR200'] = df_calc['TR'].rolling(window=200, min_periods=1).mean()
    df_calc['withd'] = df_calc['ATR200'] * box_withd
    
    # 5. Vectorized Support & Resistance Level Tracking (Bug D Fix)
    pivot_lows = df_calc['pivot_low'].values
    pivot_highs = df_calc['pivot_high'].values
    vols = df_calc['Vol'].values
    vol_hi_arr = df_calc['vol_hi'].values
    vol_lo_arr = df_calc['vol_lo'].values
    withd_arr = df_calc['withd'].values
    
    sup_cond = (~np.isnan(pivot_lows)) & (vols > vol_hi_arr)
    res_cond = (~np.isnan(pivot_highs)) & (vols < vol_lo_arr)
    
    sup_vals = np.where(sup_cond, pivot_lows, np.nan)
    sup_vals_1 = np.where(sup_cond, pivot_lows - withd_arr, np.nan)
    sup_indices = np.where(sup_cond, np.arange(n), np.nan)
    
    res_vals = np.where(res_cond, pivot_highs, np.nan)
    res_vals_1 = np.where(res_cond, pivot_highs + withd_arr, np.nan)
    res_indices = np.where(res_cond, np.arange(n), np.nan)
    
    # Forward-fill to propagate active S/R levels efficiently using pandas
    # NOTE: .copy() is required — pandas 2.x/3.x Copy-on-Write mode returns a
    # read-only array from .values here, and the slice-assignment below would
    # raise "assignment destination is read-only" without it.
    s_val = pd.Series(sup_vals).ffill().values.copy()
    s_val_1 = pd.Series(sup_vals_1).ffill().values.copy()
    s_idx = pd.Series(sup_indices).ffill().values.copy()
    
    r_val = pd.Series(res_vals).ffill().values.copy()
    r_val_1 = pd.Series(res_vals_1).ffill().values.copy()
    r_idx = pd.Series(res_indices).ffill().values.copy()
    
    # Mask values before lookbackPeriod * 2 as nan
    s_val[:lookbackPeriod * 2] = np.nan
    s_val_1[:lookbackPeriod * 2] = np.nan
    s_idx[:lookbackPeriod * 2] = np.nan
    r_val[:lookbackPeriod * 2] = np.nan
    r_val_1[:lookbackPeriod * 2] = np.nan
    r_idx[:lookbackPeriod * 2] = np.nan
    
    # 6. Vectorized Breakout & Hold detection
    current_lows = df_calc['low'].values
    current_highs = df_calc['high'].values
    prev_lows = np.roll(current_lows, 1)
    prev_highs = np.roll(current_highs, 1)
    
    # brekout_res: prev_low <= resistanceLevel_1 and current_low > resistanceLevel_1
    brekout_res_arr = (prev_lows <= r_val_1) & (current_lows > r_val_1)
    # res_holds: prev_high >= resistanceLevel and current_high < resistanceLevel
    res_holds_arr = (prev_highs >= r_val) & (current_highs < r_val)
    # sup_holds: prev_low <= supportLevel and current_low > supportLevel
    sup_holds_arr = (prev_lows <= s_val) & (current_lows > s_val)
    # brekout_sup: prev_high >= supportLevel_1 and current_high < supportLevel_1
    brekout_sup_arr = (prev_highs >= s_val_1) & (current_highs < s_val_1)
    
    # Mask out before boundary
    brekout_res_arr[:lookbackPeriod * 2] = False
    res_holds_arr[:lookbackPeriod * 2] = False
    sup_holds_arr[:lookbackPeriod * 2] = False
    brekout_sup_arr[:lookbackPeriod * 2] = False
    
    # Extract states for the final bar (n - 1)
    brekout_res_sig = bool(brekout_res_arr[-1])
    res_holds_sig = bool(res_holds_arr[-1])
    sup_holds_sig = bool(sup_holds_arr[-1])
    brekout_sup_sig = bool(brekout_sup_arr[-1])
    
    supportLevel = s_val[-1]
    supportLevel_1 = s_val_1[-1]
    sup_bar_idx = s_idx[-1]
    
    if not np.isnan(sup_bar_idx):
        sup_event_idx = max(0, int(sup_bar_idx) - lookbackPeriod)
        sup_time = str(df_calc.index[sup_event_idx])
        support_zone = {
            "top": float(supportLevel),
            "bottom": float(supportLevel_1),
            "bar_index": sup_event_idx,
            "time": sup_time
        }
    else:
        support_zone = None
        
    resistanceLevel = r_val[-1]
    resistanceLevel_1 = r_val_1[-1]
    res_bar_idx = r_idx[-1]
    
    if not np.isnan(res_bar_idx):
        res_event_idx = max(0, int(res_bar_idx) - lookbackPeriod)
        res_time = str(df_calc.index[res_event_idx])
        resistance_zone = {
            "top": float(resistanceLevel_1),
            "bottom": float(resistanceLevel),
            "bar_index": res_event_idx,
            "time": res_time
        }
    else:
        resistance_zone = None
        
    # Reconstruct last events
    last_breakout_res = None
    last_breakout_sup = None
    last_res_holds = None
    last_sup_holds = None
    
    br_indices = np.where(brekout_res_arr)[0]
    if len(br_indices) > 0:
        last_idx = int(br_indices[-1])
        last_breakout_res = {"type": "breakout_res", "event_bar_index": last_idx, "bar_index": last_idx, "event_time": str(df_calc.index[last_idx]), "time": str(df_calc.index[last_idx]), "price": float(current_highs[last_idx])}
        
    bs_indices = np.where(brekout_sup_arr)[0]
    if len(bs_indices) > 0:
        last_idx = int(bs_indices[-1])
        last_breakout_sup = {"type": "breakout_sup", "event_bar_index": last_idx, "bar_index": last_idx, "event_time": str(df_calc.index[last_idx]), "time": str(df_calc.index[last_idx]), "price": float(current_lows[last_idx])}
        
    rh_indices = np.where(res_holds_arr)[0]
    if len(rh_indices) > 0:
        last_idx = int(rh_indices[-1])
        last_res_holds = {"type": "res_holds", "event_bar_index": last_idx, "bar_index": last_idx, "event_time": str(df_calc.index[last_idx]), "time": str(df_calc.index[last_idx]), "price": float(current_highs[last_idx])}
        
    sh_indices = np.where(sup_holds_arr)[0]
    if len(sh_indices) > 0:
        last_idx = int(sh_indices[-1])
        last_sup_holds = {"type": "sup_holds", "event_bar_index": last_idx, "bar_index": last_idx, "event_time": str(df_calc.index[last_idx]), "time": str(df_calc.index[last_idx]), "price": float(current_lows[last_idx])}

    signal = "HOLD"
    base_confidence = 0
    reasoning = []
    
    event_details = {"type": "None", "event_bar_index": None, "bar_index": None, "event_time": None, "time": None, "price": None}

    if brekout_res_sig:
        signal = "BUY"
        base_confidence = 75
        reasoning.append("Resistance broken upwards (Breakout)")
        if last_breakout_res:
            event_details = last_breakout_res
    elif sup_holds_sig:
        signal = "BUY"
        base_confidence = 65
        reasoning.append("Support tested and held (Rejection)")
        if last_sup_holds:
            event_details = last_sup_holds
        
    if brekout_sup_sig:
        signal = "SELL"
        base_confidence = 75
        reasoning.append("Support broken downwards (Breakout)")
        if last_breakout_sup:
            event_details = last_breakout_sup
    elif res_holds_sig:
        signal = "SELL"
        base_confidence = 65
        reasoning.append("Resistance tested and held (Rejection)")
        if last_res_holds:
            event_details = last_res_holds
            
    # Dynamic Confidence Calculation (Bug C Fix)
    if signal == "HOLD":
        confidence = 0
    else:
        confidence = base_confidence
        
        # A. Volume Ratio Confirmation
        try:
            current_vol = float(volumes[-1])
            avg_vol = float(np.mean(volumes[-20:])) if len(volumes) >= 20 else float(np.mean(volumes))
            if avg_vol > 1e-8:
                vol_ratio = current_vol / avg_vol
                if vol_ratio > 1.3:
                    vol_bonus = min(12, int((vol_ratio - 1.0) * 10))
                    confidence += vol_bonus
                elif vol_ratio < 0.7:
                    vol_penalty = min(10, int((1.0 - vol_ratio) * 10))
                    confidence -= vol_penalty
        except Exception:
            pass
            
        # B. Trend Alignment (EMA20 & EMA50)
        try:
            closes_series = df_calc['close']
            ema20 = float(closes_series.ewm(span=20).mean().iloc[-1])
            ema50 = float(closes_series.ewm(span=50).mean().iloc[-1])
            current_price = float(closes_series.iloc[-1])
            
            if signal == "BUY":
                if current_price > ema20 > ema50:
                    confidence += 10
                elif current_price < ema20 < ema50:
                    confidence -= 8
            elif signal == "SELL":
                if current_price < ema20 < ema50:
                    confidence += 10
                elif current_price > ema20 > ema50:
                    confidence -= 8
        except Exception:
            pass
            
        # C. Rejection Candle Shadow Strength (Hold signals only)
        if "tested and held" in "".join(reasoning):
            try:
                op = float(opens[-1])
                cl = float(closes[-1])
                hi = float(current_highs[-1])
                lo = float(current_lows[-1])
                body_size = abs(cl - op)
                
                if signal == "BUY":
                    lower_wick = min(op, cl) - lo
                    if lower_wick > body_size * 1.5:
                        confidence += 8
                elif signal == "SELL":
                    upper_wick = hi - max(op, cl)
                    if upper_wick > body_size * 1.5:
                        confidence += 8
            except Exception:
                pass
                
        # D. S/R Level Age Alignment
        try:
            target_idx = res_bar_idx if signal == "SELL" else sup_bar_idx
            if not np.isnan(target_idx):
                age_bars = (n - 1) - int(target_idx)
                if 5 <= age_bars <= 50:
                    confidence += 5
                elif age_bars > 150:
                    confidence += 8
        except Exception:
            pass
            
        # Bound confidence
        confidence = max(20, min(95, confidence))
        
    return {
        "signal": signal,
        "confidence": int(confidence),
        "reasoning": " | ".join(reasoning) if reasoning else "No active breakout or hold",
        "support_zone": support_zone,
        "resistance_zone": resistance_zone,
        "brekout_res": bool(brekout_res_sig),
        "res_holds": bool(res_holds_sig),
        "sup_holds": bool(sup_holds_sig),
        "brekout_sup": bool(brekout_sup_sig),
        "event_bar_index": event_details.get("event_bar_index"),
        "event_time": event_details.get("event_time"),
        "event_details": event_details
    }

def _empty_result() -> Dict[str, Any]:
    return {
        "signal": "HOLD",
        "confidence": 0,
        "reasoning": "Not enough data",
        "support_zone": None,
        "resistance_zone": None,
        "brekout_res": False,
        "res_holds": False,
        "sup_holds": False,
        "brekout_sup": False,
        "event_bar_index": None,
        "event_time": None,
        "event_details": {"type": "None", "event_bar_index": None, "bar_index": None, "event_time": None, "time": None, "price": None}
    }

def to_voting_signal(result: dict) -> dict:
    """
    SR Volume natijalaridan ovoz berish moduli uchun BUY/SELL/HOLD signali chiqaradi.
    """
    if not result:
        return {"signal": "HOLD", "confidence": 0}
    return {
        "signal": result.get("signal", "HOLD"),
        "confidence": result.get("confidence", 0)
    }
