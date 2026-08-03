import json
import MetaTrader5 as mt5
from ai_analysis import build_decision_context, get_ai_decision, load_env, init_db

def test_live_ai_decision():
    load_env()
    init_db()
    
    if not mt5.initialize():
        print("MT5 ulanishda xatolik:", mt5.last_error())
        
    pair = "EURUSD"
    timeframe = "H1"
    
    print(f"[{pair} {timeframe}] Kontekst yig'ilmoqda...")
    context = build_decision_context(pair, timeframe)
    
    # MOCK VOTING ENGINE (majburiy BUY va 2% risk)
    print("Voting Engine natijasi vaqtincha MOCK qilinmoqda (BUY, 2% risk)...")
    context["voting_result"] = {
        "direction": "BUY",
        "risk_pct": 2.0,
        "agreeing_strategies": ["SMC", "News", "Pattern MOCK"],
        "confidence_scores": {
            "SMC": 75,
            "Pattern": 75,
            "News": 80
        }
    }
    
    print("\n=== CLAUDE UCHUN YIG'ILGAN PROMPT ===")
    from ai_analysis import build_claude_prompt
    print(build_claude_prompt(context))
    
    print("\n.env da ANTHROPIC_API_KEY yo'qligi sababli Claude API javobi simulyatsiya (mock) qilinmoqda...")
    mock_claude_json = '''{
      "final_decision": "REJECT",
      "reasoning": "SMC trendi Bearish ko'rsatmoqda, garchi Voting Engine BUY qarori bergan bo'lsa ham ziddiyat bor. Savdo rad etildi.",
      "risk_pct": 2.0,
      "direction": "BUY",
      "warnings": ["SMC va Voting Engine o'rtasida kuchli ziddiyat."],
      "wait_until": null
    }'''
    decision = get_ai_decision(context, mock_response=mock_claude_json)
    
    print("\n=== CLAUDE JAVOBI (JSON) ===")
    print(json.dumps(decision, indent=2, ensure_ascii=False))
    
    mt5.shutdown()

if __name__ == "__main__":
    test_live_ai_decision()
