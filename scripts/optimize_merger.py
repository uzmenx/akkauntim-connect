import sqlite3
import os
import json
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def optimize_merger_weights(db_path='bot_learning.db', config_out='merger_weights.json', days_back=7):
    """
    Oxirgi N kundagi natijalarni tahlil qilib, LSTM ishonchliligi (max_base_weight)
    uchun optimal qiymatlarni hisoblaydi va JSON faylga saqlaydi.
    Bu skriptni cron yoki job_listener orqali har hafta ishga tushirish mumkin.
    """
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_db_path = os.path.join(root_dir, db_path)
    
    if not os.path.exists(full_db_path):
        logger.warning(f"Database topilmadi, o'rganish ma'lumotlari yo'q: {full_db_path}")
        return
        
    conn = sqlite3.connect(full_db_path)
    cursor = conn.cursor()
    
    # Oxirgi N kundagi shadow (virtual) savdolar aniqligini baholaymiz
    since_date = (datetime.now() - timedelta(days=days_back)).isoformat()
    
    try:
        # shadow_trade_history table might not exist if no trades were closed yet
        cursor.execute('''CREATE TABLE IF NOT EXISTS shadow_trade_history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            ticket INTEGER,
                            symbol TEXT,
                            type INTEGER,
                            open_time INTEGER,
                            close_time INTEGER,
                            price_open REAL,
                            price_close REAL,
                            volume REAL,
                            profit REAL,
                            timestamp TEXT,
                            magic INTEGER,
                            sl REAL,
                            tp REAL
                        )''')

        cursor.execute("""
            SELECT symbol, 
                   COUNT(*) as total_trades,
                   SUM(CASE WHEN profit > 0 THEN 1 ELSE 0 END) as winning_trades
            FROM shadow_trade_history 
            WHERE timestamp > ?
            GROUP BY symbol
        """, (since_date,))
        
        results = cursor.fetchall()
        
        config_path = os.path.join(root_dir, config_out)
        
        # Oldingi konfiguratsiyani o'qiymiz
        current_config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                current_config = json.load(f)
                
        symbol_weights = current_config.get("symbol_weights", {})
        
        updated_count = 0
        for row in results:
            symbol, total, wins = row
            if total < 5:
                continue # Kichik sample uchun o'zgartirmaymiz
                
            win_rate = wins / total
            
            # Joriy og'irlikni olamiz (yo'q bo'lsa default 0.60)
            current_weight = symbol_weights.get(symbol, 0.60)
            
            # Kichik qadamlar (learning rate = 0.02) bilan sozlaymiz
            # Win rate 55% dan baland bo'lsa, LSTM ga ishonchni oshiramiz
            if win_rate > 0.55:
                new_weight = min(0.85, current_weight + 0.02)
            # Win rate 45% dan past bo'lsa, ishonchni pasaytiramiz
            elif win_rate < 0.45:
                new_weight = max(0.15, current_weight - 0.02)
            else:
                new_weight = current_weight
                
            if new_weight != current_weight:
                symbol_weights[symbol] = round(new_weight, 3)
                logger.info(f"[{symbol}] Win rate: {win_rate:.2f} ({wins}/{total} trades). Weight updated: {current_weight:.3f} -> {new_weight:.3f}")
                updated_count += 1
            else:
                logger.info(f"[{symbol}] Win rate: {win_rate:.2f} ({wins}/{total} trades). Weight stable at {current_weight:.3f}")
            
        new_config = {
            "last_updated": datetime.now().isoformat(),
            "days_back_analyzed": days_back,
            "symbol_weights": symbol_weights
        }
        
        with open(config_path, 'w') as f:
            json.dump(new_config, f, indent=4)
            
        logger.info(f"Optimizatsiya yakunlandi. {updated_count} ta juftlik yangilandi. Config saqlandi: {config_path}")
        
    except Exception as e:
        logger.error(f"Optimizatsiyada xatolik: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    logger.info("Merger og'irliklarini avtomatik optimizatsiya qilish boshlandi...")
    optimize_merger_weights()
