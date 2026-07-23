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
    
    supportLevel = np.nan
    supportLevel_1 = np.nan
    resistanceLevel = np.nan
    resistanceLevel_1 = np.nan
    
    brekout_res_sig = False
    res_holds_sig = False
    sup_holds_sig = False
    brekout_sup_sig = False
    
    support_zone = None
    resistance_zone = None
    
    for i in range(lookbackPeriod * 2, n):
        vol = df_calc['Vol'].iloc[i]
        vol_hi = df_calc['vol_hi'].iloc[i]
        vol_lo = df_calc['vol_lo'].iloc[i]
        
        pv_low = df_calc['pivot_low'].iloc[i]
        pv_high = df_calc['pivot_high'].iloc[i]
        withd = df_calc['withd'].iloc[i]
        
        # New Support
        if not np.isnan(pv_low) and vol > vol_hi:
            supportLevel = pv_low
            supportLevel_1 = supportLevel - withd
            
        # New Resistance
        if not np.isnan(pv_high) and vol < vol_lo:
            resistanceLevel = pv_high
            resistanceLevel_1 = resistanceLevel + withd
            
        current_low = df_calc['low'].iloc[i]
        current_high = df_calc['high'].iloc[i]
        prev_low = df_calc['low'].iloc[i-1]
        prev_high = df_calc['high'].iloc[i-1]
        
        # Breakout / Holds logic using crossover / crossunder
        if not np.isnan(resistanceLevel_1):
            brekout_res = (prev_low <= resistanceLevel_1) and (current_low > resistanceLevel_1)
        else:
            brekout_res = False
            
        if not np.isnan(resistanceLevel):
            res_holds = (prev_high >= resistanceLevel) and (current_high < resistanceLevel)
        else:
            res_holds = False
            
        if not np.isnan(supportLevel):
            sup_holds = (prev_low <= supportLevel) and (current_low > supportLevel)
        else:
            sup_holds = False
            
        if not np.isnan(supportLevel_1):
            brekout_sup = (prev_high >= supportLevel_1) and (current_high < supportLevel_1)
        else:
            brekout_sup = False
            
        if i == n - 1:
            brekout_res_sig = brekout_res
            res_holds_sig = res_holds
            sup_holds_sig = sup_holds
            brekout_sup_sig = brekout_sup
            
            if not np.isnan(supportLevel):
                support_zone = {
                    "top": float(supportLevel),
                    "bottom": float(supportLevel_1)
                }
            if not np.isnan(resistanceLevel):
                resistance_zone = {
                    "top": float(resistanceLevel_1),
                    "bottom": float(resistanceLevel)
                }

    signal = "NEUTRAL"
    confidence = 0
    reasoning = []
    
    if brekout_res_sig:
        signal = "BUY"
        confidence = 75
        reasoning.append("Resistance broken upwards (Breakout)")
    elif sup_holds_sig:
        signal = "BUY"
        confidence = 65
        reasoning.append("Support tested and held (Rejection)")
        
    if brekout_sup_sig:
        signal = "SELL"
        confidence = 75
        reasoning.append("Support broken downwards (Breakout)")
    elif res_holds_sig:
        signal = "SELL"
        confidence = 65
        reasoning.append("Resistance tested and held (Rejection)")
        
    return {
        "signal": signal,
        "confidence": confidence,
        "reasoning": " | ".join(reasoning) if reasoning else "No active breakout or hold",
        "support_zone": support_zone,
        "resistance_zone": resistance_zone,
        "brekout_res": bool(brekout_res_sig),
        "res_holds": bool(res_holds_sig),
        "sup_holds": bool(sup_holds_sig),
        "brekout_sup": bool(brekout_sup_sig)
    }

def _empty_result() -> Dict[str, Any]:
    return {
        "signal": "NEUTRAL",
        "confidence": 0,
        "reasoning": "Not enough data",
        "support_zone": None,
        "resistance_zone": None,
        "brekout_res": False,
        "res_holds": False,
        "sup_holds": False,
        "brekout_sup": False
    }
