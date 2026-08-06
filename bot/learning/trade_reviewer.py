import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import os

from bot.learning.ai_strategist import AIStrategist
from bot.learning.ai_memory import AIMemory

try:
    from bot.learning.shadow_collector import ShadowStateCollector
except ImportError:
    ShadowStateCollector = None

try:
    from bot.prediction.adaptive_weights import AdaptiveWeightManager
except ImportError:
    AdaptiveWeightManager = None

try:
    from bot.learning.pattern_memory import PatternMemoryBank
except ImportError:
    PatternMemoryBank = None

logger = logging.getLogger(__name__)

class TradeReviewer:
    def __init__(self, mt5_client: Any, ai_client: Any, config: Any, db_path: str = 'bot_learning.db'):
        self.mt5 = mt5_client
        self.ai = ai_client
        self.config = config
        
        # Determine paths
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if not os.path.isabs(db_path):
            self.db_path = os.path.join(root_dir, db_path)
        else:
            self.db_path = db_path
            
        self.decisions_db = os.path.join(root_dir, 'decisions_log.db')
        
        # Initialize AIStrategist
        def llm_wrapper(prompt: str) -> str:
            if hasattr(self.ai, 'get_simple_response'):
                return self.ai.get_simple_response(prompt, max_tokens=2000, model_tier="weak")
            return ""
        
        # Expose model name for traceability/version control of insights
        llm_wrapper.model_name = getattr(config, "ai_model_weak", "claude-haiku-4-5-20251001")
            
        self.ai_strategist = AIStrategist(
            llm_call_fn=llm_wrapper,
            knowledge_base_dir=os.path.join(root_dir, 'knowledge_base'),
            db_path=os.path.join(root_dir, 'strategist_db.sqlite'),
            chroma_db_dir=os.path.join(root_dir, 'chroma_db')
        )
        
        # AI Memory (doimiy xotira)
        self.ai_memory = AIMemory(
            db_path=os.path.join(root_dir, 'ai_memory.db')
        )
        
        # Shadow Learning Pipeline integratsiyasi
        self.shadow_collector = None
        if ShadowStateCollector is not None:
            try:
                self.shadow_collector = ShadowStateCollector(db_path='bot_learning.db')
            except Exception as e:
                logger.warning(f"ShadowStateCollector init failed: {e}")
        
        self.adaptive_weights = None
        if AdaptiveWeightManager is not None:
            try:
                self.adaptive_weights = AdaptiveWeightManager(db_path='bot_learning.db')
            except Exception as e:
                logger.warning(f"AdaptiveWeightManager init failed: {e}")

        self.pattern_memory = None
        if PatternMemoryBank is not None:
            try:
                self.pattern_memory = PatternMemoryBank(db_path='bot_learning.db')
            except Exception as e:
                logger.warning(f"PatternMemoryBank init failed: {e}")
        
        self.init_schema()

    def init_schema(self):
        try:
            conn = sqlite3.connect(self.db_path)
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
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS review_state (
                    id INTEGER PRIMARY KEY,
                    last_reviewed_time TEXT,
                    total_trades_analyzed INTEGER DEFAULT 0
                )
            ''')
            
            # Insert default state if empty
            cursor.execute("SELECT COUNT(*) FROM review_state")
            if cursor.fetchone()[0] == 0:
                # 30 kun oldingi vaqtni boshlang'ich qilib olamiz
                past_time = (datetime.now() - timedelta(days=30)).isoformat()
                cursor.execute("INSERT INTO review_state (id, last_reviewed_time, total_trades_analyzed) VALUES (1, ?, 0)", (past_time,))
                
            conn.commit()
        except Exception as e:
            logger.error(f"Error initializing learning DB: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    def _get_last_review_time(self) -> str:
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT last_reviewed_time FROM review_state WHERE id = 1")
            row = cursor.fetchone()
            return row[0] if row else "2000-01-01T00:00:00"
        except Exception:
            return "2000-01-01T00:00:00"
        finally:
            if 'conn' in locals():
                conn.close()
                
    def _update_review_state(self, new_time: str, trades_added: int):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("UPDATE review_state SET last_reviewed_time = ?, total_trades_analyzed = total_trades_analyzed + ? WHERE id = 1", (new_time, trades_added))
            conn.commit()
        except Exception as e:
            logger.error(f"Error updating review state: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    def get_closed_deals_since(self, since_iso: str) -> List[Any]:
        try:
            since_dt = datetime.fromisoformat(since_iso)
            now = datetime.now()
            
            trade_deals = []
            
            # 1. MT5 dagi haqiqiy/demo bitimlarni olish
            deals = self.mt5.history_deals_get(since_dt, now)
            if deals:
                # mt5 deal_type: 0 (BUY), 1 (SELL), entry 1 means closed deal
                mt5_deals = [d for d in deals if d.type in (0, 1) and d.entry == 1]
                trade_deals.extend(mt5_deals)
                
            # 2. Soya (Shadow) bitimlarni olish
            if getattr(self.config, "shadow_mode", False):
                try:
                    import os
                    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'bot_learning.db')
                    if os.path.exists(db_path):
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()
                        cursor.execute("SELECT id, symbol, profit, close_reason, timestamp FROM shadow_trade_history WHERE timestamp > ?", (since_iso,))
                        rows = cursor.fetchall()
                        
                        class DummyDeal:
                            def __init__(self, symbol, profit, timestamp, type=1, entry=1, volume=0.01):
                                self.symbol = symbol
                                self.profit = profit
                                self.time = datetime.fromisoformat(timestamp).timestamp()
                                self.type = type
                                self.entry = entry
                                self.volume = volume
                        
                        for row in rows:
                            dummy = DummyDeal(row[1], row[2], row[4])
                            trade_deals.append(dummy)
                            
                            # Shadow Learning: label past states
                            self._label_shadow_states(
                                symbol=row[1], pnl=row[2], 
                                trade_close_time=row[4]
                            )
                            
                        conn.close()
                except Exception as shadow_e:
                    logger.error(f"Error getting shadow deals: {shadow_e}")
                    
            return trade_deals
        except Exception as e:
            logger.error(f"Error getting MT5/Shadow deals: {e}")
            return []

    def _label_shadow_states(self, symbol: str, pnl: float, 
                              trade_close_time: str, timeframe: str = "H1"):
        """
        Savdo yopilganda shadow_states qatorlarini label qilish (Qadam 1 integratsiyasi).
        """
        if not self.shadow_collector:
            return
        try:
            # Trade ochilish vaqtini taxminiy aniqlash (yopilishdan 24 soat oldin)
            close_dt = datetime.fromisoformat(trade_close_time)
            open_dt = close_dt - timedelta(hours=24)
            
            direction = "BUY" if pnl > 0 else "SELL"  # taxminiy
            
            self.shadow_collector.label_past_states(
                symbol=symbol,
                timeframe=timeframe,
                direction=direction,
                pnl=pnl,
                trade_open_time=open_dt.isoformat(),
                trade_close_time=trade_close_time
            )
        except Exception as e:
            logger.debug(f"Shadow states label qilishda xatolik: {e}")

    def get_ai_decisions_for_deals(self, deals: List[Any]) -> List[Dict]:
        """Matches closed deals with their AI decisions from decisions_log.db"""
        matched = []
        try:
            conn = sqlite3.connect(self.decisions_db)
            cursor = conn.cursor()
            
            for deal in deals:
                deal_time = datetime.fromtimestamp(deal.time)
                
                # Baza orqali shu juftlik bo'yicha deal_time ga eng yaqin (oldingi) AI qarorini qidiramiz
                # time format: isoformat (e.g., 2026-07-24T22:00:00)
                cursor.execute('''
                    SELECT final_decision, context_json, ai_response 
                    FROM ai_decisions 
                    WHERE pair = ? AND timestamp <= ? 
                    ORDER BY id DESC LIMIT 1
                ''', (deal.symbol, deal_time.isoformat()))
                row = cursor.fetchone()
                
                ai_decision = "Unknown"
                ai_reasoning = "No context"
                market_context = {}
                
                if row:
                    ai_decision = row[0]
                    # context_json ni parse qilish
                    try:
                        ctx = json.loads(row[1])
                        # Barcha 8 ta strategiya signallarini o'rganish moduliga taqdim etamiz
                        market_context = {
                            "smc_trend": ctx.get("smc_structure", {}).get("trend", {}),
                            "harmonic_signal": ctx.get("harmonic_pattern", {}).get("signal", "HOLD"),
                            "news_bias": ctx.get("news_context", {}).get("historical_bias", {}).get("direction", "Neutral"),
                            "wyckoff_signal": ctx.get("wyckoff", {}).get("signal", "HOLD"),
                            "sr_volume_signal": ctx.get("sr_volume", {}).get("signal", "HOLD"),
                            "auto_patterns_signal": ctx.get("auto_patterns", {}).get("signal", "HOLD"),
                            "kill_zones_active": ctx.get("kill_zones", {}).get("active_sessions", []),
                            "kill_zones_signal": ctx.get("kill_zones", {}).get("signal", "HOLD")
                        }
                    except:
                        pass
                        
                    # Pattern data ni olish
                    try:
                        resp = json.loads(row[2])
                        ai_reasoning = resp.get("reasoning", "")[:150] # qisqacha
                        
                        audit = resp.get("_audit", {})
                        pattern_data = audit.get("pattern_data_for_reviewer")
                    except:
                        pass
                
                matched.append({
                    "symbol": deal.symbol,
                    "profit": deal.profit,
                    "volume": deal.volume,
                    "deal_time": deal_time.isoformat(),
                    "ai_action_taken": ai_decision,
                    "market_conditions_at_entry": market_context,
                    "ai_original_reasoning": ai_reasoning,
                    "pattern_data": pattern_data
                })
        except Exception as e:
            logger.error(f"Error fetching AI decisions for review: {e}")
        finally:
            if 'conn' in locals():
                conn.close()
                
        return matched

    def check_and_run_review(self):
        last_time = self._get_last_review_time()
        deals = self.get_closed_deals_since(last_time)
        
        # Har 10 ta yopilgan savdodan so'ng tahlil
        if len(deals) >= 10:
            logger.info(f"Yangi {len(deals)} ta yopilgan savdo topildi. AI Trade Reviewer o'rganishni boshladi...")
            self._run_review_cycle(deals, is_50_trades=(len(deals) >= 50))
            
    def _run_review_cycle(self, deals: List[Any], is_50_trades: bool):
        wins = [d for d in deals if d.profit > 0]
        losses = [d for d in deals if d.profit <= 0]
        win_rate = len(wins) / len(deals) if deals else 0
        
        avg_profit = sum(d.profit for d in wins) / len(wins) if wins else 0
        avg_loss = abs(sum(d.profit for d in losses) / len(losses)) if losses else 1
        avg_rr = avg_profit / avg_loss if avg_loss > 0 else 0
        
        matched_data = self.get_ai_decisions_for_deals(deals)

        # Record patterns to PatternMemoryBank
        if self.pattern_memory:
            for m in matched_data:
                pdata = m.get("pattern_data")
                if pdata and pdata.get("recent_candles"):
                    direction = m.get("ai_action_taken")
                    if direction in ("BUY", "SELL"):
                        outcome = "WIN" if m.get("profit", 0) > 0 else "LOSS"
                        try:
                            self.pattern_memory.record_pattern(
                                symbol=m["symbol"],
                                timeframe="H1",  # Yoki m.get dan olamiz, asosan H1
                                direction=direction,
                                candles=pdata["recent_candles"],
                                atr=pdata.get("atr", 0.0),
                                smc_zone_type=pdata.get("smc_zone_type"),
                                outcome=outcome,
                                pnl=m.get("profit", 0)
                            )
                        except Exception as e:
                            logger.error(f"Error recording pattern: {e}")
        
        prompt = f"""Sen ilg'or Trading AI Reviewersan.
Quyida botning oxirgi {len(deals)} ta savdo natijalari keltirilgan.
Bozor o'zgaruvchan. Sening vazifang qilingan xatolardan saboq olish va win_rate ni oshirish.
Qaysi strategiya yoki juftlik ishlamayotgan bo'lsa, o'shani cheklashni tavsiya qil. Qaysi biri yaxshi bo'lsa qo'llab quvvatla.

Statistika:
- Jami savdolar: {len(deals)}
- Win Rate: {win_rate*100:.1f}%
- Foydali savdolar o'rtacha foydasi: {avg_profit:.2f}
- Zararli savdolar o'rtacha zarari: {avg_loss:.2f}

Oxirgi savdolar:
{json.dumps(matched_data[:15], indent=2)}

Vazifang - faqat quyidagi JSON formatida sozlamalar kiritish (qo'shimcha matnsiz):
{{
  "analysis_summary": "Nima xato va nima to'g'ri bo'lgani xulosasi. 3-5 gapda yoz.",
  "adjustments": {{
    "sl_multiplier": 1.0,  # 0.5 dan 1.5 gacha bo'lishi SHART
    "tp_multiplier": 1.0,  # 0.5 dan 1.5 gacha bo'lishi SHART
    "avoid_symbols": []
  }},
  "strategy_weights": {{
    "smc": 1.0,
    "harmonic": 1.0,
    "wyckoff": 1.0,
    "sr_volume": 1.0,
    "auto_patterns": 1.0,
    "kill_zones": 1.0,
    "news": 1.0
  }}
}}
Har bir strategy_weight 0.3 dan 2.0 gacha bo'lishi mumkin.
Agar biror strategiya doimo xato signal bergan bo'lsa, uning vaznini kamaytir (masalan 0.5).
Agar biror strategiya ko'p to'g'ri signal bergan bo'lsa, vaznini oshir (masalan 1.5).
"""
        try:
            response = self.ai.get_decision(prompt, max_tokens=600, model_tier="weak")
            if response and "adjustments" in response:
                self.save_adjustments(
                    review_type="50_trade" if is_50_trades else "10_trade",
                    trades_analyzed=len(deals),
                    win_rate=win_rate,
                    avg_rr=avg_rr,
                    recommendations=response.get("analysis_summary", ""),
                    adjustments=response.get("adjustments", {})
                )
                
                # === YANGI: Saboqlarni xotiraga saqlash ===
                try:
                    summary = response.get("analysis_summary", "")
                    if summary:
                        def llm_wrapper(p):
                            return self.ai.get_simple_response(p, max_tokens=600, model_tier="weak")
                        self.ai_memory.auto_extract_lessons(summary, llm_wrapper)
                except Exception as e:
                    logger.warning(f"Saboqlarni xotiraga saqlashda xatolik: {e}")
                
                # === YANGI: Strategiya vaznlarini saqlash ===
                try:
                    strategy_weights = response.get("strategy_weights", {})
                    if strategy_weights:
                        for strat_name, weight in strategy_weights.items():
                            self.ai_memory.save_strategy_performance(
                                strategy_name=strat_name,
                                wins=len([d for d in deals if d.profit > 0]),
                                losses=len([d for d in deals if d.profit <= 0]),
                                total_profit=sum(d.profit for d in deals),
                                avg_rr=avg_rr,
                                recommended_weight=weight
                            )
                        logger.info(f"Strategiya vaznlari yangilandi: {strategy_weights}")
                except Exception as e:
                    logger.warning(f"Strategiya vaznlarini saqlashda xatolik: {e}")

                # Keyingi safar tekshirmasligi uchun vaqtni yangilash
                self._update_review_state(datetime.now().isoformat(), len(deals))
                logger.info(f"AI Trade Reviewer o'rganishni yakunladi. WinRate: {win_rate*100:.1f}%. Adjustments saqlandi.")
        except Exception as e:
            logger.error(f"Error during AI review cycle: {e}")

    def save_adjustments(self, review_type: str, trades_analyzed: int, win_rate: float, avg_rr: float, recommendations: str, adjustments: Dict):
        if "sl_multiplier" in adjustments:
            try: adjustments["sl_multiplier"] = max(0.5, min(1.5, float(adjustments["sl_multiplier"])))
            except: adjustments["sl_multiplier"] = 1.0
        if "tp_multiplier" in adjustments:
            try: adjustments["tp_multiplier"] = max(0.5, min(1.5, float(adjustments["tp_multiplier"])))
            except: adjustments["tp_multiplier"] = 1.0
            
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("UPDATE learning_adjustments SET active = 0 WHERE active = 1")
            
            cursor.execute('''
                INSERT INTO learning_adjustments 
                (timestamp, review_type, trades_analyzed, win_rate, avg_rr, ai_recommendations, adjustments_applied, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ''', (
                datetime.now().isoformat(),
                review_type,
                trades_analyzed,
                win_rate,
                avg_rr,
                json.dumps(recommendations, ensure_ascii=False),
                json.dumps(adjustments, ensure_ascii=False)
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Error saving adjustments: {e}")
        finally:
            if 'conn' in locals():
                conn.close()

    def get_active_adjustments(self) -> Dict[str, Any]:
        """Treyder moduli uchun joriy faol moslashuvlarni qaytaradi."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT adjustments_applied FROM learning_adjustments WHERE active = 1 ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row and row[0]:
                return json.loads(row[0])
            return {}
        except Exception:
            return {}
        finally:
            if 'conn' in locals():
                conn.close()
