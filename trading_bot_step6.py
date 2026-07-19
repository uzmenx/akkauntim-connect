import os
import json
import MetaTrader5 as mt5
import pandas as pd
import anthropic

from smc_structure import SMCStructure
from pattern_detector import HarmonicPatternDetector, extract_pivots_from_data
from news_detector import NewsDetector
from news_impact_analyzer import get_aggregated_news_summary
from smc_memory_bank import check_current_price_in_zone
from voting_engine import aggregate_signals
from risk_manager import validate_trade

def run_smart_bot(symbol="EURUSD"):
    if not mt5.initialize():
        print("MT5 ulanishda xatolik:", mt5.last_error())
        return

    # 1. Narx ma'lumotlarini olish
    rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 100)
    rates_m5 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 50)
    df_h1 = pd.DataFrame(rates_h1)
    df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
    df_m5 = pd.DataFrame(rates_m5)
    df_m5['time'] = pd.to_datetime(df_m5['time'], unit='s')
    
    current_price = df_m5['close'].iloc[-1]

    # 2. SMC Memory Bank tahlili
    smc_alerts = check_current_price_in_zone(symbol, current_price, buffer_pips=10.0)
    memory_bank_text = ""
    if smc_alerts:
        memory_bank_text = "🚨 SMC MEMORY BANK ALERTS (Tarixiy zonalar):\n"
        for a in smc_alerts:
            memory_bank_text += f"- Narx {a['time_created']} dagi {a['timeframe']} {a['direction']} FVG zonasiga kirdi (Chegaralar: {a['zone_bottom']} - {a['zone_top']}).\n"
    else:
        memory_bank_text = "SMC Memory Bank: Joriy narx atrofida kuchli tarixiy zonalar topilmadi.\n"

    # 3. Joriy SMC Struktura tahlili
    smc_detector = SMCStructure()
    smc_detector.run(df_h1['high'].tolist(), df_h1['low'].tolist(), df_h1['close'].tolist())
    smc_result = smc_detector.latest_context()
    
    smc_summary = "SMC ko'rsatkichlari aniqlanmadi."
    if smc_result:
        smc_summary = f"Trend: {smc_result.get('trend', 'N/A')} | Oxirgi hodisalar: {', '.join(smc_result.get('events', []))}"

    # 4. Pattern tahlili
    pivots = extract_pivots_from_data(df_h1, depth=5)
    pattern_detector = HarmonicPatternDetector(error_allowance=0.15)
    pattern_result = pattern_detector.detect_patterns(pivots) if len(pivots) >= 5 else None
    
    pattern_summary = "Pattern topilmadi."
    if pattern_result:
        pattern_summary = f"Aniqlangan: {pattern_result['type']} {', '.join(pattern_result['patterns'])}"

    # 5. Deep News Aggregator (Kelgusi xabarlar va Tarixiy statistika)
    news_detector = NewsDetector(target_currencies=["USD", "EUR"])
    news_detector.fetch_calendar()
    upcoming = news_detector.get_upcoming_news(impact_filter=["High"], minutes_ahead=1440) # next 24h
    
    deep_news_text = "=== FUNDAMENTAL & HISTORICAL NEWS ANALYSIS ===\n"
    if upcoming:
        deep_news_text += "Yaqin 24 soat ichida kutilayotgan O'ta Muhim (High Impact) yangiliklar va ularning o'tmishdagi statistikasi:\n\n"
        for event in upcoming:
            title = event.get('title')
            # Fetch smart statistical summary from our SQLite DB
            stats = get_aggregated_news_summary(symbol, title, lookback_months=120)
            
            deep_news_text += f"🔹 {event['country']} - {title} (Qolgan vaqt: {round(event.get('minutes_to_release',0)/60,1)} soat)\n"
            deep_news_text += f"   Prognoz: {event.get('forecast', 'N/A')} | Oldingi: {event.get('previous', 'N/A')}\n"
            deep_news_text += f"   📊 Tizim xulosasi: {stats}\n\n"
    else:
        deep_news_text += "Yaqin 24 soatda bozorni harakatlantiruvchi kuchli yangiliklar kutilmayapti.\n"

    # 6. AI Prompt (Claude ga yuborish)
    prompt = f"""Sen professional Forex treyderi va Quantitative Analistisan.
Sening asosiy ustunliging: xom ma'lumotlarni o'qishdan tashqari, tizim tomonidan berilgan "Tarixiy Xotira" (Memory Bank) xulosalariga tayanasan.

=== 1. JORIY HOLAT ({symbol}) ===
Hozirgi narx: {current_price}
{memory_bank_text}

=== 2. TEXNIK TAHLIL (H1) ===
SMC Holati: {smc_summary}
Harmonic Patternlar: {pattern_summary}

=== 3. DEEP NEWS AGGREGATOR ===
{deep_news_text}

=== VAZIFA ===
Yuqoridagi ma'lumotlarni tahlil qil. AI sifatida seni qiynamaslik uchun tizim allaqachon senga tarixiy yangiliklarning o'rtacha ta'sirini (foizlarda) hisoblab bergan. 
Agar narx kuchli tarixiy SMC zonasida (Memory Bank) bo'lsa va yaqinlashayotgan yangilikning tarixiy yo'nalishi buni tasdiqlasa, juda yuqori ishonch bilan savdo qilishing kerak.
Agar kelishuv bo'lmasa yoki yangilik natijasini oldindan bilib bo'lmasa, HOLD signalini ber.

JAVOBNI FAQAT JSON FORMATIDA QAYTAR (boshqa gap yozma):
{{
  "signal": "BUY" | "SELL" | "HOLD",
  "confidence": 0-100,
  "reasoning": "nega bu qarorga kelganing (qisqacha)",
  "stop_loss_pips": 10-50,
  "take_profit_pips": 20-150
}}
"""
    print("\n[AI ga yuborilayotgan so'rov tayyorlanmoqda...]\n")
    print("--- YUBORILAYOTGAN MA'LUMOT (TEJALGAN TOKENLAR BILAN) ---")
    print(deep_news_text)
    print(memory_bank_text)
    print("----------------------------------------------------------\n")
    
    # 7. Claude API call (Simulated here if no key, but we assume key exists or we just print the prompt for testing)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY topilmadi. Faqat prompt shakllantirildi.")
        mt5.shutdown()
        return

    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        ai_text = response.content[0].text
        ai_text_clean = ai_text.strip()
        if ai_text_clean.startswith("```"):
            ai_text_clean = ai_text_clean.split("```")[1]
            if ai_text_clean.startswith("json"):
                ai_text_clean = ai_text_clean[4:]
        
        ai_result = json.loads(ai_text_clean)
        
        print("=== AI XULOSASI ===")
        print(f"Signal: {ai_result['signal']} ({ai_result['confidence']}% ishonch)")
        print(f"Sabab: {ai_result['reasoning']}")
        
        # 8. Validatsiya (faqat ai_result ni bitta signal sifatida ko'rsatish)
        # Yoki voting_engine ni qo'shish. Ammo biz bu yerda AI ni yagona qaror qabul qiluvchi sifatida ishlatyapmiz.
        # Sizning avvalgi rejangizda "Voting Engine" AIni yonida ishlardi. 
        # Biz AIni xulosasini risk_manager orqali tekshiramiz.
        
        approved, msg, lot = validate_trade(symbol, ai_result['signal'], ai_result['confidence'], ai_result['stop_loss_pips'], risk_pct=0.02)
        print(f"Risk Natijasi: {msg} (Lot: {lot})")

    except Exception as e:
        print("AI API xatolik:", e)
        
    mt5.shutdown()

if __name__ == "__main__":
    run_smart_bot("EURUSD")
