import sqlite3
import random
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bot.learning.shadow_collector import ShadowStateCollector

collector = ShadowStateCollector('bot_learning.db')

for i in range(150):
    candle = {
        'open': random.uniform(1.0, 1.2),
        'high': random.uniform(1.2, 1.3),
        'low': random.uniform(0.9, 1.0),
        'close': random.uniform(1.0, 1.2),
        'tick_volume': random.randint(100, 1000)
    }
    collector.record_state("EURUSD", "H1", candle, {}, {}, "TREND", random.choice(["BUY", "SELL", "HOLD"]))

print("Created shadow_states table and inserted 150 random rows!")
