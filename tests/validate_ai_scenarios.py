import os
import json
import pandas as pd
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from ai_analysis import get_ai_decision, load_env

def run_scenario(name, context, expected_result, mock_response=None):
    print(f"\n{'='*50}\nSTSENARIY: {name}\n{'='*50}")
    
    decision = get_ai_decision(context, mock_response=mock_response)
    
    print(f"Kutilgan Natija: {expected_result}")
    print(f"Claude Qarori: {decision.get('final_decision')}")
    print(f"Claude Reasoning: {decision.get('reasoning')}")
    if decision.get('warnings'):
        print(f"Claude Warnings: {decision.get('warnings')}")
    
    is_match = False
    if expected_result in decision.get('final_decision', ''):
        is_match = True
    elif expected_result == "REJECT_OR_WAIT" and decision.get('final_decision') in ["REJECT", "WAIT"]:
        is_match = True
    elif expected_result == "REJECT_OR_HOLD" and decision.get('final_decision') in ["REJECT", "HOLD"]:
        is_match = True
        
    result_str = "HA (YES)" if is_match else "YO'Q (NO)"
    print(f"Kutilganga mosmi? {result_str}")
    
    return {
        "scenario": name,
        "voting_result": context.get("voting_result", {}).get("direction", "N/A"),
        "claude_decision": decision.get("final_decision", "ERROR"),
        "claude_reasoning": decision.get("reasoning", ""),
        "match": is_match
    }

def main():
    load_env()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("DIQQAT: .env faylida ANTHROPIC_API_KEY topilmadi. Claude API javoblari mock qilinadi.")
        
    results = []
    
    # STSENARIY 1 — To'liq mos kelish (3/3)
    ctx1 = {
        "pair": "EURUSD",
        "timeframe": "H1",
        "current_price": 1.1000,
        "smc_structure": {
            "trend": {"internal": "Up Trend", "external": "Up Trend"},
            "last_bos": {"type": "Bullish", "price": 1.0980},
            "events": ["Major Bullish ChoCh", "Demand OB fresh"]
        },
        "harmonic_pattern": {
            "signal": "BUY",
            "patterns": [{"name": "Bullish Gartley"}]
        },
        "news_context": {
            "status": "CLEAR",
            "next_event": {"name": "NFP", "minutes_to_release": 120},
            "historical_bias": {"direction": "Bullish", "confidence": 70}
        },
        "voting_result": {
            "direction": "BUY",
            "risk_pct": 4.0,
            "agreeing_strategies": ["SMC", "Pattern", "News"],
            "confidence_scores": {"SMC": 75, "Pattern": 68, "News": 70}
        }
    }
    m1 = json.dumps({"final_decision": "EXECUTE", "reasoning": "Barcha uchala strategiya (SMC, Harmonic, News) bir xil BUY signalini bermoqda va ziddiyat mavjud emas.", "risk_pct": 4.0, "direction": "BUY", "warnings": [], "wait_until": None})
    results.append(run_scenario("1 - To'liq mos kelish (3/3)", ctx1, "EXECUTE", mock_response=m1 if not os.environ.get("ANTHROPIC_API_KEY") else None))
    
    # STSENARIY 2 — Faqat News signal kuchli, lekin yakka (1/3)
    ctx2 = {
        "pair": "EURUSD",
        "timeframe": "H1",
        "current_price": 1.1000,
        "smc_structure": {
            "trend": {"internal": "No Trend", "external": "No Trend"}
        },
        "harmonic_pattern": {
            "signal": "NEUTRAL"
        },
        "news_context": {
            "status": "CLEAR",
            "next_event": {"name": "NFP beat", "minutes_to_release": 30},
            "historical_bias": {"direction": "Bullish", "confidence": 85}
        },
        "voting_result": {
            "direction": "HOLD",
            "risk_pct": 0.0,
            "agreeing_strategies": ["News"],
            "confidence_scores": {"SMC": 40, "Pattern": 35, "News": 85}
        }
    }
    results.append(run_scenario("2 - Faqat News signal kuchli, lekin yakka (1/3)", ctx2, "REJECT_OR_HOLD"))
    
    # STSENARIY 3 — SMC + Pattern mos, lekin yangilik xavfli yaqinlashmoqda
    ctx3 = {
        "pair": "EURUSD",
        "timeframe": "H1",
        "current_price": 1.1000,
        "smc_structure": {
            "trend": {"internal": "Up Trend"}
        },
        "harmonic_pattern": {
            "signal": "BUY"
        },
        "news_context": {
            "status": "AWAITING_NEWS",
            "next_event": {"name": "High Impact NFP", "minutes_to_release": 10},
            "historical_bias": {"direction": "Neutral", "confidence": 0}
        },
        "voting_result": {
            "direction": "BUY",
            "risk_pct": 2.0,
            "agreeing_strategies": ["SMC", "Pattern"],
            "confidence_scores": {"SMC": 70, "Pattern": 65, "News": 0}
        }
    }
    m3 = json.dumps({"final_decision": "WAIT", "reasoning": "Texnik signallar kuchli bo'lsa-da, atigi 10 daqiqadan so'ng yuqori ta'sirli NFP yangiligi chiqadi. Katta volatillik xavfi sababli kutish tavsiya etiladi.", "risk_pct": 2.0, "direction": "BUY", "warnings": ["Yaqinlashayotgan NFP yangiligi"], "wait_until": "Yangilik chiqib bo'lguncha"})
    results.append(run_scenario("3 - SMC + Pattern mos, yangilik xavfi (10 daqiqa)", ctx3, "REJECT_OR_WAIT", mock_response=m3 if not os.environ.get("ANTHROPIC_API_KEY") else None))
    
    # STSENARIY 4 — Zaif confidence bilan 2/3 mos kelish
    ctx4 = {
        "pair": "EURUSD",
        "timeframe": "H1",
        "current_price": 1.1000,
        "smc_structure": {
            "trend": {"internal": "Up Trend"}
        },
        "harmonic_pattern": {
            "signal": "BUY"
        },
        "news_context": {
            "status": "CLEAR",
            "next_event": {"name": "None", "minutes_to_release": 1000},
            "historical_bias": {"direction": "Neutral", "confidence": 0}
        },
        "voting_result": {
            "direction": "BUY",
            "risk_pct": 2.0,
            "agreeing_strategies": ["SMC", "Pattern"],
            "confidence_scores": {"SMC": 61, "Pattern": 62, "News": 0}
        }
    }
    m4 = json.dumps({"final_decision": "EXECUTE", "reasoning": "SMC va Harmonic ishonch darajasi chegaraga yaqin bo'lsa ham, texnik tasdiq mavjud va fundamental xavf yo'q.", "risk_pct": 2.0, "direction": "BUY", "warnings": ["Ishonch darajasi pastroq"], "wait_until": None})
    results.append(run_scenario("4 - Zaif confidence bilan 2/3 mos kelish", ctx4, "EXECUTE", mock_response=m4 if not os.environ.get("ANTHROPIC_API_KEY") else None))
    
    # STSENARIY 5 — Kunlik limit yaqinlashgan holat
    ctx5 = {
        "pair": "EURUSD",
        "timeframe": "H1",
        "current_price": 1.1000,
        "smc_structure": {
            "trend": {"internal": "Up Trend"}
        },
        "harmonic_pattern": {
            "signal": "BUY"
        },
        "news_context": {
            "status": "CLEAR",
            "next_event": {"name": "None", "minutes_to_release": 1000},
            "historical_bias": {"direction": "Bullish", "confidence": 70}
        },
        "voting_result": {
            "direction": "BUY",
            "risk_pct": 4.0,
            "agreeing_strategies": ["SMC", "Pattern", "News"],
            "confidence_scores": {"SMC": 75, "Pattern": 75, "News": 75}
        },
        "risk_manager": {
            "daily_drawdown_pct": -8.0,
            "daily_limit_pct": -10.0
        }
    }
    m5 = json.dumps({"final_decision": "REJECT", "reasoning": "Kunlik zarar limiti -10% va hozir allaqachon -8% ga yetgan. Qo'shimcha risk olish qat'iyan man etiladi.", "risk_pct": 4.0, "direction": "BUY", "warnings": ["Kunlik limitga juda yaqinlashgan!"], "wait_until": "Ertangi kun boshlanishigacha"})
    results.append(run_scenario("5 - Kunlik limit yaqinlashgan holat (-8%)", ctx5, "REJECT_OR_WAIT", mock_response=m5 if not os.environ.get("ANTHROPIC_API_KEY") else None))
    
    # STSENARIY 6 — To'g'ridan-to'g'ri qarama-qarshi ikkita kuchli signal
    ctx6 = {
        "pair": "EURUSD",
        "timeframe": "H1",
        "current_price": 1.1000,
        "smc_structure": {
            "trend": {"internal": "Up Trend"}
        },
        "harmonic_pattern": {
            "signal": "NEUTRAL"
        },
        "news_context": {
            "status": "CLEAR",
            "next_event": {"name": "Strong Bearish Data", "minutes_to_release": 60},
            "historical_bias": {"direction": "Bearish", "confidence": 78}
        },
        "voting_result": {
            "direction": "HOLD",
            "risk_pct": 0.0,
            "agreeing_strategies": [],
            "confidence_scores": {"SMC": 80, "Pattern": 0, "News": 78}
        }
    }
    results.append(run_scenario("6 - To'g'ridan-to'g'ri qarama-qarshi ikkita kuchli signal", ctx6, "REJECT_OR_HOLD"))
    
    print("\n" + "="*80)
    print("XULOSA JADVALI")
    print("="*80)
    print(f"| {'Stsenariy':<50} | {'Voting':<6} | {'Claude Qarori':<13} | {'Mosmi?':<8} |")
    print("-" * 85)
    for r in results:
        print(f"| {r['scenario']:<50} | {r['voting_result']:<6} | {r['claude_decision']:<13} | {'HA' if r['match'] else 'YO`Q' :<8} |")
    print("="*80)

if __name__ == "__main__":
    main()
