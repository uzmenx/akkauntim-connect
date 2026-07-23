import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def aggregate_signals(
    smc_data: Dict[str, Any],
    pattern_data: Dict[str, Any],
    news_data: Dict[str, Any],
    wyckoff_data: Dict[str, Any],
    sr_volume_data: Dict[str, Any],
    auto_pattern_data: Dict[str, Any],
    kill_zones_data: Dict[str, Any],
    config: Any
) -> Dict[str, Any]:
    """
    Yetti strategiyaning natijalarini oladi va umumiy risk/signal hisoblaydi.
    Kutilayotgan format: {"signal": "BUY"|"SELL"|"HOLD", "confidence": 0-100}
    """
    conf_smc = getattr(config, "strategy_weight_smc", 60)
    conf_pattern = getattr(config, "strategy_weight_pattern", 60)
    conf_news = getattr(config, "strategy_weight_news", 60)
    conf_wyckoff = getattr(config, "strategy_weight_wyckoff", 50)
    conf_sr_volume = getattr(config, "strategy_weight_sr_volume", 50)
    conf_auto_pattern = getattr(config, "strategy_weight_auto_pattern", 50)
    conf_kill_zones = getattr(config, "strategy_weight_kill_zones", 50)
    allow_single = getattr(config, "allow_single_strategy_trade", False)
    
    smc_data = smc_data or {}
    pattern_data = pattern_data or {}
    news_data = news_data or {}
    wyckoff_data = wyckoff_data or {}
    sr_volume_data = sr_volume_data or {}
    auto_pattern_data = auto_pattern_data or {}
    kill_zones_data = kill_zones_data or {}
    valid_signals = []
    
    # 1. Belgilangan threshold'dan past ishonch va HOLD larni filtrlash
    if str(smc_data.get("signal") or "").upper() in ["BUY", "SELL"] and int(smc_data.get("confidence") or 0) >= conf_smc:
        valid_signals.append(("SMC", str(smc_data.get("signal")).upper()))
        
    if str(pattern_data.get("signal") or "").upper() in ["BUY", "SELL"] and int(pattern_data.get("confidence") or 0) >= conf_pattern:
        valid_signals.append(("Pattern", str(pattern_data.get("signal")).upper()))
        
    if str(news_data.get("signal") or "").upper() in ["BUY", "SELL"] and int(news_data.get("confidence") or 0) >= conf_news:
        valid_signals.append(("News", str(news_data.get("signal")).upper()))

    if str(wyckoff_data.get("signal") or "").upper() in ["BUY", "SELL"] and int(wyckoff_data.get("confidence") or 0) >= conf_wyckoff:
        valid_signals.append(("Wyckoff", str(wyckoff_data.get("signal")).upper()))

    if str(sr_volume_data.get("signal") or "").upper() in ["BUY", "SELL"] and int(sr_volume_data.get("confidence") or 0) >= conf_sr_volume:
        valid_signals.append(("SR_Volume", str(sr_volume_data.get("signal")).upper()))

    if str(auto_pattern_data.get("signal") or "").upper() in ["BUY", "SELL"] and int(auto_pattern_data.get("confidence") or 0) >= conf_auto_pattern:
        valid_signals.append(("Auto_Pattern", str(auto_pattern_data.get("signal")).upper()))

    if str(kill_zones_data.get("signal") or "").upper() in ["BUY", "SELL"] and int(kill_zones_data.get("confidence") or 0) >= conf_kill_zones:
        valid_signals.append(("Kill_Zones", str(kill_zones_data.get("signal")).upper()))
        
    # 2. Yo'nalishlarni guruhlash
    buy_strategies = [s[0] for s in valid_signals if s[1] == "BUY"]
    sell_strategies = [s[0] for s in valid_signals if s[1] == "SELL"]
    
    # Eng kuchli yo'nalishni aniqlash
    if len(buy_strategies) > len(sell_strategies):
        winner_direction = "BUY"
        winner_strategies = set(buy_strategies)
    elif len(sell_strategies) > len(buy_strategies):
        winner_direction = "SELL"
        winner_strategies = set(sell_strategies)
    else:
        # Durang yoki umuman signal yo'q
        logger.info("Strategiyalar o'rtasida ziddiyat bor yoki kuchli signal topilmadi.")
        return {
            "signal": "HOLD",
            "risk_pct": 0.0,
            "agreed_strategies": [],
            "reasoning": "Strategiyalar o'rtasida ziddiyat bor yoki kuchli signal topilmadi."
        }
        
    # 3. Kombinatsiyaga qarab riskni belgilash
    risk_pct = 0.0
    num_strats = len(winner_strategies)
    
    if num_strats >= 5:
        risk_pct = 0.05
    elif num_strats == 4:
        risk_pct = 0.04
    elif num_strats == 3:
        risk_pct = 0.03
    elif num_strats == 2:
        risk_pct = 0.02
    elif num_strats == 1:
        if allow_single:
            risk_pct = 0.01
        else:
            logger.info("Yakka strategiya signali olingan, ammo ruxsat etilmagan.")
            return {
                "signal": "HOLD",
                "risk_pct": 0.0,
                "agreed_strategies": list(winner_strategies),
                "reasoning": "Yakka strategiya signali olingan, ammo ruxsat etilmagan (allow_single_strategy_trade=False)."
            }
            
    reasoning = f"{num_strats} ta strategiya ({', '.join(winner_strategies)}) kelishdi."
    logger.info(f"Voting natijasi: {winner_direction}, Risk: {risk_pct}, Sabab: {reasoning}")
    
    return {
        "signal": winner_direction,
        "risk_pct": risk_pct,
        "agreed_strategies": list(winner_strategies),
        "reasoning": reasoning
    }
