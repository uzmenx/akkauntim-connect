# voting_engine.py

ALLOW_SINGLE_STRATEGY_TRADE = False

def aggregate_signals(smc_data: dict, pattern_data: dict, news_data: dict) -> dict:
    """
    Uchta strategiyaning natijalarini oladi va umumiy risk/signal hisoblaydi.
    Kutilayotgan format: {"signal": "BUY"|"SELL"|"HOLD", "confidence": 0-100}
    """
    valid_signals = []
    
    # 1. 60% dan past ishonch va HOLD larni filtrlash
    if smc_data.get("signal") in ["BUY", "SELL"] and smc_data.get("confidence", 0) >= 60:
        valid_signals.append(("SMC", smc_data["signal"]))
        
    if pattern_data.get("signal") in ["BUY", "SELL"] and pattern_data.get("confidence", 0) >= 60:
        valid_signals.append(("Pattern", pattern_data["signal"]))
        
    if news_data.get("signal") in ["BUY", "SELL"] and news_data.get("confidence", 0) >= 60:
        valid_signals.append(("News", news_data["signal"]))
        
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
        return {
            "signal": "HOLD",
            "risk_pct": 0.0,
            "agreed_strategies": [],
            "reasoning": "Strategiyalar o'rtasida ziddiyat bor yoki kuchli signal topilmadi."
        }
        
    # 3. Kombinatsiyaga qarab riskni belgilash
    risk_pct = 0.0
    num_strats = len(winner_strategies)
    
    if num_strats == 3:
        # SMC + News + Pattern
        risk_pct = 0.04
    elif num_strats == 2:
        if "SMC" in winner_strategies and "News" in winner_strategies:
            risk_pct = 0.03
        elif "SMC" in winner_strategies and "Pattern" in winner_strategies:
            risk_pct = 0.02
        elif "News" in winner_strategies and "Pattern" in winner_strategies:
            risk_pct = 0.02
    elif num_strats == 1:
        if ALLOW_SINGLE_STRATEGY_TRADE:
            risk_pct = 0.01
        else:
            return {
                "signal": "HOLD",
                "risk_pct": 0.0,
                "agreed_strategies": list(winner_strategies),
                "reasoning": "Yakka strategiya signali olingan, ammo ruxsat etilmagan (ALLOW_SINGLE_STRATEGY_TRADE=False)."
            }
            
    return {
        "signal": winner_direction,
        "risk_pct": risk_pct,
        "agreed_strategies": list(winner_strategies),
        "reasoning": f"{num_strats} ta strategiya ({', '.join(winner_strategies)}) kelishdi."
    }

if __name__ == "__main__":
    # Test cases
    print(aggregate_signals(
        {"signal": "BUY", "confidence": 65}, # SMC
        {"signal": "BUY", "confidence": 70}, # Pattern
        {"signal": "HOLD", "confidence": 50} # News
    ))
    
    print(aggregate_signals(
        {"signal": "SELL", "confidence": 80}, # SMC
        {"signal": "SELL", "confidence": 75}, # Pattern
        {"signal": "SELL", "confidence": 90}  # News
    ))
    
    print(aggregate_signals(
        {"signal": "BUY", "confidence": 80},  # SMC
        {"signal": "HOLD", "confidence": 0},  # Pattern
        {"signal": "HOLD", "confidence": 0}   # News
    ))
