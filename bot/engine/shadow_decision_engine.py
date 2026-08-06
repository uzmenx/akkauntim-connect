import logging
import traceback
import sqlite3
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    from bot.prediction.signal_merger import merge_signals, MergedSignal
except ImportError:
    # Create fallback classes if the original module is missing to prevent crashes
    class MergedSignal:
        def __init__(self, direction, confidence, agreement, lstm_weight_used, stat_weight_used, audit_trail):
            self.direction = direction
            self.confidence = confidence
            self.agreement = agreement
            self.lstm_weight_used = lstm_weight_used
            self.stat_weight_used = stat_weight_used
            self.audit_trail = audit_trail
            
    def merge_signals(*args, **kwargs):
        return MergedSignal("NEUTRAL", 0.0, False, 0.0, 0.0, {})

try:
    from bot.engine.confluence import compute_atr, _extract_fresh_zones
except ImportError:
    def compute_atr(df, period=14):
        return 0.0010
    
    def _extract_fresh_zones(smc_data, direction, current_price, atr, max_distance_atr=3.0):
        return []

try:
    from bot.prediction.adaptive_weights import AdaptiveWeightManager
except ImportError:
    AdaptiveWeightManager = None

try:
    from bot.learning.ai_memory import AIMemory
except ImportError:
    AIMemory = None

try:
    from bot.learning.economic_calendar import EconomicCalendarManager
except ImportError:
    EconomicCalendarManager = None

try:
    from bot.learning.pattern_memory import PatternMemoryBank
except ImportError:
    PatternMemoryBank = None

logger = logging.getLogger(__name__)

class ShadowDecisionEngine:
    """
    A production-grade autonomous decision engine that replaces external LLM API calls 
    with local ML predictions, integrating LSTM, RL Agent, and Voting System.
    """
    def __init__(self, predictor, rl_agent, config, merger_tracker=None, 
                 ai_memory=None, adaptive_weights=None,
                 economic_calendar=None, pattern_memory=None):
        """
        Initialize the shadow decision engine.
        
        Args:
            predictor: PredictorEngine instance
            rl_agent: RLAgentRunner instance
            config: BotConfig instance
            merger_tracker: ShadowMergerTracker instance (optional)
            ai_memory: AIMemory instance (optional) — tarixiy saboqlar uchun
            adaptive_weights: AdaptiveWeightManager instance (optional) — dinamik og'irliklar
            economic_calendar: EconomicCalendarManager instance (optional) — yangilik filteri
            pattern_memory: PatternMemoryBank instance (optional) — pattern xotirasi
        """
        self.predictor = predictor
        self.rl_agent = rl_agent
        self.config = config
        self.merger_tracker = merger_tracker
        
        # Reasoning Engine dependencies
        self.ai_memory = ai_memory
        self.adaptive_weights = adaptive_weights
        self.economic_calendar = economic_calendar
        self.pattern_memory = pattern_memory
        
        # Lazy-init if not provided
        if self.ai_memory is None and AIMemory is not None:
            try:
                self.ai_memory = AIMemory()
            except Exception as e:
                logger.warning(f"AIMemory lazy-init failed: {e}")
        
        if self.adaptive_weights is None and AdaptiveWeightManager is not None:
            try:
                self.adaptive_weights = AdaptiveWeightManager()
            except Exception as e:
                logger.warning(f"AdaptiveWeightManager lazy-init failed: {e}")

        if self.economic_calendar is None and EconomicCalendarManager is not None:
            try:
                self.economic_calendar = EconomicCalendarManager()
            except Exception as e:
                logger.warning(f"EconomicCalendarManager lazy-init failed: {e}")

        if self.pattern_memory is None and PatternMemoryBank is not None:
            try:
                self.pattern_memory = PatternMemoryBank()
            except Exception as e:
                logger.warning(f"PatternMemoryBank lazy-init failed: {e}")

    def _get_safe_fallback(self, reason: str, warnings: List[str] = None) -> Dict[str, Any]:
        """Return a default HOLD decision."""
        if warnings is None:
            warnings = []
        return {
            "decision": "HOLD",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_pct": 0.0,
            "confidence": 0.0,
            "reasoning": f"HOLD - {reason}",
            "warnings": warnings,
            "_source": "shadow_ai",
            "_audit": {}
        }

    def _get_pip_divisor(self, symbol: str) -> float:
        """Get pip divisor for forex precision."""
        if "JPY" in symbol.upper():
            return 100.0
        return 10000.0

    def _determine_rl_direction(self, rl_action: str) -> str:
        """Map RL action to standard direction."""
        rl_action = str(rl_action).upper()
        if rl_action in ("BUY", "SELL"):
            return rl_action
        return "NEUTRAL"

    def _get_memory_context(self, symbol: str, direction: str) -> Dict[str, Any]:
        """
        AIMemory dan shu symbol va yo'nalish uchun tarixiy kontekst olish.
        """
        context = {"lessons": "", "stats": {}, "similar_win_rate": None}
        if not self.ai_memory:
            return context
        try:
            # Eng muhim saboqlarni olish
            context["lessons"] = self.ai_memory.get_recent_lessons(limit=3)
            context["stats"] = self.ai_memory.get_statistics()
            
            # Shu symbol uchun strategiya vaznlari
            strat_weights = self.ai_memory.get_strategy_weights()
            if strat_weights:
                context["strategy_weights"] = strat_weights
        except Exception as e:
            logger.debug(f"Memory context olishda xatolik: {e}")
        return context

    def _build_reasoning_chain(self, direction: str, confidence: float,
                                lstm_dir: str, lstm_conf: float,
                                rl_dir: str, voting_dir: str, voting_conf: float,
                                entry_price: float, sl_price: float, tp_price: float,
                                atr: float, closest_zone: Optional[Dict],
                                symbol: str, timeframe: str,
                                adaptive_w: Optional[Dict] = None,
                                memory_ctx: Optional[Dict] = None) -> str:
        """
        Claude Agent kabi strukturali reasoning chain yaratish.
        Har bir qaror uchun dalillar zanjirini qurib beradi.
        """
        lines = []
        
        # [SIGNAL] — asosiy qaror
        lines.append(f"[SIGNAL] {direction} | Confidence: {confidence*100:.1f}%")
        
        # [EVIDENCE] — model dalillari
        evidence_parts = []
        evidence_parts.append(f"LSTM: {lstm_dir}({lstm_conf*100:.0f}%)")
        evidence_parts.append(f"RL: {rl_dir}")
        evidence_parts.append(f"Voting: {voting_dir}({voting_conf*100:.0f}%)")
        
        agree_count = sum(1 for d in [lstm_dir, rl_dir, voting_dir] if d == direction)
        agreement_str = f"{agree_count}/3 kelishdi" if agree_count >= 2 else f"{agree_count}/3 (ziddiyat!)"
        evidence_parts.append(f"[{agreement_str}]")
        lines.append(f"[EVIDENCE] {' | '.join(evidence_parts)}")
        
        # [CONTEXT] — bozor konteksti
        context_parts = []
        if closest_zone:
            z_top = closest_zone.get('top', 0)
            z_bot = closest_zone.get('bottom', 0)
            zone_type = 'Demand' if direction == 'BUY' else 'Supply'
            context_parts.append(f"SMC {zone_type} Zone [{z_bot:.5f}-{z_top:.5f}]")
        else:
            context_parts.append("SMC zonasi topilmadi")
        context_parts.append(f"ATR: {atr:.5f}")
        context_parts.append(f"{symbol} {timeframe}")
        lines.append(f"[CONTEXT] {' | '.join(context_parts)}")
        
        # [MEMORY] — tarixiy xotiradan ma'lumot
        if memory_ctx:
            mem_parts = []
            stats = memory_ctx.get("stats", {})
            total_lessons = stats.get("total_lessons", 0)
            if total_lessons > 0:
                mem_parts.append(f"{total_lessons} ta saboq xotirada")
            
            lessons_text = memory_ctx.get("lessons", "")
            if lessons_text and lessons_text != "AI xotirasi hali bo'sh. Savdolar va kitoblardan saboqlar to'planishi kerak.":
                # Birinchi saboqni qisqacha ko'rsatish
                first_lesson = lessons_text.split('\n')[0][:80]
                mem_parts.append(f"Eng muhim: {first_lesson}")
            
            if mem_parts:
                lines.append(f"[MEMORY] {' | '.join(mem_parts)}")
        
        # [RISK] — risk parametrlari
        pip_div = self._get_pip_divisor(symbol)
        sl_pips = abs(entry_price - sl_price) * pip_div
        tp_pips = abs(tp_price - entry_price) * pip_div
        rr_ratio = tp_pips / max(sl_pips, 0.1)
        risk_pct = getattr(self.config, 'risk_per_trade', 0.02) * 100
        lines.append(f"[RISK] SL: {sl_pips:.1f} pip | TP: {tp_pips:.1f} pip | RR: 1:{rr_ratio:.1f} | Risk: {risk_pct:.1f}%")
        
        # [WEIGHT] — adaptive weights
        if adaptive_w:
            w_parts = [f"LSTM:{adaptive_w.get('lstm', 0.35)*100:.0f}%",
                       f"Voting:{adaptive_w.get('voting', 0.40)*100:.0f}%",
                       f"RL:{adaptive_w.get('rl', 0.25)*100:.0f}%"]
            lines.append(f"[WEIGHT] {' '.join(w_parts)} (adaptive)")
        
        return "\n".join(lines)

    def _self_critique(self, direction: str, confidence: float,
                        lstm_dir: str, rl_dir: str, voting_dir: str,
                        atr: float, current_price: float, symbol: str,
                        timeframe: str, closest_zone: Optional[Dict],
                        entry_price: float, sl_price: float) -> Dict[str, Any]:
        """
        Self-Critique Loop — qarorni chiqarishdan OLDIN tekshiradi.
        "Nima xato bo'lishi mumkin?" deb o'zini tanqid qiladi.
        
        Returns:
            {
                'approved': bool,
                'concerns': list[str],
                'adjusted_confidence': float,
                'critique_reasoning': str
            }
        """
        concerns = []
        penalty = 0.0

        # 1. VOLATILLIK TEKSHIRUVI — ATR juda baland bo'lsa xavfli
        pip_div = self._get_pip_divisor(symbol)
        atr_pips = atr * pip_div
        if atr_pips > 50:  # 50 pipdan ko'p ATR = juda volatil
            concerns.append(f"Yuqori volatillik: ATR {atr_pips:.1f} pip (>50)")
            penalty += 0.08
        elif atr_pips > 30:
            concerns.append(f"O'rta-yuqori volatillik: ATR {atr_pips:.1f} pip")
            penalty += 0.04

        # 2. SIGNAL ZIDDIYAT — modellar kelishmasa
        agree_count = sum(1 for d in [lstm_dir, rl_dir, voting_dir] if d == direction)
        if agree_count < 3:
            disagree_models = []
            if lstm_dir != direction: disagree_models.append(f"LSTM={lstm_dir}")
            if rl_dir != direction: disagree_models.append(f"RL={rl_dir}")
            if voting_dir != direction: disagree_models.append(f"Voting={voting_dir}")
            concerns.append(f"Ziddiyat: {', '.join(disagree_models)}")
            penalty += 0.05 * (3 - agree_count)

        # 3. SL MASOFASI — juda kichik yoki juda katta bo'lsa
        sl_dist_pips = abs(entry_price - sl_price) * pip_div
        if sl_dist_pips < 5:
            concerns.append(f"SL juda yaqin: {sl_dist_pips:.1f} pip (<5). Noise bilan yopilishi mumkin.")
            penalty += 0.06
        elif sl_dist_pips > 80:
            concerns.append(f"SL juda uzoq: {sl_dist_pips:.1f} pip (>80). Risk/Reward yomon.")
            penalty += 0.05

        # 4. SMC ZONA TOPILMADIMI
        if closest_zone is None:
            concerns.append("SMC support/demand zonasi topilmadi — sof texnik signal.")
            penalty += 0.03

        # 5. ISHONCH JUDA PAST
        if confidence < 0.60:
            concerns.append(f"Ishonch past: {confidence*100:.1f}% (<60%)")
            penalty += 0.04

        # 6. ECONOMIC CALENDAR — yangilik tekshiruvi
        if self.economic_calendar:
            try:
                calendar_check = self.economic_calendar.is_safe_to_trade(symbol)
                if not calendar_check.get('safe', True):
                    reason = calendar_check.get('reason', 'Yangilik yaqinlashmoqda')
                    concerns.append(f"📅 {reason}")
                    penalty += 0.15  # Yangiliklar oldidan katta penalty
            except Exception as e:
                logger.debug(f"Economic calendar tekshiruvda xatolik: {e}")

        # 7. PATTERN MEMORY — o'xshash patternlar LOSS bo'lganmi
        # (Bu yerda faqat salbiy signalni tekshiramiz; ijobiy boost decide() da)
        if self.pattern_memory and hasattr(self, '_last_candles_for_critique'):
            try:
                adj = self.pattern_memory.get_confidence_adjustment(
                    symbol=symbol, direction=direction,
                    candles=self._last_candles_for_critique,
                    atr=atr
                )
                if adj.get('adjustment', 0) < -0.05:
                    concerns.append(f"⚠️ O'xshash patternlar ko'pincha LOSS: {adj.get('reasoning', '')}")
                    penalty += abs(adj['adjustment'])
            except Exception as e:
                logger.debug(f"Pattern memory tekshiruvda xatolik: {e}")

        # YAKUNIY QAROR
        adjusted_confidence = max(0.0, confidence - penalty)
        approved = len(concerns) < 3 and adjusted_confidence >= 0.45

        critique_parts = []
        if concerns:
            critique_parts.append(f"[CRITIQUE] {len(concerns)} ta muammo topildi:")
            for i, c in enumerate(concerns, 1):
                critique_parts.append(f"  {i}. {c}")
            if not approved:
                critique_parts.append(f"[VERDICT] ❌ RAD ETILDI — confidence {adjusted_confidence*100:.1f}% ga tushdi")
            else:
                critique_parts.append(f"[VERDICT] ✅ TASDIQLANDI — confidence {confidence*100:.1f}% → {adjusted_confidence*100:.1f}%")
        else:
            critique_parts.append("[CRITIQUE] Muammo topilmadi. Signal sifati yuqori.")
            critique_parts.append(f"[VERDICT] ✅ TO'LIQ TASDIQLANDI")

        return {
            'approved': approved,
            'concerns': concerns,
            'adjusted_confidence': adjusted_confidence,
            'critique_reasoning': "\n".join(critique_parts),
            'penalty': penalty
        }

    def decide(self, recent_candles: List[Dict[str, Any]], obs_data: List[float], 
               voting_result: Dict[str, Any], smc_context: Any, 
               df_major: Any, current_price: float, symbol: str, timeframe: str = "H1") -> Dict[str, Any]:
        """
        Produce a trading decision matching AIClient format.
        """
        warnings = []
        try:
            # 1. Validate Inputs
            if not recent_candles or df_major is None or df_major.empty:
                warnings.append("No candles or dataframe provided.")
                return self._get_safe_fallback("Invalid input data", warnings)
                
            if current_price is None or current_price <= 0:
                warnings.append("Invalid current price.")
                return self._get_safe_fallback("Invalid current price", warnings)

            # 2. Get LSTM Prediction
            lstm_prediction = {"prediction": "HOLD", "confidence": 0.0}
            try:
                if self.predictor:
                    lstm_prediction = self.predictor.predict(recent_candles)
            except Exception as e:
                logger.error(f"ShadowEngine: Predictor error - {e}")
                warnings.append("LSTM Predictor failed.")
            
            lstm_dir = str(lstm_prediction.get("prediction", "HOLD")).upper()
            if lstm_dir == "UP":
                lstm_dir = "BUY"
            elif lstm_dir == "DOWN":
                lstm_dir = "SELL"
            else:
                lstm_dir = "NEUTRAL"
            lstm_conf = float(lstm_prediction.get("confidence", 0.0)) / 100.0

            # 3. Get RL Agent Action
            rl_action = "HOLD"
            try:
                if self.rl_agent and obs_data:
                    rl_action = self.rl_agent.predict_action(obs_data)
            except Exception as e:
                logger.error(f"ShadowEngine: RL Agent error - {e}")
                warnings.append("RL Agent failed.")
            
            rl_dir = self._determine_rl_direction(rl_action)
            
            # 4. Get Voting Stats
            voting_dir = str(voting_result.get("signal", "HOLD")).upper()
            if voting_dir not in ("BUY", "SELL"):
                voting_dir = "NEUTRAL"
            voting_conf = float(voting_result.get("score", 0.0)) / 100.0

            # 5. Get Shadow Stats
            shadow_win_rate = 0.5
            shadow_trade_count = 0
            if self.merger_tracker:
                try:
                    stats = self.merger_tracker.get_shadow_lstm_stats(symbol)
                    shadow_win_rate = stats.get("win_rate", 0.5)
                    shadow_trade_count = stats.get("trade_count", 0)
                except Exception as e:
                    logger.error(f"ShadowEngine: Merger tracker error - {e}")

            # 6. Merge Signals
            # For stat_direction and stat_confidence we'll use RL as proxy here, or 
            # if we have a dedicated statistical model we'd pass it. We use rl_dir as stat_direction.
            try:
                merged = merge_signals(
                    symbol=symbol,
                    timeframe=timeframe,
                    voting_direction=voting_dir,
                    voting_confidence=voting_conf,
                    lstm_direction=lstm_dir,
                    lstm_confidence=lstm_conf,
                    shadow_win_rate=shadow_win_rate,
                    shadow_trade_count=shadow_trade_count,
                    stat_direction=rl_dir,
                    stat_confidence=0.5, # Default RL confidence proxy
                    stat_weight_base=1.0
                )
            except Exception as e:
                logger.error(f"ShadowEngine: Merge signals error - {e}")
                return self._get_safe_fallback("Signal merge error", warnings)
            
            direction = merged.direction
            confidence = merged.confidence
            
            # Check agreement and minimum confidence
            min_confidence = getattr(self.config, 'shadow_min_confidence', 0.55)
            
            if direction == "NEUTRAL" or confidence < min_confidence:
                reason = f"Ishonch past ({confidence:.2f} < {min_confidence})" if direction != "NEUTRAL" else "Signal topilmadi"
                return self._get_safe_fallback(reason, warnings)
                
            # Agreement check: Need at least 2 out of 3 (Voting, LSTM, RL)
            agree_count = sum(1 for d in [voting_dir, lstm_dir, rl_dir] if d == direction)
            if agree_count < 2:
                warnings.append(f"Qarama-qarshilik. Ovoz: {voting_dir}, LSTM: {lstm_dir}, RL: {rl_dir}")
                return self._get_safe_fallback("Modellar kelisha olmadi", warnings)

            # 6.5. Pattern Memory — confidence boost
            pattern_adj = None
            if self.pattern_memory and recent_candles:
                try:
                    atr_for_pattern = 0.0
                    try:
                        atr_for_pattern = compute_atr(df_major, period=14)
                    except Exception:
                        atr_for_pattern = current_price * 0.0010
                    
                    pattern_adj = self.pattern_memory.get_confidence_adjustment(
                        symbol=symbol, direction=direction,
                        candles=recent_candles, atr=max(atr_for_pattern, 1e-10)
                    )
                    if pattern_adj and pattern_adj.get('adjustment', 0) != 0:
                        old_conf = confidence
                        confidence = max(0.0, min(1.0, confidence + pattern_adj['adjustment']))
                        logger.info(f"Pattern Memory: confidence {old_conf:.3f} → {confidence:.3f} ({pattern_adj.get('reasoning', '')})")
                except Exception as e:
                    logger.debug(f"Pattern memory adjustment xatolik: {e}")

            # 7. Smart Trade Params (SMC Zone Logic)
            atr = 0.0
            try:
                atr = compute_atr(df_major, period=14)
            except Exception as e:
                logger.error(f"ShadowEngine: ATR compute error - {e}")

            if atr <= 0:
                atr = current_price * 0.0010  # Fallback 10 pips approx

            smc_for_zones = smc_context if isinstance(smc_context, dict) else {}
            zone_direction = "demand" if direction == "BUY" else "supply"
            target_zones = []
            try:
                target_zones = _extract_fresh_zones(
                    smc_for_zones, zone_direction, current_price, atr, max_distance_atr=3.0
                )
            except Exception as e:
                logger.error(f"ShadowEngine: Zone extraction error - {e}")
            
            # Find closest zone
            closest_zone = None
            min_dist = float('inf')
            
            for zone in target_zones:
                if not isinstance(zone, dict):
                    continue
                z_top = zone.get("top", 0)
                z_bot = zone.get("bottom", 0)
                if z_top <= 0 or z_bot <= 0:
                    continue
                    
                z_mid = (z_top + z_bot) / 2.0
                dist = abs(current_price - z_mid)
                if dist < min_dist:
                    min_dist = dist
                    closest_zone = zone
                    
            entry_price = current_price
            order_type = direction
            sl_price = 0.0
            tp_price = 0.0
            
            if closest_zone:
                z_top = closest_zone.get("top", 0)
                z_bot = closest_zone.get("bottom", 0)
                
                # Zone boundary depending on direction
                zone_boundary = z_top if direction == "BUY" else z_bot
                zone_sl_boundary = z_bot if direction == "BUY" else z_top
                
                dist_to_zone = abs(current_price - zone_boundary)
                
                if dist_to_zone > 0.5 * atr:
                    order_type = f"LIMIT_{direction}"
                    entry_price = zone_boundary
                else:
                    order_type = direction
                    entry_price = current_price
                    
                if direction == "BUY":
                    sl_price = zone_sl_boundary - (0.5 * atr)
                else:
                    sl_price = zone_sl_boundary + (0.5 * atr)
                    
            else:
                # Fallback if no fresh zones found
                if direction == "BUY":
                    sl_price = current_price - (1.5 * atr)
                else:
                    sl_price = current_price + (1.5 * atr)
                    
            # Set TP based on 1:2 RRR
            sl_dist = abs(entry_price - sl_price)
            if direction == "BUY":
                tp_price = entry_price + (2.0 * sl_dist)
            else:
                tp_price = entry_price - (2.0 * sl_dist)
                
            # Format precision
            entry_price = round(entry_price, 5)
            sl_price = round(sl_price, 5)
            tp_price = round(tp_price, 5)

            # 8. Adaptive Weights olish
            adaptive_w = None
            if self.adaptive_weights:
                try:
                    adaptive_w = self.adaptive_weights.get_weights(symbol, timeframe)
                except Exception as e:
                    logger.debug(f"Adaptive weights olishda xatolik: {e}")

            # 9. Memory Context olish
            memory_ctx = self._get_memory_context(symbol, direction)

            # 10. SELF-CRITIQUE LOOP — qarorni tekshirish
            self._last_candles_for_critique = recent_candles  # pattern memory uchun
            critique = self._self_critique(
                direction=direction, confidence=confidence,
                lstm_dir=lstm_dir, rl_dir=rl_dir, voting_dir=voting_dir,
                atr=atr, current_price=current_price, symbol=symbol,
                timeframe=timeframe, closest_zone=closest_zone,
                entry_price=entry_price, sl_price=sl_price
            )

            if not critique['approved']:
                warnings.extend(critique['concerns'])
                fallback = self._get_safe_fallback(
                    f"Self-Critique rad etdi ({len(critique['concerns'])} muammo)", 
                    warnings
                )
                fallback['_audit']['critique'] = critique
                fallback['reasoning'] = critique['critique_reasoning']
                return fallback

            # Critique tasdiqladi — adjusted confidence ishlatamiz
            confidence = critique['adjusted_confidence']

            # 11. Build Reasoning Chain (Claude Agent uslubida)
            reasoning = self._build_reasoning_chain(
                direction=direction, confidence=confidence,
                lstm_dir=lstm_dir, lstm_conf=lstm_conf,
                rl_dir=rl_dir, voting_dir=voting_dir, voting_conf=voting_conf,
                entry_price=entry_price, sl_price=sl_price, tp_price=tp_price,
                atr=atr, closest_zone=closest_zone,
                symbol=symbol, timeframe=timeframe,
                adaptive_w=adaptive_w, memory_ctx=memory_ctx
            )
            # Self-Critique natijasini reasoningga qo'shish
            reasoning += "\n" + critique['critique_reasoning']

            # Pattern Memory natijasini qo'shish
            if pattern_adj and pattern_adj.get('match_count', 0) > 0:
                reasoning += f"\n[PATTERN] {pattern_adj.get('reasoning', '')} (O'xshash: {pattern_adj['match_count']})"

            audit_info = {
                "lstm_prediction": lstm_dir,
                "lstm_confidence": lstm_conf,
                "rl_action": rl_dir,
                "voting_direction": voting_dir,
                "voting_confidence": voting_conf,
                "merged_confidence": confidence,
                "atr": atr,
                "zone_used": closest_zone is not None,
                "adaptive_weights": adaptive_w,
                "memory_lessons_count": memory_ctx.get("stats", {}).get("total_lessons", 0) if memory_ctx else 0,
                "reasoning_version": "v3_critique",
                "critique": {
                    "approved": critique['approved'],
                    "concerns_count": len(critique['concerns']),
                    "penalty": critique.get('penalty', 0),
                    "adjusted_confidence": critique['adjusted_confidence']
                },
                "pattern_memory": {
                    "adjustment": pattern_adj.get('adjustment', 0) if pattern_adj else 0,
                    "match_count": pattern_adj.get('match_count', 0) if pattern_adj else 0
                },
                "pattern_data_for_reviewer": {
                    "recent_candles": recent_candles[-5:] if recent_candles else [],
                    "atr": atr,
                    "smc_zone_type": "Demand" if direction == "BUY" else ("Supply" if direction == "SELL" else None)
                }
            }
            if hasattr(merged, 'audit_trail'):
                audit_info["merged_audit"] = merged.audit_trail

            return {
                "decision": order_type,
                "entry_price": entry_price,
                "stop_loss": sl_price,
                "take_profit": tp_price,
                "risk_pct": getattr(self.config, 'risk_per_trade', 0.02),
                "confidence": confidence,
                "reasoning": reasoning,
                "warnings": warnings,
                "_source": "shadow_ai",
                "_audit": audit_info
            }
            
        except Exception as e:
            logger.error(f"ShadowEngine: Critical error in decide() - {e}\n{traceback.format_exc()}")
            return self._get_safe_fallback("Kutilmagan xatolik yuz berdi", warnings)
