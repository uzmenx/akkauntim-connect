import sqlite3
import pandas as pd
import json

db_path = 'decisions_log.db'
conn = sqlite3.connect(db_path)
df = pd.read_sql_query("SELECT * FROM ai_decisions ORDER BY rowid DESC LIMIT 5", conn)
with open('scratch/decisions.json', 'w', encoding='utf-8') as f:
    df.to_json(f, orient='records', force_ascii=False)
conn.close()
