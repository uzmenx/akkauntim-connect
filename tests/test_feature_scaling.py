import sys
import os
import unittest
import numpy as np

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from bot.learning.features import InstitutionalFeatureScaler


class TestInstitutionalFeatureScaler(unittest.TestCase):
    def test_scaler_fit_transform(self):
        # 30 samples, 12 features
        np.random.seed(42)
        raw_features = np.random.randn(30, 12) * 50.0 + 100.0
        # Introduce an extreme outlier
        raw_features[0, 0] = 1e6

        scaler = InstitutionalFeatureScaler(clip_range=5.0)
        scaled = scaler.fit_transform(raw_features)

        self.assertEqual(scaled.shape, (30, 12))
        self.assertFalse(np.isnan(scaled).any())
        self.assertFalse(np.isinf(scaled).any())
        self.assertTrue((scaled >= -5.0).all() and (scaled <= 5.0).all())

    def test_zero_variance_constant_features(self):
        # 20 samples with constant feature values (std = 0)
        constant_features = np.ones((20, 12), dtype=np.float32) * 105.0

        scaler = InstitutionalFeatureScaler(clip_range=5.0)
        scaled = scaler.fit_transform(constant_features)

        self.assertFalse(np.isnan(scaled).any())
        self.assertFalse(np.isinf(scaled).any())
        self.assertTrue(np.allclose(scaled, 0.0))

    def test_serialization_to_from_dict(self):
        raw_features = np.random.randn(40, 12) * 10.0 + 5.0
        scaler = InstitutionalFeatureScaler(clip_range=5.0)
        scaler.fit(raw_features)

        scaled1 = scaler.transform(raw_features)

        d = scaler.to_dict()
        scaler2 = InstitutionalFeatureScaler.from_dict(d)
        scaled2 = scaler2.transform(raw_features)

        self.assertTrue(np.allclose(scaled1, scaled2, atol=1e-5))


if __name__ == "__main__":
    unittest.main()
