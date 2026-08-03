# -*- coding: utf-8 -*-
"""
Confluence Engine unit testlari.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np

def test_helpers():
    """Zone overlap va distance funksiyalarini test qilish."""
    from bot.engine.confluence import _zones_overlap, _zone_distance_atr

    print("=== Zone Overlap Testlar ===")
    
    # Test 1: Overlap bor
    o1, p1 = _zones_overlap(100, 90, 105, 95)
    assert o1 == True, f"Test 1 FAILED: overlap should be True, got {o1}"
    assert 0.4 <= p1 <= 0.6, f"Test 1 FAILED: overlap_pct should be ~0.5, got {p1}"
    print(f"  Test 1 PASS: Overlap bor (90-100 vs 95-105): overlap={o1}, pct={p1:.2f}")
    
    # Test 2: Overlap yo'q
    o2, p2 = _zones_overlap(100, 90, 80, 70)
    assert o2 == False, f"Test 2 FAILED: overlap should be False, got {o2}"
    print(f"  Test 2 PASS: Overlap yoq (90-100 vs 70-80): overlap={o2}, pct={p2:.2f}")
    
    # Test 3: To'liq overlap
    o3, p3 = _zones_overlap(100, 90, 100, 90)
    assert o3 == True, f"Test 3 FAILED: overlap should be True"
    assert p3 == 1.0, f"Test 3 FAILED: overlap_pct should be 1.0, got {p3}"
    print(f"  Test 3 PASS: Tuliq overlap (90-100 vs 90-100): overlap={o3}, pct={p3:.2f}")
    
    # Test 4: Kichik overlap (ichma-ich)
    o4, p4 = _zones_overlap(100, 90, 98, 92)
    assert o4 == True, f"Test 4 FAILED: overlap should be True"
    assert p4 == 1.0, f"Test 4 FAILED: inner zone fully covered, got {p4}"
    print(f"  Test 4 PASS: Kichik overlap (90-100 vs 92-98): overlap={o4}, pct={p4:.2f}")
    
    # Test 5: Chegarada tegish
    o5, p5 = _zones_overlap(100, 90, 90, 80)
    assert o5 == False or p5 == 0.0, f"Test 5: border touch"
    print(f"  Test 5 PASS: Chegara tegish (90-100 vs 80-90): overlap={o5}, pct={p5:.2f}")

    print("\n=== Distance Testlar ===")
    
    # Test 6: Narx ichida
    d1 = _zone_distance_atr(100, 90, 95, 5)
    assert d1 == 0.0, f"Test 6 FAILED: should be 0.0 (inside zone), got {d1}"
    print(f"  Test 6 PASS: Narx ichida (95 in 90-100, ATR=5): {d1:.2f} ATR")
    
    # Test 7: Narx yuqorida
    d2 = _zone_distance_atr(100, 90, 110, 5)
    assert d2 == 2.0, f"Test 7 FAILED: should be 2.0, got {d2}"
    print(f"  Test 7 PASS: Narx yuqorida (110 vs 90-100, ATR=5): {d2:.2f} ATR")
    
    # Test 8: Narx pastda
    d3 = _zone_distance_atr(100, 90, 80, 5)
    assert d3 == 2.0, f"Test 8 FAILED: should be 2.0, got {d3}"
    print(f"  Test 8 PASS: Narx pastda (80 vs 90-100, ATR=5): {d3:.2f} ATR")


def test_compute_atr():
    """ATR hisoblashni test qilish."""
    from bot.engine.confluence import compute_atr
    
    print("\n=== ATR Testlar ===")
    
    # Oddiy test data
    np.random.seed(42)
    n = 50
    prices = 100 + np.cumsum(np.random.randn(n) * 0.5)
    df = pd.DataFrame({
        "open": prices,
        "high": prices + np.random.rand(n) * 2,
        "low": prices - np.random.rand(n) * 2,
        "close": prices + np.random.randn(n) * 0.3,
    })
    
    atr = compute_atr(df, period=14)
    assert atr > 0, f"ATR should be positive, got {atr}"
    print(f"  ATR = {atr:.4f} (expected > 0)")
    
    # Bo'sh DataFrame
    atr_empty = compute_atr(pd.DataFrame(), period=14)
    assert atr_empty == 0.0, f"Empty DF ATR should be 0, got {atr_empty}"
    print(f"  Empty DF ATR = {atr_empty} (expected 0.0)")
    print("  ATR testlari PASS!")


def test_full_confluence():
    """To'liq confluence hisoblashni test qilish."""
    from bot.engine.confluence import calculate_confluence
    
    print("\n=== Full Confluence Test ===")
    
    # Test data yaratish
    np.random.seed(42)
    n = 100
    base_prices = np.linspace(1.1000, 1.1100, n) + np.random.randn(n) * 0.0005
    
    df = pd.DataFrame({
        "open": base_prices,
        "high": base_prices + np.random.rand(n) * 0.002,
        "low": base_prices - np.random.rand(n) * 0.002,
        "close": base_prices + np.random.randn(n) * 0.0003,
    })
    
    current_price = float(df["close"].iloc[-1])
    
    # --- Test 1: SMC demand OB + Harmonic Bullish PRZ overlap ---
    smc_data = {
        "trend": {"internal": "Up Trend", "external": "Up Trend"},
        "last_bos": {"type": "Bullish", "price": 1.1080, "bar_index": 95},
        "last_choch": None,
        "order_blocks": {
            "demand": [
                {
                    "top": current_price + 0.0005,
                    "bottom": current_price - 0.0010,
                    "status": "fresh",
                    "origin": "ChoCh Main",
                    "level": "Major",
                    "bar_index": 90,
                    "distance_pct": 0.1,
                }
            ],
            "supply": [],
        },
        "fvg": {
            "demand": [
                {
                    "top": current_price + 0.0003,
                    "bottom": current_price - 0.0005,
                    "status": "fresh",
                    "bar_index": 92,
                }
            ],
            "supply": [],
        },
        "liquidity": {
            "static_high": current_price + 0.0050,
            "static_low": current_price - 0.0030,
            "dynamic_high": None,
            "dynamic_low": current_price - 0.0020,
        },
    }
    
    harmonic_data = {
        "current_price": current_price,
        "active_pattern": {
            "name": "Gartley",
            "direction": "Bullish",
            "xabcd_points": {
                "x": current_price - 0.0100,
                "a": current_price + 0.0050,
                "b": current_price - 0.0030,
                "c": current_price + 0.0020,
                "d": current_price - 0.0005,
            },
            "ratios": {"xab": 0.55, "xad": 0.80, "abc": 0.60, "bcd": 1.50},
            "bars_since_d": 3,
        },
        "emerging_patterns": [],
        "signal": "BUY",
        "fib_levels": {
            "entry": current_price - 0.0003,
            "tp": current_price + 0.0040,
            "sl": current_price - 0.0015,
        },
        "all_detected_patterns": [],
    }
    
    news_data = {
        "historical_bias": {
            "direction": "Bullish",
            "confidence": 0.7,
            "sample_size": 20,
            "avg_move_pct": 0.15,
        },
        "institutional_context": {
            "cot_trend": "Net Long",
            "note": "Institutional buyers dominant",
        },
        "next_event": None,
    }
    
    result = calculate_confluence(
        smc_data=smc_data,
        harmonic_data=harmonic_data,
        news_data=news_data,
        df=df,
        current_price=current_price,
    )
    
    print(f"  Signal: {result.signal}")
    print(f"  Score: {result.score}/140")
    print(f"  Decision: {result.decision}")
    print(f"  Risk: {result.risk_pct:.1%}")
    print(f"  Direction: {result.direction}")
    print(f"  Breakdown: {result.score_breakdown}")
    print(f"  Warnings: {result.warnings}")
    print(f"  Reasoning: {result.reasoning[:200]}...")
    
    assert result.signal == "BUY", f"Expected BUY, got {result.signal}"
    assert result.score >= 50, f"Expected score >= 50, got {result.score}"
    assert result.direction == "Bullish", f"Expected Bullish, got {result.direction}"
    assert result.risk_pct > 0, f"Expected risk > 0, got {result.risk_pct}"
    print("  Full confluence test 1 PASS! (Kuchli BUY confluence)")
    
    # --- Test 2: Hech narsa yo'q — REJECT bo'lishi kerak ---
    empty_smc = {
        "trend": {"internal": "No Trend", "external": "No Trend"},
        "order_blocks": {"demand": [], "supply": []},
        "fvg": {"demand": [], "supply": []},
        "liquidity": {},
    }
    empty_harmonic = {
        "signal": "NEUTRAL",
        "active_pattern": None,
        "emerging_patterns": [],
    }
    
    result2 = calculate_confluence(
        smc_data=empty_smc,
        harmonic_data=empty_harmonic,
        news_data={},
        df=df,
    )
    
    print(f"\n  Test 2 - Bo'sh data:")
    print(f"  Signal: {result2.signal}")
    print(f"  Score: {result2.score}/140")
    print(f"  Decision: {result2.decision}")
    
    assert result2.signal == "HOLD", f"Expected HOLD, got {result2.signal}"
    assert result2.decision == "REJECT", f"Expected REJECT, got {result2.decision}"
    print("  Full confluence test 2 PASS! (HOLD/REJECT with no data)")
    
    # --- Test 3: Faqat SMC bor, Harmonic yo'q ---
    result3 = calculate_confluence(
        smc_data=smc_data,
        harmonic_data=empty_harmonic,
        news_data={},
        df=df,
    )
    
    print(f"\n  Test 3 - Faqat SMC:")
    print(f"  Signal: {result3.signal}")
    print(f"  Score: {result3.score}/140")
    print(f"  Decision: {result3.decision}")
    print(f"  Breakdown: {result3.score_breakdown}")
    
    assert result3.score < result.score, "SMC only should score less than full confluence"
    print("  Full confluence test 3 PASS! (SMC only = lower score)")


def test_to_dict():
    """ConfluenceResult.to_dict() testlash."""
    from bot.engine.confluence import calculate_confluence
    
    print("\n=== to_dict Test ===")
    
    df = pd.DataFrame({
        "open": np.ones(30),
        "high": np.ones(30) * 1.01,
        "low": np.ones(30) * 0.99,
        "close": np.ones(30),
    })
    
    result = calculate_confluence(
        smc_data={},
        harmonic_data={},
        news_data={},
        df=df,
    )
    
    d = result.to_dict()
    assert isinstance(d, dict), "to_dict should return dict"
    assert "signal" in d, "Missing 'signal' key"
    assert "score" in d, "Missing 'score' key"
    assert "decision" in d, "Missing 'decision' key"
    assert "score_breakdown" in d, "Missing 'score_breakdown' key"
    print(f"  to_dict returned: {list(d.keys())}")
    print("  to_dict test PASS!")


if __name__ == "__main__":
    print("=" * 60)
    print("CONFLUENCE ENGINE TESTLARI")
    print("=" * 60)
    
    test_helpers()
    test_compute_atr()
    test_full_confluence()
    test_to_dict()
    
    print("\n" + "=" * 60)
    print("BARCHA TESTLAR MUVAFFAQIYATLI OTDI!")
    print("=" * 60)
