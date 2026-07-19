import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pattern_detector import HarmonicPatternDetector, extract_pivots_from_data

def generate_mock_data(n_bars=500):
    """Generate some mock OHLC data with a predictable zigzag pattern to test harmonic detection"""
    dates = [datetime.now() - timedelta(hours=x) for x in range(n_bars)]
    dates.reverse()
    
    df = pd.DataFrame(index=dates)
    
    # Generate a sine wave to create highs and lows
    t = np.linspace(0, 4 * np.pi, n_bars)
    base_price = 1.1000
    amplitude = 0.0500
    
    # Adding a complex wave to simulate realistic harmonic movements
    wave = np.sin(t) + 0.5 * np.cos(2*t) + 0.2 * np.sin(3*t)
    prices = base_price + wave * amplitude
    
    # Create OHLC
    df['open'] = prices
    df['high'] = prices + np.random.uniform(0.0010, 0.0050, n_bars)
    df['low'] = prices - np.random.uniform(0.0010, 0.0050, n_bars)
    df['close'] = prices + np.random.uniform(-0.0020, 0.0020, n_bars)
    
    return df

def test_specific_pattern():
    """Test the detector with specific pivot points that form a Bat pattern."""
    detector = HarmonicPatternDetector(error_allowance=0.15)
    
    # Bullish Bat Pattern ratios:
    # xab = 0.382 to 0.5
    # abc = 0.382 to 0.886
    # bcd = 1.618 to 2.618
    # xad = 0.886
    
    # D < C for Bullish
    
    # Let X = 1.0
    # Let A = 2.0 (Move up 1.0)
    # Let B = 1.5 (Retrace 0.5 -> xab = 0.5)
    # Let C = 1.8 (Retrace 0.3 -> abc = 0.3/0.5 = 0.6)
    # Let D = 1.114 (Down 0.686 -> bcd = 0.686/0.3 = 2.28, xad = 0.886/1.0 = 0.886)
    
    pivots = [1.0, 2.0, 1.5, 1.8, 1.114]
    
    print("\n--- Testing Specific Pivot Points ---")
    print(f"Pivots: {pivots}")
    result = detector.detect_patterns(pivots)
    if result:
        print(f"Detected {result['type']} Pattern(s): {', '.join(result['patterns'])}")
        print(f"Ratios: {result['ratios']}")
    else:
        print("No patterns detected.")

def main():
    print("--- Pattern Strategy Validation ---")
    
    # Test 1: Specific mathematical points
    test_specific_pattern()
    
    # Test 2: Mock OHLC Data
    print("\n--- Testing Mock OHLC Data ---")
    df = generate_mock_data(200)
    
    pivots = extract_pivots_from_data(df, depth=5)
    
    print(f"Extracted latest pivots: {pivots}")
    
    if len(pivots) >= 5:
        detector = HarmonicPatternDetector(error_allowance=0.10)
        result = detector.detect_patterns(pivots)
        
        if result:
            print(f"Detected {result['type']} Pattern(s): {', '.join(result['patterns'])}")
            print(f"Ratios: {result['ratios']}")
        else:
            print("No patterns detected in the current mock data segment.")
            
            # Print calculated ratios to debug why
            x, a, b, c, d = pivots[-5:]
            xab = abs(b - a) / abs(x - a) if abs(x - a) != 0 else 0
            xad = abs(a - d) / abs(x - a) if abs(x - a) != 0 else 0
            abc = abs(b - c) / abs(a - b) if abs(a - b) != 0 else 0
            bcd = abs(c - d) / abs(b - c) if abs(b - c) != 0 else 0
            
            print(f"Calculated ratios were: XAB={xab:.3f}, ABC={abc:.3f}, BCD={bcd:.3f}, XAD={xad:.3f}")
    else:
        print("Not enough pivots detected. Try a smaller depth or larger data set.")

if __name__ == '__main__':
    main()
