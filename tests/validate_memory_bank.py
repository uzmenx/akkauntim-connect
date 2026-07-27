from smc_memory_bank import init_memory_db, check_current_price_in_zone
from news_impact_analyzer import get_aggregated_news_summary, init_db

print("=== SMC Memory Bank Test ===")
init_memory_db()
# Let's mock a record in smc_memory.db
import sqlite3
conn = sqlite3.connect("smc_memory.db")
cursor = conn.cursor()
cursor.execute("DELETE FROM historical_fvg")
cursor.execute('''
    INSERT INTO historical_fvg (symbol, timeframe, direction, time, top_price, bottom_price)
    VALUES ('EURUSD', 'D1', 'Bearish', '2026-03-01 00:00:00', 1.0870, 1.0850)
''')
conn.commit()
conn.close()

# Test check_current_price_in_zone
alerts = check_current_price_in_zone("EURUSD", 1.0860)
print(f"Joriy narx 1.0860 bo'lganda ogohlantirishlar soni: {len(alerts)}")
if alerts:
    for a in alerts:
        print(f"DIQQAT: Narx tarixiy {a['timeframe']} {a['direction']} FVG zonasiga kirdi (Yaratilgan: {a['time_created']}, Zona: {a['zone_bottom']} - {a['zone_top']})")

print("\n=== Deep News Aggregator Test ===")
init_db()
# We already have mock_news.csv data in news_history.db from earlier tests (or we can just run it)
# We'll use the summary function
summary = get_aggregated_news_summary("XAUUSD", "Non-Farm Employment Change", lookback_months=120)
print(summary)
