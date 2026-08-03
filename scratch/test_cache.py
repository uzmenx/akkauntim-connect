import os
from ai_analysis import get_ai_decision, load_env
import json

def main():
    load_env()
    ctx = {
        "pair": "CACHE_TEST_PAIR",
        "timeframe": "H1",
        "current_price": 1.1000,
        "smc_structure": {
            "trend": {"internal": "Up Trend"}
        },
        "harmonic_pattern": {
            "signal": "BUY"
        },
        "news_context": {
            "status": "CLEAR"
        },
        "voting_result": {
            "direction": "BUY",
            "risk_pct": 2.0
        }
    }
    
    print("1-chi chaqiruv (API ga borishi kerak)...")
    res1 = get_ai_decision(ctx)
    print("Natija:", res1.get('reasoning'))
    
    print("\n2-chi chaqiruv (Keshdan olinishi kerak)...")
    res2 = get_ai_decision(ctx)
    print("Natija:", res2.get('reasoning'))

if __name__ == "__main__":
    main()
