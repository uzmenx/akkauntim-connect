import pandas as pd
import numpy as np

def calculate_zigzag(df: pd.DataFrame, window: int = 5) -> pd.Series:
    """
    Translates the ZigZag logic with N-bar pivot detection.
    """
    highs = df['high'].values
    lows = df['low'].values
    pivots = pd.Series(index=df.index, dtype=float)
    pivots[:] = np.nan
    
    for i in range(window, len(df) - window):
        # Check if it's a swing high
        if highs[i] == max(highs[i-window:i+window+1]):
            pivots.iloc[i] = highs[i]
        # Check if it's a swing low  
        elif lows[i] == min(lows[i-window:i+window+1]):
            pivots.iloc[i] = lows[i]
    
    # Remove consecutive same-direction pivots
    result = pivots.dropna()
    
    # Keep alternating highs and lows
    if not result.empty:
        filtered_idx = []
        last_type = None
        last_val = None
        last_i = None
        
        for i, val in result.items():
            is_high = (val == df.at[i, 'high'])
            curr_type = 1 if is_high else -1
            
            if last_type is None:
                last_type = curr_type
                last_val = val
                last_i = i
            elif curr_type != last_type:
                filtered_idx.append(last_i)
                last_type = curr_type
                last_val = val
                last_i = i
            else:
                if curr_type == 1 and val > last_val:
                    last_val = val
                    last_i = i
                elif curr_type == -1 and val < last_val:
                    last_val = val
                    last_i = i
        if last_i is not None:
            filtered_idx.append(last_i)
            
        result = result.loc[filtered_idx]
        
    return result

def get_ratios(x, a, b, c, d):
    xa_diff = abs(x - a)
    ab_diff = abs(a - b)
    bc_diff = abs(b - c)
    
    if xa_diff == 0 or ab_diff == 0 or bc_diff == 0:
        return None
        
    return {
        'xab': abs(b - a) / xa_diff,
        'xad': abs(d - x) / xa_diff,
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

IDEAL_PATTERN_RATIOS = {
    "Bat": {"xab": 0.442, "abc": 0.618, "bcd": 2.0, "xad": 0.886},
    "Anti Bat": {"xab": 0.618, "abc": 1.618, "bcd": 2.0, "xad": 0.886},
    "Alt Bat": {"xab": 0.382, "abc": 0.618, "bcd": 2.618, "xad": 1.13},
    "Butterfly": {"xab": 0.786, "abc": 0.618, "bcd": 1.618, "xad": 1.272},
    "Anti Butterfly": {"xab": 0.5, "abc": 1.618, "bcd": 1.13, "xad": 0.618},
    "ABCD": {"abc": 0.618, "bcd": 1.618},
    "Gartley": {"xab": 0.618, "abc": 0.618, "bcd": 1.272, "xad": 0.786},
    "Anti Gartley": {"xab": 0.618, "abc": 1.618, "bcd": 2.0, "xad": 1.272},
    "Crab": {"xab": 0.618, "abc": 0.618, "bcd": 3.14, "xad": 1.618},
    "Anti Crab": {"xab": 0.382, "abc": 1.618, "bcd": 2.0, "xad": 0.618},
    "Shark": {"xab": 0.618, "abc": 1.272, "bcd": 1.618, "xad": 0.886},
    "Anti Shark": {"xab": 0.618, "abc": 0.786, "bcd": 1.618, "xad": 0.886},
    "5-O": {"xab": 1.272, "abc": 1.618, "bcd": 0.5, "xad": 0.118},
    "Wolf Wave": {"xab": 1.414, "abc": 1.0, "bcd": 1.414, "xad": 1.0},
    "Head and Shoulders": {"xab": 2.5, "abc": 1.0, "bcd": 0.5, "xad": 1.0},
    "Contracting Triangle": {"xab": 0.5, "abc": 0.5, "bcd": 0.5, "xad": 0.5},
    "Expanding Triangle": {"xab": 1.414, "abc": 1.272, "bcd": 1.618, "xad": 2.118}
}

def calculate_pattern_confidence(pattern_name: str, ratios: dict) -> float:
    """
    Calculates dynamic pattern confidence (50.0 - 98.0%) based on ratio proximity to ideal Fibonacci targets.
    """
    if not ratios or pattern_name not in IDEAL_PATTERN_RATIOS:
        return 75.0
    
    ideals = IDEAL_PATTERN_RATIOS[pattern_name]
    errors = []
    for key, ideal_val in ideals.items():
        if key in ratios and ideal_val > 0:
            actual_val = ratios[key]
            err = abs(actual_val - ideal_val) / ideal_val
            errors.append(err)
    
    if not errors:
        return 75.0
    
    avg_error = float(np.mean(errors))
    score = max(50.0, min(98.0, 100.0 * (1.0 - avg_error)))
    return float(round(score, 1))

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
    if df is None or df.empty or len(df) < 20:
        return {
            "current_price": None,
            "active_pattern": None,
            "emerging_patterns": [],
            "signal": "NEUTRAL",
            "fib_levels": {"entry": None, "tp": None, "sl": None},
            "all_detected_patterns": []
        }

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
            bar_time = str(zz_points.index[i])
            
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
                            "time": bar_time,
                            "d_price": float(d)
                        })
                    # Check Bearish (mode = -1)
                    if p_func(ratios, -1, c, d):
                        all_detected_patterns.append({
                            "name": p_name,
                            "direction": "Bearish",
                            "bar_index": bar_index,
                            "time": bar_time,
                            "d_price": float(d)
                        })
        
        # Current active pattern (from the very last 5 points)
        x = zz_points.iloc[-5]
        a = zz_points.iloc[-4]
        b = zz_points.iloc[-3]
        c = zz_points.iloc[-2]
        d = zz_points.iloc[-1]
        
        idx_x = zz_points.index[-5]
        idx_a = zz_points.index[-4]
        idx_b = zz_points.index[-3]
        idx_c = zz_points.index[-2]
        idx_d = zz_points.index[-1]

        d_index = df.index.get_loc(idx_d)
        bars_since_d = len(df) - 1 - d_index
        
        xabcd_coords = {
            "x": {"price": float(x), "time": str(idx_x), "bar_index": int(df.index.get_loc(idx_x))},
            "a": {"price": float(a), "time": str(idx_a), "bar_index": int(df.index.get_loc(idx_a))},
            "b": {"price": float(b), "time": str(idx_b), "bar_index": int(df.index.get_loc(idx_b))},
            "c": {"price": float(c), "time": str(idx_c), "bar_index": int(df.index.get_loc(idx_c))},
            "d": {"price": float(d), "time": str(idx_d), "bar_index": int(df.index.get_loc(idx_d))}
        }
        xabcd_times = {
            "x": str(idx_x), "a": str(idx_a), "b": str(idx_b), "c": str(idx_c), "d": str(idx_d)
        }
        xabcd_bar_indices = {
            "x": int(df.index.get_loc(idx_x)), "a": int(df.index.get_loc(idx_a)),
            "b": int(df.index.get_loc(idx_b)), "c": int(df.index.get_loc(idx_c)),
            "d": int(df.index.get_loc(idx_d))
        }

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
                            "xabcd_points": {"x": float(x), "a": float(a), "b": float(b), "c": float(c), "d": float(d)},
                            "xabcd_coords": xabcd_coords,
                            "xabcd_times": xabcd_times,
                            "xabcd_bar_indices": xabcd_bar_indices,
                            "ratios": ratios,
                            "bars_since_d": bars_since_d
                        }
                        break # Found one
                    elif p_func(ratios, -1, c, d):
                        active_pattern_info = {
                            "name": p_name,
                            "direction": "Bearish",
                            "xabcd_points": {"x": float(x), "a": float(a), "b": float(b), "c": float(c), "d": float(d)},
                            "xabcd_coords": xabcd_coords,
                            "xabcd_times": xabcd_times,
                            "xabcd_bar_indices": xabcd_bar_indices,
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
    
    if active_pattern_info and signal in ["BUY", "SELL"]:
        confidence = calculate_pattern_confidence(
            active_pattern_info["name"],
            active_pattern_info.get("ratios", {})
        )
        active_pattern_info["confidence"] = confidence
    else:
        confidence = 0.0

    return {
        "current_price": float(current_price) if current_price is not None else None,
        "active_pattern": active_pattern_info,
        "emerging_patterns": emerging_patterns,
        "signal": signal,
        "confidence": confidence,
        "fib_levels": fib_levels,
        "all_detected_patterns": all_detected_patterns[-30:] # Last 30 detected patterns
    }


def to_voting_signal(result: dict) -> dict:
    """
    Harmonic pattern tahlili natijalaridan ovoz berish signali shakllantiradi.
    """
    if not result:
        return {"signal": "HOLD", "confidence": 0}
        
    sig = result.get("signal", "HOLD")
    if sig == "NEUTRAL":
        sig = "HOLD"
        
    conf = result.get("confidence", 0.0)
    try:
        conf = int(round(float(conf)))
    except:
        conf = 0
        
    return {"signal": sig, "confidence": conf}

