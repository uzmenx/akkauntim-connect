import pytest
from unittest.mock import MagicMock, patch
import pandas as pd

from bot.main import TradingBot
from bot.config import BotConfig

def test_run_cycle_hold_logs_signal():
    """
    Test that log_ai_signal is called even when AI decision is 'HOLD'.
    """
    # Create a basic config
    config = BotConfig()
    config.timeframe_major = "H1"
    config.timeframe_minor = "M15"
    config.telegram_bot_token = ""
    config.telegram_chat_id = ""
    
    bot = TradingBot(config)
    
    # Mock all external dependencies
    bot.mt5 = MagicMock()
    bot.ai = MagicMock()
    bot.sync = MagicMock()
    bot.telegram = MagicMock()
    bot.reviewer = MagicMock()
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
    
    # Mock data fetching to prevent early return
    dummy_df = pd.DataFrame({
        'time': pd.date_range('2023-01-01', periods=3),
        'open': [1.0, 1.0, 1.0],
        'high': [1.5, 1.5, 1.5],
        'low': [0.5, 0.5, 0.5],
        'close': [1.2, 1.2, 1.2],
        'tick_volume': [100, 100, 100]
    })
    bot._fetch_data = MagicMock(return_value=dummy_df)
    
    # Mock AI response to return HOLD
    bot.ai.get_decision.return_value = {
        "decision": "HOLD",
        "reasoning": "Market is too volatile, staying out."
    }
    
    # Mock prompt builder
    bot.prompt_builder.build_context_summary.return_value = {}
    bot.prompt_builder.build_trading_prompt.return_value = "dummy test prompt"
    
    # Run the cycle for a dummy symbol
    bot.run_cycle("EURUSD")
    
    # Assert log_ai_signal was called exactly once
    bot.sync.log_ai_signal.assert_called_once()
    
    # Check the arguments passed to log_ai_signal
    args, kwargs = bot.sync.log_ai_signal.call_args
    assert kwargs.get("signal") == "HOLD"
    assert kwargs.get("symbol") == "EURUSD"
    assert kwargs.get("reasoning") == "Market is too volatile, staying out."
    assert kwargs.get("entry_price") is None
    assert kwargs.get("sl_price") is None
    assert kwargs.get("tp_price") is None
    assert kwargs.get("stop_loss_pips") == 0.0
    assert kwargs.get("take_profit_pips") == 0.0
