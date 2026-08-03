from bot.learning.predictor import PredictorEngine
import logging
logging.basicConfig(level=logging.INFO)

engine = PredictorEngine()
# evaluate_ensemble_approach internally generates mock data? No, it uses self.db_path which might not have data if not run.
# Let's seed it with some mock data first if needed.
import sqlite3
import datetime
import os
db_path = "bot_learning.db"
if not os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS shadow_states (id INTEGER PRIMARY KEY, timestamp TEXT, symbol TEXT, timeframe TEXT, price_open REAL, price_high REAL, price_low REAL, price_close REAL, tick_volume REAL, smc_context TEXT, indicators TEXT, market_regime TEXT, ai_decision TEXT)''')
    base_price = 1.1000
    start = datetime.datetime(2026, 8, 1)
    for i in range(100):
        ts = (start + datetime.timedelta(minutes=5*i)).isoformat()
        decision = "UP" if i % 3 == 0 else ("DOWN" if i % 3 == 1 else "HOLD")
        c.execute('''INSERT INTO shadow_states (timestamp, symbol, timeframe, price_open, price_high, price_low, price_close, tick_volume, smc_context, indicators, market_regime, ai_decision) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', (ts, "EURUSD", "M5", base_price, base_price, base_price, base_price, 100, "{}", "{}", "TRENDING", decision))
    conn.commit()
    conn.close()

res = engine.evaluate_ensemble_approach(epochs=2)
print("RESULT:", res)
