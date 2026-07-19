import MetaTrader5 as mt5
import pandas as pd
import os
import anthropic
from smc_structure import SMCStructure
from pattern_detector import HarmonicPatternDetector, extract_pivots_from_data
from news_detector import NewsDetector

def main():
    print("--- Combined AI Analysis Validation (SMC + Patterns + News) ---")
    
    # 1. MT5 ga ulanish
    if not mt5.initialize():
        print("MT5 ulanishda xatolik:", mt5.last_error())
        # Agar MT5 ulanmasa, mock ma'lumotlar bilan davom etamiz
        print("MT5 ulanmaganligi sababli testni mock ma'lumotlar bilan davom ettiramiz.")
        rates_h1 = []
        rates_m5 = []
    else:
        symbol = "EURUSD"
        rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 100)
        rates_m5 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 100)
        mt5.shutdown()

    # 2. DataFrame hosil qilish
    if len(rates_h1) > 0:
        df_h1 = pd.DataFrame(rates_h1)
        df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
        df_m5 = pd.DataFrame(rates_m5)
        df_m5['time'] = pd.to_datetime(df_m5['time'], unit='s')
    else:
        # Mock data generating for testing
        from datetime import datetime, timedelta
        import numpy as np
        dates = [datetime.now() - timedelta(hours=x) for x in range(100)]
        dates.reverse()
        df_h1 = pd.DataFrame(index=dates)
        prices = 1.1000 + np.sin(np.linspace(0, 10, 100)) * 0.02
        df_h1['high'] = prices + 0.002
        df_h1['low'] = prices - 0.002
        df_h1['close'] = prices
        df_h1['open'] = prices - 0.001
        df_h1['time'] = df_h1.index

        df_m5 = df_h1.copy() # Soddalashtirish uchun

    # 3. SMC Tahlili
    smc_detector = SMCStructure()
    smc_detector.run(df_h1['high'].tolist(), df_h1['low'].tolist(), df_h1['close'].tolist())
    smc_result = smc_detector.latest_context()
    
    # 4. Pattern Tahlili
    pivots = extract_pivots_from_data(df_h1, depth=5)
    pattern_detector = HarmonicPatternDetector(error_allowance=0.15)
    pattern_result = pattern_detector.detect_patterns(pivots) if len(pivots) >= 5 else None

    # 5. News Tahlili
    news_detector = NewsDetector(target_currencies=["USD", "EUR"])
    news_detector.fetch_calendar()
    # 48 soatlik tarix va 12 soatlik bo'lajak yangiliklarni tahlil qilish uchun AI ga yuboramiz
    news_text = news_detector.format_news_for_ai(hours_back=48, minutes_ahead=720)

    # 6. Prompt tayyorlash
    h1_text = df_h1[['time', 'open', 'high', 'low', 'close']].tail(15).to_string(index=False)
    
    smc_summary = "SMC ko'rsatkichlari aniqlanmadi yoki yetarli ma'lumot yo'q."
    if smc_result:
        smc_summary = f"Trend: {smc_result.get('trend', 'N/A')}\n"
        smc_summary += f"Oxirgi High: {smc_result.get('high_val', 'N/A')} | Oxirgi Low: {smc_result.get('low_val', 'N/A')}\n"
        if smc_result.get('events'):
            smc_summary += f"Oxirgi SMC hodisalari: {', '.join(smc_result['events'])}"

    pattern_summary = "Garmonik patternlar topilmadi."
    if pattern_result:
        pattern_summary = f"Aniqlangan pattern: {pattern_result['type']} {', '.join(pattern_result['patterns'])}\n"
        pattern_summary += f"Nisbatlar (Ratios): {pattern_result['ratios']}"

    prompt = f"""Sen professional Forex treyderi va fundamental tahlilchisisan.
Quyida EURUSD uchun olingan Texnik (SMC + Garmonik patternlar) hamda Fundamental (Iqtisodiy yangiliklar) ma'lumotlar keltirilgan.

=== 1. NARX MA'LUMOTLARI (EURUSD H1 - oxirgi 15 bar) ===
{h1_text}

=== 2. TEXNIK SMC TAHLILI ===
{smc_summary}

=== 3. HARMONIC PATTERN DETECTOR ===
{pattern_summary}

{news_text}

=== VAZIFA ===
Ushbu texnik ko'rsatkichlarni hamda yangiliklarning haqiqiy (Actual) va prognoz (Forecast) ko'rsatkichlarini chuqur tahlil qil.
Ayniqsa, yaqinda chiqqan yangiliklarning (masalan, AQSh yoki Yevrohudud iqtisodiy ko'rsatkichlari) EURUSD yo'nalishiga fundamental ta'sirini bahola.
Shu asosida bozorda qanday harakat (BUY, SELL yoki HOLD) qilish bo'yicha qaror ber.

JAVOBNI FAQAT quyidagi JSON formatida qaytar, boshqa hech qanday izoh yoki tushuntirish yozma:

{{
  "signal": "BUY" yoki "SELL" yoki "HOLD",
  "confidence": 0 dan 100 gacha foiz,
  "reasoning": "fundamental va texnik tahlilning qisqacha birlashtirilgan xulosasi (o'zbek tilida, 2-3 gap)",
  "stop_loss_pips": son (HOLD bo'lsa 0),
  "take_profit_pips": son (HOLD bo'lsa 0)
}}
"""

    print("\n--- GENERATED PROMPT FOR AI ---")
    print(prompt)

    # 7. Claude API ga yuborish
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n[WARNING] ANTHROPIC_API_KEY topilmadi. AI so'rovi yuborilmadi.")
        return

    print("\nCalling Claude API...")
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        print("\n=== AI RESPONSE ===")
        print(response.content[0].text)
    except Exception as e:
        print(f"API chaqiruvida xatolik yuz berdi: {e}")

if __name__ == '__main__':
    main()
