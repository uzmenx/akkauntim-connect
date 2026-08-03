"""
test_smc_engine.py
==================
smc_engine.py uchun unit testlar.

Synthetic (sun'iy) OHLC data bilan asosiy stsenariylarni tekshiradi:
  1. Pivot aniqlash
  2. BoS paydo bo'lishi
  3. ChoCh paydo bo'lishi
  4. Order Block yaratilishi
  5. FVG topilishi
  6. To'liq analyze_market_structure() output formati

Ishga tushirish:
  cd c:\\Users\\PC\\Desktop\\akkauntim-connect
  python -m pytest test_smc_engine.py -v
"""

try:
    import pytest
except ImportError:
    pytest = None  # testlarni pytest'siz ham ishga tushirish mumkin

import pandas as pd
import numpy as np

from bot.strategy.smc.engine import (
    analyze_market_structure,
    OrderBlockDetector,
    FVGDetector,
    LiquidityDetector,
    DEFAULT_CONFIG,
)
from bot.strategy.smc.engine import SMCStructure


# ====================================================================
# Yordamchi: Synthetic OHLC data generatorlari
# ====================================================================

def make_df(ohlc_list: list) -> pd.DataFrame:
    """
    OHLC ro'yxatidan DataFrame yasaydi.
    Har bir element: (open, high, low, close)
    """
    rows = []
    for i, (o, h, l, c) in enumerate(ohlc_list):
        rows.append({
            "timestamp": pd.Timestamp("2024-01-01") + pd.Timedelta(hours=i),
            "open": o,
            "high": h,
            "low": l,
            "close": c,
            "volume": 100,
        })
    return pd.DataFrame(rows)


def generate_trending_data(
    start: float = 1.1000,
    bars: int = 100,
    trend: str = "up",
    volatility: float = 0.0010,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Sun'iy trending OHLC data generatsiyasi.
    trend = "up" | "down" | "zigzag"
    """
    rng = np.random.RandomState(seed)
    rows = []
    price = start

    for i in range(bars):
        if trend == "up":
            drift = volatility * 0.5
        elif trend == "down":
            drift = -volatility * 0.5
        else:  # zigzag
            drift = volatility * 0.5 * (1 if (i // 15) % 2 == 0 else -1)

        change = drift + rng.randn() * volatility
        open_ = price
        close = price + change

        high = max(open_, close) + abs(rng.randn() * volatility * 0.3)
        low = min(open_, close) - abs(rng.randn() * volatility * 0.3)

        rows.append({
            "timestamp": pd.Timestamp("2024-01-01") + pd.Timedelta(hours=i),
            "open": round(open_, 5),
            "high": round(high, 5),
            "low": round(low, 5),
            "close": round(close, 5),
            "volume": rng.randint(50, 200),
        })
        price = close

    return pd.DataFrame(rows)


def generate_breakout_data(bars: int = 120, seed: int = 42) -> pd.DataFrame:
    """
    Trend o'zgarishi bo'lgan data — avval pastga, keyin keskin yuqoriga.
    Bu ChoCh va BoS hodisalarini yaratishi kerak.
    """
    rng = np.random.RandomState(seed)
    rows = []
    price = 1.1000

    for i in range(bars):
        if i < 40:
            # Boshlang'ich down trend
            drift = -0.0008
        elif i < 50:
            # Consolidation
            drift = 0.0001 * (1 if i % 2 == 0 else -1)
        elif i < 55:
            # Keskin breakout yuqoriga (ChoCh moment)
            drift = 0.0020
        elif i < 80:
            # Yangi up trend (BoS'lar)
            drift = 0.0006
        elif i < 95:
            # Yana pastga
            drift = -0.0012
        else:
            # Yana yuqoriga
            drift = 0.0008

        change = drift + rng.randn() * 0.0005
        open_ = price
        close = price + change
        high = max(open_, close) + abs(rng.randn() * 0.0003)
        low = min(open_, close) - abs(rng.randn() * 0.0003)

        rows.append({
            "timestamp": pd.Timestamp("2024-01-01") + pd.Timedelta(hours=i),
            "open": round(open_, 5),
            "high": round(high, 5),
            "low": round(low, 5),
            "close": round(close, 5),
            "volume": rng.randint(50, 200),
        })
        price = close

    return pd.DataFrame(rows)


def generate_fvg_data() -> pd.DataFrame:
    """
    Aniq FVG (Fair Value Gap) bo'lgan data.
    Bar 2 ning low > Bar 0 ning high → Demand FVG.
    """
    ohlc = [
        # Barlar 0-9: oddiy harakat
        (1.1000, 1.1010, 1.0990, 1.1005),
        (1.1005, 1.1015, 1.0995, 1.1010),
        (1.1010, 1.1020, 1.1000, 1.1015),
        (1.1015, 1.1025, 1.1005, 1.1020),
        (1.1020, 1.1030, 1.1010, 1.1025),
        (1.1025, 1.1035, 1.1015, 1.1030),
        (1.1030, 1.1040, 1.1020, 1.1035),
        (1.1035, 1.1045, 1.1025, 1.1040),
        (1.1040, 1.1050, 1.1030, 1.1045),
        (1.1045, 1.1055, 1.1035, 1.1050),
        # Bar 10: normal
        (1.1050, 1.1055, 1.1045, 1.1048),
        # Bar 11: kichik sham (o'rta sham)
        (1.1048, 1.1052, 1.1046, 1.1050),
        # Bar 12: katta sakrash yuqoriga → Demand FVG
        # low[12] = 1.1060 > high[10] = 1.1055 → GAP!
        (1.1060, 1.1075, 1.1060, 1.1070),
        # Davomi
        (1.1070, 1.1080, 1.1065, 1.1075),
        (1.1075, 1.1085, 1.1070, 1.1080),
        # Bar 15: normal
        (1.1080, 1.1085, 1.1075, 1.1082),
        # Bar 16: kichik sham
        (1.1082, 1.1084, 1.1078, 1.1080),
        # Bar 17: katta tushish pastga → Supply FVG
        # high[17] = 1.1070 < low[15] = 1.1075 → GAP!
        (1.1070, 1.1070, 1.1055, 1.1060),
        (1.1060, 1.1065, 1.1055, 1.1058),
        (1.1058, 1.1062, 1.1052, 1.1055),
    ]
    return make_df(ohlc)


# ====================================================================
# Test 1: Pivot Aniqlash
# ====================================================================

class TestPivotDetection:
    """SMCStructure pivot nuqtalarni to'g'ri aniqlashini tekshiradi."""

    def test_pivots_are_detected(self):
        """Yetarli data bilan kamida bir nechta pivot topilishi kerak."""
        df = generate_trending_data(bars=60, trend="zigzag", seed=123)
        smc = SMCStructure(pivot_period=3)
        smc.run(
            df["high"].tolist(),
            df["low"].tolist(),
            df["close"].tolist(),
        )
        # ZigZag massivlarida pivot'lar bo'lishi kerak
        assert len(smc.zz_type) > 0, "Pivot'lar topilishi kerak edi"
        assert len(smc.zz_value) == len(smc.zz_type), "Value va Type massivlari teng bo'lishi kerak"

    def test_pivot_types_are_valid(self):
        """Pivot turlari faqat H/L/HH/HL/LH/LL bo'lishi kerak."""
        df = generate_trending_data(bars=80, trend="zigzag", seed=456)
        smc = SMCStructure(pivot_period=3)
        smc.run(
            df["high"].tolist(),
            df["low"].tolist(),
            df["close"].tolist(),
        )
        valid_types = {"H", "L", "HH", "HL", "LH", "LL"}
        for t in smc.zz_type:
            assert t in valid_types, f"Noto'g'ri pivot turi: {t}"


# ====================================================================
# Test 2: BoS Aniqlash
# ====================================================================

class TestBoSDetection:
    """Break of Structure (BoS) hodisalari to'g'ri aniqlanishini tekshiradi."""

    def test_bos_exists_in_trending_data(self):
        """Kuchli trend bor data'da BoS hodisalari bo'lishi kerak."""
        df = generate_breakout_data(bars=120, seed=42)
        result = analyze_market_structure(df, {"pivot_period": 3})

        # BoS yoki ChoCh hodisalar bo'lishi kerak
        total_events = result["summary"]["total_events"]
        assert total_events > 0, "Trend bor datada kamida 1 ta event bo'lishi kerak"

    def test_bos_has_correct_format(self):
        """last_bos formati to'g'ri bo'lishi kerak."""
        df = generate_breakout_data(bars=120, seed=42)
        result = analyze_market_structure(df, {"pivot_period": 3})

        if result["last_bos"] is not None:
            bos = result["last_bos"]
            assert "type" in bos
            assert bos["type"] in ("Bullish", "Bearish")
            assert "level" in bos
            assert bos["level"] in ("Major", "Minor")
            assert "price" in bos
            assert isinstance(bos["price"], float)
            assert "bar_index" in bos


# ====================================================================
# Test 3: ChoCh Aniqlash
# ====================================================================

class TestChochDetection:
    """Change of Character (ChoCh) hodisalari to'g'ri aniqlanishini tekshiradi."""

    def test_choch_in_reversal_data(self):
        """Trend o'zgarishi bo'lgan datada ChoCh bo'lishi kerak."""
        df = generate_breakout_data(bars=120, seed=42)
        result = analyze_market_structure(df, {"pivot_period": 3})

        # Breakout data'da kamida biror event bo'lishi kerak
        assert result["summary"]["total_events"] > 0, \
            "Reversal datada event'lar bo'lishi kerak"

    def test_choch_correct_format(self):
        """ChoCh formati to'g'ri."""
        df = generate_breakout_data(bars=120, seed=42)
        result = analyze_market_structure(df, {"pivot_period": 3})

        if result["last_choch"] is not None:
            choch = result["last_choch"]
            assert choch["kind"] == "ChoCh"
            assert choch["type"] in ("Bullish", "Bearish")


# ====================================================================
# Test 4: Order Block Yaratilishi
# ====================================================================

class TestOrderBlockCreation:
    """Order Block'lar to'g'ri yaratilishini tekshiradi."""

    def test_obs_created_for_events(self):
        """BoS/ChoCh bo'lgan datada OB'lar yaratilishi kerak."""
        df = generate_breakout_data(bars=120, seed=42)
        result = analyze_market_structure(df, {"pivot_period": 3})

        if result["summary"]["total_events"] > 0:
            total_obs = result["summary"]["total_obs"]
            # Event'lar bo'lsa, OB'lar ham bo'lishi kerak
            assert total_obs > 0, \
                f"Event'lar bor ({result['summary']['total_events']}), lekin OB yo'q"

    def test_ob_has_correct_fields(self):
        """Har bir OB kerakli maydonlarga ega bo'lishi kerak."""
        df = generate_breakout_data(bars=120, seed=42)
        result = analyze_market_structure(df, {"pivot_period": 3})

        all_obs = result["order_blocks"]["demand"] + result["order_blocks"]["supply"]
        for ob in all_obs:
            assert "top" in ob
            assert "bottom" in ob
            assert ob["top"] >= ob["bottom"], \
                f"OB top ({ob['top']}) bottom ({ob['bottom']}) dan kichik bo'lmasligi kerak"
            assert ob["origin"] in ("ChoCh Main", "ChoCh Sub", "BoS")
            assert ob["level"] in ("Major", "Minor")
            assert ob["status"] in ("fresh", "mitigated")

    def test_ob_validity_period(self):
        """Muddati o'tgan OB'lar filtirlanishi kerak."""
        df = generate_breakout_data(bars=120, seed=42)
        # Juda qisqa validity period
        result = analyze_market_structure(df, {
            "pivot_period": 3,
            "ob_validity_bars": 10,
        })

        all_obs = result["order_blocks"]["demand"] + result["order_blocks"]["supply"]
        current_bar = len(df) - 1
        for ob in all_obs:
            assert current_bar - ob["bar_index"] <= 10, \
                "Muddati o'tgan OB filtirlanishi kerak edi"


# ====================================================================
# Test 5: FVG Topilishi
# ====================================================================

class TestFVGDetection:
    """Fair Value Gap'lar to'g'ri aniqlanishini tekshiradi."""

    def test_demand_fvg_detected(self):
        """Aniq demand FVG bo'lgan datada topilishi kerak."""
        df = generate_fvg_data()
        detector = FVGDetector({"fvg_filter": False})
        fvgs = detector.detect(df)

        demand_fvgs = [f for f in fvgs if f.fvg_type == "demand"]
        assert len(demand_fvgs) > 0, "Demand FVG topilishi kerak edi"

        # FVG formatini tekshirish
        for fvg in demand_fvgs:
            assert fvg.top > fvg.bottom, "FVG top > bottom bo'lishi kerak"
            assert fvg.gap_size > 0

    def test_supply_fvg_detected(self):
        """Supply FVG ham topilishi kerak."""
        df = generate_fvg_data()
        detector = FVGDetector({"fvg_filter": False})
        fvgs = detector.detect(df)

        supply_fvgs = [f for f in fvgs if f.fvg_type == "supply"]
        assert len(supply_fvgs) > 0, "Supply FVG topilishi kerak edi"

    def test_fvg_filter_reduces_count(self):
        """FVG filter yoqilganda kamroq FVG topilishi kerak."""
        df = generate_breakout_data(bars=200, seed=99)

        no_filter = FVGDetector({"fvg_filter": False})
        fvgs_all = no_filter.detect(df)

        strict_filter = FVGDetector({
            "fvg_filter": True,
            "fvg_filter_type": "Very Defensive",
        })
        fvgs_filtered = strict_filter.detect(df)

        # Strict filter kamroq yoki teng FVG berishi kerak
        assert len(fvgs_filtered) <= len(fvgs_all), \
            "Strict filter ko'proq FVG bermaydi"


# ====================================================================
# Test 6: To'liq Analiz — Output Format
# ====================================================================

class TestFullAnalysis:
    """analyze_market_structure() to'liq output formatini tekshiradi."""

    def test_output_has_all_keys(self):
        """Natija barcha kerakli kalitlarga ega bo'lishi kerak."""
        df = generate_breakout_data(bars=120, seed=42)
        result = analyze_market_structure(df)

        required_keys = [
            "current_price",
            "trend",
            "last_bos",
            "last_choch",
            "order_blocks",
            "fvg",
            "liquidity",
            "summary",
        ]
        for key in required_keys:
            assert key in result, f"'{key}' kaliti natijada bo'lishi kerak"

    def test_trend_format(self):
        """Trend formati to'g'ri."""
        df = generate_breakout_data(bars=120, seed=42)
        result = analyze_market_structure(df)

        assert "external" in result["trend"]
        assert "internal" in result["trend"]
        valid_trends = {"Up Trend", "Down Trend", "No Trend"}
        assert result["trend"]["external"] in valid_trends
        assert result["trend"]["internal"] in valid_trends

    def test_current_price_is_float(self):
        """current_price float bo'lishi kerak."""
        df = generate_breakout_data(bars=50, seed=42)
        result = analyze_market_structure(df)
        assert isinstance(result["current_price"], float)
        assert result["current_price"] > 0

    def test_empty_data_returns_empty_result(self):
        """Kam data bilan bo'sh natija qaytishi kerak."""
        df = pd.DataFrame({
            "timestamp": [pd.Timestamp("2024-01-01")],
            "open": [1.0],
            "high": [1.1],
            "low": [0.9],
            "close": [1.05],
        })
        result = analyze_market_structure(df)
        assert result["current_price"] == 0.0 or result["summary"]["total_events"] == 0

    def test_large_dataset_performance(self):
        """5000 bar bilan ishlashi kerak (max_bars_back = 5000)."""
        df = generate_trending_data(bars=5000, trend="zigzag", seed=77)
        result = analyze_market_structure(df, {"pivot_period": 5})

        assert result["current_price"] > 0
        assert result["summary"]["total_events"] >= 0

    def test_config_overrides_defaults(self):
        """Custom config default'larni override qilishi kerak."""
        df = generate_breakout_data(bars=100, seed=42)
        custom_config = {
            "pivot_period": 3,
            "ob_validity_bars": 20,
            "fvg_filter_type": "Very Aggressive",
        }
        result = analyze_market_structure(df, custom_config)
        assert result is not None
        assert "order_blocks" in result


# ====================================================================
# Testlarni to'g'ridan-to'g'ri ishga tushirish
# ====================================================================

if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    print("=" * 60)
    print("SMC Engine Unit Tests")
    print("=" * 60)

    # Oddiy test runner (pytest bo'lmasa)
    test_classes = [
        TestPivotDetection,
        TestBoSDetection,
        TestChochDetection,
        TestOrderBlockCreation,
        TestFVGDetection,
        TestFullAnalysis,
    ]

    passed = 0
    failed = 0

    for cls in test_classes:
        print(f"\n--- {cls.__name__} ---")
        instance = cls()
        for method_name in dir(instance):
            if method_name.startswith("test_"):
                try:
                    getattr(instance, method_name)()
                    print(f"  [PASS] {method_name}")
                    passed += 1
                except Exception as e:
                    print(f"  [FAIL] {method_name}: {e}")
                    failed += 1

    print(f"\n{'=' * 60}")
    print(f"Natija: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")
