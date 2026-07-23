"""
bot/strategy/auto_patterns/zigzag.py
====================================
Zigzag algoritmi - grafikdagi so'nggi eng baland va eng past nuqtalarni (pivots) topadi.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any

def find_pivots(df: pd.DataFrame, order: int = 8) -> List[Dict[str, Any]]:
    """
    Pivot nuqtalarini topish. 
    order - bu chap va o'ng tomonlardagi shamlarning soni (lookback).
    
    Qaytaradi:
    [{'index': int, 'price': float, 'type': 'High' | 'Low'}, ...]
    """
    highs = df['high'].values
    lows = df['low'].values
    n = len(df)
    
    pivots = []
    
    for i in range(order, n - order):
        window_h = highs[i - order : i + order + 1]
        window_l = lows[i - order : i + order + 1]
        
        is_high = (highs[i] == np.max(window_h))
        is_low = (lows[i] == np.min(window_l))
        
        if is_high and not is_low:
            pivots.append({'index': i, 'price': float(highs[i]), 'type': 'High'})
        elif is_low and not is_high:
            pivots.append({'index': i, 'price': float(lows[i]), 'type': 'Low'})
            
    # Filtr: ketma-ket ikkita High yoki Low kelib qolsa, kuchlirog'ini saqlab qolamiz.
    if not pivots:
        return []
        
    filtered_pivots = [pivots[0]]
    for i in range(1, len(pivots)):
        curr = pivots[i]
        last = filtered_pivots[-1]
        
        if curr['type'] == last['type']:
            if curr['type'] == 'High':
                if curr['price'] > last['price']:
                    filtered_pivots[-1] = curr # Kattarog'i bilan almashtiramiz
            else:
                if curr['price'] < last['price']:
                    filtered_pivots[-1] = curr # Kichikrog'i bilan almashtiramiz
        else:
            filtered_pivots.append(curr)
            
    return filtered_pivots
