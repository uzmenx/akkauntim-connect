import sqlite3
import pandas as pd

db_paths = [
    'decisions_log.db',
    'smc_history.db',
    'trade_state.db',
    'test_state.db'
]

for db_path in db_paths:
    print(f"\n--- Checking {db_path} ---")
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        if not tables:
            print("No tables found.")
            continue
        for table in tables:
            table_name = table[0]
            print(f"Table: {table_name}")
            try:
                df = pd.read_sql_query(f"SELECT * FROM {table_name} ORDER BY rowid DESC LIMIT 5", conn)
                print(df.to_string())
            except Exception as e:
                print(f"Error querying table {table_name}: {e}")
        conn.close()
    except Exception as e:
        print(f"Error connecting to {db_path}: {e}")
