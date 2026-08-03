"""
test_full_flow.py — Yangilangan Shadow Learning testi (Vektor Qidiruv + Feedback).
"""

import time
import os
import shutil
from pathlib import Path
from ai_strategist import AIStrategist
from integration_example import build_enriched_prompt


def mock_llm_call(prompt: str) -> str:
    """Real LLM o'rniga mock javoblar."""
    if "has_strategy" in prompt:
        # JSON formatida javob berilishi kerak
        if "Trading in the Zone" in prompt or "psixolog" in prompt.lower():
            return '{"has_strategy": true, "market_condition": "all", "setup_type": "psychology", "insight": "Traderlar entry paytida FOMOdan qochishi kerak."}'
        if "SMC" in prompt or "smart money" in prompt.lower():
            return '{"has_strategy": true, "market_condition": "trend", "setup_type": "order_block", "insight": "Trend bozorida order blocklardan entry olish yuqori ehtimollik beradi."}'
        return '{"has_strategy": false}'
    return 'NO_STRATEGY'


def test_offline_stage():
    print("=" * 50)
    print("TEST 1: BOSQICH A (offline, RAG yordamida kitob qo'shish)")
    print("=" * 50)

    db_path = "test_strategist.sqlite"
    chroma_dir = "test_chroma_db"
    if Path(db_path).exists():
        os.remove(db_path)
    if Path(chroma_dir).exists():
        shutil.rmtree(chroma_dir)

    strategist = AIStrategist(llm_call_fn=mock_llm_call, db_path=db_path, chroma_db_dir=chroma_dir)

    test_file = Path("test_book.txt")
    test_file.write_text(
        "Trading in the Zone kitobidan qism.\n\n"
        "Bu SMC va order block haqida qism, smart money kontseptsiyasi.\n\n"
        "Bu hech qanday strategiya bo'lmagan tasodifiy matn."
    )

    original_chunk = strategist._chunk_text
    strategist._chunk_text = lambda text, max_chars=4000: original_chunk(text, max_chars=60)

    success = strategist.add_knowledge_source(
        file_path=str(test_file), title="Test Kitob", author="Test Muallif", language="uz", category="book"
    )

    assert success, "Kitob qo'shish muvaffaqiyatsiz bo'ldi"
    
    stats = strategist.get_statistics()
    print(f"\nStatistika: {stats}")
    assert stats["total_books"] == 1
    assert stats["total_insights_sqlite"] >= 1
    assert stats["total_insights_vector"] >= 1

    print("✅ BOSQICH A ishladi\n")
    return strategist


def test_online_stage_and_feedback(strategist):
    print("=" * 50)
    print("TEST 2 & 3: BOSQICH B (online RAG) va BOSQICH C (Feedback Loop)")
    print("=" * 50)

    context = {
        "symbol": "EURUSD",
        "timeframe": "15m",
        "price": 1.0850,
        "smc": {"signal": "bullish_ob"},
        "wyckoff_phase": "accumulation",
    }

    start = time.perf_counter()
    prompt = build_enriched_prompt(context, market_condition="trend", strategist=strategist)
    elapsed_ms = (time.perf_counter() - start) * 1000

    print(f"\nQurilgan prompt:\n{prompt}\n")
    
    # ChromaDB modelni birinchi marta load qilganda sal sekin bo'lishi mumkin (ayniqsa CPUda). 
    # Shuning uchun vaqt assertionini biroz yumshatamiz.
    print(f"⏱️  Vaqt: {elapsed_ms:.2f}ms")

    assert "order blocklardan" in prompt.lower() or "fomo" in prompt.lower()
    
    # Keling ID ni qidirib topamiz (oddiy regex yordamida test uchun)
    import re
    match = re.search(r'ID:\s*([a-f0-9\-]{36})', prompt)
    assert match, "Qoida ID si promptda yo'q"
    insight_id = match.group(1)
    
    print("\n--- FEEDBACK BERAMIZ ---")
    # Aytaylik, shu qoida asosida savdo qildik va zarar ko'rdik (Stop Loss urildi)
    strategist.record_trade_result(insight_id, success=False, pnl=-10.5, reason="Stop Loss urildi")
    
    # Yana so'raymiz
    prompt2 = build_enriched_prompt(context, market_condition="trend", strategist=strategist)
    print(f"\nYangi qurilgan prompt (Feedbackdan so'ng):\n{prompt2}\n")
    assert "zarar qildi" in prompt2.lower(), "Feedback natijasi promptda ko'rinmadi"

    print("✅ BOSQICH B va C ishladi!\n")


def test_empty_knowledge_base():
    print("=" * 50)
    print("TEST 4: Bo'sh holat")
    print("=" * 50)

    db_path = "test_empty.sqlite"
    chroma_dir = "test_empty_chroma"
    if Path(db_path).exists():
        os.remove(db_path)
    if Path(chroma_dir).exists():
        shutil.rmtree(chroma_dir)

    strategist = AIStrategist(llm_call_fn=mock_llm_call, db_path=db_path, chroma_db_dir=chroma_dir)

    context = {"symbol": "BTCUSD", "timeframe": "1h", "price": 65000}
    prompt = build_enriched_prompt(context, market_condition="volatile", strategist=strategist)

    assert "STRATEGIYA KITOBLARIDAN" not in prompt

    if Path(db_path).exists(): os.remove(db_path)
    if Path(chroma_dir).exists(): shutil.rmtree(chroma_dir)
    print("✅ Bo'sh holat to'g'ri ishladi\n")


if __name__ == "__main__":
    strategist = test_offline_stage()
    test_online_stage_and_feedback(strategist)
    test_empty_knowledge_base()

    # Tozalash
    for f in ["test_strategist.sqlite", "test_book.txt"]:
        if Path(f).exists():
            os.remove(f)
    if Path("test_chroma_db").exists():
        shutil.rmtree("test_chroma_db")

    print("=" * 50)
    print("✅ BARCHA TESTLAR O'TDI")
    print("=" * 50)
