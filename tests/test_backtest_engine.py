"""
test_backtest_engine.py
========================
Institutional Unit Test Suite for Backtest Engine, MockBroker, Baseline Benchmarks,
and Statistical Significance calculations using standard unittest.
"""
import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from bot.config import BotConfig
from bot.execution.mock_broker import MockBroker
from bot.engine.backtester import (
    Backtester,
    BacktestStrategy,
    BuyAndHoldStrategy,
    RandomBaselineStrategy
)


class DummyAIClient:
    def get_decision(self, prompt, system_prompt=None):
        return {"approved": True, "reasoning": "Approved for test"}


def generate_synthetic_candles(num_bars: int = 300, start_price: float = 1.1000, trend: float = 0.0001) -> pd.DataFrame:
    """Generates synthetic candlestick data for testing backtest execution."""
    np.random.seed(42)
    start_time = datetime(2026, 1, 1, 0, 0)
    records = []
    price = start_price

    for i in range(num_bars):
        time_stamp = start_time + timedelta(hours=i)
        change = (np.random.randn() * 0.0015) + trend
        open_p = price
        close_p = open_p + change
        high_p = max(open_p, close_p) + abs(np.random.randn() * 0.0005)
        low_p = min(open_p, close_p) - abs(np.random.randn() * 0.0005)
        volume = int(np.random.randint(100, 1000))

        records.append({
            'time': time_stamp,
            'open': round(open_p, 5),
            'high': round(high_p, 5),
            'low': round(low_p, 5),
            'close': round(close_p, 5),
            'tick_volume': volume,
            'symbol': 'EURUSD'
        })
        price = close_p

    return pd.DataFrame(records)


class TestMockBroker(unittest.TestCase):
    """Institutional tests for MockBroker execution, spread/slippage calculation, and position handling."""

    def test_mock_broker_initialization(self):
        broker = MockBroker(initial_balance=10000.0, config={'spread_pips': 1.5, 'slippage_pips': 0.8})
        self.assertEqual(broker.balance, 10000.0)
        self.assertEqual(broker.equity, 10000.0)
        self.assertEqual(len(broker.open_positions), 0)
        self.assertEqual(len(broker.trade_history), 0)

    def test_open_buy_order_spread_and_slippage(self):
        broker = MockBroker(initial_balance=10000.0, config={'spread_pips': 2.0, 'slippage_pips': 0.0, 'dynamic_slippage': False, 'dynamic_spread': False})
        broker.open_order('EURUSD', 'BUY', 0.1, 1.1000, sl=1.0950, tp=1.1100, time=datetime.now())

        self.assertEqual(len(broker.open_positions), 1)
        pos = broker.open_positions[0]
        # Half spread for 2.0 pips = 1.0 pip = 0.0001
        self.assertAlmostEqual(pos['open_price'], 1.1001, places=5)

    def test_stop_loss_hit(self):
        broker = MockBroker(initial_balance=10000.0, config={'spread_pips': 0.0, 'slippage_pips': 0.0, 'dynamic_slippage': False, 'dynamic_spread': False, 'commission_per_lot': 0.0})
        broker.open_order('EURUSD', 'BUY', 1.0, 1.1000, sl=1.0950, tp=1.1100, time=datetime.now())

        # Update price to hit SL (low=1.0940)
        row = {'time': datetime.now(), 'open': 1.0980, 'high': 1.0980, 'low': 1.0940, 'close': 1.0945, 'symbol': 'EURUSD'}
        broker.update_price(row)

        self.assertEqual(len(broker.open_positions), 0)
        self.assertEqual(len(broker.trade_history), 1)
        trade = broker.trade_history[0]
        self.assertEqual(trade['reason'], 'SL')
        # 1.0 lot, 50 pips loss = -$500
        self.assertAlmostEqual(trade['profit'], -500.0, delta=1.0)

    def test_take_profit_hit(self):
        broker = MockBroker(initial_balance=10000.0, config={'spread_pips': 0.0, 'slippage_pips': 0.0, 'dynamic_slippage': False, 'dynamic_spread': False, 'commission_per_lot': 0.0})
        broker.open_order('EURUSD', 'BUY', 1.0, 1.1000, sl=1.0950, tp=1.1100, time=datetime.now())

        # Update price to hit TP (high=1.1120)
        row = {'time': datetime.now(), 'open': 1.1050, 'high': 1.1120, 'low': 1.1040, 'close': 1.1110, 'symbol': 'EURUSD'}
        broker.update_price(row)

        self.assertEqual(len(broker.open_positions), 0)
        self.assertEqual(len(broker.trade_history), 1)
        trade = broker.trade_history[0]
        self.assertEqual(trade['reason'], 'TP')
        # 1.0 lot, 100 pips gain = +$1000
        self.assertAlmostEqual(trade['profit'], 1000.0, delta=1.0)

    def test_simultaneous_sl_and_tp_conservative_sl(self):
        """In case of an extreme candle triggering both SL and TP, conservative risk management assumes SL first."""
        broker = MockBroker(initial_balance=10000.0, config={'spread_pips': 0.0, 'slippage_pips': 0.0, 'dynamic_slippage': False, 'dynamic_spread': False, 'commission_per_lot': 0.0})
        broker.open_order('EURUSD', 'BUY', 1.0, 1.1000, sl=1.0950, tp=1.1100, time=datetime.now())

        # Extreme candle crossing low 1.0900 and high 1.1200
        row = {'time': datetime.now(), 'open': 1.1000, 'high': 1.1200, 'low': 1.0900, 'close': 1.1000, 'symbol': 'EURUSD'}
        broker.update_price(row)

        self.assertEqual(len(broker.trade_history), 1)
        self.assertEqual(broker.trade_history[0]['reason'], 'SL')

    def test_pending_stop_order_trigger(self):
        broker = MockBroker(initial_balance=10000.0, config={'spread_pips': 1.0, 'slippage_pips': 0.0, 'dynamic_slippage': False, 'dynamic_spread': False})
        broker.add_pending_order('EURUSD', 'BUY_STOP', 0.5, 1.1050, sl=1.1000, tp=1.1150)
        self.assertEqual(len(broker.pending_orders), 1)

        # Price triggers BUY_STOP (high >= 1.1050)
        row = {'time': datetime.now(), 'open': 1.1020, 'high': 1.1060, 'low': 1.1010, 'close': 1.1055, 'symbol': 'EURUSD'}
        broker.update_price(row)

        self.assertEqual(len(broker.pending_orders), 0)
        self.assertEqual(len(broker.open_positions), 1)
        self.assertEqual(broker.open_positions[0]['type'], 'BUY')


class TestBaselineStrategies(unittest.TestCase):
    """Unit tests for Buy & Hold and Random Coin-Flip baseline strategies."""

    def test_buy_and_hold_strategy(self):
        config = BotConfig()
        broker = MockBroker(10000.0, {'spread_pips': 0.0, 'slippage_pips': 0.0, 'dynamic_slippage': False, 'dynamic_spread': False, 'commission_per_lot': 0.0})
        ai_client = DummyAIClient()
        bnh = BuyAndHoldStrategy('EURUSD', config, broker, ai_client)

        df = generate_synthetic_candles(num_bars=150, start_price=1.1000, trend=0.0002)

        for i in range(len(df)):
            row = df.iloc[i]
            broker.update_price(row)
            bnh.on_bar(df.iloc[:i+1], row, 0.0010, 0.0001, mode='ai_siz')

        bnh.finalize(df.iloc[-1])

        self.assertEqual(len(broker.trade_history), 1)
        trade = broker.trade_history[0]
        self.assertEqual(trade['type'], 'BUY')
        # Total profit should reflect upwards price trend
        self.assertGreater(trade['profit'], 0)

    def test_random_baseline_strategy_reproducibility(self):
        config = BotConfig()
        broker1 = MockBroker(10000.0)
        broker2 = MockBroker(10000.0)
        ai_client = DummyAIClient()

        rand1 = RandomBaselineStrategy('EURUSD', config, broker1, ai_client, seed=123)
        rand2 = RandomBaselineStrategy('EURUSD', config, broker2, ai_client, seed=123)

        df = generate_synthetic_candles(num_bars=200)

        for i in range(100, len(df)):
            row = df.iloc[i]
            broker1.update_price(row)
            broker2.update_price(row)
            rand1.on_bar(df.iloc[:i+1], row, 0.0015, 0.0001, mode='ai_siz')
            rand2.on_bar(df.iloc[:i+1], row, 0.0015, 0.0001, mode='ai_siz')

        self.assertEqual(len(broker1.trade_history), len(broker2.trade_history))


class TestBacktesterEngine(unittest.TestCase):
    """Institutional tests for Backtester orchestration, statistical math, and baseline alpha reports."""

    def test_z_test_statistical_math(self):
        bt = Backtester('EURUSD', 16384)
        
        # Scenario 1: Identical proportions
        res1 = bt._calculate_proportions_z_test(wins1=50, total1=100, wins2=50, total2=100)
        self.assertEqual(res1['p_value'], 1.0)
        self.assertFalse(res1['significant'])

        # Scenario 2: Large statistically significant difference (75% vs 45% win rate)
        res2 = bt._calculate_proportions_z_test(wins1=75, total1=100, wins2=45, total2=100)
        self.assertLess(res2['p_value'], 0.01)
        self.assertTrue(res2['significant'])

    def test_advanced_stats_metrics(self):
        broker = MockBroker(10000.0)
        broker.trade_history = [
            {'profit': 200.0, 'slippage_pips': 0.5, 'slippage_usd': 5.0},
            {'profit': -100.0, 'slippage_pips': 0.8, 'slippage_usd': 8.0},
            {'profit': 300.0, 'slippage_pips': 0.4, 'slippage_usd': 4.0},
        ]
        broker.balance = 10400.0

        bt = Backtester('EURUSD', 16384)
        stats = bt._calculate_advanced_stats(broker)

        self.assertEqual(stats['total_trades'], 3)
        self.assertEqual(stats['winning_trades'], 2)
        self.assertEqual(stats['losing_trades'], 1)
        self.assertAlmostEqual(stats['win_rate'], 66.67, delta=0.1)
        self.assertEqual(stats['gross_profit'], 500.0)
        self.assertEqual(stats['gross_loss'], 100.0)
        self.assertEqual(stats['profit_factor'], 5.0)
        self.assertEqual(stats['total_profit'], 400.0)

    def test_baseline_report_generation(self):
        bt = Backtester('EURUSD', 16384)

        strategy_stats = {'total_profit': 1500.0, 'win_rate': 65.0, 'winning_trades': 65, 'total_trades': 100}
        bnh_stats = {'total_profit': 300.0, 'win_rate': 100.0, 'winning_trades': 1, 'total_trades': 1}
        rand_stats = {'total_profit': -200.0, 'win_rate': 48.0, 'winning_trades': 48, 'total_trades': 100}

        report = bt._generate_baseline_report(strategy_stats, bnh_stats, rand_stats)
        self.assertIn("ZERO-COST BASELINE BENCHMARK TAHLILI", report)
        self.assertIn("Alpha", report)
        self.assertIn("BUY & HOLD", report)
        self.assertIn("TASODIFIY COIN-FLIP", report)


if __name__ == '__main__':
    unittest.main()
