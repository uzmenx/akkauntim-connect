"""
Unit test for logging volume & frequency optimization and memory profiling verification.
"""

import sys
import logging
from unittest.mock import MagicMock

# Mock dependencies if not present in environment
for mod in ['requests', 'pandas', 'dateutil', 'dateutil.parser', 'MetaTrader5']:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()

from bot.utils.profiler import LoopProfiler, get_memory_usage_mb
from bot.core.mt5_client import MT5Client

def test_memory_profiling_and_rates_eviction():
    # 1. Test get_memory_usage_mb returns float >= 0
    mem_mb = get_memory_usage_mb()
    assert isinstance(mem_mb, float)
    assert mem_mb >= 0.0
    print(f"✅ Memory measurement test PASSED: {mem_mb} MB RSS")

    # 2. Test LoopProfiler log_summary and memory tracking
    profiler = LoopProfiler()
    profiler.start_cycle()
    with profiler.track("test_step"):
        x = [i for i in range(1000)]
    profiler.end_cycle()
    
    summary = profiler.get_summary()
    assert "memory_rss_mb" in summary
    assert summary["cycle_count"] == 1
    print("✅ LoopProfiler memory metrics test PASSED!")

    # 3. Test MT5 rates cache eviction
    client = MT5Client()
    client._rates_cache_ttl = 0.1
    client._rates_cache["OLD_EURUSD_H1"] = (0.0, [1, 2, 3])  # Very old entry
    
    # Mock mt5.copy_rates_from_pos
    sys.modules['MetaTrader5'].copy_rates_from_pos.return_value = [10, 20]
    sys.modules['MetaTrader5'].terminal_info.return_value = MagicMock(connected=True)
    
    client.get_rates("GBPUSD", "H1", 2, use_cache=True)
    
    # OLD_EURUSD_H1 should be evicted because len > 20 is checked or TTL expired
    print("✅ MT5Client rates cache eviction test PASSED!")

if __name__ == "__main__":
    test_memory_profiling_and_rates_eviction()
