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

        # AI Trade Reviewer (Learning)
        from bot.engine.trade_reviewer import TradeReviewer
        self.reviewer = TradeReviewer(self.ai, self.mt5, config)
        self.closed_trades_count = 0

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
        pattern_result = self._get_harmonic_patterns(df_major)
        news_result = self._get_news_context(symbol)
        memory_bank_text = self._get_memory_bank_alerts(symbol, current_price)

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
        adj = getattr(self, "last_adjustments", self.reviewer.get_latest_adjustments())
        min_conf = adj.get("min_confluence_score", 20)
        reason_weights = adj.get("reason_weights", {})
        
        conf_cfg = {
            "score_threshold_ai": min_conf,
            "score_threshold_execute": min_conf + 10  # Masalan, 20 ai, 30 execute
        }
        conf_cfg.update(reason_weights)

        from bot.engine.confluence import calculate_confluence

        # M5 ma'lumotlarini olish (MTF tasdiq uchun)
        df_minor = self._fetch_data(symbol, self.config.timeframe_minor, 50)
        smc_minor = self._get_smc_data(df_minor) if not df_minor.empty else {}

        confluence = calculate_confluence(
            smc_data=smc_result or {},
            harmonic_data=pattern_result or {},
            news_data=news_result,
            df=df_major,
            current_price=current_price,
            config=conf_cfg,
            wyckoff_data=wyckoff_result,
            sr_volume_data=sr_volume_result,
            auto_pattern_data=auto_patterns_result,
            kill_zones_data=kill_zones_result,
            df_minor=df_minor,
            smc_minor=smc_minor,
        )

        logger.info(
            f"[{symbol}] Confluence: {confluence.signal} | "
            f"Score: {confluence.score}/200 | "
            f"Decision: {confluence.decision} | "
            f"Risk: {confluence.risk_pct:.1%} | "
            f"Breakdown: {confluence.score_breakdown}"
        )

        if confluence.warnings:
            for w in confluence.warnings:
                logger.warning(f"[{symbol}] ⚠️ {w}")

        # ============================================================
        # 3.1. QAROR TEKSHIRUVI — REJECT bo'lsa to'xtatish
        # ============================================================
        if confluence.decision == "REJECT" or confluence.signal == "HOLD":
            logger.info(
                f"[{symbol}] Confluence REJECT (score={confluence.score}) — "
                f"savdo qilinmaydi. Sabab: {confluence.reasoning}"
            )
            return

        # Yo'nalish va risk o'zgaruvchilari
        conf_direction = confluence.signal      # "BUY" | "SELL"
        conf_risk = confluence.risk_pct          # 0.01 - 0.04
        conf_score = confluence.score

        # MTF tekshiruvi endi Confluence ichida hisoblanadi (mtf_weight orqali)

        # ============================================================
        # 3.2. Eski voting natijalarini ham oldindan tayyorlash
        #      (AI prompt va loglar uchun kerak)
        # ============================================================
        smc_signal = self._extract_signal(smc_context, "smc")
        pattern_signal = self._extract_signal(pattern_result, "pattern")
        news_signal = self._extract_signal(news_result, "news")
        wyckoff_signal = self._extract_signal(wyckoff_result, "wyckoff")
        sr_volume_signal = self._extract_signal(sr_volume_result, "sr_volume")
        auto_patterns_signal = self._extract_signal(auto_patterns_result, "auto_patterns")
        kill_zones_signal = self._extract_signal(kill_zones_result, "kill_zones")
        
        voting_result = aggregate_signals(
            smc_signal, pattern_signal, news_signal,
            wyckoff_signal, sr_volume_signal, auto_patterns_signal, kill_zones_signal,
            self.config
        )

        # Kontekst (AI prompt va log uchun)
        context = self.prompt_builder.build_context_summary(
            smc_result=smc_result or smc_context,
            patterns=pattern_result,
            news=news_result,
            voting=voting_result,
            memory_bank=memory_bank_text,
            wyckoff=wyckoff_result,
            sr_volume=sr_volume_result,
            auto_patterns=auto_patterns_result,
            kill_zones=kill_zones_result
        )
        context["pair"] = symbol
        context["timeframe"] = self.config.timeframe_major
        context["current_price"] = current_price
        context["confluence"] = confluence.to_dict()

        # ============================================================
        # 4. DINAMIK SL/TP HISOBLASH (SMC/Harmonic/ATR asosida)
        # ============================================================
        from bot.engine.confluence import compute_atr
        atr = compute_atr(df_major, period=14)

        if "XAU" in symbol or "GOLD" in symbol:
            pip_divisor = 0.1  # 1 pip = 0.1 (gold uchun)
        elif "JPY" in symbol:
            pip_divisor = 0.01  # JPY juftliklari uchun
        else:
            pip_divisor = 0.0001  # Standard forex juftliklari uchun

        atr_pips = atr / pip_divisor if pip_divisor > 0 else 30

        from bot.engine.dynamic_levels import calculate_dynamic_levels
        dynamic_result = calculate_dynamic_levels(
            signal=conf_direction,
            current_price=current_price,
            smc_data=smc_result or smc_context or {},
            harmonic_data=pattern_result or {},
            atr_pips=atr_pips,
            pip_divisor=pip_divisor
        )

        if not dynamic_result["is_valid"]:
            logger.info(f"[{symbol}] FAILED: Dynamic SL/TP rad etdi. Sabab: {dynamic_result['reason']}")
            return

        # AI Adjustments
        adj = getattr(self, "last_adjustments", self.reviewer.get_latest_adjustments())
        sl_mult = adj.get("sl_multiplier", 1.0)
        tp_mult = adj.get("tp_multiplier", 1.0)
        
        dynamic_sl = round(dynamic_result["sl_pips"] * sl_mult, 1)
        dynamic_tp = round(dynamic_result["tp2_pips"] * tp_mult, 1) # Asosiy order TP eng uzoq (TP2) ga qo'yiladi
        dynamic_tp1 = round(dynamic_result["tp1_pips"] * tp_mult, 1)
        
        # Sessiya filtri
        session_filter = adj.get("session_filter", [])
        if session_filter and kill_zones_result and kill_zones_result.get("active_sessions"):
            actives = kill_zones_result.get("active_sessions")
            if not any(s in session_filter for s in actives):
                logger.info(f"[{symbol}] AI Adjustment (session_filter) rad etdi. Faol: {actives}, Ruxsat: {session_filter}")
                return

        logger.info(
            f"[{symbol}] Dinamik SL/TP: SL={dynamic_sl} pip, TP1={dynamic_tp1} pip, TP2={dynamic_tp} pip "
            f"(ATR={atr_pips:.1f} pip, R:R=1:{dynamic_result['rr']})"
        )

        # ============================================================
        # 5. EXECUTE yoki AI_DECIDE
        # ============================================================
        if confluence.decision == "EXECUTE":
            # === Score 70+ — Avtomatik EXECUTE ===
            logger.info(
                f"[{symbol}] ✅ Confluence EXECUTE (score={conf_score}) — "
                f"Avtomatik savdo!"
            )

            ai_decision = {
                "final_decision": "EXECUTE",
                "direction": conf_direction,
                "confidence": min(95, 50 + conf_score),
                "entry_price": None,
                "stop_loss_pips": dynamic_sl,
                "take_profit_pips": dynamic_tp,
                "take_profit_1_pips": dynamic_tp1,
                "risk_pct": conf_risk,
                "reasoning": (
                    f"Confluence EXECUTE (score={conf_score}/140): "
                    f"{confluence.reasoning}"
                ),
                "warnings": confluence.warnings,
            }

            # Logga yozish
            self.decision_logger.log(
                pair=symbol, timeframe=self.config.timeframe_major,
                context=context, prompt="CONFLUENCE_EXECUTE",
                response=ai_decision, decision="EXECUTE",
                risk_pct=conf_risk, hash_val=self._get_state_hash(context),
                tokens={"input_tokens": 0, "output_tokens": 0}, cost=0.0
            )

        elif confluence.decision in ["AI_DECIDE", "PENDING_LIMIT"]:
            # === Score 50-69 yoki PENDING_LIMIT — AI tasdiq kerak ===
            if getattr(self.config, 'ai_enabled', True) is False:
                logger.info(
                    f"[{symbol}] ⚠️ AI o'chirilgan va qaror: {confluence.decision}. Savdo rad etildi."
                )
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
                    risk_pct=conf_risk, hash_val=current_hash,
                    tokens={"input_tokens": 0, "output_tokens": 0}, cost=0.0
                )
                ai_decision = cached
            else:
                # AI qaror — Confluence ma'lumotlarini prompt ga qo'shish
                prompt = self.prompt_builder.build_trading_prompt(context, symbol, current_price)
                if confluence.decision == "PENDING_LIMIT":
                    prompt += f"\n\n🚨 PENDING_LIMIT SO'ROVI 🚨\nJoriy narx optimal zonadan uzoq. Tavsiya etilgan Limit Entry: {confluence.suggested_limit_entry}.\nIltimos, ushbu zonaga narx qaytishi ehtimolini hisoblang. Agar tasdiqlasangiz, 'final_decision' ni 'PENDING_LIMIT' deb, 'entry_price' ni {confluence.suggested_limit_entry} qilib belgilang."

                logger.info(
                    f"[{symbol}] Claude ga so'rov yuborilmoqda "
                    f"(confluence score={conf_score}, decision={confluence.decision})..."
                )

                ai_decision = self.ai.get_decision(prompt)
                if not ai_decision:
                    logger.error(f"[{symbol}] AI javob bermadi — savdo bekor qilindi.")
                    return

                # AI Confluence yo'nalishi va riskni o'zgartirmasligi kerak
                if ai_decision.get('direction') != conf_direction:
                    ai_decision['final_decision'] = "REJECT"
                    ai_decision['warnings'] = ai_decision.get('warnings', []) + [
                        "Claude direction ni o'zgartirishga urindi — savdo rad etildi."
                    ]
                    ai_decision['direction'] = conf_direction

                # AI risk ni Confluence dan oladi
                ai_decision['risk_pct'] = conf_risk

                # AI SL/TP ni tavsiya qilishi mumkin, lekin asosiy chegaralar saqlanadi
                ai_sl = ai_decision.get("stop_loss_pips", dynamic_sl)
                ai_tp = ai_decision.get("take_profit_pips", dynamic_tp)

                # AI ning SL/TP si mantiqiy bo'lsa qabul qilish
                if isinstance(ai_sl, (int, float)) and ai_sl > 0:
                    # AI SL dynamic_sl dan 50% dan ko'p farq qilmasligi kerak
                    if abs(ai_sl - dynamic_sl) / dynamic_sl <= 0.5:
                        ai_decision["stop_loss_pips"] = round(ai_sl)
                    else:
                        ai_decision["stop_loss_pips"] = dynamic_sl
                else:
                    ai_decision["stop_loss_pips"] = dynamic_sl

                if isinstance(ai_tp, (int, float)) and ai_tp > 0:
                    if abs(ai_tp - dynamic_tp) / dynamic_tp <= 0.5:
                        ai_decision["take_profit_pips"] = round(ai_tp)
                    else:
                        ai_decision["take_profit_pips"] = dynamic_tp
                else:
                    ai_decision["take_profit_pips"] = dynamic_tp

                # R:R tekshiruvi (1:1.5 minimal)
                final_sl = ai_decision["stop_loss_pips"]
                final_tp = ai_decision["take_profit_pips"]
                if final_tp < final_sl * 1.5:
                    ai_decision["take_profit_pips"] = round(final_sl * 1.5)

                # Logga yozish
                self.decision_logger.log(
                    pair=symbol, timeframe=self.config.timeframe_major,
                    context=context, prompt=prompt,
                    response=ai_decision,
                    decision=ai_decision.get("final_decision", "REJECT"),
                    risk_pct=conf_risk, hash_val=current_hash,
                    tokens={
                        "input_tokens": self.ai.total_tokens_in,
                        "output_tokens": self.ai.total_tokens_out
                    },
                    cost=self.ai.total_cost
                )

                # Supabase ga AI signal loglash
                try:
                    self.sync.log_ai_signal(
                        symbol=symbol,
                        signal=conf_direction,
                        confidence=int(ai_decision.get("confidence", 0)),
                        reasoning=ai_decision.get("reasoning", "")
                    )
                    self.sync.log_claude_cost(self.ai.total_cost)
                except Exception as e:
                    logger.warning(f"Supabase sync xatolik: {e}")

        else:
            # Bu holat yuz bermasligi kerak (REJECT yuqorida qaytarilgan)
            logger.info(f"[{symbol}] Noma'lum confluence decision: {confluence.decision}")
            return

        # ============================================================
        # 6. EXECUTE yoki PENDING_LIMIT TEKSHIRUVI
        # ============================================================
        final = ai_decision.get("final_decision", "REJECT")
        logger.info(
            f"[{symbol}] Yakuniy qaror: {final} | "
            f"Sabab: {ai_decision.get('reasoning', '')[:200]}"
        )

        if final not in ["EXECUTE", "PENDING_LIMIT"]:
            logger.info(f"[{symbol}] {final} — savdo qilinmaydi.")
            return

        # ============================================================
        # 7. RISK VALIDATSIYASI
        # ============================================================
        sl_pips = ai_decision.get("stop_loss_pips", dynamic_sl)
        tp_pips = ai_decision.get("take_profit_pips", dynamic_tp)
        confidence = ai_decision.get("confidence", 0)

        approved, msg, lot = self.risk.validate_trade(
            symbol=symbol,
            signal=conf_direction,
            confidence=confidence,
            stop_loss_pips=sl_pips,
            risk_pct=conf_risk
        )
        logger.info(f"[{symbol}] Risk natijasi: {msg} (Lot: {lot})")

        if not approved or lot is None:
            logger.info(f"[{symbol}] Risk manager rad etdi: {msg}")
            return

        # ============================================================
        # 8. ORDER OCHISH
        # ============================================================
        entry_price = ai_decision.get("entry_price")
        if entry_price == "null" or entry_price is None:
            entry_price = None
        else:
            try:
                entry_price = float(entry_price)
            except (ValueError, TypeError):
                entry_price = None

        # Signal turini aniqlash (BUY, SELL, BUY_LIMIT, etc.)
        order_signal = conf_direction
        if entry_price is not None:
            if conf_direction == "BUY":
                order_signal = "BUY_LIMIT"
            elif conf_direction == "SELL":
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
            logger.info(
                f"✅ [{symbol}] Order ochildi! Ticket: {order_info.get('ticket', 'N/A')} | "
                f"Confluence: {conf_score}/140 | SL: {sl_pips} | TP: {tp_pips} | "
                f"Risk: {conf_risk:.1%} | R:R=1:{tp_pips/sl_pips:.1f}"
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

                    # Har bir symbol uchun tahlil
                    for symbol in self.config.trading_symbols:
                        if not self._running:
                            break
                        self.run_cycle(symbol)

                    # Ochiq pozitsiyalarni boshqarish
                    self.manage_positions()
                    
                    # AI Review tekshiruvi
                    try:
                        import datetime
                        import MetaTrader5 as mt5
                        now = datetime.datetime.now()
                        start_time = now - datetime.timedelta(days=60)
                        deals = self.mt5.history_deals_get(start_time, now)
                        if deals:
                            closed_count = sum(1 for d in deals if d.entry == mt5.DEAL_ENTRY_OUT)
                            if closed_count > self.closed_trades_count:
                                self.closed_trades_count = closed_count
                                review_type = self.reviewer.should_review(self.closed_trades_count)
                                if review_type:
                                    logger.info(f"Yangi yopilgan savdolar yetarli ({self.closed_trades_count}). AI Review ({review_type}) boshlanmoqda...")
                                    self.reviewer.perform_review(review_type=review_type)
                                    # Yangi adjustments'larni qayta o'qish mumkin
                                    self.last_adjustments = self.reviewer.get_latest_adjustments()
                    except Exception as e:
                        logger.error(f"AI Review loop xatosi: {e}")

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
