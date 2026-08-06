import pytest
import datetime
from unittest.mock import MagicMock
from bot.config import BotConfig
from bot.execution.order_manager import OrderManager

def test_session_blackout_windows():
    config = BotConfig()
    config.session_blackout_enabled = True
    config.session_blackout_windows = [
        {"start": "21:45", "end": "22:15", "name": "NY_Close_Rollover"},
        {"start": "23:55", "end": "00:15", "name": "Sydney_Open_Reset"},
        {"start": "07:55", "end": "08:05", "name": "London_Open_Vol"}
    ]
    
    mock_mt5 = MagicMock()
    mock_sm = MagicMock()
    om = OrderManager(mt5_client=mock_mt5, state_manager=mock_sm, config=config)

    # 1. Normal trading time (e.g. 14:30 UTC - NY afternoon session)
    dt_normal = datetime.datetime(2026, 8, 6, 14, 30, 0, tzinfo=datetime.timezone.utc)
    is_blackout, reason = om._is_in_blackout_window(dt_normal.timestamp())
    assert is_blackout is False
    assert reason == ""

    # 2. NY Rollover window (e.g. 22:00 UTC)
    dt_ny = datetime.datetime(2026, 8, 6, 22, 0, 0, tzinfo=datetime.timezone.utc)
    is_blackout, reason = om._is_in_blackout_window(dt_ny.timestamp())
    assert is_blackout is True
    assert "NY_Close_Rollover" in reason

    # 3. Midnight crossing window - before midnight (23:58 UTC)
    dt_mid1 = datetime.datetime(2026, 8, 6, 23, 58, 0, tzinfo=datetime.timezone.utc)
    is_blackout, reason = om._is_in_blackout_window(dt_mid1.timestamp())
    assert is_blackout is True
    assert "Sydney_Open_Reset" in reason

    # 4. Midnight crossing window - after midnight (00:05 UTC)
    dt_mid2 = datetime.datetime(2026, 8, 7, 0, 5, 0, tzinfo=datetime.timezone.utc)
    is_blackout, reason = om._is_in_blackout_window(dt_mid2.timestamp())
    assert is_blackout is True
    assert "Sydney_Open_Reset" in reason

    # 5. London Open window (08:00 UTC)
    dt_lon = datetime.datetime(2026, 8, 6, 8, 0, 0, tzinfo=datetime.timezone.utc)
    is_blackout, reason = om._is_in_blackout_window(dt_lon.timestamp())
    assert is_blackout is True
    assert "London_Open_Vol" in reason

def test_session_blackout_disabled():
    config = BotConfig()
    config.session_blackout_enabled = False
    mock_mt5 = MagicMock()
    mock_sm = MagicMock()
    om = OrderManager(mt5_client=mock_mt5, state_manager=mock_sm, config=config)

    dt_ny = datetime.datetime(2026, 8, 6, 22, 0, 0, tzinfo=datetime.timezone.utc)
    is_blackout, reason = om._is_in_blackout_window(dt_ny.timestamp())
    assert is_blackout is False
    assert reason == ""
