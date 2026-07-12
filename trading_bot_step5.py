import MetaTrader5 as mt5
import pandas as pd
import os
import anthropic
import json
from risk_manager import validate_trade

# ===== 1. MT5 ga ulanish =====
if not mt5.initialize():
    print("MT5 ulanishda xatolik:", mt5.last_error())
    quit()

symbol = "EURUSD"

# ===== 2. Narx ma'lumotlarini olish =====
rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 50)
rates_m5 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 50)

df_h1 = pd.DataFrame(rates_h1)
df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')

df_m5 = pd.DataFrame(rates_m5)
df_m5['time'] = pd.to_datetime(df_m5['time'], unit='s')

# ===== 3. Ma'lumotni AI uchun matn formatiga aylantirish =====
h1_text = df_h1[['time', 'open', 'high', 'low', 'close']].tail(20).to_string(index=False)
m5_text = df_m5[['time', 'open', 'high', 'low', 'close']].tail(20).to_string(index=False)

prompt = f"""Sen professional forex tahlilchisisan. Quyida {symbol} juftligining narx ma'lumotlari berilgan.

H1 (1 soatlik) so'nggi 20 ta sham:
{h1_text}

M5 (5 daqiqalik) so'nggi 20 ta sham:
{m5_text}

Shu ma'lumotlar asosida JAVOBNI FAQAT quyidagi JSON formatida ber, boshqa hech qanday matn qo'shma:

{{
  "signal": "BUY" yoki "SELL" yoki "HOLD",
  "confidence": 0 dan 100 gacha son,
  "reasoning": "qisqacha sabab, 1-2 gap",
  "stop_loss_pips": son,
  "take_profit_pips": son
}}
"""

# ===== 4. Claude API ga so'rov yuborish =====
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

response = client.messages.create(
    model="claude-sonnet-4-6",
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

# ===== 5. Risk-boshqaruv orqali tekshirish =====
approved, message, lot_size = validate_trade(
    symbol=symbol,
    signal=ai_result['signal'],
    confidence=ai_result['confidence'],
    stop_loss_pips=ai_result['stop_loss_pips']
)

print("\n=== RISK TEKSHIRUVI ===")
print(f"Natija: {message}")

if approved:
    print(f"✅ SAVDO TASDIQLANDI")
    print(f"Tavsiya etilgan lot hajmi: {lot_size}")
else:
    print(f"❌ SAVDO RAD ETILDI: {message}")

mt5.shutdown()