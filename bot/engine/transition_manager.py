"""
Transition Manager Module
Handles switching between API, HYBRID, and SHADOW AI modes for the trading bot.
Ensures fault-tolerant operation and smooth fallback mechanisms.
"""

import threading
import logging
from enum import Enum
from typing import Dict, Any, Tuple, Optional
from collections import deque

logger = logging.getLogger(__name__)

class AIMode(Enum):
    API = "api"       # Tashqi LLM API faqat
    HYBRID = "hybrid" # API + Shadow parallel (taqqoslash)
    SHADOW = "shadow" # To'liq lokal Shadow AI

class TransitionManager:
    """
    Manages the transition between different AI modes (API, HYBRID, SHADOW).
    Responsible for routing decision requests and logging performance metrics
    in HYBRID mode.
    """
    def __init__(
        self,
        config: Any,
        ai_client: Any,
        shadow_engine: Any,
        predictor: Any
    ):
        """
        Initialize the TransitionManager.

        Args:
            config: BotConfig instance.
            ai_client: AIClient instance for external API.
            shadow_engine: ShadowDecisionEngine instance for local AI.
            predictor: PredictorEngine instance for readiness check.
        """
        self.config = config
        self.ai_client = ai_client
        self.shadow_engine = shadow_engine
        self.predictor = predictor
        
        self._mode_lock = threading.Lock()
        self._comparison_log: deque = deque(maxlen=200)
        self._shadow_accuracy_window: deque = deque(maxlen=100)
        self._mode = self._detect_initial_mode()
        
        logger.info(f"TransitionManager initialized with mode: {self._mode.value}")

    def _has_valid_api_keys(self) -> bool:
        """Check if any valid API key is present in the config."""
        keys = [
            getattr(self.config, 'anthropic_api_key', None),
            getattr(self.config, 'openrouter_api_key', None),
            getattr(self.config, 'kimi_api_key', None)
        ]
        return any(isinstance(k, str) and len(k.strip()) > 0 for k in keys)

    def _detect_initial_mode(self) -> AIMode:
        """Config va mavjud resurslar asosida boshlang'ich rejimni aniqlash"""
        forced_mode = getattr(self.config, 'ai_mode', 'auto').lower()
        
        if forced_mode == 'api':
            return AIMode.API
        elif forced_mode == 'hybrid':
            return AIMode.HYBRID
        elif forced_mode == 'shadow':
            return AIMode.SHADOW
            
        # Auto detection logic
        has_keys = self._has_valid_api_keys()
        
        try:
            readiness = self.predictor.evaluate_production_readiness() if self.predictor else {"ready": False}
            shadow_ready = readiness.get("ready", False)
        except Exception as e:
            logger.error(f"Failed to evaluate shadow predictor readiness: {e}")
            shadow_ready = False
            
        if not has_keys and shadow_ready:
            return AIMode.SHADOW
        elif has_keys and shadow_ready:
            return AIMode.HYBRID
        else:
            # Default fallback if shadow is not ready
            return AIMode.API

    @property
    def mode(self) -> AIMode:
        """Get the current AI mode in a thread-safe manner."""
        with self._mode_lock:
            return self._mode

    def set_mode(self, new_mode: AIMode, reason: str = "") -> None:
        """Set a new AI mode with a log reason."""
        with self._mode_lock:
            old_mode = self._mode
            self._mode = new_mode
            logger.warning(f"TransitionManager mode changed: {old_mode.value} -> {new_mode.value}. Reason: {reason}")

    def get_decision(
        self,
        recent_candles: Any,
        obs_data: Any,
        voting_result: Any,
        smc_context: Any,
        df_major: Any,
        current_price: float,
        symbol: str,
        timeframe: str,
        prompt_data: Optional[Tuple[str, str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Rejimga qarab qaror olish.
        prompt_data: tuple(system_prompt, prompt) — faqat API/HYBRID uchun
        context: dict — prompt build qilish uchun kerak bo'lgan kontekst
        Returns: dict (same format as AIClient.get_decision())
        """
        current_mode = self.mode
        decision = None
        
        kwargs = {
            'recent_candles': recent_candles,
            'obs_data': obs_data,
            'voting_result': voting_result,
            'smc_context': smc_context,
            'df_major': df_major,
            'current_price': current_price,
            'symbol': symbol,
            'timeframe': timeframe
        }

        try:
            if current_mode == AIMode.API:
                decision = self._api_decision(prompt_data, **kwargs)
                if decision is None:
                    # Fallback to shadow if available, else HOLD
                    logger.warning("API decision failed in API mode. Attempting Shadow fallback.")
                    decision = self._shadow_decision(**kwargs)
            elif current_mode == AIMode.SHADOW:
                decision = self._shadow_decision(**kwargs)
            elif current_mode == AIMode.HYBRID:
                decision = self._hybrid_decision(prompt_data, **kwargs)
                self._check_auto_transition()
        except Exception as e:
            logger.error(f"Critical error in get_decision ({current_mode.value}): {e}", exc_info=True)
            decision = None

        if not decision:
            decision = self._get_safe_hold(symbol, current_price)
            
        # Barcha qarorlarga _transition_mode qoshish
        decision["_transition_mode"] = current_mode.value
        return decision

    def _api_decision(self, prompt_data: Optional[Tuple[str, str]], **kwargs) -> Optional[Dict[str, Any]]:
        """Tashqi API orqali qaror olish"""
        if not prompt_data:
            logger.error("API decision requested but no prompt_data provided.")
            return None
            
        system_prompt, prompt = prompt_data
        
        try:
            # get_decision requires (prompt, system_prompt=None, ...)
            result = self.ai_client.get_decision(
                prompt=prompt,
                system_prompt=system_prompt,
                model_tier='auto'
            )
            return result
        except Exception as e:
            logger.error(f"Error fetching API decision: {e}")
            return None

    def _shadow_decision(self, **kwargs) -> Dict[str, Any]:
        """Lokal Shadow AI orqali qaror olish"""
        if not getattr(self.config, 'allow_shadow_trading', True):
            logger.warning("Shadow AI qabul qildi, biroq config.allow_shadow_trading=False bo'lgani uchun HOLD qaytarilmoqda.")
            return self._get_safe_hold(kwargs.get('symbol', 'UNKNOWN'), kwargs.get('current_price', 0.0))
            
        try:
            result = self.shadow_engine.decide(**kwargs)
            if result:
                return result
        except Exception as e:
            logger.error(f"Error fetching Shadow decision: {e}")
            
        return self._get_safe_hold(kwargs.get('symbol', 'UNKNOWN'), kwargs.get('current_price', 0.0))

    def _hybrid_decision(self, prompt_data: Optional[Tuple[str, str]], **kwargs) -> Dict[str, Any]:
        """
        IKKALASINI parallel/qator chaqirish:
        1. Shadow decide() — natija doim mavjud
        2. API get_decision() — fail bo'lishi mumkin
        """
        # 1. Shadow get decision (fallback guaranteed)
        shadow_result = self._shadow_decision(**kwargs)
        
        # 2. API get decision
        api_result = self._api_decision(prompt_data, **kwargs)
        
        symbol = kwargs.get('symbol', 'UNKNOWN')
        
        # Log comparison between results
        self._log_comparison(api_result, shadow_result, symbol)
        
        if api_result:
            return api_result
        else:
            logger.warning("HYBRID mode: API failed, falling back to SHADOW decision.")
            shadow_result["_hybrid_fallback"] = True
            return shadow_result

    def _log_comparison(
        self,
        api_result: Optional[Dict[str, Any]],
        shadow_result: Dict[str, Any],
        symbol: str
    ) -> None:
        """API vs Shadow natijasini logga yozish (agreement, disagreement)"""
        if not api_result:
            return
            
        api_decision = str(api_result.get("decision", "HOLD")).upper()
        shadow_decision = str(shadow_result.get("decision", "HOLD")).upper()
        
        same_direction = api_decision == shadow_decision
        
        api_risk = float(api_result.get("risk_pct", 0.0) or 0.0)
        shadow_risk = float(shadow_result.get("risk_pct", 0.0) or 0.0)
        risk_diff = abs(api_risk - shadow_risk)
        
        api_entry = float(api_result.get("entry_price", 0.0) or 0.0)
        shadow_entry = float(shadow_result.get("entry_price", 0.0) or 0.0)
        entry_diff = abs(api_entry - shadow_entry)
        
        import time
        comparison = {
            "symbol": symbol,
            "api_decision": api_decision,
            "shadow_decision": shadow_decision,
            "same_direction": same_direction,
            "risk_diff": risk_diff,
            "entry_diff": entry_diff,
            "timestamp": time.time()
        }
        
        with self._mode_lock:
            self._comparison_log.append(comparison)
            
        logger.debug(f"HYBRID Comparison [{symbol}]: API={api_decision}, SHADOW={shadow_decision}, match={same_direction}")

    def get_mode_stats(self) -> Dict[str, Any]:
        """Joriy rejim statistikasi (UI/Telegram uchun)"""
        with self._mode_lock:
            total_comparisons = len(self._comparison_log)
            agreements = sum(1 for c in self._comparison_log if c.get("same_direction", False))
            
            agreement_rate = (agreements / total_comparisons * 100) if total_comparisons > 0 else 0.0
            
            return {
                "mode": self._mode.value,
                "total_comparisons": total_comparisons,
                "agreement_rate_pct": round(agreement_rate, 2),
                "shadow_ready": hasattr(self, 'predictor') and self.predictor is not None
            }

    def _check_auto_transition(self) -> None:
        """HYBRID → SHADOW avtomatik o'tish tavsiyasi logikasi"""
        stats = self.get_mode_stats()
        
        # 100+ comparison va shadow agreement >= 70%
        if stats["total_comparisons"] >= 100 and stats["agreement_rate_pct"] >= 70.0:
            logger.info(
                f"RECOMMENDATION (Telegram Alert): Shadow AI agreement rate is {stats['agreement_rate_pct']}% "
                f"over {stats['total_comparisons']} comparisons. Safe to switch to SHADOW mode."
            )

    def _get_safe_hold(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """Qaror olishda xatolik bo'lsa xavfsiz HOLD qaytarish"""
        return {
            "decision": "HOLD",
            "entry_price": current_price,
            "stop_loss": 0.0,
            "take_profit": 0.0,
            "risk_pct": 0.0,
            "reasoning": "System fallback HOLD triggered due to engine or API failures.",
            "warnings": ["CRITICAL: Fallback HOLD triggered."],
            "_web_search_used": 0,
            "_source": "fallback",
            "symbol": symbol
        }
