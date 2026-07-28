"""
integration_example.py

Bu fayl main.py'ga qanday integratsiya qilishni ko'rsatadi.
Yangi Shadow Learning v2 funksiyalaridan foydalanadi (Vector Search + Feedback Loop).
"""

from ai_strategist import AIStrategist


def example_llm_call(prompt: str) -> str:
    raise NotImplementedError(
        "Buni o'zingizning LLM client chaqiruvingiz bilan almashtiring"
    )


def build_enriched_prompt(context: dict, market_condition: str, strategist: AIStrategist) -> str:
    # 1. Joriy holatni vektor qidiruv uchun matnga aylantiramiz
    current_situation = f"{context.get('symbol')} {context.get('timeframe')} timeframeda. " \
                        f"SMC signali: {context.get('smc', {}).get('signal', 'yoq')}. " \
                        f"Wyckoff fazasi: {context.get('wyckoff_phase', 'yoq')}. " \
                        f"Bozor holati: {market_condition}."
                        
    # 2. ChromaDB RAG orqali eng mos qoidalarni olamiz
    book_knowledge = strategist.get_relevant_context(current_situation, market_condition)

    knowledge_section = ""
    if book_knowledge:
        knowledge_section = f"""
STRATEGIYA KITOBLARIDAN OLINGAN QOIDALAR VA ULARNING STATISTIKASI:
{book_knowledge}

Yuqoridagi bilimni hisobga oling, ayniqsa statistikasi yomon (ko'p zarar qilgan) qoidalardan ehtiyot bo'ling.
Agar biror qoidani tanlasangiz, uning ID sini ham qaytaring.
"""

    prompt = f"""Siz trading bot uchun yakuniy qaror qabul qiluvchisiz.

BOZOR KONTEKSTI:
- Symbol: {context.get('symbol', 'N/A')}
- Timeframe: {context.get('timeframe', 'N/A')}
- Narx: {context.get('price', 'N/A')}
- SMC signal: {context.get('smc', {})}
- Wyckoff fazasi: {context.get('wyckoff_phase', 'N/A')}
- Bozor sharoiti: {market_condition}
{knowledge_section}
VAZIFA:
Yuqoridagi barcha ma'lumot asosida savdo qarorini chiqaring.

JSON formatda javob bering:
{{
  "direction": "BUY/SELL/HOLD",
  "entry": <raqam yoki null>,
  "sl": <raqam yoki null>,
  "tp": <raqam yoki null>,
  "confidence": <0-100>,
  "reasoning": "<qisqa tushuntirish>",
  "used_insight_id": "<foydalanilgan qoida ID si, agar bo'lsa>"
}}"""

    return prompt


# ==================== ISHLATISH MISOLI ====================

def run_cycle_example(context: dict, market_condition: str, strategist: AIStrategist, claude_call_fn):
    """
    Bitta trade signalida ishlatiladigan to'liq oqim.
    """
    prompt = build_enriched_prompt(context, market_condition, strategist)
    response_json = claude_call_fn(prompt)
    
    # Keling, JSON ni parse qilamiz (real loyihada yaxshiroq parser kerak)
    import json
    try:
        decision = json.loads(response_json)
        used_id = decision.get("used_insight_id")
    except Exception:
        used_id = None
        
    # Tasavvur qilamiz, trade ochildi va 1 soatdan keyin natijasi ma'lum bo'ldi.
    # Agar biz u qoidadan foydalangan bo'lsak, natijani darhol feedback loop orqali jo'natamiz.
    
    return response_json, used_id

    # Aslida feedback loop ni trade yopiluvchi (websocket/webhook) joydan chaqirasiz:
    # if used_id:
    #     strategist.record_trade_result(insight_id=used_id, success=True, pnl=15.5, reason="TP urildi")

if __name__ == "__main__":
    print(__doc__)
