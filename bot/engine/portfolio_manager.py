import logging
import pandas as pd
from abc import ABC, abstractmethod
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class Strategy(ABC):
    def __init__(self, name: str, default_weight: int = 50):
        self.name = name
        self.default_weight = default_weight
        self.dynamic_weight = default_weight  # AI orqali keyinchalik o'zgaradi

    @abstractmethod
    def analyze(self, df: pd.DataFrame, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Tahlil funksiyasi.
        Kutilayotgan natija formati:
        {
            "signal": "BUY" | "SELL" | "HOLD",
            "confidence": 0-100,
            "details": {...}
        }
        """
        pass

class PortfolioManager:
    """
    Barcha strategiyalarni bitta markazda boshqaruvchi (Multi-Strategy) modul.
    """
    
    # Qaysi strategiya qaysi rejimda faol va ishonchli ishlashini belgilovchi xarita
    REGIME_STRATEGY_MAP = {
        "TREND": ["SMC", "Wyckoff", "Pattern", "Swift"],
        "RANGE": ["SR_Volume", "Pattern", "Wyckoff", "Swift"],
        "VOLATILE": ["News", "Auto_Pattern", "Pattern", "Swift"],
        "BLACK_SWAN": [], # Barcha strategiyalar to'xtatiladi, faqat himoya
        "UNKNOWN": ["SMC", "News"]
    }

    def __init__(self, config):
        self.config = config
        self.strategies: List[Strategy] = []
        
    def register_strategy(self, strategy: Strategy):
        self.strategies.append(strategy)
        logger.info(f"Registered Strategy: {strategy.name} (Weight: {strategy.default_weight})")
        
    def analyze_all(self, df: pd.DataFrame, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Barcha strategiyalardan signallarni yig'ish va yagona qarorga kelish (Voting).
        """
        valid_signals = []
        detailed_results = {}
        
        current_regime = context.get("regime", "UNKNOWN")
        allowed_strategies = self.REGIME_STRATEGY_MAP.get(current_regime, [])
        
        if current_regime == "BLACK_SWAN":
            logger.warning("🚨 BLACK SWAN rejimi aniqlandi! Barcha strategiyalar to'xtatildi (HOLD).")
            return {
                "signal": "HOLD",
                "risk_pct": 0.0,
                "agreed_strategies": [],
                "details": {},
                "reasoning": "BLACK SWAN - Favqulodda himoya rejimi."
            }
        
        # AI Reviewer orqali dinamik vaznlarni yangilash
        adjustments = context.get("learning_adjustments", [])
        for strategy in self.strategies:
            strategy.dynamic_weight = strategy.default_weight
            for adj in adjustments:
                # Agar adjustment shu strategiyaga tegishli bo'lsa
                if adj.get("target") == "strategy_weight" and strategy.name.lower() in adj.get("reason", "").lower():
                    strategy.dynamic_weight += adj.get("value", 0)
            # 10 va 100 orasida cheklash
            strategy.dynamic_weight = max(10, min(100, strategy.dynamic_weight))

        for strategy in self.strategies:
            try:
                # Bozor rejimiga qarab strategiyani o'chirish
                if strategy.name not in allowed_strategies:
                    logger.debug(f"Strategy {strategy.name} is disabled in {current_regime} regime.")
                    detailed_results[strategy.name] = {"signal": "HOLD", "confidence": 0}
                    continue
                    
                result = strategy.analyze(df, context)
                detailed_results[strategy.name] = result
                
                sig = str(result.get("signal", "HOLD")).upper()
                conf = int(result.get("confidence", 0))
                
                if sig in ["BUY", "SELL"] and conf >= strategy.dynamic_weight:
                    valid_signals.append((strategy.name, sig))
            except Exception as e:
                logger.error(f"Strategy {strategy.name} xatosi: {e}")
                
        # Voting mexanizmi
        buy_strategies = [s[0] for s in valid_signals if s[1] == "BUY"]
        sell_strategies = [s[0] for s in valid_signals if s[1] == "SELL"]
        
        if len(buy_strategies) > len(sell_strategies):
            winner_direction = "BUY"
            winner_strategies = set(buy_strategies)
        elif len(sell_strategies) > len(buy_strategies):
            winner_direction = "SELL"
            winner_strategies = set(sell_strategies)
        else:
            logger.info("PortfolioManager: Ziddiyat bor yoki kuchli signal yo'q.")
            return {
                "signal": "HOLD",
                "risk_pct": 0.0,
                "agreed_strategies": [],
                "details": detailed_results,
                "reasoning": "Ziddiyat yoki yetarli ishonchli signal yo'q."
            }
            
        risk_pct = getattr(self.config, "risk_per_trade", 0.02)
        allow_single = getattr(self.config, "allow_single_strategy_trade", False)
        
        if len(winner_strategies) == 1 and not allow_single:
            logger.info(f"Yakka strategiya ({list(winner_strategies)[0]}) signali ruxsat etilmagan.")
            return {
                "signal": "HOLD",
                "risk_pct": 0.0,
                "agreed_strategies": list(winner_strategies),
                "details": detailed_results,
                "reasoning": "Yakka strategiya signali ruxsat etilmagan."
            }
            
        # Kill Zones (Vaqt) va Volatillik (Context) asosida riskni moslashtirish
        kill_zones_data = context.get("kill_zones", {})
        if kill_zones_data.get("is_kill_zone") or kill_zones_data.get("is_overlap"):
            risk_pct *= 1.0
        elif kill_zones_data.get("is_dead_zone"):
            risk_pct *= 0.5
        else:
            risk_pct *= 0.75

        # Fundamental Veto (NLP Kayfiyat)
        news_details = detailed_results.get("News", {})
        sentiment_score = news_details.get("sentiment_score", 50)
        
        if winner_direction == "BUY" and sentiment_score < 30:
            logger.warning(f"🚨 FUNDAMENTAL VETO! Texnik: BUY, lekin NLP Sentiment juda salbiy ({sentiment_score}). Savdo bekor qilindi.")
            return {
                "signal": "HOLD",
                "risk_pct": 0.0,
                "agreed_strategies": list(winner_strategies),
                "details": detailed_results,
                "reasoning": f"Fundamental Veto: Texnik tahlil O'sishni ko'rsatdi, lekin AI NLP kayfiyati juda yomon (Score: {sentiment_score})."
            }
            
        if winner_direction == "SELL" and sentiment_score > 70:
            logger.warning(f"🚨 FUNDAMENTAL VETO! Texnik: SELL, lekin NLP Sentiment juda ijobiy ({sentiment_score}). Savdo bekor qilindi.")
            return {
                "signal": "HOLD",
                "risk_pct": 0.0,
                "agreed_strategies": list(winner_strategies),
                "details": detailed_results,
                "reasoning": f"Fundamental Veto: Texnik tahlil Qulashni ko'rsatdi, lekin AI NLP kayfiyati juda yaxshi (Score: {sentiment_score})."
            }

        reasoning = f"{len(winner_strategies)} ta strategiya ({', '.join(winner_strategies)}) kelishdi. Sentiment: {sentiment_score}."
        logger.info(f"PortfolioManager Natija: {winner_direction}, Risk: {risk_pct}, Sabab: {reasoning}")
        
        # State ni Veb UI uchun eksport qilish
        self._export_portfolio_state(sentiment_score)
        
        # Score (ishonchlilik darajasi) ni hisoblash
        total_score = 0
        if winner_strategies:
            for s in winner_strategies:
                total_score += detailed_results.get(s, {}).get("confidence", 0)
            avg_score = int(total_score / len(winner_strategies))
        else:
            avg_score = 0
            
        return {
            "signal": winner_direction,
            "risk_pct": risk_pct,
            "agreed_strategies": list(winner_strategies),
            "details": detailed_results,
            "reasoning": reasoning,
            "score": avg_score
        }

    def _export_portfolio_state(self, sentiment_score: int):
        import os
        import json
        public_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'public')
        if not os.path.exists(public_dir):
            try:
                os.makedirs(public_dir)
            except:
                pass
                
        state = {
            "sentiment_score": sentiment_score,
            "strategies": [{"name": s.name, "weight": s.dynamic_weight} for s in self.strategies]
        }
        try:
            with open(os.path.join(public_dir, 'portfolio_state.json'), 'w') as f:
                json.dump(state, f)
        except Exception as e:
            logger.debug(f"Portfolio state saqlashda xato: {e}")

# ==========================================
# Strategy Implementations (Wrappers)
# ==========================================

class SMCStrategy(Strategy):
    def __init__(self, main_bot):
        super().__init__("SMC", getattr(main_bot.config, "strategy_weight_smc", 60))
        self.bot = main_bot

    def analyze(self, df: pd.DataFrame, context: Dict[str, Any] = None) -> Dict[str, Any]:
        smc_result = self.bot._get_smc_full_analysis(df)
        if smc_result:
            try:
                from bot.strategy.smc.engine import to_voting_signal as smc_voting
                sig_data = smc_voting(smc_result)
                smc_result["signal"] = sig_data.get("signal", "HOLD")
                smc_result["confidence"] = sig_data.get("confidence", 0)
            except Exception as e:
                logger.error(f"SMC to_voting_signal xatosi: {e}")
        else:
            smc_result = {"signal": "HOLD", "confidence": 0}
        return smc_result

class PatternStrategy(Strategy):
    def __init__(self, main_bot):
        super().__init__("Pattern", getattr(main_bot.config, "strategy_weight_pattern", 60))
        self.bot = main_bot

    def analyze(self, df: pd.DataFrame, context: Dict[str, Any] = None) -> Dict[str, Any]:
        result = self.bot._get_harmonic_patterns(df)
        if result:
            try:
                from bot.strategy.harmonic.engine import to_voting_signal as harmonic_voting
                sig_data = harmonic_voting(result)
                result["signal"] = sig_data.get("signal", "HOLD")
                result["confidence"] = sig_data.get("confidence", 0)
            except Exception as e:
                logger.error(f"Harmonic to_voting_signal xatosi: {e}")
                result["signal"] = "HOLD"
                result["confidence"] = 0
        else:
            result = {"signal": "HOLD", "confidence": 0}
        return result

class NewsStrategy(Strategy):
    def __init__(self, main_bot):
        super().__init__("News", getattr(main_bot.config, "strategy_weight_news", 60))
        self.bot = main_bot

    def analyze(self, df: pd.DataFrame, context: Dict[str, Any] = None) -> Dict[str, Any]:
        symbol = context.get("symbol") if context else None
        result = self.bot._get_news_context(symbol) if symbol else {}
        if result:
            rec = result.get("recommendation", "neutral")
            if rec == "prepare_long":
                result["signal"] = "BUY"
                result["confidence"] = 80
            elif rec == "prepare_short":
                result["signal"] = "SELL"
                result["confidence"] = 80
            else:
                result["signal"] = "HOLD"
                result["confidence"] = 0
        return result or {"signal": "HOLD", "confidence": 0}

class WyckoffStrategy(Strategy):
    def __init__(self, main_bot):
        super().__init__("Wyckoff", getattr(main_bot.config, "strategy_weight_wyckoff", 50))
        self.bot = main_bot

    def analyze(self, df: pd.DataFrame, context: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            from bot.strategy.wyckoff.engine import analyze_wyckoff, to_voting_signal as wyckoff_voting
            result = analyze_wyckoff(df)
            if result:
                sig_data = wyckoff_voting(result)
                result["signal"] = sig_data.get("signal", "HOLD")
                result["confidence"] = sig_data.get("confidence", 0)
            else:
                result = {"signal": "HOLD", "confidence": 0}
            return result
        except Exception as e:
            logger.error(f"Wyckoff tahlil xatosi: {e}")
            return {"signal": "HOLD", "confidence": 0}

class SRVolumeStrategy(Strategy):
    def __init__(self, main_bot):
        super().__init__("SR_Volume", getattr(main_bot.config, "strategy_weight_sr_volume", 50))
        self.bot = main_bot

    def analyze(self, df: pd.DataFrame, context: Dict[str, Any] = None) -> Dict[str, Any]:
        result = self.bot._get_sr_volume_analysis(df)
        if result:
            try:
                from bot.strategy.sr_volume.engine import to_voting_signal as sr_voting
                sig_data = sr_voting(result)
                result["signal"] = sig_data.get("signal", "HOLD")
                result["confidence"] = sig_data.get("confidence", 0)
            except Exception as e:
                logger.error(f"SR_Volume to_voting_signal xatosi: {e}")
        else:
            result = {"signal": "HOLD", "confidence": 0}
        return result

class AutoPatternStrategy(Strategy):
    def __init__(self, main_bot):
        super().__init__("Auto_Pattern", getattr(main_bot.config, "strategy_weight_auto_pattern", 50))
        self.bot = main_bot

    def analyze(self, df: pd.DataFrame, context: Dict[str, Any] = None) -> Dict[str, Any]:
        current_price = context.get("current_price")
        result = self.bot._get_auto_patterns_analysis(df, current_price)
        return result or {"signal": "HOLD", "confidence": 0}


class SwiftStrategy(Strategy):
    """11-strategiya: SWIFT ALGO (Pine Script v5 -> Python konvertatsiyasi)."""

    def __init__(self, main_bot):
        super().__init__("Swift", getattr(main_bot.config, "strategy_weight_swift", 55))
        self.bot = main_bot

    def analyze(self, df: pd.DataFrame, context: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            from bot.strategy.swift.engine import analyze_swift, to_voting_signal as swift_voting
            base_minutes = 15
            if context:
                base_minutes = int(context.get("base_minutes", 15) or 15)
            result = analyze_swift(df, base_minutes=base_minutes)
            sig_data = swift_voting(result)
            result["signal"] = sig_data.get("signal", "HOLD")
            result["confidence"] = sig_data.get("confidence", 0)
            return result
        except Exception as e:
            logger.error(f"Swift tahlil xatosi: {e}")
            return {"signal": "HOLD", "confidence": 0}
