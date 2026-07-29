import pytest
from unittest.mock import MagicMock, patch
import pandas as pd

from bot.main import TradingBot
from bot.config import BotConfig

def setup_bot():
    config = BotConfig()
    config.timeframe_major = "H1"
    config.timeframe_minor = "M15"
    config.telegram_bot_token = ""
    config.telegram_chat_id = ""
    config.trading_symbols = ["EURUSD"]
    
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
        'close': [1.1000, 1.1000, 1.1000],  # Current price is 1.1000
        'tick_volume': [100, 100, 100]
    })
    bot._fetch_data = MagicMock(return_value=dummy_df)
    bot._get_state_hash = MagicMock(return_value="mock_hash")
    
    bot.risk.validate_trade.return_value = (True, "Approved", 0.1)
    
    # Mock order success
    bot.orders.place_pending_order.return_value = (True, "Success", {"ticket": 123})
    bot.orders.place_order.return_value = (True, "Success", {"ticket": 124})
    
    # We must mock get_confluence to not crash
    bot.confluence = MagicMock()
    bot.confluence.get_confluence.return_value = {}
    
    return bot

def test_auto_pending_near_zone():
    bot = setup_bot()
    
    # Scenario A: SMC+Auto Pattern BUY, Wyckoff HOLD, price NEAR zone
    # AI returns BUY, entry_price is VERY CLOSE to current price 1.1000
    # Let's say entry_price is 1.0999 (1 pip away).
    bot.ai.get_decision.return_value = {
        "decision": "BUY",
        "entry_price": 1.0999,
        "stop_loss": 1.0950,
        "take_profit": 1.1100,
        "risk_pct": 0.01,
        "reasoning": "Near zone, SMC+Auto BUY, Wyckoff HOLD"
    }
    
    bot.run_cycle("EURUSD")
    
    # Because price diff is 1 pip <= 3.0 pips, it should place a MARKET order
    bot.orders.place_order.assert_called_once()
    bot.orders.place_pending_order.assert_not_called()
    
    args, kwargs = bot.orders.place_order.call_args
    assert kwargs["signal"] == "BUY"

def test_auto_pending_far_zone():
    bot = setup_bot()
    
    # Scenario B: SMC+Auto Pattern BUY, Wyckoff HOLD, price FAR from zone
    # AI returns BUY, but entry_price is FAR from current price 1.1000
    # Let's say entry_price is 1.0950 (50 pips away).
    bot.ai.get_decision.return_value = {
        "decision": "BUY",
        "entry_price": 1.0950,
        "stop_loss": 1.0900,
        "take_profit": 1.1100,
        "risk_pct": 0.01,
        "reasoning": "Far zone, SMC+Auto BUY, Wyckoff HOLD"
    }
    
    bot.run_cycle("EURUSD")
    
    # Because price diff is 50 pips > 3.0 pips, it should convert to BUY_LIMIT
    bot.orders.place_pending_order.assert_called_once()
    bot.orders.place_order.assert_not_called()
    
    args, kwargs = bot.orders.place_pending_order.call_args
    assert kwargs["order_type_str"] == "BUY_LIMIT"
