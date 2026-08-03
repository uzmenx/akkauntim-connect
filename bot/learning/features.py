"""
Institutional Feature Engineering Engine for Akcume AI Trading Bot.
Provides modular, fault-tolerant, and audited technical indicator and feature extraction utilities.
"""

import numpy as np
import pandas as pd
from typing import Union, List, Dict, Any


def sanitize_market_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Sanitizes market dataset by filtering out invalid, zero, NULL, corrupt, and closed-market dead bars:
    - Removes NULL / NaN price columns
    - Removes non-positive prices (Open, High, Low, Close <= 0)
    - Removes invalid bar geometry (High < Low, Close > High, Close < Low, Open > High, Open < Low)
    - Removes zero-volume flat dead bars (High == Low and Volume == 0)
    - Removes duplicate timestamps
    - Removes corrupt extreme price spikes (>30% single-bar anomaly)
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df_clean = df.copy()

    # Column mapping
    col_map = {
        'price_open': 'open',
        'price_high': 'high',
        'price_low': 'low',
        'price_close': 'close',
        'tick_volume': 'volume',
        'timestamp': 'time'
    }
    for old_col, new_col in col_map.items():
        if old_col in df_clean.columns and new_col not in df_clean.columns:
            df_clean[new_col] = df_clean[old_col]

    req_cols = ['open', 'high', 'low', 'close']
    for c in req_cols:
        if c not in df_clean.columns:
            return pd.DataFrame()
        df_clean[c] = pd.to_numeric(df_clean[c], errors='coerce')

    if 'volume' in df_clean.columns:
        df_clean['volume'] = pd.to_numeric(df_clean['volume'], errors='coerce').fillna(0.0)
    else:
        df_clean['volume'] = 0.0

    # 1. Drop NaN in essential price columns
    df_clean = df_clean.dropna(subset=req_cols)

    # 2. Filter non-positive prices (prices must be > 0)
    valid_prices = (df_clean['open'] > 0) & (df_clean['high'] > 0) & (df_clean['low'] > 0) & (df_clean['close'] > 0)
    df_clean = df_clean[valid_prices]

    # 3. Filter invalid bar geometry
    valid_geom = (
        (df_clean['high'] >= df_clean['low']) &
        (df_clean['high'] >= df_clean['open']) &
        (df_clean['high'] >= df_clean['close']) &
        (df_clean['low'] <= df_clean['open']) &
        (df_clean['low'] <= df_clean['close'])
    )
    df_clean = df_clean[valid_geom]

    # 4. Filter zero-volume flat dead bars (market closed / frozen quotes)
    is_flat_zero_vol = (df_clean['high'] == df_clean['low']) & (df_clean['volume'] <= 0)
    df_clean = df_clean[~is_flat_zero_vol]

    # 5. Filter corrupt extreme single-bar price spikes (> 30% jump)
    pct_change = (df_clean['close'] - df_clean['open']).abs() / (df_clean['open'] + 1e-8)
    valid_spike = pct_change < 0.30
    df_clean = df_clean[valid_spike]

    # 6. Deduplicate timestamps if time column exists
    if 'time' in df_clean.columns and not df_clean['time'].isnull().all():
        df_clean = df_clean.drop_duplicates(subset=['time'], keep='last')

    return df_clean.reset_index(drop=True)


def calculate_rsi(close_series: pd.Series, period: int = 14) -> pd.Series:
    """Calculates Relative Strength Index (RSI)."""
    close = pd.to_numeric(close_series, errors='coerce').fillna(0.0)
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()
    
    rs = avg_gain / (avg_loss + 1e-8)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return rsi.fillna(50.0)


def calculate_atr(high_series: pd.Series, low_series: pd.Series, close_series: pd.Series, period: int = 14) -> pd.Series:
    """Calculates Average True Range (ATR)."""
    high = pd.to_numeric(high_series, errors='coerce').fillna(0.0)
    low = pd.to_numeric(low_series, errors='coerce').fillna(0.0)
    close = pd.to_numeric(close_series, errors='coerce').fillna(0.0)
    
    prev_close = close.shift(1).fillna(close)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=1).mean()
    return atr.fillna(0.0)


def calculate_ma_diff(close_series: pd.Series, fast_period: int = 5, slow_period: int = 20) -> pd.Series:
    """Calculates normalized difference between fast MA and slow MA: (MA_fast - MA_slow) / Close."""
    close = pd.to_numeric(close_series, errors='coerce').fillna(0.0)
    ma_fast = close.rolling(window=fast_period, min_periods=1).mean()
    ma_slow = close.rolling(window=slow_period, min_periods=1).mean()
    
    diff = (ma_fast - ma_slow) / (close + 1e-8)
    return diff.fillna(0.0)


def calculate_momentum(close_series: pd.Series, period: int = 5) -> pd.Series:
    """Calculates rate of change momentum: (Close - Close_N) / Close_N."""
    close = pd.to_numeric(close_series, errors='coerce').fillna(0.0)
    close_prev = close.shift(period).fillna(close)
    
    mom = (close - close_prev) / (close_prev + 1e-8)
    return mom.fillna(0.0)


def calculate_volume_change(volume_series: pd.Series) -> pd.Series:
    """Calculates volume percentage change: (Vol - Vol_prev) / Vol_prev."""
    vol = pd.to_numeric(volume_series, errors='coerce').fillna(0.0)
    vol_prev = vol.shift(1).fillna(vol)
    
    v_change = (vol - vol_prev) / (vol_prev + 1e-8)
    return v_change.fillna(0.0)


def calculate_body_to_range_ratio(open_series: pd.Series, high_series: pd.Series, low_series: pd.Series, close_series: pd.Series) -> pd.Series:
    """Calculates body size to high-low candle range ratio."""
    open_p = pd.to_numeric(open_series, errors='coerce').fillna(0.0)
    high_p = pd.to_numeric(high_series, errors='coerce').fillna(0.0)
    low_p = pd.to_numeric(low_series, errors='coerce').fillna(0.0)
    close_p = pd.to_numeric(close_series, errors='coerce').fillna(0.0)
    
    body = (close_p - open_p).abs()
    candle_range = (high_p - low_p)
    ratio = body / (candle_range + 1e-8)
    return ratio.fillna(0.0)


def calculate_time_sine_encoding(time_series: pd.Series) -> pd.Series:
    """Calculates cyclic sine encoding for hour of day: sin(2 * pi * hour / 24)."""
    if time_series is None or time_series.empty:
        return pd.Series(0.0, index=pd.RangeIndex(0))
        
    hours = pd.to_datetime(time_series, errors='coerce').dt.hour.fillna(0)
    sin_enc = np.sin(2.0 * np.pi * hours / 24.0)
    return pd.Series(sin_enc, index=time_series.index).fillna(0.0)


def compute_12_features(data: Union[pd.DataFrame, List[Dict[str, Any]]]) -> np.ndarray:
    """
    Computes 12 institutional trading features:
    1. Open
    2. High
    3. Low
    4. Close
    5. Tick Volume
    6. RSI-14
    7. ATR-14
    8. MA5-MA20 Difference (Normalized)
    9. Momentum (5-period ROC)
    10. Volume % Change
    11. Body to Range Ratio
    12. Time Sine Encoding
    """
    if isinstance(data, pd.DataFrame):
        df = data.copy()
    elif isinstance(data, list):
        if not data:
            return np.zeros((0, 12), dtype=np.float32)
        df = pd.DataFrame(data)
    else:
        return np.zeros((0, 12), dtype=np.float32)

    if df.empty:
        return np.zeros((0, 12), dtype=np.float32)

    # Column normalization mapping
    col_map = {
        'price_open': 'open',
        'price_high': 'high',
        'price_low': 'low',
        'price_close': 'close',
        'tick_volume': 'volume',
        'timestamp': 'time'
    }
    for old_col, new_col in col_map.items():
        if old_col in df.columns and new_col not in df.columns:
            df[new_col] = df[old_col]

    open_p = pd.to_numeric(df.get('open', pd.Series(0.0, index=df.index)), errors='coerce').fillna(0.0)
    high_p = pd.to_numeric(df.get('high', pd.Series(0.0, index=df.index)), errors='coerce').fillna(0.0)
    low_p = pd.to_numeric(df.get('low', pd.Series(0.0, index=df.index)), errors='coerce').fillna(0.0)
    close_p = pd.to_numeric(df.get('close', pd.Series(0.0, index=df.index)), errors='coerce').fillna(0.0)
    vol_p = pd.to_numeric(df.get('volume', pd.Series(0.0, index=df.index)), errors='coerce').fillna(0.0)

    time_col = df.get('time', pd.Series(None, index=df.index))

    # Feature calculations
    f1 = open_p
    f2 = high_p
    f3 = low_p
    f4 = close_p
    f5 = vol_p
    f6_rsi = calculate_rsi(close_p, period=14)
    f7_atr = calculate_atr(high_p, low_p, close_p, period=14)
    f8_ma_diff = calculate_ma_diff(close_p, fast_period=5, slow_period=20)
    f9_momentum = calculate_momentum(close_p, period=5)
    f10_vol_change = calculate_volume_change(vol_p)
    f11_body_ratio = calculate_body_to_range_ratio(open_p, high_p, low_p, close_p)
    f12_time_sin = calculate_time_sine_encoding(time_col)

    features_df = pd.DataFrame({
        'open': f1,
        'high': f2,
        'low': f3,
        'close': f4,
        'volume': f5,
        'rsi_14': f6_rsi,
        'atr_14': f7_atr,
        'ma_diff': f8_ma_diff,
        'momentum': f9_momentum,
        'vol_change': f10_vol_change,
        'body_ratio': f11_body_ratio,
        'time_sin': f12_time_sin
    })

    arr = features_df.to_numpy(dtype=np.float32)
    return np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0)


class InstitutionalFeatureScaler:
    """
    Production-grade feature normalizer for LSTM neural networks.
    Provides Z-score standardization, zero-variance protection, non-stationary price handling,
    and extreme outlier clipping [-5.0, 5.0] to guarantee gradient stability.
    """
    def __init__(self, clip_range: float = 5.0, eps: float = 1e-8):
        self.clip_range = clip_range
        self.eps = eps
        self.mean_ = None
        self.std_ = None
        self.n_features_in_ = 12
        self.is_fitted = False

    def fit(self, X: np.ndarray):
        X_arr = np.asarray(X, dtype=np.float32)
        if X_arr.ndim == 1:
            X_arr = X_arr.reshape(-1, 1)
        if X_arr.shape[0] == 0:
            return self

        self.n_features_in_ = X_arr.shape[1]
        self.mean_ = np.nanmean(X_arr, axis=0)
        self.std_ = np.nanstd(X_arr, axis=0)
        # Protect division by zero for constant features
        self.std_ = np.where(self.std_ < self.eps, 1.0, self.std_)
        self.is_fitted = True
        return self

    def transform(self, X: np.ndarray) -> np.ndarray:
        X_arr = np.asarray(X, dtype=np.float32)
        if not self.is_fitted or self.mean_ is None or self.std_ is None:
            # Fallback window normalization if scaler not yet fitted
            mean = np.nanmean(X_arr, axis=0, keepdims=True)
            std = np.nanstd(X_arr, axis=0, keepdims=True)
            std = np.where(std < self.eps, 1.0, std)
            scaled = (X_arr - mean) / std
        else:
            scaled = (X_arr - self.mean_) / self.std_

        scaled = np.nan_to_num(scaled, nan=0.0, posinf=self.clip_range, neginf=-self.clip_range)

        if self.clip_range is not None and self.clip_range > 0:
            scaled = np.clip(scaled, -self.clip_range, self.clip_range)

        return scaled.astype(np.float32)

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        return self.fit(X).transform(X)

    def to_dict(self) -> dict:
        return {
            "mean": self.mean_.tolist() if self.mean_ is not None else [],
            "std": self.std_.tolist() if self.std_ is not None else [],
            "n_features_in": self.n_features_in_,
            "clip_range": self.clip_range,
            "is_fitted": self.is_fitted
        }

    @classmethod
    def from_dict(cls, d: dict):
        scaler = cls(clip_range=d.get("clip_range", 5.0))
        if d.get("mean") and d.get("std"):
            scaler.mean_ = np.array(d["mean"], dtype=np.float32)
            scaler.std_ = np.array(d["std"], dtype=np.float32)
            scaler.n_features_in_ = d.get("n_features_in", 12)
            scaler.is_fitted = d.get("is_fitted", True)
        return scaler


def compute_12_features_dict(data: Union[pd.DataFrame, List[Dict[str, Any]], Dict[str, Any]]) -> Dict[str, Any]:
    """
    Returns feature dictionary and 12-dimensional vector for a single candle or dataset tail.
    """
    if isinstance(data, dict):
        data = [data]
        
    arr = compute_12_features(data)
    if len(arr) == 0:
        fallback_vec = [0.0] * 12
        return {
            "open": 0.0, "high": 0.0, "low": 0.0, "close": 0.0, "volume": 0.0,
            "rsi_14": 50.0, "atr_14": 0.0, "ma_diff": 0.0, "momentum": 0.0,
            "vol_change": 0.0, "body_ratio": 0.0, "time_sin": 0.0,
            "f12_vector": fallback_vec
        }
        
    last_row = arr[-1]
    vec = [float(x) for x in last_row]
    return {
        "open": vec[0],
        "high": vec[1],
        "low": vec[2],
        "close": vec[3],
        "volume": vec[4],
        "rsi_14": vec[5],
        "atr_14": vec[6],
        "ma_diff": vec[7],
        "momentum": vec[8],
        "vol_change": vec[9],
        "body_ratio": vec[10],
        "time_sin": vec[11],
        "f12_vector": vec
    }
