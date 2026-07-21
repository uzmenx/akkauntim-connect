import pytest
import pandas as pd
import numpy as np
from harmonic_engine import get_ratios, PATTERN_FUNCTIONS, calculate_zigzag, calc_fib

def test_zigzag_calculation():
    data = {
        'open':  [10, 10, 10, 15, 15, 20, 20, 18],
        'high':  [12, 11, 16, 17, 22, 21, 19, 18],
        'low':   [8,   9,  9, 14, 14, 18, 17, 15],
        'close': [11,  9, 15, 16, 21, 19, 18, 16] 
    }
    df = pd.DataFrame(data)
    zz = calculate_zigzag(df)
    
    # 0: up
    # 1: down -> pivot max
    assert zz.iloc[1] == 12.0
    # 2: up -> pivot min
    assert zz.iloc[2] == 9.0
    # 5: down -> pivot max
    assert zz.iloc[5] == 22.0

def test_get_ratios():
    r = get_ratios(100, 200, 150, 175, 138.2)
    assert abs(r['xab'] - 0.5) < 0.01
    assert abs(r['abc'] - 0.5) < 0.01

def test_gartley_ratios():
    ratios = {'xab': 0.618, 'abc': 0.6, 'bcd': 1.5, 'xad': 0.786}
    assert PATTERN_FUNCTIONS['Gartley'](ratios, 1, 200, 100) == True
    assert PATTERN_FUNCTIONS['Gartley'](ratios, -1, 100, 200) == True
    # Test failure condition
    ratios_bad = {'xab': 0.4, 'abc': 0.6, 'bcd': 1.5, 'xad': 0.786}
    assert PATTERN_FUNCTIONS['Gartley'](ratios_bad, 1, 200, 100) == False

def test_bat_ratios():
    ratios = {'xab': 0.45, 'abc': 0.5, 'bcd': 2.0, 'xad': 0.6}
    assert PATTERN_FUNCTIONS['Bat'](ratios, 1, 200, 100) == True
    assert PATTERN_FUNCTIONS['Bat'](ratios, -1, 100, 200) == True

def test_crab_ratios():
    ratios = {'xab': 0.6, 'abc': 0.5, 'bcd': 3.0, 'xad': 1.618}
    assert PATTERN_FUNCTIONS['Crab'](ratios, 1, 200, 100) == True
    assert PATTERN_FUNCTIONS['Crab'](ratios, -1, 100, 200) == True

def test_shark_ratios():
    ratios = {'xab': 0.6, 'abc': 1.2, 'bcd': 1.5, 'xad': 1.0}
    assert PATTERN_FUNCTIONS['Shark'](ratios, 1, 200, 100) == True

def test_abcd_ratios():
    ratios = {'xab': 0.5, 'abc': 0.6, 'bcd': 1.5, 'xad': 0.5}
    assert PATTERN_FUNCTIONS['ABCD'](ratios, 1, 200, 100) == True

def test_fib_calc():
    # d > c
    # calc_fib(c, d, rate): d - (fib_range * rate)
    assert calc_fib(100, 200, 0.5) == 150
    assert calc_fib(100, 200, 0.236) == 200 - (100 * 0.236)
    
    # d < c
    # calc_fib(c, d, rate): d + (fib_range * rate)
    assert calc_fib(200, 100, 0.5) == 150
    assert calc_fib(200, 100, 0.236) == 100 + (100 * 0.236)
