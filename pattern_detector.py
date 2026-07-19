"""
pattern_detector.py
===================
Harmonic Pattern Detector

Identifies common harmonic patterns based on zigzag pivot points:
Bat, Butterfly, Gartley, Crab, Shark, Cypher, etc.

Ported from TradingView Pine Script.
"""

import math
import pandas as pd
import numpy as np

class HarmonicPatternDetector:
    def __init__(self, error_allowance=0.10):
        # error_allowance allows for standard deviation in ratio matching (e.g. 10%)
        self.err = error_allowance

    def _check_ratio(self, ratio, target_min, target_max):
        # We allow a small error margin for exact matches
        if target_min == target_max:
            return (target_min * (1 - self.err)) <= ratio <= (target_max * (1 + self.err))
        return (target_min * (1 - self.err)) <= ratio <= (target_max * (1 + self.err))

    def detect_patterns(self, pivots):
        """
        pivots: list of the last 5 pivot points (prices).
        pivots = [X, A, B, C, D]
        where D is the most recent point.
        """
        if len(pivots) < 5:
            return None

        x, a, b, c, d = pivots[-5:]

        # Mode detection (1 = Bullish, -1 = Bearish)
        # In a bullish pattern, D is a low point (d < c)
        mode = 1 if d < c else -1

        # Calculate ratios
        # Avoid division by zero
        if abs(x - a) == 0 or abs(a - b) == 0 or abs(b - c) == 0:
            return None

        xab = abs(b - a) / abs(x - a)
        xad = abs(a - d) / abs(x - a)
        abc = abs(b - c) / abs(a - b)
        bcd = abs(c - d) / abs(b - c)

        patterns = []

        # Bat
        if self._check_ratio(xab, 0.382, 0.5) and self._check_ratio(abc, 0.382, 0.886) and \
           self._check_ratio(bcd, 1.618, 2.618) and self._check_ratio(xad, 0.886, 0.886):
            patterns.append("Bat")

        # Anti Bat
        if self._check_ratio(xab, 0.382, 0.618) and self._check_ratio(abc, 0.382, 0.886) and \
           self._check_ratio(bcd, 1.272, 2.0) and self._check_ratio(xad, 1.13, 1.13):
            patterns.append("Anti Bat")

        # Alt Bat
        if self._check_ratio(xab, 0.382, 0.382) and self._check_ratio(abc, 0.382, 0.886) and \
           self._check_ratio(bcd, 2.0, 3.618) and self._check_ratio(xad, 1.13, 1.13):
            patterns.append("Alt Bat")

        # Butterfly
        if self._check_ratio(xab, 0.786, 0.786) and self._check_ratio(abc, 0.382, 0.886) and \
           self._check_ratio(bcd, 1.618, 2.618) and self._check_ratio(xad, 1.27, 1.618):
            patterns.append("Butterfly")

        # Anti Butterfly
        if self._check_ratio(xab, 0.618, 0.618) and self._check_ratio(abc, 0.382, 0.886) and \
           self._check_ratio(bcd, 1.272, 2.0) and self._check_ratio(xad, 0.786, 0.786):
            patterns.append("Anti Butterfly")

        # AB=CD
        if self._check_ratio(abc, 0.382, 0.886) and self._check_ratio(bcd, 1.13, 2.618):
            patterns.append("AB=CD")

        # Gartley
        if self._check_ratio(xab, 0.618, 0.618) and self._check_ratio(abc, 0.382, 0.886) and \
           self._check_ratio(bcd, 1.13, 2.618) and self._check_ratio(xad, 0.786, 0.786):
            patterns.append("Gartley")

        # Crab
        if self._check_ratio(xab, 0.382, 0.618) and self._check_ratio(abc, 0.382, 0.886) and \
           self._check_ratio(bcd, 2.24, 3.618) and self._check_ratio(xad, 1.618, 1.618):
            patterns.append("Crab")

        # Deep Crab
        if self._check_ratio(xab, 0.886, 0.886) and self._check_ratio(abc, 0.382, 0.886) and \
           self._check_ratio(bcd, 2.0, 3.618) and self._check_ratio(xad, 1.618, 1.618):
            patterns.append("Deep Crab")

        # Shark
        if self._check_ratio(xab, 0.0, 100.0) and self._check_ratio(abc, 1.13, 1.618) and \
           self._check_ratio(bcd, 1.618, 2.24) and self._check_ratio(xad, 0.886, 1.13):
            patterns.append("Shark")

        # 5-0
        if self._check_ratio(xab, 1.13, 1.618) and self._check_ratio(abc, 1.618, 2.24) and \
           self._check_ratio(bcd, 0.5, 0.5) and self._check_ratio(xad, 0.0, 100.0):
            patterns.append("5-0")

        # 3 Drives
        if self._check_ratio(xab, 1.27, 1.618) and self._check_ratio(abc, 0.618, 0.786) and \
           self._check_ratio(bcd, 1.27, 1.618) and self._check_ratio(xad, 0.618, 0.786):
            patterns.append("3 Drives")

        # Cypher
        if self._check_ratio(xab, 0.382, 0.618) and self._check_ratio(abc, 1.13, 1.414) and \
           self._check_ratio(bcd, 1.272, 2.0) and self._check_ratio(xad, 0.786, 0.786):
            patterns.append("Cypher")

        if patterns:
            pattern_type = "Bullish" if mode == 1 else "Bearish"
            return {
                "type": pattern_type,
                "patterns": patterns,
                "pivots": {"X": x, "A": a, "B": b, "C": c, "D": d},
                "ratios": {"XAB": xab, "ABC": abc, "BCD": bcd, "XAD": xad}
            }
        
        return None

def extract_pivots_from_data(df, depth=10):
    """
    Simplistic zigzag implementation to extract pivots from a DataFrame.
    Returns a list of values (highs/lows) that act as pivots.
    """
    pivots = []
    # A simple swing high/low detector for testing purposes
    for i in range(depth, len(df) - depth):
        is_high = all(df['high'].iloc[i] > df['high'].iloc[i-depth:i]) and \
                  all(df['high'].iloc[i] > df['high'].iloc[i+1:i+depth+1])
        is_low = all(df['low'].iloc[i] < df['low'].iloc[i-depth:i]) and \
                 all(df['low'].iloc[i] < df['low'].iloc[i+1:i+depth+1])
        
        if is_high:
            pivots.append(df['high'].iloc[i])
        elif is_low:
            pivots.append(df['low'].iloc[i])
            
    # Return last 5 pivots if available
    if len(pivots) >= 5:
        return pivots[-5:]
    return pivots
