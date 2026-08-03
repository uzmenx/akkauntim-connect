import numpy as np
import pytest
from bot.prediction.fan_simulator import (
    FanConfig, 
    compute_volatility, 
    compute_drift, 
    simulate_fan
)

def test_compute_volatility():
    # Constant prices -> 0 volatility (except we clip it to 0.001 minimum)
    closes_const = np.array([100.0, 100.0, 100.0, 100.0])
    vol = compute_volatility(closes_const)
    assert vol == 0.001
    
    # Alternating prices: 1.0, 1.1, 1.0, 1.1 -> non-zero volatility
    closes_var = np.array([1.0, 1.1, 1.0, 1.1])
    vol_var = compute_volatility(closes_var)
    assert vol_var > 0.001

def test_compute_drift_neutral():
    vol = 0.01
    
    # If confidence is 0, drift should be 0 regardless of direction
    drift_buy_zero_conf = compute_drift("BUY", 0.0, vol)
    assert drift_buy_zero_conf == 0.0
    
    # If direction is NEUTRAL, drift should be 0 regardless of confidence
    drift_neutral = compute_drift("NEUTRAL", 1.0, vol)
    assert drift_neutral == 0.0

def test_simulate_fan_shape():
    config = FanConfig(n_paths=100, n_steps=20, seed=42)
    closes = np.array([100.0, 101.0, 102.0, 101.5])
    
    result = simulate_fan(closes, "BUY", 0.8, config)
    
    assert isinstance(result, np.ndarray)
    assert result.shape == (100, 20)
    
def test_simulate_fan_directionality():
    config = FanConfig(n_paths=1000, n_steps=10, seed=42)
    closes = np.array([100.0, 101.0, 102.0, 101.5, 102.5, 103.0])
    
    # Strong BUY signal
    buy_paths = simulate_fan(closes, "BUY", 1.0, config)
    # Strong SELL signal
    sell_paths = simulate_fan(closes, "SELL", 1.0, config)
    
    # Check median final prices
    buy_median = np.median(buy_paths[:, -1])
    sell_median = np.median(sell_paths[:, -1])
    
    last_price = closes[-1]
    
    # The BUY median should be higher than the SELL median
    assert buy_median > sell_median
    
    # The BUY median should ideally drift upwards from the last price 
    # and SELL median should drift downwards.
    assert buy_median > last_price
    assert sell_median < last_price
