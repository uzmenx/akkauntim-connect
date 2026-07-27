import pytest
import json
from ai_analysis import get_ai_decision, build_decision_context, extract_smc_signal, extract_pattern_signal, extract_news_signal

def test_extract_signals():
    smc_res = {"trend": {"internal": "Up Trend"}}
    assert extract_smc_signal(smc_res)["signal"] == "BUY"
    
    pat_res = {"signal": "SELL"}
    assert extract_pattern_signal(pat_res)["signal"] == "SELL"
    
    news_res = {"recommendation": "prepare_long"}
    assert extract_news_signal(news_res)["signal"] == "BUY"

def test_ai_decision_hold():
    # If voting engine returns HOLD, Claude is not called and we return REJECT
    context = {
        "voting_result": {
            "direction": "HOLD",
            "risk_pct": 0.0
        }
    }
    decision = get_ai_decision(context)
    assert decision["final_decision"] == "REJECT"
    assert "AI chaqirilmadi" in decision["reasoning"]

def test_ai_decision_execute():
    context = {
        "pair": "EURUSD",
        "timeframe": "H1",
        "voting_result": {
            "direction": "BUY",
            "risk_pct": 0.02,
            "agreeing_strategies": ["SMC", "News"]
        }
    }
    mock_response = json.dumps({
        "final_decision": "EXECUTE",
        "reasoning": "Kontekst yaxshi ko'rinmoqda, o'sish ehtimoli yuqori.",
        "risk_pct": 0.02,
        "direction": "BUY",
        "warnings": [],
        "wait_until": None
    })
    
    decision = get_ai_decision(context, mock_response=mock_response)
    assert decision["final_decision"] == "EXECUTE"
    assert decision["direction"] == "BUY"
    assert decision["risk_pct"] == 0.02

def test_ai_decision_wait():
    context = {
        "pair": "GBPUSD",
        "timeframe": "H1",
        "voting_result": {
            "direction": "SELL",
            "risk_pct": 0.03,
            "agreeing_strategies": ["SMC", "News"]
        }
    }
    mock_response = json.dumps({
        "final_decision": "WAIT",
        "reasoning": "Yaqinda NFP yangiligi kutilyapti, kuting.",
        "risk_pct": 0.03,
        "direction": "SELL",
        "warnings": ["News volatility"],
        "wait_until": "15:30"
    })
    
    decision = get_ai_decision(context, mock_response=mock_response)
    assert decision["final_decision"] == "WAIT"

def test_ai_decision_invalid_json():
    context = {
        "voting_result": {
            "direction": "BUY",
            "risk_pct": 0.02
        }
    }
    mock_response = "Bu yerda JSON emas, shunchaki matn yozilgan."
    decision = get_ai_decision(context, mock_response=mock_response)
    assert decision["final_decision"] == "REJECT"
    assert "JSON Parse xato" in decision["warnings"][0]

def test_ai_decision_alters_risk():
    context = {
        "voting_result": {
            "direction": "BUY",
            "risk_pct": 0.02
        }
    }
    mock_response = json.dumps({
        "final_decision": "EXECUTE",
        "reasoning": "Zo'r signal ekan, riskni oshiramiz.",
        "risk_pct": 0.05,
        "direction": "BUY",
        "warnings": [],
        "wait_until": None
    })
    decision = get_ai_decision(context, mock_response=mock_response)
    assert decision["final_decision"] == "REJECT"
    assert "o'zgartirishga urindi" in decision["warnings"][0]
    assert decision["risk_pct"] == 0.02  # O'zgartirilgan bo'lishi kerak

def test_ai_decision_alters_direction():
    context = {
        "voting_result": {
            "direction": "BUY",
            "risk_pct": 0.02
        }
    }
    mock_response = json.dumps({
        "final_decision": "EXECUTE",
        "reasoning": "Aslida bu SELL.",
        "risk_pct": 0.02,
        "direction": "SELL",
        "warnings": [],
        "wait_until": None
    })
    decision = get_ai_decision(context, mock_response=mock_response)
    assert decision["final_decision"] == "REJECT"
    assert "o'zgartirishga urindi" in decision["warnings"][0]
    assert decision["direction"] == "BUY"
