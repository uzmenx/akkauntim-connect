from bot.strategy.news.detector import NewsDetector
from bot.strategy.news.impact import analyze_historical_impact, get_cot_trend
from bot.strategy.news.ai_analyzer import NewsAIAnalyzer
import logging

logger = logging.getLogger(__name__)

def watch_upcoming_news(pair: str, minutes_ahead: int = 60, detector=None) -> dict:
    if detector is None:
        detector = NewsDetector()
        
    # Keshni majburiy yangilash (agar yangilikka oz qolgan bo'lsa)
    # Hozircha doimiy tekshirmaymiz, faqat kesh eskirmaganini fetch_calendar orqali ko'ramiz
    upcoming = detector.get_upcoming_news(impact_filter=["High", "Medium"], minutes_ahead=minutes_ahead)
    
    if not upcoming:
        return {
            "status": "UNKNOWN",
            "next_event": None,
            "historical_bias": None,
            "recommended_action": "none",
            "reason": ""
        }
        
    # Find the nearest High impact news, or if none, the nearest Medium
    nearest_event = next((e for e in upcoming if e.get('impact') == 'High'), upcoming[0])
    
    # Analyze historical impact for this event
    hist_impact = analyze_historical_impact(pair, nearest_event['title'], lookback_months=6, currency=nearest_event.get('currency'))
    
    status = "AWAITING_NEWS"
    recommended_action = "none"
    reason = ""
    bias_info = None
    
    if hist_impact and not hist_impact.get("insufficient_data"):
        beat_summary = hist_impact.get('when_actual_beats_forecast')
        miss_summary = hist_impact.get('when_actual_misses_forecast')
        
        best_confidence = 0
        direction = "Neutral"
        avg_move = 0.0
        
        if beat_summary and beat_summary['confidence'] > best_confidence:
            best_confidence = beat_summary['confidence']
            direction = beat_summary['direction']
            avg_move = beat_summary['avg_move_1h_pct']
            
        if miss_summary and miss_summary['confidence'] > best_confidence:
            best_confidence = miss_summary['confidence']
            direction = miss_summary['direction']
            avg_move = miss_summary['avg_move_1h_pct']
            
        bias_info = {
            "direction": direction,
            "confidence": best_confidence,
            "sample_size": hist_impact.get("sample_size"),
            "avg_move_pct": avg_move,
            "avg_volatility_spike": hist_impact.get("avg_volatility_spike")
        }
        
    if nearest_event['minutes_to_release'] <= 30:
        status = "PRE_NEWS"
        recommended_action = "reduce_position"
        reason = f"{nearest_event['impact']}-impact news approaching"
        # 30 daqiqa qolganda tez-tez ma'lumot olish uchun keshni majburiy yangilaymiz
        detector.fetch_calendar(force_refresh=True)
            
    return {
        "status": status,
        "next_event": {
            "name": nearest_event['title'],
            "time": nearest_event['date'],
            "impact": nearest_event['impact'],
            "minutes_to_release": nearest_event['minutes_to_release']
        },
        "historical_bias": bias_info,
        "recommended_action": recommended_action,
        "reason": reason
    }

def check_recent_news_ai(pair: str, detector: NewsDetector, ai_client=None) -> dict:
    """Yaqinda chiqqan yangilikni AI yordamida chuqur tahlil qiladi."""
    recent = detector.get_news_history(hours_back=1)
    if not recent:
        return {}
        
    # Faqat High/Medium ni qidiramiz
    target_event = next((e for e in recent if e.get('impact') in ['High', 'Medium'] and e.get('actual')), None)
    
    if target_event and ai_client:
        title = target_event.get('title', '')
        actual = target_event.get('actual', '')
        forecast = target_event.get('forecast', '')
        previous = target_event.get('previous', '')
        
        prompt = NewsAIAnalyzer.get_prompt_for_news(pair, title, actual, forecast, previous)
        
        try:
            logger.info(f"[{pair}] {title} uchun AI Fundamental tahlili so'ralmoqda (Actual: {actual})...")
            ai_response = ai_client.get_simple_response(prompt, system_prompt="Faqat aniq formatda javob qaytaring.")
            hukm = NewsAIAnalyzer.parse_hukm(ai_response)
            
            return {
                "event": title,
                "ai_analysis": ai_response,
                "ai_direction": hukm,
                "time_since_release_hours": target_event.get('hours_ago')
            }
        except Exception as e:
            logger.error(f"News AI Analyzer xatosi: {e}")
            
    return {}

def get_news_signal(pair: str, ai_client=None) -> dict:
    detector = NewsDetector()
    
    # Oldin upcoming ni tekshiramiz
    watch_data = watch_upcoming_news(pair, minutes_ahead=60, detector=detector)
    
    # Agar post-news holat bo'lsa (yangilik endi chiqdi), AI dan so'raymiz
    ai_news_data = check_recent_news_ai(pair, detector, ai_client)
    
    cot_data = get_cot_trend(pair)
    status = watch_data["status"]
    
    # Agar AI dan aniq yo'nalish chiqqan bo'lsa, uni historical_bias ustunidan afzal ko'ramiz
    ai_direction = "Neutral"
    if ai_news_data and ai_news_data.get("ai_direction"):
        ai_direction = ai_news_data["ai_direction"]
        status = "POST_NEWS_ACTIVE"
        
    signal = {
        "current_status": status,
        "next_event": watch_data.get("next_event"),
        "historical_bias": watch_data.get("historical_bias") if watch_data.get("historical_bias") else {
            "direction": "Neutral", "confidence": 0.0, "sample_size": 0, "avg_move_pct": 0.0
        },
        "ai_analysis": ai_news_data,
        "institutional_context": {
            "cot_trend": cot_data.get("cot_trend", "Unknown"),
            "note": cot_data.get("note", "")
        },
        "recommendation": watch_data.get("recommended_action", "neutral"),
        "reason": watch_data.get("reason", "")
    }
    
    # Agar AI qarori bo'lsa, "recommendation" ga ta'sir qilishi mumkin
    if ai_direction == "BUY":
        signal["recommendation"] = "prepare_long"
        signal["reason"] += " (AI Fundamental BUY)"
    elif ai_direction == "SELL":
        signal["recommendation"] = "prepare_short"
        signal["reason"] += " (AI Fundamental SELL)"
        
    return signal

if __name__ == "__main__":
    print("Testing get_news_signal for XAUUSD:")
    import json
    # ai_client ni uzatmasdan test qilyapmiz
    print(json.dumps(get_news_signal("XAUUSD"), indent=2))
