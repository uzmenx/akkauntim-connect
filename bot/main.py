"""
TradingBot — Asosiy orchestrator.

Barcha komponentlarni birlashtiradi va trading siklini boshqaradi.
Bu fayl trading_bot_step5.py va trading_bot_step6.py ni almashtiradi.
"""
import signal
import sys
import time
import hashlib
import json
import logging
import pandas as pd
from typing import Optional, Dict, Any

from bot.config import BotConfig
from bot.core.mt5_client import MT5Client
from bot.core.ai_client import AIClient
from bot.core.state_manager import StateManager
from bot.engine.voting import aggregate_signals
from bot.engine.prompt_builder import PromptBuilder
from bot.engine.decision_logger import DecisionLogger
from bot.execution.risk_manager import RiskManager
from bot.execution.order_manager import OrderManager
from bot.sync.supabase_sync import SupabaseSync

logger = logging.getLogger(__name__)


class TradingBot:
    """
    AI Trading Bot — professional arxitektura bilan qurilgan.
    
    Barcha komponentlar DI orqali ulanadi:
    - MT5Client: MetaTrader 5 bilan aloqa
    - AIClient: Anthropic Claude bilan aloqa
    - Strategiyalar: SMC, Harmonic, News
    - Voting Engine: Signal aggregatsiyasi
    - Risk Manager: Savdo validatsiyasi
    - Order Manager: Order joylashtirish va boshqarish
    """

    def __init__(self, config: BotConfig):
        self.config = config
        self._running = False

        # Core
        self.mt5 = MT5Client(config)
        self.ai = AIClient(config)
        self.state = StateManager()
        self.decision_logger = DecisionLogger()

        # Engine
        self.prompt_builder = PromptBuilder(config)

        # Execution
        self.risk = RiskManager(self.mt5, config)
        self.orders = OrderManager(self.mt5, self.state, config)

        # Sync
        self.sync = SupabaseSync(config)

        # Signal handler (graceful shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Graceful shutdown — Ctrl+C bilan to'xtash."""
        logger.info("Shutdown signali qabul qilindi. Bot to'xtayapti...")
        self._running = False

    def _get_smc_data(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """SMC Structure tahlili."""
        try:
            from bot.strategy.smc.structure import SMCStructure
            smc = SMCStructure()
            smc.run(
                df['high'].tolist(),
                df['low'].tolist(),
                df['close'].tolist()
            )
            return smc.latest_context()
        except Exception as e:
            logger.error(f"SMC tahlil xatolik: {e}")
            return None

    def _get_smc_full_analysis(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """SMC Engine orqali to'liq tahlil (OB, FVG, Liquidity)."""
        try:
            from bot.strategy.smc.engine import analyze_market_structure
            return analyze_market_structure(df)
        except Exception as e:
            logger.error(f"SMC Engine xatolik: {e}")
            return None

    def _get_harmonic_patterns(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Harmonic pattern aniqlash."""
        try:
            from bot.strategy.harmonic.engine import analyze_harmonic_patterns
            return analyze_harmonic_patterns(df)
        except Exception as e:
            logger.error(f"Harmonic tahlil xatolik: {e}")
            return None

    def _get_news_context(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Yangiliklar konteksti."""
        try:
            from bot.strategy.news.scheduler import get_news_signal
            return get_news_signal(symbol)
        except Exception as e:
            logger.error(f"News tahlil xatolik: {e}")
            return None

    def _get_memory_bank_alerts(self, symbol: str, current_price: float) -> str:
        """SMC Memory Bank — tarixiy zonalar."""
        try:
            from bot.strategy.smc.zones import ZoneManager
            zone_mgr = ZoneManager()
            alerts = zone_mgr.get_nearby_zones(symbol, self.config.timeframe_major, current_price, threshold_pct=0.5)
            if alerts:
                text = "🚨 SMC MEMORY BANK ALERTS (Tarixiy zonalar):\n"
                for a in alerts:
                    text += f"- Narx {a.get('creation_time', '')} dagi {a.get('timeframe', '')} {a.get('zone_type', '')} zonasiga yaqin "
                    text += f"(Chegaralar: {a.get('bottom_price', '')} - {a.get('top_price', '')}).\n"
                return text
            return "SMC Memory Bank: Joriy narx atrofida kuchli tarixiy zonalar topilmadi.\n"
        except Exception as e:
            logger.warning(f"Memory Bank xatolik (davom etamiz): {e}")
            return "SMC Memory Bank: Ma'lumot olishda xatolik.\n"

    @staticmethod
    def _extract_signal(data: Optional[Dict], signal_type: str) -> Dict[str, Any]:
        """Signal ma'lumotlaridan BUY/SELL/HOLD signalini ajratish."""
        if not data:
            return {"signal": "HOLD", "confidence": 0}

        if signal_type == "smc":
            trend = data.get("trend", {})
            if isinstance(trend, dict):
                int_trend = trend.get("internal", "No Trend")
            else:
                int_trend = str(trend)
            if "Up" in int_trend:
                return {"signal": "BUY", "confidence": 75}
            elif "Down" in int_trend:
                return {"signal": "SELL", "confidence": 75}

        elif signal_type == "pattern":
            sig = data.get("signal", "NEUTRAL")
            if sig == "BUY":
                return {"signal": "BUY", "confidence": 75}
            elif sig == "SELL":
                return {"signal": "SELL", "confidence": 75}

        elif signal_type == "news":
            rec = data.get("recommendation", "neutral")
            if rec == "prepare_long":
                return {"signal": "BUY", "confidence": 80}
            elif rec == "prepare_short":
                return {"signal": "SELL", "confidence": 80}

        return {"signal": "HOLD", "confidence": 0}

    def _get_state_hash(self, context: Dict[str, Any]) -> str:
        """Kontekst xeshini yaratish (kesh uchun)."""
        news = context.get('news_context', {}) or {}
        next_event = news.get('next_event', {}) or {}
        state = {
            "vote": context.get('voting_result', {}).get('signal'),
            "vote_risk": context.get('voting_result', {}).get('risk_pct'),
            "smc_trend": context.get('smc_structure', {}).get('trend'),
            "pat_signal": context.get('harmonic_pattern', {}).get('signal'),
            "news_event": next_event.get('name'),
        }
        state_str = json.dumps(state, sort_keys=True)
        return hashlib.md5(state_str.encode('utf-8')).hexdigest()

    def _get_trailing_decision(self, symbol: str) -> str:
        """AI dan trailing rejimini so'rash."""
        try:
            context = {"smc_structure": self._get_smc_data(
                self._fetch_data(symbol, self.config.timeframe_major, 100)
            )}
            prompt = self.prompt_builder.build_trailing_prompt(context)
            response = self.ai.get_simple_response(
                prompt,
                system_prompt="Faqat bitta so'z bilan javob ber.",
                max_tokens=10
            )
            text = response.upper()
            if "CLOSE" in text:
                return "CLOSE_ALL"
            elif "STRUCT" in text:
                return "STRUCTURE"
            return "STEP"
        except Exception as e:
            logger.error(f"Trailing qarori olishda xato: {e}")
            return "STEP"

    def _fetch_data(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        """MT5 dan narx ma'lumotlarini olish."""
        rates = self.mt5.get_rates(symbol, timeframe, count)
        if rates is None or len(rates) == 0:
            return pd.DataFrame()
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def run_cycle(self, symbol: str) -> None:
        """
        Bitta symbol uchun to'liq trading siklini bajarish.
        
        1. Ma'lumot olish
        2. Texnik tahlil (SMC + Harmonic + News)
        3. Ovoz berish (Voting Engine)
        4. AI qaror (Claude)
        5. Risk tekshiruv
        6. Order joylashtirish
        """
        logger.info(f"=== [{symbol}] Tahlil boshlandi ===")

        # 1. Ma'lumot olish
        df_major = self._fetch_data(symbol, self.config.timeframe_major, 150)
        if df_major.empty:
            logger.warning(f"[{symbol}] uchun ma'lumot olib bo'lmadi, o'tkazib yuborildi.")
            return

        current_price = float(df_major.iloc[-1]['close'])

        # 2. Texnik tahlil
        smc_result = self._get_smc_full_analysis(df_major)
        smc_context = self._get_smc_data(df_major)
        pattern_result = self._get_harmonic_patterns(df_major)
        news_result = self._get_news_context(symbol)
        memory_bank_text = self._get_memory_bank_alerts(symbol, current_price)

        # 3. Signallarni ajratish
        smc_signal = self._extract_signal(smc_context, "smc")
        pattern_signal = self._extract_signal(pattern_result, "pattern")
        news_signal = self._extract_signal(news_result, "news")

        # 4. Voting Engine
        voting_result = aggregate_signals(smc_signal, pattern_signal, news_signal, self.config)
        logger.info(f"[{symbol}] Voting: {voting_result['signal']} | Strategies: {voting_result['agreed_strategies']}")

        vote_direction = voting_result.get("signal", "HOLD")
        vote_risk = voting_result.get("risk_pct", 0.0)

        # Agar HOLD bo'lsa, AI chaqirilmaydi
        if vote_direction == "HOLD" or vote_risk == 0.0:
            logger.info(f"[{symbol}] Voting Engine HOLD — AI chaqirilmadi.")
            return

        # 5. Kontekst va kesh
        context = self.prompt_builder.build_context_summary(
            smc_result=smc_result or smc_context,
            patterns=pattern_result,
            news=news_result,
            voting=voting_result,
            memory_bank=memory_bank_text
        )
        context["pair"] = symbol
        context["timeframe"] = self.config.timeframe_major
        context["current_price"] = current_price

        # Kelishgan strategiyalar soni
        agreed_count = len(voting_result.get('agreed_strategies', []))

        if agreed_count >= 2:
            # === 2+ strategiya kelishdi — AI ni bypass qilish, to'g'ridan-to'g'ri execute ===
            logger.info(f"[{symbol}] ✅ {agreed_count} strategiya kelishdi — Auto-Execute rejimi!")
            
            # Symbol-specific SL/TP
            if "XAU" in symbol or "GOLD" in symbol:
                default_sl, default_tp = 300, 600  # Oltin uchun kattaroq
            else:
                default_sl, default_tp = 30, 60  # Forex juftliklari uchun
            
            ai_decision = {
                "final_decision": "EXECUTE",
                "direction": vote_direction,
                "confidence": 80,
                "entry_price": None,
                "stop_loss_pips": default_sl,
                "take_profit_pips": default_tp,
                "risk_pct": vote_risk,
                "reasoning": f"Auto-execute: {agreed_count} strategiya ({', '.join(voting_result.get('agreed_strategies', []))}) tasdiqladi"
            }
            
            # Logga yozish
            self.decision_logger.log(
                pair=symbol, timeframe=self.config.timeframe_major,
                context=context, prompt="AUTO_EXECUTE",
                response=ai_decision, decision="EXECUTE",
                risk_pct=vote_risk, hash_val=self._get_state_hash(context),
                tokens={"input_tokens": 0, "output_tokens": 0}, cost=0.0
            )
        else:
            # === 1 strategiya — AI qaror bersin ===
            if getattr(self.config, 'ai_enabled', True) is False:
                logger.info(f"[{symbol}] ⚠️ AI o'chirilgan va faqat {agreed_count} ta strategiya mos keldi. Savdo rad etildi (kamida 2 ta kerak).")
                return

            # Kesh tekshirish
            current_hash = self._get_state_hash(context)
            cached = self.decision_logger.get_last_cached_response(symbol, current_hash)
            if cached:
                logger.info(f"[{symbol}] Keshdan foydalanildi (hash: {current_hash[:8]}...)")
                cached["reasoning"] = "(CACHED) " + cached.get("reasoning", "")
                self.decision_logger.log(
                    pair=symbol, timeframe=self.config.timeframe_major,
                    context=context, prompt="CACHED_PROMPT",
                    response=cached, decision=cached.get("final_decision", "REJECT"),
                    risk_pct=vote_risk, hash_val=current_hash,
                    tokens={"input_tokens": 0, "output_tokens": 0}, cost=0.0
                )
                ai_decision = cached
            else:
                # AI qaror
                prompt = self.prompt_builder.build_trading_prompt(context, symbol, current_price)
                logger.info(f"[{symbol}] Claude ga so'rov yuborilmoqda...")

                ai_decision = self.ai.get_decision(prompt)
                if not ai_decision:
                    logger.error(f"[{symbol}] AI javob bermadi — savdo bekor qilindi.")
                    return

                # Direction/risk o'zgartirilganini tekshirish
                if ai_decision.get('direction') != vote_direction or ai_decision.get('risk_pct') != vote_risk:
                    ai_decision['final_decision'] = "REJECT"
                    ai_decision['warnings'] = ai_decision.get('warnings', []) + [
                        "Claude risk_pct yoki direction ni o'zgartirishga urindi, savdo rad etildi."
                    ]
                    ai_decision['direction'] = vote_direction
                    ai_decision['risk_pct'] = vote_risk

                # Logga yozish
                self.decision_logger.log(
                    pair=symbol, timeframe=self.config.timeframe_major,
                    context=context, prompt=prompt,
                    response=ai_decision,
                    decision=ai_decision.get("final_decision", "REJECT"),
                    risk_pct=vote_risk, hash_val=current_hash,
                    tokens={"input_tokens": self.ai.total_tokens_in, "output_tokens": self.ai.total_tokens_out},
                    cost=self.ai.total_cost
                )

                # Supabase ga AI signal loglash
                try:
                    self.sync.log_ai_signal(
                        symbol=symbol,
                        signal=vote_direction,
                        confidence=int(ai_decision.get("confidence", 0)),
                        reasoning=ai_decision.get("reasoning", "")
                    )
                    self.sync.log_claude_cost(self.ai.total_cost)
                except Exception as e:
                    logger.warning(f"Supabase sync xatolik: {e}")

        # 7. EXECUTE tekshiruvi
        final = ai_decision.get("final_decision", "REJECT")
        logger.info(f"[{symbol}] AI Qaror: {final} | Sabab: {ai_decision.get('reasoning', '')}")

        if final != "EXECUTE":
            logger.info(f"[{symbol}] AI {final} berdi — savdo qilinmaydi.")
            return

        # 8. Risk validatsiyasi
        sl_pips = ai_decision.get("stop_loss_pips", 30)
        tp_pips = ai_decision.get("take_profit_pips", 60)
        confidence = ai_decision.get("confidence", 0)

        approved, msg, lot = self.risk.validate_trade(
            symbol=symbol,
            signal=vote_direction,
            confidence=confidence,
            stop_loss_pips=sl_pips,
            risk_pct=vote_risk
        )
        logger.info(f"[{symbol}] Risk natijasi: {msg} (Lot: {lot})")

        if not approved or lot is None:
            logger.info(f"[{symbol}] Risk manager rad etdi: {msg}")
            return

        # 9. Order ochish
        entry_price = ai_decision.get("entry_price")
        if entry_price == "null" or entry_price is None:
            entry_price = None
        else:
            try:
                entry_price = float(entry_price)
            except (ValueError, TypeError):
                entry_price = None

        # Signal turini aniqlash (BUY, SELL, BUY_LIMIT, etc.)
        order_signal = vote_direction
        if entry_price is not None:
            # Agar entry_price berilgan bo'lsa, pending order
            if vote_direction == "BUY":
                order_signal = "BUY_LIMIT"
            elif vote_direction == "SELL":
                order_signal = "SELL_LIMIT"

        success, order_msg, order_info = self.orders.place_order(
            symbol=symbol,
            signal=order_signal,
            lot_size=lot,
            stop_loss_pips=sl_pips,
            take_profit_pips=tp_pips,
            entry_price=entry_price
        )

        if success:
            logger.info(f"✅ [{symbol}] Order ochildi! Ticket: {order_info.get('ticket', 'N/A')}")
        else:
            logger.error(f"❌ [{symbol}] Order xatolik: {order_msg}")

    def manage_positions(self) -> None:
        """Ochiq pozitsiyalarni boshqarish (partial close, trailing)."""
        try:
            self.orders.manage_open_trades(
                trailing_decision_fn=self._get_trailing_decision
            )
        except Exception as e:
            logger.error(f"Pozitsiya boshqarishda xatolik: {e}")

    def start(self) -> None:
        """Bot siklini ishga tushirish (graceful shutdown bilan)."""
        logger.info("=" * 60)
        logger.info("🤖 AI Trading Bot ishga tushdi!")
        logger.info(f"   Symbollar: {self.config.trading_symbols}")
        logger.info(f"   Timeframe: {self.config.timeframe_major} / {self.config.timeframe_minor}")
        logger.info(f"   Interval: {self.config.loop_interval_minutes} daqiqa")
        logger.info(f"   AI Model: {self.config.ai_model}")
        logger.info("=" * 60)

        # MT5 ga ulanish
        if not self.mt5.connect():
            logger.critical("MT5 ga ulanib bo'lmadi. Bot to'xtadi.")
            return

        self._running = True

        try:
            while self._running:
                try:
                    # Cloud'dan yangi sozlamalarni yuklab olish
                    try:
                        settings = self.sync.fetch_bot_settings()
                        if settings:
                            self.config.update_from_dict(settings)
                            logger.info("Bot sozlamalari yangilandi.")
                    except Exception as e:
                        logger.warning(f"Sozlamalarni yangilashda xatolik: {e}")

                    # Har bir symbol uchun tahlil
                    for symbol in self.config.trading_symbols:
                        if not self._running:
                            break
                        self.run_cycle(symbol)

                    # Ochiq pozitsiyalarni boshqarish
                    self.manage_positions()

                    # Cloud sync
                    try:
                        self.sync.sync_all(self.mt5, is_running=True, message="Bot is running")
                    except Exception as e:
                        logger.warning(f"Cloud sync xatolik: {e}")

                    if not self._running:
                        break

                    logger.info(f"Barcha juftliklar tekshirildi. {self.config.loop_interval_minutes} daqiqa kutilmoqda...")

                    # Kutish (chunked — har 1 soniyada _running tekshirish)
                    wait_seconds = self.config.loop_interval_minutes * 60
                    for _ in range(wait_seconds):
                        if not self._running:
                            break
                        time.sleep(1)

                except Exception as e:
                    logger.error(f"Asosiy siklda xatolik: {e}", exc_info=True)
                    if self._running:
                        time.sleep(10)  # Xatolikdan keyin 10 soniya kutish

        finally:
            # Graceful shutdown
            logger.info("Bot to'xtayapti...")
            try:
                self.sync.sync_all(self.mt5, is_running=False, message="Bot stopped")
            except Exception:
                pass
            self.mt5.disconnect()
            logger.info("🛑 Bot to'xtadi.")


def create_bot(env_path: str = ".env", config_path: str = "config.json") -> TradingBot:
    """BotConfig yuklab TradingBot yaratish."""
    config = BotConfig.load(env_path, config_path)
    return TradingBot(config)
