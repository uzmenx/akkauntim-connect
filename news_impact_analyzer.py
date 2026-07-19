import sqlite3
import pandas as pd
import requests
import MetaTrader5 as mt5
from datetime import datetime, timedelta, timezone
import dateutil.parser
import os

DB_NAME = "news_history.db"

COT_MARKET_NAMES = {
    "XAUUSD": "GOLD - COMMODITY EXCHANGE INC.",
    "EURUSD": "EURO FX - CHICAGO MERCANTILE EXCHANGE",
    "GBPUSD": "BRITISH POUND - CHICAGO MERCANTILE EXCHANGE",
    "USDJPY": "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE"
}

COT_REPORT_URL = "https://www.cftc.gov/dea/newcot/deacot.txt"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historical_news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_date TEXT,
            currency TEXT,
            event_name TEXT,
            impact TEXT,
            actual REAL,
            forecast REAL,
            previous REAL,
            move_5m_pct REAL,
            move_1h_pct REAL,
            move_4h_pct REAL,
            atr_multiple REAL
        )
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_news_currency_event 
        ON historical_news (currency, event_name)
    ''')
    conn.commit()
    conn.close()

def parse_number(val):
    if pd.isna(val) or val == "" or val is None:
        return None
    try:
        val_str = str(val).strip().lower()
        multiplier = 1.0
        if val_str.endswith('k'):
            multiplier = 1000.0
            val_str = val_str[:-1]
        elif val_str.endswith('m'):
            multiplier = 1000000.0
            val_str = val_str[:-1]
        elif val_str.endswith('b'):
            multiplier = 1000000000.0
            val_str = val_str[:-1]
        elif val_str.endswith('%'):
            val_str = val_str[:-1]
        return float(val_str) * multiplier
    except Exception:
        return None

def fetch_price_move(symbol, event_date_utc):
    if not mt5.initialize():
        return None, None, None, None
    
    start_dt = event_date_utc - timedelta(hours=24)
    end_dt = event_date_utc + timedelta(hours=6)
    
    rates_m5 = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, start_dt, end_dt)
    if rates_m5 is None or len(rates_m5) == 0:
        return None, None, None, None
        
    df_m5 = pd.DataFrame(rates_m5)
    df_m5['time_dt'] = pd.to_datetime(df_m5['time'], unit='s', utc=True)
    
    df_m5['time_diff'] = abs((df_m5['time_dt'] - event_date_utc).dt.total_seconds())
    closest_idx = df_m5['time_diff'].idxmin()
    
    if df_m5.loc[closest_idx, 'time_diff'] > 3600:
        return None, None, None, None

    entry_price = df_m5.loc[closest_idx, 'open']
    
    idx_5m = min(closest_idx + 1, len(df_m5) - 1)
    price_5m = df_m5.loc[idx_5m, 'close']
    move_5m_pct = ((price_5m - entry_price) / entry_price) * 100.0
    
    idx_1h = min(closest_idx + 12, len(df_m5) - 1)
    price_1h = df_m5.loc[idx_1h, 'close']
    move_1h_pct = ((price_1h - entry_price) / entry_price) * 100.0
    
    idx_4h = min(closest_idx + 48, len(df_m5) - 1)
    price_4h = df_m5.loc[idx_4h, 'close']
    move_4h_pct = ((price_4h - entry_price) / entry_price) * 100.0
    
    historical_bars = df_m5.iloc[max(0, closest_idx - 168):closest_idx]
    if len(historical_bars) > 10:
        highs = historical_bars['high']
        lows = historical_bars['low']
        closes = historical_bars['close'].shift(1)
        tr1 = highs - lows
        tr2 = abs(highs - closes)
        tr3 = abs(lows - closes)
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.mean()
        actual_move_points = abs(price_1h - entry_price)
        atr_multiple = actual_move_points / atr if atr > 0 else 0
    else:
        atr_multiple = 0.0

    return move_5m_pct, move_1h_pct, move_4h_pct, atr_multiple

def backfill_historical_data(csv_path: str, pair: str = "XAUUSD"):
    if not os.path.exists(csv_path):
        print(f"CSV fayli topilmadi: {csv_path}")
        return
        
    df = pd.read_csv(csv_path)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    inserted = 0
    for idx, row in df.iterrows():
        try:
            date_str = f"{row['Date']} {row['Time']}"
            dt = dateutil.parser.parse(date_str)
            dt_utc = dt.replace(tzinfo=timezone.utc)
            
            currency = str(row['Currency']).strip()
            event_name = str(row['Event']).strip()
            impact = str(row['Impact']).strip()
            actual = parse_number(row.get('Actual', ''))
            forecast = parse_number(row.get('Forecast', ''))
            previous = parse_number(row.get('Previous', ''))
            
            m5_pct, m1h_pct, m4h_pct, atr_mult = fetch_price_move(pair, dt_utc)
            
            if m5_pct is not None:
                cursor.execute('''
                    INSERT INTO historical_news (
                        event_date, currency, event_name, impact, 
                        actual, forecast, previous, 
                        move_5m_pct, move_1h_pct, move_4h_pct, atr_multiple
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    dt_utc.isoformat(), currency, event_name, impact,
                    actual, forecast, previous,
                    m5_pct, m1h_pct, m4h_pct, atr_mult
                ))
                inserted += 1
                
        except Exception as e:
            print(f"Error parsing row {idx}: {e}")
            
    conn.commit()
    conn.close()
    print(f"Backfill tugadi. {inserted} ta yozuv qo'shildi.")

def analyze_historical_impact(currency_pair: str, event_name: str, lookback_months: int = 6) -> dict:
    init_db()
    
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cutoff_dt = datetime.now(timezone.utc) - timedelta(days=lookback_months*30)
    
    cursor.execute('''
        SELECT * FROM historical_news 
        WHERE event_name = ? AND event_date >= ?
    ''', (event_name, cutoff_dt.isoformat()))
    
    rows = cursor.fetchall()
    conn.close()
    
    sample_size = len(rows)
    if sample_size == 0:
        return {
            "event_name": event_name,
            "pair": currency_pair,
            "sample_size": 0,
            "insufficient_data": True
        }
        
    beats = []
    misses = []
    
    for row in rows:
        actual = row['actual']
        forecast = row['forecast']
        
        if actual is None or forecast is None:
            continue
            
        if actual > forecast:
            beats.append(row)
        elif actual < forecast:
            misses.append(row)
            
    def summarize(subset):
        if not subset:
            return None
        avg_5m = sum(r['move_5m_pct'] for r in subset) / len(subset)
        avg_1h = sum(r['move_1h_pct'] for r in subset) / len(subset)
        bullish_count = sum(1 for r in subset if r['move_1h_pct'] > 0)
        
        direction = "Bullish" if avg_1h > 0 else "Bearish"
        confidence = bullish_count / len(subset) if direction == "Bullish" else (len(subset) - bullish_count) / len(subset)
        
        return {
            "avg_move_5min_pct": round(avg_5m, 4),
            "avg_move_1h_pct": round(avg_1h, 4),
            "direction": direction,
            "confidence": round(confidence, 2),
            "sample_size": len(subset)
        }

    beat_summary = summarize(beats)
    miss_summary = summarize(misses)
    
    avg_volatility = sum(r['atr_multiple'] for r in rows) / len(rows) if rows else 0
    
    return {
        "event_name": event_name,
        "pair": currency_pair,
        "sample_size": sample_size,
        "insufficient_data": sample_size < 5,
        "when_actual_beats_forecast": beat_summary,
        "when_actual_misses_forecast": miss_summary,
        "avg_volatility_spike": round(avg_volatility, 2)
    }

def get_cot_trend(pair: str) -> dict:
    market_name = COT_MARKET_NAMES.get(pair)
    if not market_name:
        return {"cot_trend": "Unknown", "note": f"COT_MARKET_NAMES da {pair} uchun xaritalash yo'q."}
        
    try:
        response = requests.get(COT_REPORT_URL, timeout=15)
        if response.status_code != 200:
            return {"cot_trend": "Unknown", "note": f"Failed to download COT data (HTTP {response.status_code})"}
            
        lines = response.text.split('\n')
        target_line = None
        
        for line in lines:
            if market_name in line:
                target_line = line
                break
                
        if not target_line:
            return {"cot_trend": "Unknown", "note": f"{market_name} CFTC hisobotidan topilmadi."}
            
        parts = [p.strip().strip('"') for p in target_line.split(',')]
        if len(parts) > 9:
            try:
                nc_long = int(parts[7].strip()) if parts[7].strip() else 0
                nc_short = int(parts[8].strip()) if parts[8].strip() else 0
            except ValueError:
                return {"cot_trend": "Unknown", "note": "Ma'lumotlarni parslashda xatolik."}
                
            net_position = nc_long - nc_short
            if net_position > 0:
                trend = "Net Long"
                note = f"Institutsional xaridorlar ustun (Longs: {nc_long}, Shorts: {nc_short})"
            else:
                trend = "Net Short"
                note = f"Institutsional sotuvchilar ustun (Longs: {nc_long}, Shorts: {nc_short})"
                
            return {
                "cot_trend": trend,
                "note": note,
                "net_position": net_position
            }
        else:
            return {"cot_trend": "Unknown", "note": "Kutilgan format topilmadi."}
            
    except Exception as e:
        return {"cot_trend": "Unknown", "note": f"COT yuklashda xatolik: {e}"}

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
    print("Testing COT retrieval for XAUUSD...")
    print(get_cot_trend("XAUUSD"))
