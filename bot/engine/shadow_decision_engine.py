import logging
import traceback
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

logger = logging.getLogger(__name__)

class ShadowDecisionEngine:
    """
    A production-grade autonomous decision engine that replaces external LLM API calls 
    with local ML predictions, integrating LSTM, RL Agent, and Voting System.
    """
    def __init__(self, predictor, rl_agent, config, merger_tracker=None):
        """
        Initialize the shadow decision engine.
        
        Args:
            predictor: PredictorEngine instance
            rl_agent: RLAgentRunner instance
            config: BotConfig instance
            merger_tracker: ShadowMergerTracker instance (optional)
        """
        self.predictor = predictor
        self.rl_agent = rl_agent
        self.config = config
        self.merger_tracker = merger_tracker

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

            # 8. Build Reasoning
            reasoning = f"Mahalliy AI modellari qarori: {direction}. "
            reasoning += f"LSTM ({lstm_dir}), RL ({rl_dir}), Ovoz ({voting_dir}). "
            reasoning += f"Ishonch: {confidence*100:.1f}%. "
            if closest_zone:
                reasoning += f"SMC zonasi topildi, ATR: {atr:.5f}."
            else:
                reasoning += f"SMC zonasi topilmadi, ATR asosida xavfsiz stop."

            audit_info = {
                "lstm_prediction": lstm_dir,
                "lstm_confidence": lstm_conf,
                "rl_action": rl_dir,
                "voting_direction": voting_dir,
                "voting_confidence": voting_conf,
                "merged_confidence": confidence,
                "atr": atr,
                "zone_used": closest_zone is not None
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
