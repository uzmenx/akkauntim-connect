import unittest
from unittest.mock import MagicMock, patch
import pandas as pd

from bot.main import TradingBot
from bot.config import BotConfig

class TestRunCycle(unittest.TestCase):
    def test_run_cycle_hold_logs_signal(self):
        """
        Test that log_ai_signal is called even when AI decision is 'HOLD'.
        """
        config = BotConfig()
        config.timeframe_major = "H1"
        config.timeframe_minor = "M15"
        config.telegram_bot_token = ""
        config.telegram_chat_id = ""
        
        bot = TradingBot(config)
        
        bot.mt5 = MagicMock()
        bot.ai = MagicMock()
        bot.sync = MagicMock()
        bot.telegram = MagicMock()
        bot.reviewer = MagicMock()
        bot.state = MagicMock()
        bot.state.get_symbol_gate_state.return_value = {}
        bot.risk = MagicMock()
        bot.orders = MagicMock()
        bot.decision_logger = MagicMock()
        bot.prompt_builder = MagicMock()

        bot.reviewer.get_active_adjustments.return_value = {}
        
        mock_symbol_info = MagicMock()
        mock_symbol_info.trade_tick_size = 0.0001
        mock_symbol_info.trade_tick_value = 1.0
        mock_symbol_info.currency_profit = "USD"
        bot.mt5.symbol_info.return_value = mock_symbol_info
        
        dummy_df = pd.DataFrame({
            'time': pd.date_range('2023-01-01', periods=3),
            'open': [1.0, 1.0, 1.0],
            'high': [1.5, 1.5, 1.5],
            'low': [0.5, 0.5, 0.5],
            'close': [1.2, 1.2, 1.2],
            'tick_volume': [100, 100, 100]
        })
        bot._fetch_data = MagicMock(return_value=dummy_df)
        
        bot.portfolio_manager = MagicMock()
        bot.portfolio_manager.analyze_all.return_value = {
            "signal": "BUY",
            "score": 80,
            "details": {}
        }
        
        bot.voting_engine = MagicMock()
        bot.voting_engine.analyze.return_value = {"signal": "BUY", "score": 80}
        
        bot.ai.get_decision.return_value = {
            "decision": "HOLD",
            "reasoning": "Market is too volatile, staying out."
        }
        bot.transition_manager = MagicMock()
        bot.transition_manager.mode.value = "api"
        bot.transition_manager.get_decision.return_value = {
            "decision": "HOLD",
            "reasoning": "Market is too volatile, staying out."
        }
        
        bot.prompt_builder.build_context_summary.return_value = {}
        bot.prompt_builder.build_trading_prompt.return_value = "dummy test prompt"
        
        with patch("bot.main.should_call_ai", return_value=(True, "Signal")):
            bot.run_cycle("EURUSD")
        
        bot.sync.log_ai_signal.assert_called_once()
        
        args, kwargs = bot.sync.log_ai_signal.call_args
        self.assertEqual(kwargs.get("signal"), "HOLD")
        self.assertEqual(kwargs.get("symbol"), "EURUSD")
        self.assertEqual(kwargs.get("reasoning"), "Market is too volatile, staying out.")
        self.assertIsNone(kwargs.get("entry_price"))
        self.assertIsNone(kwargs.get("sl_price"))
        self.assertIsNone(kwargs.get("tp_price"))
        self.assertEqual(kwargs.get("stop_loss_pips"), 0.0)
        self.assertEqual(kwargs.get("take_profit_pips"), 0.0)

if __name__ == "__main__":
    unittest.main()
