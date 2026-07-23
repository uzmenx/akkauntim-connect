"""
trade_reviewer.py
=================
Botning xatolardan o'rganishi uchun AI Review moduli.
Har 10 va 50 ta yopilgan savdodan so'ng tahlil qilib, 
Claude AI dan xulosa va strategiya tavsiyalarini (adjustments) oladi.
"""

import json
import logging
import sqlite3
import datetime
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class TradeReviewer:
    def __init__(self, ai_client, mt5_client, config, db_path: str = "bot_learning.db"):
        self.ai = ai_client
        self.mt5 = mt5_client
        self.config = config
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path, timeout=30.0) as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS learning_adjustments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        review_type TEXT,
                        trades_analyzed INTEGER,
                        win_rate REAL,
                        avg_rr REAL,
                        ai_recommendations TEXT,
                        adjustments_applied TEXT,
                        active BOOLEAN DEFAULT 1
                    )
                ''')
                conn.commit()
        except Exception as e:
            logger.error(f"Error initializing learning DB: {e}")

    def should_review(self, current_closed_count: int) -> str:
        """Qanday review qilish kerakligini qaytaradi ('50_trade', '10_trade' yoki None)."""
        if current_closed_count == 0:
            return None
        
        # 50 talikka ustunlik
        if current_closed_count % 50 == 0:
            return '50_trade'
        elif current_closed_count % 10 == 0:
            return '10_trade'
            
        return None

    def gather_trade_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """MT5 dan oxirgi `limit` ta yopilgan deal/savdolarni yig'ish."""
        import MetaTrader5 as mt5
        now = datetime.datetime.now()
        start = now - datetime.timedelta(days=60) # ko'proq tarix olamiz (50 ta savdo sig'ishi uchun)
        
        try:
            deals = self.mt5.history_deals_get(start, now)
            if not deals:
                return []
                
            history = []
            for deal in deals:
                if deal.entry == mt5.DEAL_ENTRY_OUT:
                    history.append({
                        "ticket": deal.ticket,
                        "symbol": deal.symbol,
                        "time": datetime.datetime.fromtimestamp(deal.time).isoformat(),
                        "profit": deal.profit,
                        "volume": deal.volume,
                        "reason": deal.reason,
                        "comment": deal.comment
                    })
                    
            return sorted(history, key=lambda x: x["time"], reverse=True)[:limit]
        except Exception as e:
            logger.error(f"Tarixni olishda xatolik: {e}")
            return []

    def perform_review(self, review_type: str = "10_trade") -> bool:
        """Claude dan savdolar bo'yicha review so'rash."""
        if not getattr(self.config, 'learning_enabled', True):
            return False
            
        limit = 50 if review_type == "50_trade" else 10
        history = self.gather_trade_history(limit=limit)
        
        if len(history) < limit:
            logger.info(f"AI Review bekor qilindi. Yetarli tarix yo'q ({len(history)}/{limit})")
            return False
            
        wins = sum(1 for d in history if d["profit"] > 0)
        losses = sum(1 for d in history if d["profit"] < 0)
        win_rate = wins / len(history) if history else 0
        total_profit = sum(d["profit"] for d in history)
        
        # O'rtacha RR (taxminiy)
        avg_win = sum(d["profit"] for d in history if d["profit"] > 0) / wins if wins > 0 else 0
        avg_loss = abs(sum(d["profit"] for d in history if d["profit"] < 0) / losses) if losses > 0 else 1
        avg_rr = avg_win / avg_loss if avg_loss > 0 else 0
        
        if review_type == "50_trade":
            logger.info(f"Chuqurlashtirilgan AI Trade Reviewer (50 trade) ishga tushdi...")
            prompt = f"""Sen professional Forex Quant Analyst va Risk Manager. Botning oxirgi 50 ta savdosini chuqur tahlil qil.
Natijalar: Wins: {wins}, Losses: {losses}, Win Rate: {win_rate:.1%}, Total Profit: {total_profit:.2f}, Avg R:R: 1:{avg_rr:.2f}

Quyidagi JSON da barcha savdolar keltirilgan:
{json.dumps(history, indent=2)}

Vazifalar:
1. Eng yaxshi va eng yomon savdolarni top.
2. Strategiyaning qaysi komponenti (masalan SMC OB, FVG, Harmonic PRZ, News) zarar keltirayotganini aniqla.
3. Strategiyani butunlay qayta kalibrlash uchun aniq "adjustments" tavsiya qil.
Yangi tizimda barcha strategiya sabablari bazaviy 10 ball. Sen bu vaznlarni 5 dan 20 gacha tahrirlashing mumkin. Yaxshi ishlayotganiga balandroq (15, 20), yomoniga (5, 8) ber.

Javobing QAT'IY JSON formatda bo'lishi shart! Format:
{{
    "analysis": "batafsil tahlil, patternlar, eng yomon/yaxshi savdolar",
    "recommendations": "nimalarni o'zgartirish kerakligi haqida strategik qarorlar",
    "adjustments": {{
        "sl_multiplier": 1.2,
        "tp_multiplier": 0.8,
        "min_confluence_score": 20,
        "session_filter": ["London", "New York"],
        "reason_weights": {{
            "smc_ob_weight": 12,
            "harmonic_prz_weight": 8,
            "smc_fvg_weight": 10,
            "smc_trend_weight": 15,
            "smc_liquidity_weight": 10,
            "news_bias_weight": 5,
            "wyckoff_spring_weight": 10,
            "wyckoff_phase_weight": 10,
            "sr_volume_weight": 10,
            "auto_pattern_weight": 10,
            "kill_zone_weight": 10,
            "overlap_bonus_weight": 10,
            "mtf_weight": 10
        }}
    }}
}}
Hech qanday qo'shimcha matn yozma.
"""
        else:
            logger.info(f"AI Trade Reviewer (10 trade) ishga tushdi...")
            prompt = f"""Sen professional Forex risk menejerisan. Botning oxirgi 10 ta savdosini tahlil qil.
Wins: {wins}, Losses: {losses}, Win Rate: {win_rate:.1%}, Profit: {total_profit:.2f}

Oxirgi savdolar:
{json.dumps(history, indent=2)}

Vazifang: Oxirgi 10 ta savdo tendensiyasiga qarab, SL tez urib ketayaptimi yoki qaysidir sabab (SMC, Harmonic) yolg'on ishora qilyaptimi, qisqa muddatli moslashish tavsiya qil.
Barcha ballar 10 dan boshlanadi. 5 dan 20 gacha tahrirla.

Javobing QAT'IY JSON formatda bo'lishi shart! Format:
{{
    "analysis": "qisqa tahlil",
    "recommendations": "qisqa muddatli tavsiyalar",
    "adjustments": {{
        "sl_multiplier": 1.1,
        "tp_multiplier": 1.0,
        "min_confluence_score": 20,
        "reason_weights": {{
            "smc_ob_weight": 12,
            "harmonic_prz_weight": 10,
            "mtf_weight": 10
        }}
    }}
}}
"""
        
        try:
            response = self.ai.get_decision(prompt, system_prompt="Faqat JSON qaytar.", max_tokens=2000)
            
            if response and "adjustments" in response:
                # Bazadagi oldingi activelarni inactive qilish
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("UPDATE learning_adjustments SET active = 0 WHERE active = 1")
                    
                    # Yangisini kiritish
                    cursor.execute('''
                        INSERT INTO learning_adjustments 
                        (timestamp, review_type, trades_analyzed, win_rate, avg_rr, ai_recommendations, adjustments_applied, active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    ''', (
                        datetime.datetime.now().isoformat(),
                        review_type,
                        len(history),
                        win_rate,
                        avg_rr,
                        json.dumps({
                            "analysis": response.get("analysis", ""),
                            "recommendations": response.get("recommendations", "")
                        }),
                        json.dumps(response.get("adjustments", {}))
                    ))
                    conn.commit()
                
                logger.info(f"✅ AI Review ({review_type}) muvaffaqiyatli saqlandi. Win Rate: {win_rate:.1%}")
                logger.info(f"Yangi adjustments: {response['adjustments']}")
                return True
            else:
                logger.warning(f"AI javobida 'adjustments' topilmadi. Javob: {response}")
        except Exception as e:
            logger.error(f"AI Review davomida xatolik: {e}")
            
        return False
        
    def get_latest_adjustments(self) -> Dict[str, Any]:
        """Eng so'nggi tasdiqlangan va active AI tavsiyalarini o'qib oladi."""
        default_adj = {
            "sl_multiplier": 1.0,
            "tp_multiplier": 1.0,
            "min_confluence_score": 20,
            "session_filter": [],
            "reason_weights": {}
        }
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT adjustments_applied FROM learning_adjustments 
                    WHERE active = 1 ORDER BY id DESC LIMIT 1
                ''')
                row = cursor.fetchone()
                if row and row[0]:
                    adj = json.loads(row[0])
                    for k in default_adj:
                        if k in adj:
                            default_adj[k] = adj[k]
        except Exception as e:
            logger.error(f"Adjustments o'qishda xato: {e}")
            
        return default_adj
