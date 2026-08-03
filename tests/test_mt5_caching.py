"""
MT5Client get_rates Caching Unit Test (Linux Mock)
"""

import sys
from unittest.mock import MagicMock

# Mock MetaTrader5 module before importing bot.core.mt5_client
mock_mt5 = MagicMock()
mock_mt5.TIMEFRAME_M1 = 1
mock_mt5.TIMEFRAME_M5 = 5
mock_mt5.TIMEFRAME_M15 = 15
mock_mt5.TIMEFRAME_M30 = 30
mock_mt5.TIMEFRAME_H1 = 16385
mock_mt5.TIMEFRAME_H4 = 16388
mock_mt5.TIMEFRAME_D1 = 16408
mock_mt5.TIMEFRAME_W1 = 32769
mock_mt5.TIMEFRAME_MN1 = 49153

sys.modules['MetaTrader5'] = mock_mt5

import time
from bot.core.mt5_client import MT5Client

class MockRates:
    def __init__(self, data):
        self._data = data

    def __len__(self):
        return len(self._data)

    def __getitem__(self, item):
        if isinstance(item, slice):
            return MockRates(self._data[item])
        return self._data[item]

    def copy(self):
        return MockRates(list(self._data))

def mock_copy_rates_from_pos(symbol, timeframe, start, count):
    return MockRates([{"time": 1600000000 + i, "close": 1.1000 + i*0.0001} for i in range(count)])

def test_mt5_get_rates_caching():
    client = MT5Client()
    client.clear_rates_cache()
    client.set_rates_cache_ttl(2.0)

    mock_mt5.copy_rates_from_pos.side_effect = mock_copy_rates_from_pos
    
    mock_ti_obj = MagicMock()
    mock_ti_obj.connected = True
    mock_mt5.terminal_info.return_value = mock_ti_obj

    # 1-chaqiruv: MT5 sekin javob beradi (copy_rates_from_pos chaqirilishi kerak)
    res1 = client.get_rates("EURUSD", "H1", 300)
    assert len(res1) == 300
    assert mock_mt5.copy_rates_from_pos.call_count == 1

    # 2-chaqiruv (bir necha ms dan keyin, 150 ta sham so'ralganda): Keshdan olinishi kerak!
    res2 = client.get_rates("EURUSD", "H1", 150)
    assert len(res2) == 150
    assert mock_mt5.copy_rates_from_pos.call_count == 1  # count oshmadi! Kesh muvaffaqiyatli ishlatildi!

    # 3-chaqiruv: 300 ta sham keshdan olinishi kerak
    res3 = client.get_rates("EURUSD", "H1", 300)
    assert len(res3) == 300
    assert mock_mt5.copy_rates_from_pos.call_count == 1  # count hali ham 1!

    # 4-chaqiruv: use_cache=False bo'lsa, kesh aylanib o'tiladi
    res4 = client.get_rates("EURUSD", "H1", 100, use_cache=False)
    assert len(res4) == 100
    assert mock_mt5.copy_rates_from_pos.call_count == 2  # Endi 2 ta bo'ldi

    # 5-chaqiruv: TTL o'tgandan keyin
    client.set_rates_cache_ttl(0.01)
    time.sleep(0.02)
    res5 = client.get_rates("EURUSD", "H1", 300)
    assert len(res5) == 300
    assert mock_mt5.copy_rates_from_pos.call_count == 3  # TTL tugadi, yangi chaqiruv bo'ldi!

    print("✅ MT5 get_rates Caching Unit Test MUVAFFAQIYATLI O'TDI!")

if __name__ == "__main__":
    test_mt5_get_rates_caching()
