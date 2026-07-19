import sqlite3
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone

DB_NAME = "smc_memory.db"

def init_memory_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # FVG Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historical_fvg (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            timeframe TEXT,
            direction TEXT,
            time TEXT,
            top_price REAL,
            bottom_price REAL,
            mitigated INTEGER DEFAULT 0
        )
    ''')
    # Order Block Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historical_ob (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            timeframe TEXT,
            direction TEXT,
            time TEXT,
            top_price REAL,
            bottom_price REAL,
            mitigated INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def timeframe_to_str(tf):
    mapping = {
        mt5.TIMEFRAME_M15: "M15",
        mt5.TIMEFRAME_H1: "H1",
        mt5.TIMEFRAME_H4: "H4",
        mt5.TIMEFRAME_D1: "D1",
        mt5.TIMEFRAME_W1: "W1",
    }
    return mapping.get(tf, str(tf))

def detect_fvgs(df: pd.DataFrame, min_gap_points: float = 0.00020):
    fvgs = []
    for i in range(2, len(df)):
        c1 = df.iloc[i-2]
        c2 = df.iloc[i-1]
        c3 = df.iloc[i]

        # Bullish FVG
        if c3['low'] > c1['high']:
            gap = c3['low'] - c1['high']
            if gap >= min_gap_points:
                fvgs.append({
                    "time": c2['time'],  
                    "direction": "Bullish",
                    "top_price": float(c3['low']),
                    "bottom_price": float(c1['high'])
                })
        
        # Bearish FVG
        elif c1['low'] > c3['high']:
            gap = c1['low'] - c3['high']
            if gap >= min_gap_points:
                fvgs.append({
                    "time": c2['time'],
                    "direction": "Bearish",
                    "top_price": float(c1['low']),
                    "bottom_price": float(c3['high'])
                })
    return fvgs

def fetch_and_store_historical_zones(symbol: str, months_back: int = 3):
    if not mt5.initialize():
        print("MT5 ulanishda xatolik:", mt5.last_error())
        return

    timeframes = [mt5.TIMEFRAME_W1, mt5.TIMEFRAME_D1, mt5.TIMEFRAME_H4, mt5.TIMEFRAME_H1, mt5.TIMEFRAME_M15]
    
    start_dt = datetime.now(timezone.utc) - timedelta(days=months_back*30)
    end_dt = datetime.now(timezone.utc)
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    total_fvgs = 0
    for tf in timeframes:
        rates = mt5.copy_rates_range(symbol, tf, start_dt, end_dt)
        if rates is None or len(rates) == 0:
            continue
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        min_gap = 0.00050 if tf in [mt5.TIMEFRAME_D1, mt5.TIMEFRAME_W1] else 0.00015
        
        fvgs = detect_fvgs(df, min_gap_points=min_gap)
        tf_str = timeframe_to_str(tf)
        
        cursor.execute("DELETE FROM historical_fvg WHERE symbol=? AND timeframe=?", (symbol, tf_str))
        
        for f in fvgs:
            cursor.execute('''
                INSERT INTO historical_fvg (symbol, timeframe, direction, time, top_price, bottom_price)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (symbol, tf_str, f['direction'], str(f['time']), f['top_price'], f['bottom_price']))
            total_fvgs += 1
            
    conn.commit()
    conn.close()
    print(f"SMC Memory Bank: {months_back} oylik tarix tahlil qilindi. Jami {total_fvgs} ta FVG topildi va saqlandi.")

def check_current_price_in_zone(symbol: str, current_price: float, buffer_pips: float = 5.0) -> list:
    buffer_points = buffer_pips * 0.0001
    
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM historical_fvg 
        WHERE symbol=? AND mitigated=0
    ''', (symbol,))
    
    rows = cursor.fetchall()
    conn.close()
    
    alerts = []
    for row in rows:
        top = row['top_price']
        bottom = row['bottom_price']
        
        if (bottom - buffer_points) <= current_price <= (top + buffer_points):
            alerts.append({
                "timeframe": row['timeframe'],
                "direction": row['direction'],
                "time_created": row['time'],
                "zone_top": top,
                "zone_bottom": bottom
            })
            
    return alerts

if __name__ == "__main__":
    init_memory_db()
    print("SMC Memory Bank DB yaratildi.")
