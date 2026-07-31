import logging
import time
import threading
from datetime import datetime, timedelta
from supabase import create_client, Client

from bot.config import BotConfig
from bot.engine.backtester import Backtester
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)

class JobListener:
    def __init__(self, config: BotConfig):
        self.config = config
        self.supabase: Client = create_client(config.supabase_url, config.supabase_key)
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("Backtest Job Listener ishga tushdi.")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _listen_loop(self):
        while self._running:
            try:
                # Pending vazifalarni olamiz
                res = self.supabase.table("backtest_jobs").select("*").eq("status", "pending").limit(1).execute()
                jobs = res.data
                
                if jobs:
                    job = jobs[0]
                    self._process_job(job)
                
            except Exception as e:
                logger.error(f"Job Listener xatolik: {e}")
            
            # Har 5 soniyada tekshiradi
            time.sleep(5)

    def _map_timeframe(self, tf_str: str) -> int:
        mapping = {
            "15m": mt5.TIMEFRAME_M15,
            "1h": mt5.TIMEFRAME_H1,
            "4h": mt5.TIMEFRAME_H4,
            "1d": mt5.TIMEFRAME_D1
        }
        return mapping.get(tf_str.lower(), mt5.TIMEFRAME_H1)

    def _process_job(self, job: dict):
        job_id = job['id']
        symbol = job['symbol']
        timeframe_str = job['timeframe']
        mode = job['mode']
        
        logger.info(f"Yangi backtest vazifasi qabul qilindi: {job_id} ({symbol})")
        
        # Statusni running ga o'tkazamiz
        self.supabase.table("backtest_jobs").update({"status": "running"}).eq("id", job_id).execute()
        
        try:
            # Backtestni yurgizamiz
            tf = self._map_timeframe(timeframe_str)
            
            # MT5 ulanish
            if not mt5.initialize():
                raise Exception("MT5 ga ulanib bo'lmadi")

            bt = Backtester(symbol, tf, self.config)
            
            # Oxirgi 3 oy ma'lumotlari
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30) # Default 1 oy (Webdan so'rash rejasida qolgan ochiq savolga ko'ra)
            
            results = bt.run(start_date, end_date, split_ratio=1.0) # Hammasi IS ga o'tadi
            
            if results and "IS" in results:
                stats = results["IS"]
                
                total_trades = stats.get('total_trades', 0)
                wins = stats.get('winning_trades', 0)
                win_rate = (wins / total_trades * 100) if total_trades > 0 else 0.0
                profit = stats.get('total_profit', 0.0)
                
                # Natijani test_results ga yozamiz
                test_result = {
                    "type": mode,
                    "symbol": symbol,
                    "timeframe": timeframe_str,
                    "total_trades": total_trades,
                    "win_rate": round(win_rate, 2),
                    "total_profit": round(profit, 2),
                    "reasoning": f"Tarixiy ma'lumotlarda (oxirgi 1 oy) Voting Engine orqali tekshirildi." if mode == 'ai_siz' else "AI simulyatsiya (Kelajakda to'liq ulanadi)."
                }
                
                self.supabase.table("test_results").insert(test_result).execute()
                
            self.supabase.table("backtest_jobs").update({"status": "completed"}).eq("id", job_id).execute()
            logger.info(f"Backtest yakunlandi: {job_id}")
            
        except Exception as e:
            logger.error(f"Backtest bajarishda xatolik: {e}")
            self.supabase.table("backtest_jobs").update({"status": "failed"}).eq("id", job_id).execute()
