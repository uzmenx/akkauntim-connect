from typing import List, Dict, Set
import logging
from bot.engine.regime_detector import MarketRegime

logger = logging.getLogger(__name__)

class StrategyPortfolioManager:
    """
    Strategiya Portfelini Boshqaruvchi modul.
    
    Vazifasi:
    1. RegimeDetector'dan kelgan joriy rejimga qarab strategiyalarni saralash
    2. Yangi signal ISHLAB CHIQARMAYDI, faqat mavjud (SMC, Wyckoff, etc.) strategiyalarning 
       joriy rejimdagi og'irligini belgilaydi
    """
    
    # Qaysi strategiya qaysi rejimda faol va ishonchli ishlashini belgilovchi xarita
    # Eslatma: Bu tarixiy testlar asosida o'zgartirilishi mumkin. Hozirgi qiymatlar boshlang'ich gipoteza.
    REGIME_STRATEGY_MAP: Dict[MarketRegime, List[str]] = {
        MarketRegime.TREND: ["SMC", "Wyckoff", "Kill_Zones", "Pattern"],
        MarketRegime.RANGE: ["SR_Volume", "Pattern", "Wyckoff"],
        MarketRegime.VOLATILE: ["News", "Auto_Pattern"],
        MarketRegime.UNKNOWN: ["SMC", "News"] # Default xavfsiz strategiyalar
    }
    
    def __init__(self):
        self.active_regime = MarketRegime.UNKNOWN
        
    def get_active_strategies(self, regime: MarketRegime) -> List[str]:
        """
        Berilgan rejim uchun ruxsat etilgan strategiyalar ro'yxatini qaytaradi.
        """
        self.active_regime = regime
        strategies = self.REGIME_STRATEGY_MAP.get(regime, [])
        logger.info(f"Rejim: {regime.value} -> Faol strategiyalar: {strategies}")
        return strategies

    def filter_signals(self, raw_signals: Dict[str, Dict], regime: MarketRegime) -> Dict[str, Dict]:
        """
        Barcha strategiya natijalarini oladi va faqat joriy rejimga moslarini qoldiradi.
        """
        allowed = set(self.get_active_strategies(regime))
        filtered = {}
        for strat_name, data in raw_signals.items():
            if strat_name in allowed:
                filtered[strat_name] = data
            else:
                # Agar strategiya bu rejimga kirmasa, uni HOLD yoki 0 ishonchga aylantiramiz
                filtered[strat_name] = {"signal": "HOLD", "confidence": 0}
                
        return filtered
