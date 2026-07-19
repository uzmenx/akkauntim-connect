import MetaTrader5 as mt5
import pandas as pd
import os
import json
import sqlite3
import hashlib
from datetime import datetime
import anthropic

from smc_engine import analyze_market_structure
from harmonic_engine import analyze_harmonic_patterns
from news_trade_scheduler import get_news_signal
from voting_engine import aggregate_signals

def load_env():
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ[k.strip()] = v.strip().strip('"').strip("'")

def load_config():
    if os.path.exists('config.json'):
        with open('config.json', 'r') as f:
            return json.load(f)
    return {
        "trading": {
            "timeframe_major": "H1",
            "timeframe_minor": "M5",
        },
        "ai": {
            "model": "claude-3-5-sonnet-20241022",
        }
    }

def init_db():
    conn = sqlite3.connect('decisions_log.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ai_decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            pair TEXT,
            timeframe TEXT,
            context_json TEXT,
            prompt TEXT,
            ai_response TEXT,
            final_decision TEXT,
            risk_pct REAL
        )
    ''')
    conn.commit()
    
    # Cache ustunini qo'shish
    try:
        cursor.execute("ALTER TABLE ai_decisions ADD COLUMN context_hash TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass # Allaqachon mavjud
        
    # Tokenlar va cost ustunlarini qo'shish
    try:
        cursor.execute("ALTER TABLE ai_decisions ADD COLUMN input_tokens INTEGER")
        cursor.execute("ALTER TABLE ai_decisions ADD COLUMN output_tokens INTEGER")
        cursor.execute("ALTER TABLE ai_decisions ADD COLUMN cost REAL")
        conn.commit()
    except sqlite3.OperationalError:
        pass
        
    conn.close()

def log_decision(pair, timeframe, context, prompt, ai_response, final_decision, risk_pct, context_hash=None, input_tokens=None, output_tokens=None, cost=None):
    init_db()
    conn = sqlite3.connect('decisions_log.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ai_decisions (timestamp, pair, timeframe, context_json, prompt, ai_response, final_decision, risk_pct, context_hash, input_tokens, output_tokens, cost)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().isoformat(),
        pair,
        timeframe,
        json.dumps(context, ensure_ascii=False),
        prompt,
        json.dumps(ai_response, ensure_ascii=False) if isinstance(ai_response, dict) else str(ai_response),
        final_decision,
        risk_pct,
        context_hash,
        input_tokens,
        output_tokens,
        cost
    ))
    conn.commit()
    conn.close()

def get_market_data(symbol, timeframe, n_bars=100):
    tf_map = {
        "H1": mt5.TIMEFRAME_H1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
    }
    mt5_tf = tf_map.get(timeframe, mt5.TIMEFRAME_H1)
    rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, n_bars)
    if rates is None or len(rates) == 0:
        return pd.DataFrame()
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    return df

def extract_smc_signal(smc_result):
    if not smc_result:
        return {"signal": "HOLD", "confidence": 0}
    trend = smc_result.get("trend", {})
    int_trend = trend.get("internal", "No Trend")
    if int_trend == "Up Trend":
        return {"signal": "BUY", "confidence": 75}
    elif int_trend == "Down Trend":
        return {"signal": "SELL", "confidence": 75}
    return {"signal": "HOLD", "confidence": 0}

def extract_pattern_signal(pattern_result):
    if not pattern_result:
        return {"signal": "HOLD", "confidence": 0}
    sig = pattern_result.get("signal", "NEUTRAL")
    if sig == "BUY":
        return {"signal": "BUY", "confidence": 75}
    elif sig == "SELL":
        return {"signal": "SELL", "confidence": 75}
    return {"signal": "HOLD", "confidence": 0}

def extract_news_signal(news_result):
    if not news_result:
        return {"signal": "HOLD", "confidence": 0}
    rec = news_result.get("recommendation", "neutral")
    if rec == "prepare_long":
        return {"signal": "BUY", "confidence": 80}
    elif rec == "prepare_short":
        return {"signal": "SELL", "confidence": 80}
    return {"signal": "HOLD", "confidence": 0}

def build_decision_context(pair: str, timeframe: str, settings: dict = None) -> dict:
    if settings is None:
        settings = {}
        
    df_major = get_market_data(pair, timeframe, 150)
    current_price = 0.0
    if not df_major.empty:
        current_price = float(df_major.iloc[-1]['close'])
        
    smc_result = None
    pattern_result = None
    if not df_major.empty:
        smc_result = analyze_market_structure(df_major)
        pattern_result = analyze_harmonic_patterns(df_major)
        
    news_result = get_news_signal(pair)
    
    smc_data = extract_smc_signal(smc_result)
    pattern_data = extract_pattern_signal(pattern_result)
    news_data = extract_news_signal(news_result)
    
    voting_result = aggregate_signals(smc_data, pattern_data, news_data, settings)
    
    return {
        "pair": pair,
        "timeframe": timeframe,
        "current_price": current_price,
        "smc_structure": smc_result if smc_result else {},
        "harmonic_pattern": pattern_result if pattern_result else {},
        "news_context": news_result if news_result else {},
        "voting_result": {
            "direction": voting_result.get("signal", "HOLD"),
            "risk_pct": voting_result.get("risk_pct", 0.0),
            "agreeing_strategies": voting_result.get("agreed_strategies", []),
            "confidence_scores": {
                "SMC": smc_data["confidence"],
                "Pattern": pattern_data["confidence"],
                "News": news_data["confidence"]
            }
        }
    }

def build_claude_prompt(context: dict) -> str:
    pair = context.get('pair', 'Unknown')
    price = context.get('current_price', 0.0)
    
    smc = context.get('smc_structure', {})
    trend = smc.get('trend', {})
    smc_summary = f"Trend (Internal): {trend.get('internal', 'N/A')}, Trend (External): {trend.get('external', 'N/A')}"
    last_bos = smc.get('last_bos', {})
    if last_bos:
        smc_summary += f"\\nOxirgi BoS: {last_bos.get('type', '')} at {last_bos.get('price', '')}"
        
    pat = context.get('harmonic_pattern', {})
    pat_summary = f"Pattern signal: {pat.get('signal', 'NEUTRAL')}"
    if pat.get('patterns'):
        pat_summary += f", Patterns: {', '.join([p['name'] for p in pat.get('patterns', [])])}"
        
    news = context.get('news_context', {})
    next_event = news.get('next_event') or {}
    hist_bias = news.get('historical_bias') or {}
    news_summary = f"Keyingi yangilik: {next_event.get('name', 'None')} ({next_event.get('minutes_to_release', 'N/A')} daqiqa qoldi)"
    if hist_bias:
        news_summary += f"\\nTarixiy Bias: {hist_bias.get('direction', 'Neutral')} (Ishonch: {hist_bias.get('confidence', 0)})"
        
    vote = context.get('voting_result', {})
    
    risk_info = context.get('risk_manager', {})
    risk_summary = ""
    if risk_info:
        risk_summary = f"\n\n=== RISK BOSHQRUV ===\nKunlik zarar: {risk_info.get('daily_drawdown_pct', 0)}% (Limit: {risk_info.get('daily_limit_pct', 10)}%)"
        
    prompt = f"""Quyida {pair} juftligi uchun olingan savdo va iqtisodiy ma'lumotlar berilgan.

Joriy narx: {price}

=== TEXNIK SMC TAHLILI ===
{smc_summary}

=== HARMONIC PATTERN DETECTOR ===
{pat_summary}

=== YANGILIKLAR KONTEKSTI ===
{news_summary}

=== VOTING ENGINE NATIJASI ===
Yo'nalish (Direction): {vote.get('direction')}
Risk foizi: {vote.get('risk_pct')}%
Kelishgan strategiyalar: {', '.join(vote.get('agreeing_strategies', []))}{risk_summary}

DIQQAT:
Voting Engine allaqachon risk% va yo'nalishni hisoblab bergan. Sening vazifang buni qayta hisoblash EMAS — balki quyidagi savolga javob berish: shu kontekstda bu savdoni HOZIR ochish xavfsizmi, yoki kutish/rad etish kerakmi?

Quyidagi qat'iy qoidalarga rioya qil:
1. Yangiliklar va straddle: Bot endilikda yangilik payti qopqon (straddle) qo'yadi. Shuning uchun sening bu yerdagi tahliling asosan fundamental bias va texnik SMC ga asoslanishi kerak. Agar SMC va Fundamental tahlil bir-birini rad etsa, REJECT qil.
2. Risk boshqaruvi limitlari: Agar joriy kunlik zarar (drawdown) va ochilayotgan savdoning risk% yig'indisi kunlik limitdan oshib ketadigan bo'lsa (ya'ni joriy_zarar - risk_pct <= limit_pct, masalan -8% - 4% = -12%, bu esa -10% lik limitdan o'tib ketgan), savdoni darhol REJECT qilishing SHART. Kunlik limit buzilmasligi eng oliy ustuvorlikdir.

Agar yuqoridagi qoidalarga ko'ra shartlar mos bo'lsa EXECUTE qaytar.
Yo'nalish ({vote.get('direction')}) va risk% ni aslo o'zgartirma.

JAVOBNI FAQAT quyidagi JSON formatida qaytar, boshqa hech qanday qo'shimcha matn yozma:
{{
    "final_decision": "EXECUTE" yoki "REJECT" yoki "WAIT",
    "reasoning": "Sening qisqa izohing (o'zbek tilida)",
    "risk_pct": {vote.get('risk_pct')},
    "direction": "{vote.get('direction')}",
    "warnings": ["xavf 1", "xavf 2"],
    "wait_until": "agar WAIT bo'lsa, qachongacha kutish kerakligi (yoki null)"
}}
"""
    return prompt

def get_state_hash(context: dict) -> str:
    """SMC, Pattern va News tuzilmalaridan iborat o'zgarmas holat xeshini (hash) yaratadi. Narx e'tiborga olinmaydi."""
    state = {
        "vote": context.get('voting_result', {}).get('direction'),
        "vote_risk": context.get('voting_result', {}).get('risk_pct'),
        "smc_trend": context.get('smc_structure', {}).get('trend'),
        "smc_events": context.get('smc_structure', {}).get('events'),
        "pat_signal": context.get('harmonic_pattern', {}).get('signal'),
        "news_status": context.get('news_context', {}).get('status'),
        "news_event": context.get('news_context', {}).get('next_event', {}).get('name')
    }
    state_str = json.dumps(state, sort_keys=True)
    return hashlib.md5(state_str.encode('utf-8')).hexdigest()

def get_ai_decision(context: dict, mock_response=None) -> dict:
    vote_direction = context.get('voting_result', {}).get('direction', 'HOLD')
    vote_risk = context.get('voting_result', {}).get('risk_pct', 0.0)
    
    if vote_direction == "HOLD" or vote_risk == 0.0:
        return {
            "final_decision": "REJECT",
            "reasoning": "Voting Engine HOLD karorini berganligi sababli AI chaqirilmadi.",
            "risk_pct": 0.0,
            "direction": "HOLD",
            "warnings": [],
            "wait_until": None
        }
        
    # Kesh tizimi (Cost Optimization)
    current_hash = get_state_hash(context)
    pair = context.get('pair', 'Unknown')
    
    # O'tgan xeshni tekshirish
    try:
        init_db()
        conn = sqlite3.connect('decisions_log.db')
        cursor = conn.cursor()
        cursor.execute("SELECT context_hash, ai_response FROM ai_decisions WHERE pair = ? ORDER BY id DESC LIMIT 1", (pair,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] == current_hash and row[1]:
            # Xesh mos keldi, oldingi API javobidan foydalanamiz
            old_response = row[1]
            try:
                decision = json.loads(old_response)
                decision["reasoning"] = "(CACHED) " + decision.get("reasoning", "")
                return decision
            except Exception as e:
                pass # Parse xato bo'lsa yangitdan AI chaqiramiz
    except Exception as e:
        print(f"Cache o'qishda xatolik: {e}")
        
    prompt = build_claude_prompt(context)
    
    input_tokens = None
    output_tokens = None
    cost = None
    
    if mock_response is not None:
        ai_text = mock_response
    else:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return {
                "final_decision": "REJECT",
                "reasoning": "ANTHROPIC_API_KEY topilmadi.",
                "risk_pct": vote_risk,
                "direction": vote_direction,
                "warnings": ["API Key yo'q"],
                "wait_until": None
            }
            
        config = load_config()
        model = config.get("ai", {}).get("model", "claude-3-5-sonnet-20241022")
        
        try:
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model,
                max_tokens=500,
                system="Sen xavfsizlik filtri sifatidagi yordamchi AIsan. Faqat berilgan JSON formatida javob berasan, boshqa hech narsa yozmaysan.",
                messages=[{"role": "user", "content": prompt}]
            )
            ai_text = response.content[0].text.strip()
            
            # Token usage & Cost calculation
            try:
                input_tokens = getattr(response.usage, "input_tokens", 0)
                output_tokens = getattr(response.usage, "output_tokens", 0)
                if "haiku" in model.lower():
                    cost = (input_tokens * 0.8 / 1_000_000.0) + (output_tokens * 4.0 / 1_000_000.0)
                else:
                    # Sonnet: $3.00 per M input, $15.00 per M output
                    cost = (input_tokens * 3.0 / 1_000_000.0) + (output_tokens * 15.0 / 1_000_000.0)
                
                # Sync cost to Supabase
                try:
                    from supabase_sync import log_claude_cost
                    log_claude_cost(cost)
                except Exception as sync_err:
                    print(f"Supabase sync failed for Claude cost: {sync_err}")
            except Exception as usage_err:
                print(f"Token/Cost calculation error: {usage_err}")
                
        except Exception as e:
            return {
                "final_decision": "REJECT",
                "reasoning": f"AI API xatoligi: {str(e)}",
                "risk_pct": vote_risk,
                "direction": vote_direction,
                "warnings": ["API xatolik"],
                "wait_until": None
            }

    if ai_text.startswith("```"):
        ai_text = ai_text.split("```")[1]
        if ai_text.startswith("json"):
            ai_text = ai_text[4:]
            
    try:
        decision = json.loads(ai_text.strip())
        
        if decision.get('direction') != vote_direction or decision.get('risk_pct') != vote_risk:
            decision['final_decision'] = "REJECT"
            decision['warnings'] = decision.get('warnings', []) + ["Claude risk_pct yoki direction ni o'zgartirishga urindi, savdo rad etildi."]
            decision['direction'] = vote_direction
            decision['risk_pct'] = vote_risk
            
        # Logging
        log_decision(
            context.get('pair'), 
            context.get('timeframe'),
            context,
            prompt,
            decision,
            decision.get('final_decision'),
            vote_risk,
            context_hash=current_hash,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        )
        return decision
        
    except Exception as e:
        err_res = {
            "final_decision": "REJECT",
            "reasoning": "AI javobini o'qib bo'lmadi, xavfsizlik uchun rad etildi.",
            "risk_pct": vote_risk,
            "direction": vote_direction,
            "warnings": [f"JSON Parse xato: {str(e)}"],
            "wait_until": None
        }
        log_decision(
            context.get('pair'), 
            context.get('timeframe'),
            context,
            prompt,
            ai_text,
            "REJECT",
            vote_risk,
            context_hash=current_hash,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost
        )
        return err_res

def make_trading_decision(pair: str, timeframe: str, settings: dict = None) -> dict:
    load_env()
    init_db()
    
    if not mt5.initialize():
        print("MT5 ulanishda xatolik:", mt5.last_error())
        # Agar MT5 ishlamasa, fallback: HOLD qaytaradi, lekin biz testlar uchun davom etishimiz mumkin bo'lsa yaxshi
        
    context = build_decision_context(pair, timeframe, settings)
    decision = get_ai_decision(context)
    
    mt5.shutdown()
    return decision

def get_trailing_decision(context: dict) -> str:
    """
    Ochiq pozitsiyalar uchun qaysi trailing rejimidan foydalanish kerakligini aniqlaydi.
    Qaytaradigan qiymatlar: "STEP", "STRUCTURE", yoki "CLOSE_ALL"
    """
    prompt = f"""Sen avtonom Trading AIsan. Hozirda foydada bo'lgan (TP1 2R ga yetgan va 70% yopilgan) pozitsiyani boshqaryapsan.
Sening vazifang qolgan 30% pozitsiya uchun trailing rejimini tanlash.

Bozor holati:
SMC Trend: {context.get('smc_structure', {}).get('trend', {}).get('internal', 'Unknown')}
Yangiliklar: {context.get('news_context', {}).get('next_event', {}).get('name', 'None')}

QOIDALAR:
1. Agar kuchli impuls yoki yangilik bo'lsa -> "STEP" (har 1R da SL ni surish)
2. Agar barqaror trend bo'lsa -> "STRUCTURE" (yangi High/Low da SL ni surish)
3. Agar trend keskin o'zgargan yoki bozor xavfli bo'lsa -> "CLOSE_ALL" (hammasini yopish)

JAVOBNI FAQAT SHU UCHTASIDAN BIRI SIFATIDA QAYTAR (Hech qanday qo'shimcha matnsiz):
STEP
STRUCTURE
CLOSE_ALL
"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "STEP" # Default
        
    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=10,
            system="Faqat bitta so'z bilan javob ber.",
            messages=[{"role": "user", "content": prompt}]
        )
        ai_text = response.content[0].text.strip().upper()
        if "CLOSE" in ai_text:
            return "CLOSE_ALL"
        elif "STRUCT" in ai_text:
            return "STRUCTURE"
        else:
            return "STEP"
    except Exception as e:
        print(f"Trailing qarori olishda xato: {e}")
        return "STEP"


if __name__ == "__main__":
    print("--- Testing ai_analysis.py ---")
    res = make_trading_decision("EURUSD", "H1")
    import json
    print(json.dumps(res, indent=2, ensure_ascii=False))