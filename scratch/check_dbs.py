import sqlite3
import os

dbs = [
    'decisions_log.db',
    'news_history.db',
    'smc_history.db',
    'smc_memory.db'
]

for db_name in dbs:
    if not os.path.exists(db_name):
        print(f"--- {db_name} (NOT FOUND) ---")
        continue
        
    print(f"\n--- Checking {db_name} ---")
    try:
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("No tables found.")
            continue
            
        for table in tables:
            table_name = table[0]
            print(f"\nTable: {table_name}")
            
            # Get row count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"Total records: {count}")
            
            if count > 0:
                # Get schema to find a timestamp column if any, or just get last 2 rows
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = [col[1] for col in cursor.fetchall()]
                print(f"Columns: {', '.join(columns)}")
                
                # Try to order by id or timestamp if exists
                order_by = ""
                if "id" in columns:
                    order_by = "ORDER BY id DESC"
                elif "timestamp" in columns:
                    order_by = "ORDER BY timestamp DESC"
                elif "created_at" in columns:
                    order_by = "ORDER BY created_at DESC"
                    
                cursor.execute(f"SELECT * FROM {table_name} {order_by} LIMIT 2")
                rows = cursor.fetchall()
                print("Last 2 records:")
                for row in rows:
                    print(f"  {row}")
                    
        conn.close()
    except Exception as e:
        print(f"Error reading {db_name}: {e}")
