import MetaTrader5 as mt5
import pandas as pd
import os
import anthropic
import json
from risk_manager import validate_trade
from smc_structure import SMCStructure
from pattern_detector import HarmonicPatternDetector, extract_pivots_from_data
from news_detector import NewsDetector
from supabase_sync import run_sync

# ===== 1. MT5 ga ulanish =====
if not mt5.initialize():
    print("MT5 ulanishda xatolik:", mt5.last_error())
    quit()

symbol = "EURUSD"

# ===== 2. Narx ma'lumotlarini olish (100 ta bar SMC uchun zarur) =====
rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 100)
rates_m5 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 50)

df_h1 = pd.DataFrame(rates_h1)
df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')

df_m5 = pd.DataFrame(rates_m5)
df_m5['time'] = pd.to_datetime(df_m5['time'], unit='s')

# ===== 3. SMC Tahlili =====
smc_detector = SMCStructure()
smc_detector.run(df_h1['high'].tolist(), df_h1['low'].tolist(), df_h1['close'].tolist())
smc_result = smc_detector.latest_context()

smc_summary = "SMC ko'rsatkichlari aniqlanmadi yoki yetarli ma'lumot yo'q."
if smc_result:
    smc_summary = f"Trend: {smc_result.get('trend', 'N/A')}\n"
    smc_summary += f"Oxirgi High: {smc_result.get('high_val', 'N/A')} | Oxirgi Low: {smc_result.get('low_val', 'N/A')}\n"
    if smc_result.get('events'):
        smc_summary += f"Oxirgi SMC hodisalari: {', '.join(smc_result['events'])}"

# ===== 4. Harmonic Pattern Tahlili =====
pivots = extract_pivots_from_data(df_h1, depth=5)
pattern_detector = HarmonicPatternDetector(error_allowance=0.15)
pattern_result = pattern_detector.detect_patterns(pivots) if len(pivots) >= 5 else None

pattern_summary = "Garmonik patternlar topilmadi."
if pattern_result:
    pattern_summary = f"Aniqlangan pattern: {pattern_result['type']} {', '.join(pattern_result['patterns'])}\n"
    pattern_summary += f"Nisbatlar (Ratios): {pattern_result['ratios']}"

# ===== 5. News Tahlili (Real-time & History) =====
news_detector = NewsDetector(target_currencies=["USD", "EUR"])
news_detector.fetch_calendar()
news_text = news_detector.format_news_for_ai(hours_back=48, minutes_ahead=720)

# ===== 6. Ma'lumotni AI uchun matn formatiga aylantirish =====
h1_text = df_h1[['time', 'open', 'high', 'low', 'close']].tail(20).to_string(index=False)
m5_text = df_m5[['time', 'open', 'high', 'low', 'close']].tail(20).to_string(index=False)

prompt = f"""Sen professional Forex treyderi va fundamental tahlilchisisan.
Quyida {symbol} juftligi uchun olingan Texnik (SMC + Garmonik patternlar) hamda Fundamental (Iqtisodiy yangiliklar) ma'lumotlar keltirilgan.

=== 1. NARX MA'LUMOTLARI ({symbol} H1 - oxirgi 20 bar) ===
{h1_text}

=== 2. TEXNIK SMC TAHLILI ===
{smc_summary}

=== 3. HARMONIC PATTERN DETECTOR ===
{pattern_summary}

{news_text}

=== VAZIFA ===
Ushbu texnik ko'rsatkichlarni hamda yaqinda chiqqan va kelgusi 12 soatda chiqadigan yangiliklarni (Actual va Forecast qiymatlari) tahlil qil.
Ushbu yangiliklarning EURUSD yo'nalishiga fundamental ta'sirini bahola va order ochish/yopish bo'yicha yakuniy qaror ber (BUY, SELL yoki HOLD).

JAVOBNI FAQAT quyidagi JSON formatida qaytar, boshqa hech qanday izoh yoki tushuntirish yozma:

{{
  "signal": "BUY" yoki "SELL" yoki "HOLD",
  "confidence": 0 dan 100 gacha son,
  "reasoning": "fundamental va texnik tahlilning qisqacha birlashtirilgan xulosasi (o'zbek tilida, 2-3 gap)",
  "stop_loss_pips": son,
  "take_profit_pips": son
}}
"""

# ===== 7. Claude API ga so'rov yuborish =====
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=500,
    messages=[{"role": "user", "content": prompt}]
)

ai_text = response.content[0].text

# JSON qismini ajratib olish (agar AI qo'shimcha matn qo'shsa)
ai_text_clean = ai_text.strip()
if ai_text_clean.startswith("```"):
    ai_text_clean = ai_text_clean.split("```")[1]
    if ai_text_clean.startswith("json"):
        ai_text_clean = ai_text_clean[4:]

ai_result = json.loads(ai_text_clean)

print("=== AI SIGNALI ===")
print(f"Signal: {ai_result['signal']}")
print(f"Ishonch: {ai_result['confidence']}%")
print(f"Sabab: {ai_result['reasoning']}")
print(f"Stop-loss: {ai_result['stop_loss_pips']} pips")
print(f"Take-profit: {ai_result['take_profit_pips']} pips")

# ===== 8. Risk-boshqaruv orqali tekshirish =====
approved, message, lot_size = validate_trade(
    symbol=symbol,
    signal=ai_result['signal'],
    confidence=ai_result['confidence'],
    stop_loss_pips=ai_result['stop_loss_pips']
)

print("\n=== RISK TEKSHIRUVI ===")
print(f"Natija: {message}")

if approved:
    print(f"OK: SAVDO TASDIQLANDI")
    print(f"Tavsiya etilgan lot hajmi: {lot_size}")
else:
    print(f"XATO: SAVDO RAD ETILDI: {message}")

# ===== 9. Supabase ga ma'lumotlarni sinxronlash =====
print("\n=== SUPABASE SINXRONIZATSIYA ===")
run_sync()

mt5.shutdown()