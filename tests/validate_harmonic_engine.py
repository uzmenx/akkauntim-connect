import unittest
import pandas as pd
import numpy as np
from bot.strategy.harmonic.engine import (
    get_ratios, PATTERN_FUNCTIONS, calculate_zigzag, calc_fib,
    calculate_pattern_confidence, analyze_harmonic_patterns
)

class TestHarmonicEngine(unittest.TestCase):
    def test_zigzag_calculation(self):
        data = {
            'open':  [10, 10, 10, 15, 15, 20, 20, 18],
            'high':  [12, 11, 16, 17, 22, 21, 19, 18],
            'low':   [8,   9,  9, 14, 14, 18, 17, 15],
            'close': [11,  9, 15, 16, 21, 19, 18, 16] 
        }
        df = pd.DataFrame(data)
        zz = calculate_zigzag(df)
        
        self.assertEqual(zz.iloc[1], 12.0)
        self.assertEqual(zz.iloc[2], 9.0)
        self.assertEqual(zz.iloc[5], 22.0)

    def test_get_ratios(self):
        r = get_ratios(100, 200, 150, 175, 138.2)
        self.assertLess(abs(r['xab'] - 0.5), 0.01)
        self.assertLess(abs(r['abc'] - 0.5), 0.01)

    def test_gartley_ratios(self):
        ratios = {'xab': 0.618, 'abc': 0.6, 'bcd': 1.272, 'xad': 0.786}
        self.assertTrue(PATTERN_FUNCTIONS['Gartley'](ratios, 1, 200, 100))
        self.assertTrue(PATTERN_FUNCTIONS['Gartley'](ratios, -1, 100, 200))
        
        ratios_bad = {'xab': 0.4, 'abc': 0.6, 'bcd': 1.5, 'xad': 0.786}
        self.assertFalse(PATTERN_FUNCTIONS['Gartley'](ratios_bad, 1, 200, 100))

    def test_pattern_confidence_calculation(self):
        ideal_gartley_ratios = {'xab': 0.618, 'abc': 0.618, 'bcd': 1.272, 'xad': 0.786}
        conf_ideal = calculate_pattern_confidence("Gartley", ideal_gartley_ratios)
        self.assertGreaterEqual(conf_ideal, 95.0)

        imperfect_gartley_ratios = {'xab': 0.55, 'abc': 0.5, 'bcd': 1.4, 'xad': 0.82}
        conf_imperfect = calculate_pattern_confidence("Gartley", imperfect_gartley_ratios)
        self.assertGreater(conf_imperfect, 50.0)
        self.assertLess(conf_imperfect, conf_ideal)

    def test_fib_calc(self):
        self.assertEqual(calc_fib(100, 200, 0.5), 150)
        self.assertEqual(calc_fib(100, 200, 0.236), 200 - (100 * 0.236))
        self.assertEqual(calc_fib(200, 100, 0.5), 150)
        self.assertEqual(calc_fib(200, 100, 0.236), 100 + (100 * 0.236))

if __name__ == "__main__":
    unittest.main()
