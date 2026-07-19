import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, timezone
import os
import anthropic
import json
from risk_manager import validate_trade
from order_manager import place_order, manage_open_trades
from smc_structure import SMCStructure
from pattern_detector import HarmonicPatternDetector, extract_pivots_from_data
from news_detector import NewsDetector
from news_straddle_engine import check_and_place_straddle, cleanup_straddle_orders
from supabase_sync import run_sync, fetch_bot_settings

# ===== 1. MT5 ga ulanish =====
if not mt5.initialize():
    print("MT5 ulanishda xatolik:", mt5.last_error())
    quit()

def analyze_and_trade(symbol, tf_major_str, tf_minor_str, tf_major, tf_minor, settings):
    print(f"\n[{symbol}] {tf_major_str}/{tf_minor_str} bo'yicha tahlil boshlandi...")
    # ===== 2. Narx ma'lumotlarini olish (100 ta bar SMC uchun zarur) =====
    rates_h1 = mt5.copy_rates_from_pos(symbol, tf_major, 0, 100)
    rates_m5 = mt5.copy_rates_from_pos(symbol, tf_minor, 0, 50)

    if rates_h1 is None or len(rates_h1) < 100:
        print(f"[{symbol}] Ma'lumot yetarli emas")
        return
        
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
    news_detector = NewsDetector(target_currencies=["USD", "EUR", "GBP"])
    news_detector.fetch_calendar()
    news_text = news_detector.format_news_for_ai(hours_back=48, minutes_ahead=720)

    # ===== 6. Ma'lumotni AI uchun matn formatiga aylantirish =====
    h1_text = df_h1[['time', 'open', 'high', 'low', 'close']].tail(20).to_string(index=False)
    m5_text = df_m5[['time', 'open', 'high', 'low', 'close']].tail(20).to_string(index=False)

    p_id = settings.get("prompt_identity", "Sen professional Forex treyderi va fundamental tahlilchisisan.")
    p_str = settings.get("prompt_strategy", "SMC, Garmonik patternlar va Iqtisodiy yangiliklarni birlashtirib eng yaxshi nuqtadan savdoga kirish qarorini qabul qilgin.")
    p_out = settings.get("prompt_output", 'JAVOBNI FAQAT quyidagi JSON formatida qaytar, format: {"signal": "BUY" | "SELL" | "HOLD", "confidence": 0-100, "reasoning": "...", "stop_loss_pips": 20, "take_profit_pips": 40}')

    # Vaqtinchalik prompt (AI'ga yuborilgan modal buyruq) tekshiruvi
    temp_prompt_text = ""
    temp_prompt = settings.get("prompt_temporary")
    temp_expires_at_str = settings.get("prompt_temporary_expires_at")

    if temp_prompt and temp_expires_at_str:
        try:
            # Datetime ni parse qilish (ISO 8601)
            expires_at = datetime.fromisoformat(temp_expires_at_str.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) < expires_at:
                temp_prompt_text = f"""
=== VAQTINCHALIK O'TA MUHIM KO'RSATMA ===
(Quyidagi qoidaga qat'iy amal qiling!)
{temp_prompt}
=======================================
"""
        except Exception as e:
            print(f"Vaqtinchalik promptni o'qishda xatolik: {e}")

    prompt = f"""{p_id}
{temp_prompt_text}
Quyida {symbol} juftligi uchun olingan Texnik (SMC + Garmonik patternlar) hamda Fundamental (Iqtisodiy yangiliklar) ma'lumotlar keltirilgan.

=== 1. NARX MA'LUMOTLARI ({symbol} {tf_major_str} - oxirgi 20 bar) ===
{h1_text}

=== 2. TEXNIK SMC TAHLILI ===
{smc_summary}

=== 3. HARMONIC PATTERN DETECTOR ===
{pattern_summary}

{news_text}

=== STRATEGIYA ISHONCH DARAJALARI (Muxim!) ===
SMC (Smart Money Concepts) ishonch talabi: {settings.get('strategy_weight_smc', 60)}%
Garmonik Patternlar ishonch talabi: {settings.get('strategy_weight_pattern', 60)}%
Fundamental Yangiliklar ishonch talabi: {settings.get('strategy_weight_news', 60)}%
QOIDA: Agar biron bir strategiya ushbu belgilangan ishonch foizidan past signal bersa, o'sha strategiya signalini IGNORE qiling (hisobga olmang)!

=== VAZIFA VA STRATEGIYA ===
{p_str}

=== NATIJA FORMATI ===
{p_out}
"""

    # ===== 7. Claude API ga so'rov yuborish =====
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    ai_text = response.content[0].text

    # Token usage & Cost calculation
    try:
        input_tokens = getattr(response.usage, "input_tokens", 0)
        output_tokens = getattr(response.usage, "output_tokens", 0)
        cost = (input_tokens * 0.8 / 1_000_000.0) + (output_tokens * 4.0 / 1_000_000.0)
        from supabase_sync import log_claude_cost
        log_claude_cost(cost)
    except Exception as sync_err:
        print(f"Cost sync failed: {sync_err}")

    # JSON qismini ajratib olish (agar AI qo'shimcha matn qo'shsa)
    ai_text_clean = ai_text.strip()
    if ai_text_clean.startswith("```"):
        ai_text_clean = ai_text_clean.split("```")[1]
        if ai_text_clean.startswith("json"):
            ai_text_clean = ai_text_clean[4:]

    try:
        ai_result = json.loads(ai_text_clean)
    except Exception as e:
        print(f"JSON parsing error for {symbol}: {e}")
        return

    print("=== AI SIGNALI ===")
    print(f"Signal: {ai_result.get('signal')}")
    print(f"Ishonch: {ai_result.get('confidence')}%")
    print(f"Sabab: {ai_result.get('reasoning')}")
    print(f"Stop-loss: {ai_result.get('stop_loss_pips')} pips")
    print(f"Take-profit: {ai_result.get('take_profit_pips')} pips")

    # ===== 8. Risk-boshqaruv orqali tekshirish =====
    conf_value = ai_result.get('confidence', 0)
    
    # Dinamik risk hisoblash:
    # Agar ishonch darajasi juda yuqori bo'lsa (masalan > 85), Ko'p strategiyali risk olinadi
    if conf_value >= 85:
        risk_pct = settings.get("risk_level_multiple_confirmation", 0.02)
    else:
        risk_pct = settings.get("risk_level_single_confirmation", 0.01)

    approved, message, lot_size = validate_trade(
        symbol=symbol,
        signal=ai_result.get('signal'),
        confidence=conf_value,
        stop_loss_pips=ai_result.get('stop_loss_pips', 20),
        settings=settings,
        risk_pct=risk_pct
    )

    print("\n=== RISK TEKSHIRUVI ===")
    print(f"Natija: {message}")

    if approved:
        print(f"OK: SAVDO TASDIQLANDI")
        print(f"Tavsiya etilgan lot hajmi: {lot_size}")
        
        # Order ochish
        success, msg, info = place_order(
            symbol=symbol,
            signal=ai_result.get('signal'),
            lot_size=lot_size,
            stop_loss_pips=ai_result.get('stop_loss_pips', 20),
            take_profit_pips=ai_result.get('take_profit_pips', 40)
        )
        print("MT5 Terminal Natijasi:", msg)
        if success:
            print("Order tafsilotlari:", info)
    else:
        print(f"XATO: SAVDO RAD ETILDI: {message}")


# ===== 1.5 Frontend sozlamalarini olish =====
settings = fetch_bot_settings()
print("Frontend sozlamalari yuklandi:", settings)

symbols = settings.get("symbols", ["EURUSD", "GBPUSD"])
tf_major_str = settings.get("timeframe_major", "H1")
tf_minor_str = settings.get("timeframe_minor", "M5")

TF_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}
tf_major = TF_MAP.get(tf_major_str, mt5.TIMEFRAME_H1)
tf_minor = TF_MAP.get(tf_minor_str, mt5.TIMEFRAME_M5)

print("\n=== OCHIQ POZITSIYALARNI BOSHQARISH (TRAILING/PARTIAL CLOSE) ===")
try:
    manage_open_trades()
except Exception as e:
    print(f"Ochiq pozitsiyalarni boshqarishda xatolik: {e}")

print("\n=== NEWS STRADDLE BOSHQARUVI ===")
try:
    check_and_place_straddle(symbols, settings)
    cleanup_straddle_orders()
except Exception as e:
    print(f"News Straddle boshqarishda xatolik: {e}")

for symbol in symbols:
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"OGOHLANTIRISH: {symbol} broker (MT5) tomonidan qo'llab-quvvatlanmaydi. O'tkazib yuborilmoqda.")
        continue
    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            print(f"OGOHLANTIRISH: {symbol} ni Market Watch da ko'rsatib bo'lmadi. O'tkazib yuborilmoqda.")
            continue
    analyze_and_trade(symbol, tf_major_str, tf_minor_str, tf_major, tf_minor, settings)

# ===== 9. Supabase ga ma'lumotlarni sinxronlash =====
print("\n=== SUPABASE SINXRONIZATSIYA ===")
run_sync()

mt5.shutdown()