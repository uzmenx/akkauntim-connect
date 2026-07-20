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
from ai_analysis import load_env, load_config

def run_smart_bot(symbol="EURUSD"):
    load_env()
    settings = load_config().get("trading", {})
    if not mt5.initialize():
        print("MT5 ulanishda xatolik:", mt5.last_error())
        return

    # 1. Narx ma'lumotlarini olish
    tf_map = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1,
        "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1
    }
    
    tf_major_str = settings.get("timeframe_major", "H1")
    tf_minor_str = settings.get("timeframe_minor", "M5")
    
    tf_major = tf_map.get(tf_major_str, mt5.TIMEFRAME_H1)
    tf_minor = tf_map.get(tf_minor_str, mt5.TIMEFRAME_M5)

    rates_major = mt5.copy_rates_from_pos(symbol, tf_major, 0, 100)
    rates_minor = mt5.copy_rates_from_pos(symbol, tf_minor, 0, 50)
    
    df_major = pd.DataFrame(rates_major)
    df_major['time'] = pd.to_datetime(df_major['time'], unit='s')
    df_minor = pd.DataFrame(rates_minor)
    df_minor['time'] = pd.to_datetime(df_minor['time'], unit='s')
    
    current_price = df_minor['close'].iloc[-1]

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
    smc_detector.run(df_major['high'].tolist(), df_major['low'].tolist(), df_major['close'].tolist())
    smc_result = smc_detector.latest_context()
    
    smc_summary = "SMC ko'rsatkichlari aniqlanmadi."
    if smc_result:
        smc_summary = f"Trend: {smc_result.get('trend', 'N/A')} | Oxirgi hodisalar: {', '.join(smc_result.get('events', []))}"

    # 4. Pattern tahlili
    pivots = extract_pivots_from_data(df_major, depth=5)
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
    news_signal_val = "HOLD"
    if upcoming:
        deep_news_text += "Yaqin 24 soat ichida kutilayotgan O'ta Muhim (High Impact) yangiliklar va ularning o'tmishdagi statistikasi:\n\n"
        for event in upcoming:
            title = event.get('title')
            # Fetch smart statistical summary from our SQLite DB
            stats = get_aggregated_news_summary(symbol, title, lookback_months=120)
            
            if "Ko'proq O'sish" in stats or "Buy" in stats or "Long" in stats: news_signal_val = "BUY"
            elif "Ko'proq Tushish" in stats or "Sell" in stats or "Short" in stats: news_signal_val = "SELL"
            
            deep_news_text += f"🔹 {event['country']} - {title} (Qolgan vaqt: {round(event.get('minutes_to_release',0)/60,1)} soat)\n"
            deep_news_text += f"   Prognoz: {event.get('forecast', 'N/A')} | Oldingi: {event.get('previous', 'N/A')}\n"
            deep_news_text += f"   📊 Tizim xulosasi: {stats}\n\n"
    else:
        deep_news_text += "Yaqin 24 soatda bozorni harakatlantiruvchi kuchli yangiliklar kutilmayapti.\n"

    # --- ALOHIDA SIGNALLAR (Voting) ---
    smc_sig = {"signal": "HOLD", "confidence": 0}
    if smc_result:
        t = smc_result.get('trend', '')
        if 'Up' in t: smc_sig = {"signal": "BUY", "confidence": 75}
        elif 'Down' in t: smc_sig = {"signal": "SELL", "confidence": 75}
        
    pat_sig = {"signal": "HOLD", "confidence": 0}
    if pattern_result:
        pt = pattern_result.get('type', '')
        if 'Bullish' in pt: pat_sig = {"signal": "BUY", "confidence": 75}
        elif 'Bearish' in pt: pat_sig = {"signal": "SELL", "confidence": 75}
        
    news_sig = {"signal": news_signal_val, "confidence": 80 if news_signal_val != "HOLD" else 0}
    
    voting_res = aggregate_signals(smc_sig, pat_sig, news_sig, {"strategy_weight_smc":60,"strategy_weight_pattern":60,"strategy_weight_news":60})
    voting_text = f"Voting Natijasi: {voting_res['signal']} (Kelishgan strategiyalar: {', '.join(voting_res['agreed_strategies'])})"

    # 6. AI Prompt (Claude ga yuborish)
    prompt = f"""Sen professional Forex treyderi va Quantitative Analistisan.
Sening asosiy ustunliging: xom ma'lumotlarni o'qishdan tashqari, tizim tomonidan berilgan "Tarixiy Xotira" (Memory Bank) xulosalariga tayanasan.

=== 1. JORIY HOLAT ({symbol}) ===
Hozirgi narx: {current_price}
{memory_bank_text}

=== 2. ALOHIDA STRATEGIYA SIGNALLARI ({tf_major_str}) ===
SMC Holati: {smc_summary} -> Signal: {smc_sig['signal']}
Harmonic Patternlar: {pattern_summary} -> Signal: {pat_sig['signal']}
Fundamental Yangiliklar: {news_sig['signal']}

=== 3. DEEP NEWS AGGREGATOR ===
{deep_news_text}

=== 4. VOTING ENGINE XULOSASI ===
{voting_text}

=== VAZIFA ===
Yuqoridagi 3 ta alohida strategiya signallarini va Voting Engine qarorini tahlil qil. AI sifatida seni qiynamaslik uchun tizim allaqachon senga tarixiy yangiliklarning o'rtacha ta'sirini (foizlarda) hisoblab bergan. 
Agar narx kuchli tarixiy SMC zonasida (Memory Bank) bo'lsa va yaqinlashayotgan yangilikning tarixiy yo'nalishi buni tasdiqlasa, juda yuqori ishonch bilan savdo qilishing kerak.
Agar strategiyalar bir-biriga zid kelsa yoki Voting Engine HOLD bergan bo'lsa, xavfsizlik uchun HOLD signalini ber.

JAVOBNI FAQAT JSON FORMATIDA QAYTAR (boshqa gap yozma):
{{
  "signal": "BUY" | "SELL" | "BUY_LIMIT" | "SELL_LIMIT" | "BUY_STOP" | "SELL_STOP" | "HOLD",
  "confidence": 0-100,
  "reasoning": "nega bu qarorga kelganing (qisqacha)",
  "entry_price": "agar Limit yoki Stop order bo'lsa, qaysi narxda ochilishi. Aks holda null",
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
    
    models_to_try = [
        "claude-sonnet-5",
        "claude-sonnet-4-6",
        "claude-sonnet-4-5-20250929",
        "claude-haiku-4-5-20251001",
        "claude-fable-5"
    ]
    
    ai_result = None
    for model_name in models_to_try:
        try:
            print(f"[{model_name}] modeliga so'rov yuborilmoqda...")
            response = client.messages.create(
                model=model_name,
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
            print(f"Model: {model_name}")
            print(f"Signal: {ai_result['signal']} ({ai_result['confidence']}% ishonch)")
            print(f"Sabab: {ai_result['reasoning']}")
            
            break # Muvaqqiyatli bo'lsa sikldan chiqamiz
            
        except Exception as e:
            print(f"[{model_name}] da xatolik: {e}")
            print("Avtomatik ravishda keyingi modelga o'tilmoqda...\n")
            continue
            
    if not ai_result:
        print("Barcha AI modellari ishlamadi. Savdo bekor qilindi.")
        mt5.shutdown()
        return
        
    # 8. Validatsiya
    approved, msg, lot = validate_trade(symbol, ai_result['signal'], ai_result['confidence'], ai_result.get('stop_loss_pips', 30), settings, risk_pct=0.02)
    print(f"Risk Natijasi: {msg} (Lot: {lot})")
    
    # 9. Order ochish
    if approved and lot is not None:
        from order_manager import place_order
        print(f"[{symbol}] uchun order ochilmoqda...")
        
        entry_price = ai_result.get('entry_price')
        if entry_price == "null": entry_price = None
        if entry_price is not None:
            try:
                entry_price = float(entry_price)
            except:
                entry_price = None

        success, order_msg, order_info = place_order(
            symbol=symbol,
            signal=ai_result['signal'],
            lot_size=lot,
            stop_loss_pips=ai_result.get('stop_loss_pips', 30),
            take_profit_pips=ai_result.get('take_profit_pips', 60),
            entry_price=entry_price
        )
        if success:
            print(f"Muvaffaqiyatli! Ticket: {order_info.get('ticket', 'N/A')}")
        else:
            print(f"Order ochishda xatolik: {order_msg}")
        
    mt5.shutdown()

if __name__ == "__main__":
    run_smart_bot("EURUSD")
