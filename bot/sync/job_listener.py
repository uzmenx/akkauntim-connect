import logging
import time
import threading
from datetime import datetime, timedelta
from supabase import create_client, Client

from bot.config import BotConfig
from bot.engine.backtester import Backtester
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

class JobListener:
    def __init__(self, config: BotConfig):
        self.config = config
        if config.supabase_url and config.supabase_key:
            self.supabase: Optional[Client] = create_client(config.supabase_url, config.supabase_key)
        else:
            self.supabase = None
        self._running = False
        self._thread = None

    def start(self):
        if not self.supabase:
            logger.warning("Supabase URL or Key not set. JobListener will not start.")
            return
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
        period_str = job.get('period', '1m')
        strategy = job.get('strategy', 'voting') or 'voting'
        spread_pips = float(job.get('spread_pips', 1.5) or 1.5)
        slippage_pips = float(job.get('slippage_pips', 0.8) or 0.8)
        
        logger.info(f"Yangi backtest vazifasi qabul qilindi: {job_id} ({symbol}, strategy: {strategy}, period: {period_str}, spread: {spread_pips}p, slip: {slippage_pips}p)")
        
        # Statusni running ga o'tkazamiz
        self.supabase.table("backtest_jobs").update({"status": "running"}).eq("id", job_id).execute()
        
        try:
            # Backtestni yurgizamiz
            tf = self._map_timeframe(timeframe_str)
            
            # MT5 ulanish
            if not mt5.initialize():
                raise Exception("MT5 ga ulanib bo'lmadi")

            bt = Backtester(symbol, tf, self.config, strategy=strategy, spread_pips=spread_pips, slippage_pips=slippage_pips)
            
            # Tarixiy ma'lumotlar davri
            end_date = datetime.now()
            days = 30
            if period_str == '3m': days = 90
            elif period_str == '6m': days = 180
            elif period_str == '1y': days = 365
                
            start_date = end_date - timedelta(days=days)
            
            results = bt.run(start_date, end_date, split_ratio=1.0, mode=mode)
            
            if results and "IS" in results:
                stats = results["IS"]
                
                total_trades = stats.get('total_trades', 0)
                win_rate = stats.get('win_rate', 0.0)
                profit = stats.get('total_profit', 0.0)
                profit_factor = stats.get('profit_factor', 1.0)
                max_dd_pct = stats.get('max_drawdown_pct', 0.0)
                sharpe = stats.get('sharpe_ratio', 0.0)
                avg_slip = stats.get('avg_slippage_pips', 0.0)
                slip_usd = stats.get('total_slippage_usd', 0.0)
                
                contribution_report = results.get("contribution_report", "")
                baseline_report = results.get("baseline_report", "")
                walk_forward_report = results.get("walk_forward_report", "")
                reasoning_str = (
                    f"Strategiya: {strategy.upper()} ({mode.upper()})\n"
                    f"Davr: Oxirgi {days} kun | TF: {timeframe_str}\n"
                    f"Spread: {spread_pips}p (Dinamik) | O'rtacha Slippage: {avg_slip:.1f}p | Slippage Yo'qotishi: -${slip_usd:.2f}\n"
                    f"Profit Factor: {profit_factor} | Max Drawdown: {max_dd_pct}%\n"
                    f"Sharpe Ratio: {sharpe} | Jami foyda: {profit:.2f}$\n\n"
                )
                if baseline_report:
                    reasoning_str += baseline_report + "\n\n"

                if contribution_report:
                    reasoning_str += contribution_report + "\n\n"
                else:
                    reasoning_str += "Tahlil: Komponentlar hissa hisoboti ushbu test turi uchun mavjud emas.\n\n"

                if walk_forward_report:
                    reasoning_str += walk_forward_report
                else:
                    reasoning_str += "Tahlil: Walk-Forward tahlili ushbu test turi uchun yakunlanmadi."

                # Natijani test_results ga yozamiz
                test_result = {
                    "type": mode,
                    "symbol": symbol,
                    "timeframe": timeframe_str,
                    "total_trades": total_trades,
                    "win_rate": round(win_rate, 2),
                    "total_profit": round(profit, 2),
                    "reasoning": reasoning_str
                }
                
                self.supabase.table("test_results").insert(test_result).execute()
                
            self.supabase.table("backtest_jobs").update({"status": "completed"}).eq("id", job_id).execute()
            logger.info(f"Backtest yakunlandi: {job_id}")
            
        except Exception as e:
            logger.error(f"Backtest bajarishda xatolik: {e}")
            self.supabase.table("backtest_jobs").update({"status": "failed"}).eq("id", job_id).execute()
