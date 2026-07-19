import pandas as pd
import numpy as np

def calculate_zigzag(df: pd.DataFrame) -> pd.Series:
    """
    Translates the ZigZag logic from Pine Script:
    _isUp = close >= open
    _isDown = close <= open
    _direction = _isUp[1] and _isDown ? -1 : _isDown[1] and _isUp ? 1 : nz(_direction[1])
    _zigzag = _isUp[1] and _isDown and _direction[1] != -1 ? highest(2) : _isDown[1] and _isUp and _direction[1] != 1 ? lowest(2) : na
    """
    is_up = df['close'] >= df['open']
    is_down = df['close'] <= df['open']
    
    is_up_prev = is_up.shift(1).fillna(False)
    is_down_prev = is_down.shift(1).fillna(False)
    
    highest_2 = df['high'].rolling(2).max()
    lowest_2 = df['low'].rolling(2).min()
    
    direction = np.zeros(len(df))
    zigzag = np.full(len(df), np.nan)
    
    dir_val = 0
    for i in range(1, len(df)):
        up_prev = is_up_prev.iloc[i]
        down_curr = is_down.iloc[i]
        down_prev = is_down_prev.iloc[i]
        up_curr = is_up.iloc[i]
        
        # Calculate direction
        if up_prev and down_curr:
            new_dir = -1
        elif down_prev and up_curr:
            new_dir = 1
        else:
            new_dir = dir_val
            
        # Calculate zigzag
        if up_prev and down_curr and dir_val != -1:
            zigzag[i] = highest_2.iloc[i]
        elif down_prev and up_curr and dir_val != 1:
            zigzag[i] = lowest_2.iloc[i]
            
        dir_val = new_dir
        direction[i] = dir_val
        
    return pd.Series(zigzag, index=df.index)

def get_ratios(x, a, b, c, d):
    xa_diff = abs(x - a)
    ab_diff = abs(a - b)
    bc_diff = abs(b - c)
    
    if xa_diff == 0 or ab_diff == 0 or bc_diff == 0:
        return None
        
    return {
        'xab': abs(b - a) / xa_diff,
        'xad': abs(a - d) / xa_diff,
        'abc': abs(b - c) / ab_diff,
        'bcd': abs(c - d) / bc_diff
    }

# Pine: isBat(_mode)
def is_bat(ratios, mode, c, d):
    xab, abc, bcd, xad = ratios['xab'], ratios['abc'], ratios['bcd'], ratios['xad']
    _xab = 0.382 <= xab <= 0.5
    _abc = 0.382 <= abc <= 0.886
    _bcd = 1.618 <= bcd <= 2.618
    _xad = xad <= 0.618 and xad <= 1.000
    dir_cond = (d < c) if mode == 1 else (d > c)
    return _xab and _abc and _bcd and _xad and dir_cond

# Pine: isAntiBat(_mode)
def is_anti_bat(ratios, mode, c, d):
    xab, abc, bcd, xad = ratios['xab'], ratios['abc'], ratios['bcd'], ratios['xad']
    _xab = 0.500 <= xab <= 0.886
    _abc = 1.000 <= abc <= 2.618
    _bcd = 1.618 <= bcd <= 2.618
    _xad = 0.886 <= xad <= 1.000
    dir_cond = (d < c) if mode == 1 else (d > c)
    return _xab and _abc and _bcd and _xad and dir_cond

# Pine: isAltBat(_mode)
def is_alt_bat(ratios, mode, c, d):
    xab, abc, bcd, xad = ratios['xab'], ratios['abc'], ratios['bcd'], ratios['xad']
    _xab = xab <= 0.382
    _abc = 0.382 <= abc <= 0.886
    _bcd = 2.0 <= bcd <= 3.618
    _xad = xad <= 1.13
    dir_cond = (d < c) if mode == 1 else (d > c)
    return _xab and _abc and _bcd and _xad and dir_cond

# Pine: isButterfly(_mode)
def is_butterfly(ratios, mode, c, d):
    xab, abc, bcd, xad = ratios['xab'], ratios['abc'], ratios['bcd'], ratios['xad']
    _xab = xab <= 0.786
    _abc = 0.382 <= abc <= 0.886
    _bcd = 1.618 <= bcd <= 2.618
    _xad = 1.27 <= xad <= 1.618
    dir_cond = (d < c) if mode == 1 else (d > c)
    return _xab and _abc and _bcd and _xad and dir_cond

# Pine: isAntiButterfly(_mode)
def is_anti_butterfly(ratios, mode, c, d):
    xab, abc, bcd, xad = ratios['xab'], ratios['abc'], ratios['bcd'], ratios['xad']
    _xab = 0.236 <= xab <= 0.886
    _abc = 1.130 <= abc <= 2.618
    _bcd = 1.000 <= bcd <= 1.382
    _xad = 0.500 <= xad <= 0.886
    dir_cond = (d < c) if mode == 1 else (d > c)
    return _xab and _abc and _bcd and _xad and dir_cond

# Pine: isABCD(_mode)
def is_abcd(ratios, mode, c, d):
    abc, bcd = ratios['abc'], ratios['bcd']
    _abc = 0.382 <= abc <= 0.886
    _bcd = 1.13 <= bcd <= 2.618
    dir_cond = (d < c) if mode == 1 else (d > c)
    return _abc and _bcd and dir_cond

# Pine: isGartley(_mode)
def is_gartley(ratios, mode, c, d):
    xab, abc, bcd, xad = ratios['xab'], ratios['abc'], ratios['bcd'], ratios['xad']
    _xab = 0.5 <= xab <= 0.618
    _abc = 0.382 <= abc <= 0.886
    _bcd = 1.13 <= bcd <= 2.618
    _xad = 0.75 <= xad <= 0.875
    dir_cond = (d < c) if mode == 1 else (d > c)
    return _xab and _abc and _bcd and _xad and dir_cond

# Pine: isAntiGartley(_mode)
def is_anti_gartley(ratios, mode, c, d):
    xab, abc, bcd, xad = ratios['xab'], ratios['abc'], ratios['bcd'], ratios['xad']
    _xab = 0.500 <= xab <= 0.886
    _abc = 1.000 <= abc <= 2.618
    _bcd = 1.500 <= bcd <= 5.000
    _xad = 1.000 <= xad <= 5.000
    dir_cond = (d < c) if mode == 1 else (d > c)
    return _xab and _abc and _bcd and _xad and dir_cond

# Pine: isCrab(_mode)
def is_crab(ratios, mode, c, d):
    xab, abc, bcd, xad = ratios['xab'], ratios['abc'], ratios['bcd'], ratios['xad']
    _xab = 0.500 <= xab <= 0.875
    _abc = 0.382 <= abc <= 0.886
    _bcd = 2.000 <= bcd <= 5.000
    _xad = 1.382 <= xad <= 5.000
    dir_cond = (d < c) if mode == 1 else (d > c)
    return _xab and _abc and _bcd and _xad and dir_cond

# Pine: isAntiCrab(_mode)
def is_anti_crab(ratios, mode, c, d):
    xab, abc, bcd, xad = ratios['xab'], ratios['abc'], ratios['bcd'], ratios['xad']
    _xab = 0.250 <= xab <= 0.500
    _abc = 1.130 <= abc <= 2.618
    _bcd = 1.618 <= bcd <= 2.618
    _xad = 0.500 <= xad <= 0.750
    dir_cond = (d < c) if mode == 1 else (d > c)
    return _xab and _abc and _bcd and _xad and dir_cond

# Pine: isShark(_mode)
def is_shark(ratios, mode, c, d):
    xab, abc, bcd, xad = ratios['xab'], ratios['abc'], ratios['bcd'], ratios['xad']
    _xab = 0.500 <= xab <= 0.875
    _abc = 1.130 <= abc <= 1.618
    _bcd = 1.270 <= bcd <= 2.240
    _xad = 0.886 <= xad <= 1.130
    dir_cond = (d < c) if mode == 1 else (d > c)
    return _xab and _abc and _bcd and _xad and dir_cond

# Pine: isAntiShark(_mode)
def is_anti_shark(ratios, mode, c, d):
    xab, abc, bcd, xad = ratios['xab'], ratios['abc'], ratios['bcd'], ratios['xad']
    _xab = 0.382 <= xab <= 0.875
    _abc = 0.500 <= abc <= 1.000
    _bcd = 1.250 <= bcd <= 2.618
    _xad = 0.500 <= xad <= 1.250
    dir_cond = (d < c) if mode == 1 else (d > c)
    return _xab and _abc and _bcd and _xad and dir_cond

# Pine: is5o(_mode)
def is_5o(ratios, mode, c, d):
    xab, abc, bcd, xad = ratios['xab'], ratios['abc'], ratios['bcd'], ratios['xad']
    _xab = 1.13 <= xab <= 1.618
    _abc = 1.618 <= abc <= 2.24
    _bcd = 0.5 <= bcd <= 0.625
    _xad = 0.0 <= xad <= 0.236
    dir_cond = (d < c) if mode == 1 else (d > c)
    return _xab and _abc and _bcd and _xad and dir_cond

# Pine: isWolf(_mode)
def is_wolf(ratios, mode, c, d):
    xab, abc, bcd, xad = ratios['xab'], ratios['abc'], ratios['bcd'], ratios['xad']
    _xab = 1.27 <= xab <= 1.618
    _abc = 0 <= abc <= 5
    _bcd = 1.27 <= bcd <= 1.618
    _xad = 0.0 <= xad <= 5
    dir_cond = (d < c) if mode == 1 else (d > c)
    return _xab and _abc and _bcd and _xad and dir_cond

# Pine: isHnS(_mode)
def is_hns(ratios, mode, c, d):
    xab, abc, bcd, xad = ratios['xab'], ratios['abc'], ratios['bcd'], ratios['xad']
    _xab = 2.0 <= xab <= 10
    _abc = 0.90 <= abc <= 1.1
    _bcd = 0.236 <= bcd <= 0.88
    _xad = 0.90 <= xad <= 1.1
    dir_cond = (d < c) if mode == 1 else (d > c)
    return _xab and _abc and _bcd and _xad and dir_cond

# Pine: isConTria(_mode)
def is_contria(ratios, mode, c, d):
    xab, abc, bcd, xad = ratios['xab'], ratios['abc'], ratios['bcd'], ratios['xad']
    _xab = 0.382 <= xab <= 0.618
    _abc = 0.382 <= abc <= 0.618
    _bcd = 0.382 <= bcd <= 0.618
    _xad = 0.236 <= xad <= 0.764
    dir_cond = (d < c) if mode == 1 else (d > c)
    return _xab and _abc and _bcd and _xad and dir_cond

# Pine: isExpTria(_mode)
def is_exptria(ratios, mode, c, d):
    xab, abc, bcd, xad = ratios['xab'], ratios['abc'], ratios['bcd'], ratios['xad']
    _xab = 1.236 <= xab <= 1.618
    _abc = 1.000 <= abc <= 1.618
    _bcd = 1.236 <= bcd <= 2.000
    _xad = 2.000 <= xad <= 2.236
    dir_cond = (d < c) if mode == 1 else (d > c)
    return _xab and _abc and _bcd and _xad and dir_cond

PATTERN_FUNCTIONS = {
    "Bat": is_bat,
    "Anti Bat": is_anti_bat,
    "Alt Bat": is_alt_bat,
    "Butterfly": is_butterfly,
    "Anti Butterfly": is_anti_butterfly,
    "ABCD": is_abcd,
    "Gartley": is_gartley,
    "Anti Gartley": is_anti_gartley,
    "Crab": is_crab,
    "Anti Crab": is_anti_crab,
    "Shark": is_shark,
    "Anti Shark": is_anti_shark,
    "5-O": is_5o,
    "Wolf Wave": is_wolf,
    "Head and Shoulders": is_hns,
    "Contracting Triangle": is_contria,
    "Expanding Triangle": is_exptria
}

def calc_fib(c, d, rate):
    fib_range = abs(d - c)
    if d > c:
        return d - (fib_range * rate)
    else:
        return d + (fib_range * rate)

def predict_emerging_patterns(x, a, b, c, enabled_patterns=None):
    """
    Given the last 4 pivots (X, A, B, C), projects the Potential Reversal Zone (PRZ)
    for D by scanning possible prices.
    """
    if enabled_patterns is None:
        enabled_patterns = list(PATTERN_FUNCTIONS.keys())
        
    xa_diff = abs(x - a)
    ab_diff = abs(a - b)
    bc_diff = abs(b - c)
    
    if xa_diff == 0 or ab_diff == 0 or bc_diff == 0:
        return []
        
    predictions = []
    
    # Zigzag oscillates. 
    # If C > B, C is a peak. So D will be a trough (D < C), which corresponds to Bullish (mode = 1).
    # If C < B, C is a trough. So D will be a peak (D > C), which corresponds to Bearish (mode = -1).
    if c > b:
        mode = 1
        direction = "Bullish"
        d_min_search = c - 5 * xa_diff
        d_max_search = c
    else:
        mode = -1
        direction = "Bearish"
        d_min_search = c
        d_max_search = c + 5 * xa_diff
        
    # We use numerical scan for 100% accuracy with existing pattern logic
    d_points = np.linspace(d_min_search, d_max_search, 2000)
    
    for p_name in enabled_patterns:
        p_func = PATTERN_FUNCTIONS.get(p_name)
        if not p_func: continue
        
        valid_ds = []
        for d in d_points:
            ratios = get_ratios(x, a, b, c, d)
            if ratios and p_func(ratios, mode, c, d):
                valid_ds.append(d)
                
        if valid_ds:
            prz_min = min(valid_ds)
            prz_max = max(valid_ds)
            predictions.append({
                "name": p_name,
                "direction": direction,
                "prz_min": prz_min,
                "prz_max": prz_max,
                "prz_mid": (prz_min + prz_max) / 2
            })
            
    return predictions

def analyze_harmonic_patterns(df: pd.DataFrame, config: dict = None) -> dict:
    if config is None:
        config = {}
        
    ew_rate = config.get('entry_window_rate', 0.236)
    tp_rate = config.get('tp_rate', 0.618)
    sl_rate = config.get('sl_rate', -0.236)
    
    enabled_patterns = config.get('enabled_patterns', list(PATTERN_FUNCTIONS.keys()))
    
    zigzag_series = calculate_zigzag(df)
    
    # Extract zigzag points safely
    zz_points = zigzag_series.dropna()
    
    all_detected_patterns = []
    active_pattern_info = None
    emerging_patterns = []
    signal = "NEUTRAL"
    fib_levels = {"entry": None, "tp": None, "sl": None}
    
    # We need at least 5 points to form XABCD
    if len(zz_points) >= 5:
        # Check patterns for historical data to fill all_detected_patterns
        # We will loop through the last min(30, len) zigzag points to find patterns
        # Actually, Pine valuewhen(sz, sz, 0..4) just gets the most recent 5 pivots.
        # But to show historical, we can scan through historical windows of 5.
        
        # Let's scan from index 4 to end of zz_points
        for i in range(4, len(zz_points)):
            x = zz_points.iloc[i-4]
            a = zz_points.iloc[i-3]
            b = zz_points.iloc[i-2]
            c = zz_points.iloc[i-1]
            d = zz_points.iloc[i]
            
            bar_index = df.index.get_loc(zz_points.index[i])
            
            ratios = get_ratios(x, a, b, c, d)
            if ratios is None:
                continue
                
            for p_name in enabled_patterns:
                p_func = PATTERN_FUNCTIONS.get(p_name)
                if p_func:
                    # Check Bullish (mode = 1)
                    if p_func(ratios, 1, c, d):
                        all_detected_patterns.append({
                            "name": p_name,
                            "direction": "Bullish",
                            "bar_index": bar_index,
                            "d_price": d
                        })
                    # Check Bearish (mode = -1)
                    if p_func(ratios, -1, c, d):
                        all_detected_patterns.append({
                            "name": p_name,
                            "direction": "Bearish",
                            "bar_index": bar_index,
                            "d_price": d
                        })
        
        # Current active pattern (from the very last 5 points)
        x = zz_points.iloc[-5]
        a = zz_points.iloc[-4]
        b = zz_points.iloc[-3]
        c = zz_points.iloc[-2]
        d = zz_points.iloc[-1]
        
        d_index = df.index.get_loc(zz_points.index[-1])
        bars_since_d = len(df) - 1 - d_index
        
        ratios = get_ratios(x, a, b, c, d)
        if ratios:
            # Find the active pattern
            for p_name in enabled_patterns:
                p_func = PATTERN_FUNCTIONS.get(p_name)
                if p_func:
                    if p_func(ratios, 1, c, d):
                        active_pattern_info = {
                            "name": p_name,
                            "direction": "Bullish",
                            "xabcd_points": {"x": x, "a": a, "b": b, "c": c, "d": d},
                            "ratios": ratios,
                            "bars_since_d": bars_since_d
                        }
                        break # Found one
                    elif p_func(ratios, -1, c, d):
                        active_pattern_info = {
                            "name": p_name,
                            "direction": "Bearish",
                            "xabcd_points": {"x": x, "a": a, "b": b, "c": c, "d": d},
                            "ratios": ratios,
                            "bars_since_d": bars_since_d
                        }
                        break
        
        if active_pattern_info:
            c_val = active_pattern_info['xabcd_points']['c']
            d_val = active_pattern_info['xabcd_points']['d']
            fib_levels['entry'] = calc_fib(c_val, d_val, ew_rate)
            fib_levels['tp'] = calc_fib(c_val, d_val, tp_rate)
            fib_levels['sl'] = calc_fib(c_val, d_val, sl_rate)
            
            # Check for signal based on Pine logic
            current_close = df['close'].iloc[-1]
            if active_pattern_info['direction'] == "Bullish":
                if current_close <= fib_levels['entry']:
                    signal = "BUY"
            else: # Bearish
                if current_close >= fib_levels['entry']:
                    signal = "SELL"
                    
    current_price = df['close'].iloc[-1] if not df.empty else None
    
    # If we have at least 4 points, we can predict emerging patterns!
    if len(zz_points) >= 4:
        ex = zz_points.iloc[-4]
        ea = zz_points.iloc[-3]
        eb = zz_points.iloc[-2]
        ec = zz_points.iloc[-1]
        emerging_patterns = predict_emerging_patterns(ex, ea, eb, ec, enabled_patterns)
    
    return {
        "current_price": float(current_price) if current_price is not None else None,
        "active_pattern": active_pattern_info,
        "emerging_patterns": emerging_patterns,
        "signal": signal,
        "fib_levels": fib_levels,
        "all_detected_patterns": all_detected_patterns[-30:] # Last 30 detected patterns
    }
