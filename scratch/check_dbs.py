import sqlite3

def check_db(name):
    try:
        conn = sqlite3.connect(name)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cursor.fetchall()]
        print(f"--- DB: {name} ---")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            cnt = cursor.fetchone()[0]
            print(f"Table {table}: {cnt} rows")
            
            # Print symbols if possible
            try:
                cursor.execute(f"SELECT DISTINCT symbol FROM {table} LIMIT 5")
                symbols = [s[0] for s in cursor.fetchall()]
                print(f"  Distinct symbols: {symbols}")
            except Exception:
                pass
    except Exception as e:
        print(f"Error {name}: {e}")

check_db("harmonic_patterns.db")
check_db("wyckoff_events.db")
check_db("auto_patterns.db")
check_db("smc_zones.db")
check_db("sr_volume_zones.db")
