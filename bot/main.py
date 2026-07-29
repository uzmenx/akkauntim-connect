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
from bot.engine.regime_detector import RegimeDetector
from bot.engine.strategy_portfolio import StrategyPortfolioManager
from bot.execution.risk_manager import RiskManager
from bot.engine.ai_call_gate import should_call_ai
from bot.execution.order_manager import OrderManager
from bot.learning.trade_reviewer import TradeReviewer
from bot.learning.ai_memory import AIMemory
from bot.sync.supabase_sync import SupabaseSync
from bot.sync.telegram_sync import TelegramSync
from bot.engine.close_mechanism_classifier import classify_close_mechanism
from bot.engine.blackbox_exporter import export_blackbox_json
from bot.strategy.news.straddle import check_and_place_straddle, cleanup_straddle_orders, refresh_straddle_for_delayed_news
from bot.strategy.news.fundamental import execute_fundamental_method

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
    - Trade Reviewer: AI O'rganish moduli
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
        self.reviewer = TradeReviewer(self.mt5, self.ai, config)
        self.regime_detector = RegimeDetector()
        self.portfolio_manager = StrategyPortfolioManager()

        # Execution
        self.risk = RiskManager(self.mt5, config, self.state)
        self.orders = OrderManager(self.mt5, self.state, config)
        self.closed_trades_count = 0

        # Sync
        self.sync = SupabaseSync(config)
        self.telegram = TelegramSync(config)
        
        # AI Memory (doimiy xotira)
        self.ai_memory = AIMemory()
        self.ai_memory.sync_client = self.sync
        
        # Reviewer ichidagi ai_memory ni ham cloud ga ulaymiz
        self.reviewer.ai_memory.sync_client = self.sync
        
        # Inyect dependencies into AIClient
        self.ai.sync = self.sync
        self.ai.telegram = self.telegram

        # Batch Processing holati
        self.current_symbol_index = 0

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
            return get_news_signal(symbol, ai_client=self.ai)
        except Exception as e:
            logger.error(f"News tahlil xatolik: {e}")
            return None

    def _get_sr_volume_analysis(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """SR Volume (Support & Resistance Boxes) tahlili."""
        try:
            from bot.strategy.sr_volume.engine import analyze_sr_volume
            return analyze_sr_volume(df)
        except Exception as e:
            logger.error(f"SR Volume tahlil xatosi: {e}")
            return {}

    def _get_auto_patterns_analysis(self, df: pd.DataFrame, current_price: float) -> Optional[Dict[str, Any]]:
        """Auto Chart Patterns (Figuralar) tahlili."""
        try:
            from bot.strategy.auto_patterns.engine import analyze_auto_patterns
            from bot.engine.confluence import compute_atr
            atr = compute_atr(df)
            return analyze_auto_patterns(df, current_price, atr)
        except Exception as e:
            logger.error(f"Auto Patterns tahlil xatosi: {e}")
            return {}

    def _get_kill_zones_analysis(self, df: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """Kill Zones va sessiyalar tahlili."""
        try:
            from bot.strategy.kill_zones.engine import analyze_kill_zones
            return analyze_kill_zones(df)
        except Exception as e:
            logger.error(f"Kill Zones tahlil xatosi: {e}")
            return {}

    def _get_anti_manipulation_analysis(self, df: pd.DataFrame, smc_data: Dict[str, Any], current_price: float) -> str:
        """Stop-Hunter Shield tahlili (Anti-Manipulation)."""
        try:
            from bot.strategy.anti_manipulation.engine import analyze_stop_hunting_risk
            from bot.engine.confluence import compute_atr
            atr = compute_atr(df)
            return analyze_stop_hunting_risk(df, smc_data, current_price, atr)
        except Exception as e:
            logger.error(f"Anti-Manipulation tahlil xatosi: {e}")
            return "Stop-Hunter Shield: Xatolik yuz berdi."

    def _get_trap_detection_analysis(self, df: pd.DataFrame) -> str:
        """Trap Detector tahlili (Fakeout va Rejection)."""
        try:
            from bot.strategy.trap_detector.engine import analyze_trap_detector
            return analyze_trap_detector(df)
        except Exception as e:
            logger.error(f"Trap Detector tahlil xatosi: {e}")
            return "Trap Detector: Xatolik yuz berdi."

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

        elif signal_type in ["wyckoff", "sr_volume", "auto_patterns", "kill_zones"]:
            sig = data.get("signal", "HOLD")
            conf = data.get("confidence", 60)
            if sig in ["BUY", "SELL"]:
                return {"signal": sig, "confidence": conf}

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

        YANGI OQIM (Confluence Engine):
        1. Ma'lumot olish (H1)
        2. Texnik tahlil (SMC + Harmonic + News)
        3. Confluence Ball hisoblash (0-140)
        4. Qaror: EXECUTE (70+) / AI_DECIDE (50-69) / REJECT (<50)
        5. Dinamik SL/TP hisoblash
        6. Risk tekshiruv
        7. Order joylashtirish
        """
        logger.info(f"=== [{symbol}] Tahlil boshlandi ===")

        # ============================================================
        # 1. MA'LUMOT OLISH
        # ============================================================
        df_major = self._fetch_data(symbol, self.config.timeframe_major, 150)
        if df_major.empty:
            logger.warning(f"[{symbol}] uchun ma'lumot olib bo'lmadi, o'tkazib yuborildi.")
            return

        current_price = float(df_major.iloc[-1]['close'])
        
        # ============================================================
        # 1.5. REJIM ANIQLASH VA STRATEGIYALAR PORTFELI
        # ============================================================
        current_regime = self.regime_detector.update(df_major)
        active_strategies = self.portfolio_manager.get_active_strategies(current_regime)
        
        try:
            adx_val = self.regime_detector.last_adx
            vol_pct = self.regime_detector.last_vol_pct
            self.sync.log_regime(symbol, self.config.timeframe_major, current_regime.value, adx_val, vol_pct)
        except Exception as e:
            logger.debug(f"Rejimni log qilishda xatolik: {e}")

        # ============================================================
        # 2. TEXNIK TAHLIL — barcha strategiyalarni ishga tushirish
        # ============================================================
        smc_result = self._get_smc_full_analysis(df_major)
        smc_context = self._get_smc_data(df_major)
        
        # Minor timeframe ma'lumotlarini qo'shish
        tf_minor = self.config.timeframe_minor
        df_minor = self._fetch_data(symbol, tf_minor, 150)
        smc_minor = self._get_smc_data(df_minor) if not df_minor.empty else {}
        
        pattern_result = self._get_harmonic_patterns(df_major)
        news_result = self._get_news_context(symbol)
        memory_bank_text = self._get_memory_bank_alerts(symbol, current_price)
        
        # Balans va ochiq pozitsiyalarni olish
        acc_info = self.mt5.get_account_info()
        balance = acc_info.balance if acc_info else 0.0
        margin_free = acc_info.margin_free if acc_info else 0.0
        
        open_positions = self.mt5.get_positions(symbol)
        positions_info = []
        if open_positions:
            for p in open_positions:
                positions_info.append(f"{'BUY' if p.type == self.mt5.ORDER_TYPE_BUY else 'SELL'} {p.volume} lot at {p.price_open}")

        try:
            from bot.strategy.wyckoff.engine import analyze_wyckoff
            wyckoff_result = analyze_wyckoff(df_major)
        except Exception as e:
            logger.error(f"Wyckoff tahlil xatosi: {e}")
            wyckoff_result = {}

        sr_volume_result = self._get_sr_volume_analysis(df_major)
        auto_patterns_result = self._get_auto_patterns_analysis(df_major, current_price)
        kill_zones_result = self._get_kill_zones_analysis(df_major)
        anti_manipulation_result = self._get_anti_manipulation_analysis(df_major, smc_result or smc_context, current_price)
        trap_detector_result = self._get_trap_detection_analysis(df_major)

        # ============================================================
        # 3. CONFLUENCE ENGINE — ball tizimi asosida savdo qarori
        # ============================================================
        adj = getattr(self, "last_adjustments", self.reviewer.get_active_adjustments())

        voting_result = aggregate_signals(
            smc_data=smc_result or smc_context,
            pattern_data=pattern_result,
            news_data=news_result,
            wyckoff_data=wyckoff_result,
            sr_volume_data=sr_volume_result,
            auto_pattern_data=auto_patterns_result,
            kill_zones_data=kill_zones_result,
            config=self.config,
            active_strategies=active_strategies
        )

        # ============================================================
        # AI AGENT AUTONOMOUS DECISION
        # ============================================================
        
        context = self.prompt_builder.build_context_summary(
            smc_result=smc_result or smc_context,
            patterns=pattern_result,
            news=news_result,
            voting=voting_result,
            memory_bank=memory_bank_text,
            wyckoff=wyckoff_result,
            sr_volume=sr_volume_result,
            auto_patterns=auto_patterns_result,
            kill_zones=kill_zones_result,
            anti_manipulation=anti_manipulation_result,
            trap_detector=trap_detector_result
        )
        context["pair"] = symbol
        context["regime"] = current_regime.value
        context["active_strategies"] = active_strategies
        context["timeframe"] = self.config.timeframe_major
        context["current_price"] = current_price
        context["timeframe_minor"] = tf_minor
        context["smc_minor"] = smc_minor
        context["balance"] = balance
        context["margin_free"] = margin_free
        context["open_positions"] = positions_info
        
        # Risk malumotini AI ga yuborish uchun hisoblash
        risk_info = "Risk info noaniq."
        symbol_info = self.mt5.symbol_info(symbol)
        if symbol_info:
            tick_size = symbol_info.trade_tick_size
            tick_value = symbol_info.trade_tick_value
            if tick_size > 0 and tick_value > 0:
                price_move_100 = tick_size * 100
                loss_for_01_lot = (price_move_100 / tick_size) * tick_value * 0.01
                risk_info = (f"Risk nisbati: Narx {price_move_100:.5f} ga o'zgarganda "
                             f"(100 ticks), 0.01 lot uchun xatar/foyda {loss_for_01_lot:.2f} "
                             f"{symbol_info.currency_profit} ni tashkil qiladi.")
        context["risk_info"] = risk_info
        
        # O'rganish modulidan kelgan faol moslashuvlarni olish va kontekstga qo'shish
        active_adjustments = self.reviewer.get_active_adjustments()
        context["learning_adjustments"] = active_adjustments

        # === YANGI: Kitob bilimlarini (RAG) olish ===
        try:
            smc_trend_text = str(smc_context.get('trend', {}).get('internal', 'Unknown')) if 'smc_context' in locals() and smc_context else 'Unknown'
            harmonic_sig = str(pattern_result.get('signal', 'NEUTRAL')) if 'pattern_result' in locals() and pattern_result else 'NEUTRAL'
            situation_desc = f"{symbol} {self.config.timeframe_major} SMC:{smc_trend_text} Pattern:{harmonic_sig} Regime:{current_regime.value}"
            market_cond = current_regime.value.lower() if hasattr(current_regime, 'value') else 'all'
            
            if 'trend' in market_cond:
                market_cond = 'trend'
            elif 'range' in market_cond or 'flat' in market_cond:
                market_cond = 'range'
            elif 'volatile' in market_cond or 'high' in market_cond:
                market_cond = 'volatile'
            else:
                market_cond = 'all'
            
            # Shadow (chaqaloq) AI bilimlari ishlashi uchun yoqildi, lekin token tejash uchun limit=1 qilindi
            book_knowledge = self.reviewer.ai_strategist.get_relevant_context(
                current_situation_desc=situation_desc,
                market_condition=market_cond,
                limit=1
            )
            if book_knowledge:
                context["book_knowledge"] = book_knowledge
                logger.info(f"[{symbol}] Kitob bilimlaridan {len(book_knowledge.split(chr(10)))} ta qoida topildi")
        except Exception as e:
            logger.debug(f"[{symbol}] Kitob bilimlarini olishda xatolik (davom etamiz): {e}")

        # === YANGI: AI Xotirasini olish ===
        try:
            ai_memory_text = self.ai_memory.get_recent_lessons(limit=2)
            if ai_memory_text:
                context["ai_memory"] = ai_memory_text
        except Exception as e:
            logger.debug(f"AI xotirani olishda xatolik: {e}")

        # === YANGI: Dinamik strategiya vaznlarini qo'llash ===
        try:
            strategy_weights = self.ai_memory.get_strategy_weights()
            if strategy_weights:
                for strat, weight in strategy_weights.items():
                    config_key = f"strategy_weight_{strat}"
                    if hasattr(self.config, config_key):
                        setattr(self.config, config_key, weight)
                logger.debug(f"[{symbol}] Dinamik strategiya vaznlari qo'llandi: {strategy_weights}")
        except Exception as e:
            logger.debug(f"Strategiya vaznlarini qo'llashda xatolik: {e}")

        # === AI Call Gate: bozor strukturasi o'zgarmagan bo'lsa, chaqiruvni tejash ===
        smc_for_gate = smc_result if 'smc_result' in locals() and smc_result else (smc_context if 'smc_context' in locals() and smc_context else {})
        trend_internal = str(smc_for_gate.get('trend', {}).get('internal', 'Unknown'))
        last_bos_obj = smc_for_gate.get('last_bos', {}) or {}
        bos_price = last_bos_obj.get('price')
        regime_str = current_regime.value if hasattr(current_regime, 'value') else str(current_regime)

        gate_state = self.state.get_symbol_gate_state(symbol)
        call_needed, gate_reason = should_call_ai(
            symbol=symbol,
            current_trend_internal=trend_internal,
            current_bos_price=bos_price,
            current_regime=regime_str,
            gate_state=gate_state,
        )

        if not call_needed:
            logger.info(f"[{symbol}] AI chaqiruvi o'tkazib yuborildi ({gate_reason}). "
                        f"Oldingi qaror: {gate_state.get('last_ai_decision', 'HOLD') if gate_state else 'HOLD'}")
            return  # Bu tsikl uchun HOLD bilan bir xil natija — yangi bitim ochilmaydi
        else:
            logger.info(f"[{symbol}] AI chaqirilmoqda ({gate_reason})")

        prompt = self.prompt_builder.build_trading_prompt(context, symbol, current_price)
        logger.info(f"[{symbol}] AI Agent ga bozor tahlili yuborilmoqda...")
        
        ai_decision = self.ai.get_decision(prompt)
        if not ai_decision:
            logger.error(f"[{symbol}] AI javob bermadi — savdo bekor qilindi.")
            return

        final_decision = ai_decision.get("decision", "HOLD")
        reasoning_text = ai_decision.get("reasoning", "")
        logger.info(f"[{symbol}] AI Xulosasi: {final_decision} | Sabab: {reasoning_text[:200]}")

        self.state.update_symbol_gate_state(
            symbol=symbol,
            trend_internal=trend_internal,
            bos_price=bos_price,
            regime=regime_str,
            ai_decision=final_decision,
        )

        if final_decision == "HOLD":
            reasoning_lower = reasoning_text.lower()
            if "limit order" in reasoning_lower or "limit_buy" in reasoning_lower or "limit_sell" in reasoning_lower:
                warn_msg = f"⚠️ <b>AI DIQQAT:</b> decision/reasoning nomuvofiqligi aniqlandi!\n<b>Symbol:</b> #{symbol}\n<b>Qaror:</b> HOLD\n<b>Sabab (reasoning):</b> {reasoning_text}"
                logger.warning(warn_msg)
                try:
                    self.telegram.send_message(warn_msg)
                except Exception as e:
                    logger.error(f"Telegram ga xatolik xabarini yuborishda muammo: {e}")

            try:
                self.sync.log_ai_signal(
                    symbol=symbol, signal="HOLD", confidence=80, reasoning=ai_decision.get("reasoning", ""),
                    entry_price=None, sl_price=None, tp_price=None, rr_ratio=0.0,
                    stop_loss_pips=0.0, take_profit_pips=0.0
                )
            except Exception as e:
                logger.warning(f"Supabase sync xatolik (HOLD signal): {e}")
            return
            
        pip_divisor = 0.1 if ("XAU" in symbol or "GOLD" in symbol) else (0.01 if "JPY" in symbol else 0.0001)
        
        entry_price = ai_decision.get("entry_price")
        if entry_price is None:
            entry_price = current_price
        
        sl_price = ai_decision.get("stop_loss")
        if not sl_price:
            logger.warning(f"[{symbol}] AI stop_loss bermadi! Savdo bekor qilinmoqda. (Bank-grade xavfsizlik)")
            return
            
        tp_price = ai_decision.get("take_profit")
        
        sl_price_diff = abs(entry_price - sl_price)        
        # --- O'rganish moduli moslashuvlari ---
        avoid_symbols = active_adjustments.get("avoid_symbols", [])
        if symbol in avoid_symbols:
            logger.info(f"[{symbol}] Savdo bekor qilindi (AI o'rganish moduli: avoid_symbols).")
            return
            
        sl_mult = active_adjustments.get("sl_multiplier", 1.0)
        tp_mult = active_adjustments.get("tp_multiplier", 1.0)
        
        sl_price_diff = sl_price_diff * sl_mult
        
        # Yangilangan SL/TP narxlarini hisoblash
        if final_decision in ["BUY", "LIMIT_BUY"]:
            if sl_price: sl_price = entry_price - sl_price_diff
            if tp_price: tp_price = entry_price + (abs(entry_price - tp_price) * tp_mult)
        elif final_decision in ["SELL", "LIMIT_SELL"]:
            if sl_price: sl_price = entry_price + sl_price_diff
            if tp_price: tp_price = entry_price - (abs(entry_price - tp_price) * tp_mult)
        
        sl_pips = sl_price_diff / pip_divisor
        tp_pips = abs(entry_price - tp_price) / pip_divisor if tp_price else 100 * tp_mult
        risk_pct = ai_decision.get("risk_pct")

        # Signalni "BUY", "SELL", "BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP" ga aylantirish
        order_signal = final_decision
        if final_decision == "LIMIT_BUY":
            order_signal = "BUY_LIMIT"
        elif final_decision == "LIMIT_SELL":
            order_signal = "SELL_LIMIT"
        elif final_decision in ["BUY", "SELL"]:
            # Agar AI 'BUY' yozgan bo'lsa ham, lekin entry_price ni uzoqroq qilib belgilagan bo'lsa, uni avtomatik PENDING orderga aylantiramiz
            price_diff = abs(entry_price - current_price) / pip_divisor
            if price_diff > 3.0: # Agar 3 pip dan uzoq bo'lsa
                if final_decision == "BUY":
                    if entry_price < current_price:
                        order_signal = "BUY_LIMIT"
                    else:
                        order_signal = "BUY_STOP"
                elif final_decision == "SELL":
                    if entry_price > current_price:
                        order_signal = "SELL_LIMIT"
                    else:
                        order_signal = "SELL_STOP"
                logger.info(f"[{symbol}] AI '{final_decision}' degandi, lekin narx uzoqligi sababli '{order_signal}' ga avtomatik o'zgartirildi.")
            
        approved, msg, lot = self.risk.validate_trade(
            symbol=symbol,
            signal=order_signal if "LIMIT" not in order_signal else order_signal.split("_")[0],
            confidence=80, # AI o'zi qaror qilyapti
            stop_loss_price_diff=sl_price_diff,
            risk_pct=risk_pct
        )
        
        logger.info(f"[{symbol}] Risk natijasi: {msg} (Lot: {lot})")
        if not approved or lot is None:
            logger.info(f"[{symbol}] Risk manager rad etdi: {msg}")
            return
            
        try:
            rr_ratio = round(tp_pips / sl_pips, 2) if sl_pips and sl_pips > 0 else 0.0
            self.sync.log_ai_signal(
                symbol=symbol, signal=final_decision, confidence=80, reasoning=ai_decision.get("reasoning", ""),
                entry_price=entry_price, sl_price=sl_price, tp_price=tp_price, rr_ratio=rr_ratio,
                stop_loss_pips=sl_pips, take_profit_pips=tp_pips
            )
            self.sync.log_claude_cost(self.ai.total_cost)
        except Exception as e:
            logger.warning(f"Supabase sync xatolik: {e}")

        # Buyurtmani yuborish
        if "LIMIT" in order_signal or "STOP" in order_signal:
            expiration_mins = ai_decision.get("expiration_minutes", 240) # default 4 hours
            success, order_msg, order_info = self.orders.place_pending_order(
                symbol=symbol,
                order_type_str=order_signal,
                price=entry_price,
                lot_size=lot,
                stop_loss_pips=sl_pips,
                take_profit_pips=tp_pips,
                magic=self.config.magic_number,
                comment="AI Limit",
                expiration_minutes=expiration_mins
            )
        else:
            success, order_msg, order_info = self.orders.place_order(
                symbol=symbol,
                signal=order_signal,
                lot_size=lot,
                stop_loss_pips=sl_pips,
                take_profit_pips=tp_pips,
                entry_price=entry_price
            )

        # Log to db (kitob bilimlaridan olingan insight ID larni ham saqlash)
        ticket = order_info.get("ticket") if isinstance(order_info, dict) else None
        
        # RAG dan olingan insight ID larni ajratib olish
        used_insight_ids = []
        try:
            book_ctx = context.get("book_knowledge", "")
            if book_ctx:
                import re
                ids_found = re.findall(r'\(ID: ([a-f0-9-]+)\)', book_ctx)
                used_insight_ids = ids_found
        except Exception:
            pass
        
        from bot.engine.news_coverage_check import check_news_coverage_gap
        news_gap = check_news_coverage_gap(symbol)

        self.decision_logger.log(
            pair=symbol, timeframe=self.config.timeframe_major,
            context=context, prompt="AUTONOMOUS_AI",
            response=ai_decision, decision=final_decision,
            risk_pct=risk_pct, hash_val=self._get_state_hash(context),
            tokens={"input_tokens": self.ai.total_tokens_in, "output_tokens": self.ai.total_tokens_out},
            cost=self.ai.total_cost,
            ticket=ticket,
            used_insight_ids=json.dumps(used_insight_ids) if used_insight_ids else None,
            news_coverage_gap=news_gap
        )

        if success:
            logger.info(
                f"✅ [{symbol}] AI Order ochildi! Ticket: {order_info.get('ticket', 'N/A')} | "
                f"Signal: {order_signal} | SL: {sl_pips:.1f} pip | TP: {tp_pips:.1f} pip | "
                f"Risk: {risk_pct:.1%}"
            )
            self.telegram.send_signal(
                symbol=symbol,
                signal=order_signal,
                confidence=80,
                sl=sl_pips,
                tp=tp_pips,
                reasoning=ai_decision.get("reasoning", "")
            )
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
                            
                        # === YANGI: PENDING BOOKLARNI TEKSHIRISH ===
                        try:
                            pending_books = self.sync.check_pending_books()
                            if pending_books:
                                for book in pending_books:
                                    logger.info(f"Yangi kitob topildi: {book['file_name']}")
                                    self.sync.update_book_status(book["id"], "processing")
                                    
                                    import urllib.request
                                    import tempfile
                                    import os
                                    
                                    temp_dir = tempfile.gettempdir()
                                    temp_path = os.path.join(temp_dir, book["file_name"])
                                    
                                    try:
                                        urllib.request.urlretrieve(book["file_url"], temp_path)
                                        self.reviewer.ai_strategist.sync_client = self.sync
                                        result = self.reviewer.ai_strategist.add_knowledge_source(temp_path, book["file_name"])
                                        
                                        if isinstance(result, tuple) and result[0]:
                                            _, saved, total = result
                                            self.sync.update_book_status(book["id"], f"done|{saved}|{total}")
                                        elif result is True:
                                            self.sync.update_book_status(book["id"], "done")
                                        else:
                                            self.sync.update_book_status(book["id"], "error_processing")
                                    except Exception as e:
                                        logger.error(f"Kitobni ishlashda xato: {e}")
                                        self.sync.update_book_status(book["id"], "error_download")
                                    finally:
                                        if os.path.exists(temp_path):
                                            os.remove(temp_path)
                        except Exception as e:
                            logger.error(f"Shadow Learning tekshirishda xatolik: {e}")
                            
                    except Exception as e:
                        logger.warning(f"Sozlamalarni yangilashda xatolik: {e}")

                    # === YANGILIKLAR SAVDOSI (NEWS TRADING - 2 USUL) ===
                    try:
                        # 1-usul: AI'siz Straddle (Buy Stop/Sell Stop)
                        check_and_place_straddle(self.mt5, self.orders, [], getattr(self.config, 'news_settings', {}))
                        cleanup_straddle_orders(self.mt5, self.orders)
                        # Kechikkan yangiliklar uchun orderlarni yangilab turish
                        refresh_straddle_for_delayed_news(self.mt5, self.orders)
                        
                        # 2-usul: AI bilan Uzoq muddatli (Fundamental)
                        execute_fundamental_method(self.mt5, self.orders, self.ai)
                    except Exception as e:
                        logger.error(f"News Trading siklida xatolik: {e}")

                    # Juftliklarni aniqlash (Dam olish kuni vs Ish kuni)
                    import datetime
                    is_weekend = datetime.datetime.utcnow().weekday() >= 5
                    
                    if is_weekend:
                        all_symbols = self.mt5.get_crypto_symbols()
                        if not all_symbols:
                            logger.warning("MT5 dan Kripto juftliklar topilmadi! Dam olish kuni ishlash imkonsiz.")
                        # else log yozmaymiz, chunki tsikl har marta aylanadi
                    else:
                        if getattr(self.config, "auto_discover_symbols", True):
                            all_symbols = self.mt5.get_tradeable_symbols()
                            if not all_symbols:
                                logger.warning("MT5 dan juftliklar topilmadi. Config dagi juftliklardan foydalanamiz.")
                                all_symbols = self.config.trading_symbols
                        else:
                            all_symbols = self.config.trading_symbols

                    if not all_symbols:
                        logger.warning("Tahlil uchun hech qanday juftlik yo'q.")
                        time.sleep(60)
                        continue
                        
                    batch_size = getattr(self.config, "batch_size", 3)
                    end_index = self.current_symbol_index + batch_size
                    current_batch = all_symbols[self.current_symbol_index:end_index]
                    
                    if end_index > len(all_symbols):
                        current_batch += all_symbols[0:end_index - len(all_symbols)]
                        
                    self.current_symbol_index = end_index % len(all_symbols)
                    
                    logger.info(f"Navbatdagi Batch ({len(current_batch)} ta juftlik): {current_batch}")

                    # Har bir symbol uchun tahlil (faqat joriy batch)
                    for symbol in current_batch:
                        if not self._running:
                            break
                        self.run_cycle(symbol)

                    # Ochiq pozitsiyalarni boshqarish
                    self.manage_positions()
                    
                    # Virtual Stop Loss va Spread himoyasi
                    try:
                        self.orders.manage_virtual_sl()
                    except Exception as e:
                        logger.error(f"Virtual SL boshqarishda xatolik: {e}")
                    
                    # AI Review tekshiruvi (Har safar chaqiriladi, ichkarida o'zi 10 taga to'lganini tekshiradi)
                    try:
                        self.reviewer.check_and_run_review()
                    except Exception as e:
                        logger.error(f"AI Review loop xatosi: {e}")

                    # Cloud sync
                    try:
                        status_msg = "Bot is running"
                        if getattr(self.config, "auto_discover_symbols", True) and 'all_symbols' in locals() and 'current_batch' in locals():
                            status_msg = f"Avto-qidiruv yoniq. Ruxsat: {len(all_symbols)} ta juftlik. Joriy tahlil: {', '.join(current_batch)}"
                        closed_trades = self.sync.sync_all(self.mt5, is_running=True, message=status_msg)
                        if closed_trades:
                            for ct in closed_trades:
                                close_mechanism = classify_close_mechanism(
                                    ct.get("mt5_comment", ""),
                                    ct.get("mt5_reason")
                                )
                                self.decision_logger.update_outcome(ct["ticket"], ct["profit"], close_mechanism)
                                
                                # === YANGI: Kitob qoidalariga feedback qaytarish ===
                                try:
                                    insight_ids = self.decision_logger.get_insight_ids_for_ticket(ct["ticket"])
                                    if insight_ids:
                                        is_win = ct["profit"] > 0
                                        for iid in insight_ids:
                                            self.reviewer.ai_strategist.record_trade_result(
                                                insight_id=iid,
                                                success=is_win,
                                                pnl=ct["profit"],
                                                reason=f"Trade ticket {ct['ticket']} on {ct.get('symbol', 'N/A')}"
                                            )
                                        logger.info(f"🔄 Feedback: {len(insight_ids)} ta insight yangilandi ({'WIN' if is_win else 'LOSS'})")
                                except Exception as fe:
                                    logger.debug(f"Insight feedback xatolik: {fe}")
                                    
                            try:
                                export_blackbox_json()
                            except Exception as ex:
                                logger.error(f"Black box eksport xatosi: {ex}")
                                
                    except Exception as e:
                        logger.warning(f"Cloud sync xatolik: {e}")

                    # Database backup
                    try:
                        last_backup = self.state.get_trade_info("system_last_backup") or {}
                        last_backup_time = last_backup.get("time", 0)
                        import time
                        if time.time() - last_backup_time > 86400: # 24 soat
                            logger.info("24 soatlik ma'lumotlar bazasi zaxirasi boshlandi...")
                            from bot.utils.backup_databases import backup_databases
                            if backup_databases(self.config):
                                self.state.set_trade_info("system_last_backup", {"time": time.time()})
                    except Exception as e:
                        logger.error(f"Backup tekshirish jarayonida xatolik: {e}")

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


def run_cli() -> None:
    """Console entry point: `yuksalish` CLI command."""
    import logging, os, sys
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    project_root = os.environ.get("YUKSALISH_HOME") or os.getcwd()
    env_path = os.path.join(project_root, ".env")
    config_path = os.path.join(project_root, "config.json")
    if not os.path.exists(env_path):
        print(f"[yuksalish] .env topilmadi: {env_path}")
        print("YUKSALISH_HOME muhit o'zgaruvchisini loyiha katalogiga o'rnating.")
        sys.exit(1)
    bot = create_bot(env_path=env_path, config_path=config_path)
    bot.start()
