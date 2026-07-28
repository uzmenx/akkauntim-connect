import pandas as pd
import numpy as np
from bot.engine.regime_detector import RegimeDetector, MarketRegime

def test_regime_detector_trend():
    detector = RegimeDetector(lookback=20)
    
    # Monotonik o'suvchi narx
    prices = np.linspace(100, 200, 50)
    df = pd.DataFrame({
        'open': prices - 1,
        'high': prices + 2,
        'low': prices - 2,
        'close': prices,
        'volume': np.random.randint(100, 200, 50),
        'spread': np.random.uniform(0.1, 0.5, 50)
    })
    
    regime = detector.update(df)
    print("Trend rejimi testi:", regime)
    assert regime == MarketRegime.TREND

def test_regime_detector_range():
    detector = RegimeDetector(lookback=20)
    
    # Tor diapazondagi narx
    np.random.seed(42)
    prices = 100 + np.random.normal(0, 0.5, 50)
    df = pd.DataFrame({
        'open': prices,
        'high': prices + 0.1,
        'low': prices - 0.1,
        'close': prices + 0.05,
        'volume': np.random.randint(100, 200, 50),
        'spread': np.random.uniform(0.1, 0.2, 50)
    })
    
    # Avvalgi ma'lumotlar orqali volatile qismini kamaytirish
    regime = detector.update(df)
    print("Range rejimi testi:", regime)
    assert regime == MarketRegime.RANGE

def test_regime_detector_volatile():
    detector = RegimeDetector(lookback=20)
    
    # Keskin sakrashlar (yuqori volatilite)
    prices = 100 + np.random.normal(0, 5, 50)
    highs = prices + np.abs(np.random.normal(0, 10, 50))
    lows = prices - np.abs(np.random.normal(0, 10, 50))
    
    # So'nggi qiymatni ayniqsa volatile qilish
    highs[-1] = highs[-1] + 50
    lows[-1] = lows[-1] - 50
    
    df = pd.DataFrame({
        'open': prices,
        'high': highs,
        'low': lows,
        'close': prices,
        'volume': np.random.randint(100, 200, 50),
        'spread': np.random.uniform(0.1, 0.5, 50)
    })
    
    regime = detector.update(df)
    print("Volatile rejimi testi:", regime)
    assert regime == MarketRegime.VOLATILE

def test_regime_detector_empty():
    detector = RegimeDetector(lookback=20)
    df = pd.DataFrame()
    regime = detector.update(df)
    print("Bo'sh dataframe testi:", regime)
    assert regime == MarketRegime.UNKNOWN

if __name__ == "__main__":
    print("=== RegimeDetector testlari ===")
    test_regime_detector_trend()
    test_regime_detector_range()
    test_regime_detector_volatile()
    test_regime_detector_empty()
    print("Barcha testlar muvaffaqiyatli o'tdi!")
