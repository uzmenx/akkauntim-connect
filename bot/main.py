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
from bot.learning.trade_reviewer import TradeReviewer
from bot.sync.supabase_sync import SupabaseSync
from bot.sync.telegram_sync import TelegramSync

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

        # Execution
        self.risk = RiskManager(self.mt5, config)
        self.orders = OrderManager(self.mt5, self.state, config)
        self.closed_trades_count = 0

        # Sync
        self.sync = SupabaseSync(config)
        self.telegram = TelegramSync(config)
        
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
        # 2. TEXNIK TAHLIL — barcha strategiyalarni ishga tushirish
        # ============================================================
        smc_result = self._get_smc_full_analysis(df_major)
        smc_context = self._get_smc_data(df_major)
        
        # M15 va M5 timeframelarni qo'shish
        df_m15 = self._fetch_data(symbol, "M15", 150)
        df_m5 = self._fetch_data(symbol, "M5", 150)
        smc_m15 = self._get_smc_data(df_m15) if not df_m15.empty else {}
        smc_m5 = self._get_smc_data(df_m5) if not df_m5.empty else {}
        
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

        # ============================================================
        # 3. CONFLUENCE ENGINE — ball tizimi asosida savdo qarori
        # ============================================================
        adj = getattr(self, "last_adjustments", self.reviewer.get_active_adjustments())
        # ============================================================
        # AI AGENT AUTONOMOUS DECISION
        # ============================================================
        
        context = self.prompt_builder.build_context_summary(
            smc_result=smc_result or smc_context,
            patterns=pattern_result,
            news=news_result,
            voting={},
            memory_bank=memory_bank_text,
            wyckoff=wyckoff_result,
            sr_volume=sr_volume_result,
            auto_patterns=auto_patterns_result,
            kill_zones=kill_zones_result
        )
        context["pair"] = symbol
        context["timeframe"] = self.config.timeframe_major
        context["current_price"] = current_price
        context["smc_m15"] = smc_m15
        context["smc_m5"] = smc_m5
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

        prompt = self.prompt_builder.build_trading_prompt(context, symbol, current_price)
        logger.info(f"[{symbol}] AI Agent ga bozor tahlili yuborilmoqda...")
        
        ai_decision = self.ai.get_decision(prompt)
        if not ai_decision:
            logger.error(f"[{symbol}] AI javob bermadi — savdo bekor qilindi.")
            return

        final_decision = ai_decision.get("decision", "HOLD")
        reasoning_text = ai_decision.get("reasoning", "")
        logger.info(f"[{symbol}] AI Xulosasi: {final_decision} | Sabab: {reasoning_text[:200]}")

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
        risk_pct = ai_decision.get("risk_pct", 0.01)

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

        # Log to db
        ticket = order_info.get("ticket") if isinstance(order_info, dict) else None
        self.decision_logger.log(
            pair=symbol, timeframe=self.config.timeframe_major,
            context=context, prompt="AUTONOMOUS_AI",
            response=ai_decision, decision=final_decision,
            risk_pct=risk_pct, hash_val=self._get_state_hash(context),
            tokens={"input_tokens": self.ai.total_tokens_in, "output_tokens": self.ai.total_tokens_out},
            cost=self.ai.total_cost,
            ticket=ticket
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
                    except Exception as e:
                        logger.warning(f"Sozlamalarni yangilashda xatolik: {e}")

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
                                self.decision_logger.update_outcome(ct["ticket"], ct["profit"])
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
