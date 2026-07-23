# -*- coding: utf-8 -*-
"""
Wyckoff + Confluence test.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

def test_wyckoff():
    from bot.strategy.wyckoff.engine import analyze_wyckoff
    from bot.engine.confluence import calculate_confluence
    
    print("=== Wyckoff Engine Test ===")
    
    # Fake Accumulation + Spring data
    np.random.seed(42)
    n = 120
    # Sideways market
    prices = 1.1000 + np.random.randn(n) * 0.0010
    
    # Create a downtrend at the start of the lookback window (n=120, lookback=100 -> index 20)
    prices[20:30] = np.linspace(1.1050, 1.1000, 10)
    # Price dips below range and recovers
    prices[-10] = 1.0950 # Below range
    prices[-9] = 1.0960
    prices[-8] = 1.0970
    prices[-5] = 1.1020
    prices[-1] = 1.1030
    
    df = pd.DataFrame({
        "open": prices - 0.0005, # Open is lower than close for bullish candles
        "high": prices + 0.0010,
        "low": prices - 0.0010,
        "close": prices,
        "tick_volume": np.random.randint(100, 1000, n)
    })
    
    # Fake SOS candle
    df.loc[n-5, 'open'] = 1.1000
    df.loc[n-5, 'close'] = 1.1030 # Large body = 0.0030
    df.loc[n-5, 'high'] = 1.1035
    df.loc[n-5, 'low'] = 1.0995
    df.loc[n-5, 'tick_volume'] = 2500
    
    wyckoff = analyze_wyckoff(df)
    
    print(f"Phase: {wyckoff['phase']}")
    print(f"Spring/Upthrust: {wyckoff['spring_upthrust']}")
    print(f"Momentum: {wyckoff['momentum_sign']}")
    
    assert wyckoff['phase'] == "Accumulation", f"Expected Accumulation, got {wyckoff['phase']}"
    assert wyckoff['spring_upthrust'] == "Spring", f"Expected Spring, got {wyckoff['spring_upthrust']}"
    assert wyckoff['momentum_sign'] == "SOS", f"Expected SOS, got {wyckoff['momentum_sign']}"
    
    print("Wyckoff standalone test PASS!")
    
    print("\n=== Confluence Integration Test ===")
    
    smc_data = {
        "trend": {"internal": "Up Trend", "external": "Up Trend"},
        "order_blocks": {
            "demand": [
                {
                    "top": 1.1020,
                    "bottom": 1.0990,
                    "status": "fresh",
                    "bar_index": 110,
                    "distance_pct": 0.1,
                }
            ],
            "supply": [],
        },
        "fvg": {"demand": [], "supply": []},
    }
    
    harmonic_data = {
        "signal": "BUY",
        "active_pattern": {
            "name": "Bat",
            "direction": "Bullish",
        },
        "fib_levels": {
            "entry": 1.1000,
        }
    }
    
    conf = calculate_confluence(
        smc_data=smc_data,
        harmonic_data=harmonic_data,
        news_data={},
        df=df,
        wyckoff_data=wyckoff
    )
    
    print(f"Signal: {conf.signal}")
    print(f"Score: {conf.score}/200")
    print(f"Decision: {conf.decision}")
    print(f"Breakdown: {conf.score_breakdown}")
    
    # Check if wyckoff points were added
    assert "wyckoff" in conf.score_breakdown, "Wyckoff points missing!"
    # Phase = 15, Spring = 30, SOS = 5 => Total 50 points from Wyckoff!
    assert conf.score_breakdown["wyckoff"] == 50, f"Expected 50 Wyckoff points, got {conf.score_breakdown['wyckoff']}"
    
    print("Confluence Integration test PASS!")

if __name__ == "__main__":
    test_wyckoff()
