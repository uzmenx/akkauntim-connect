from bot.strategy.news.detector import NewsDetector
from bot.strategy.news.impact import analyze_historical_impact, get_cot_trend

def watch_upcoming_news(pair: str, minutes_ahead: int = 60) -> dict:
    detector = NewsDetector()
    upcoming = detector.get_upcoming_news(impact_filter=["High", "Medium"], minutes_ahead=minutes_ahead)
    
    if not upcoming:
        return {
            "status": "UNKNOWN",
            "next_event": None,
            "historical_bias": None,
            "recommended_action": "none"
        }
        
    # Find the nearest High impact news, or if none, the nearest Medium
    nearest_event = None
    for event in upcoming:
        if event.get('impact') == 'High':
            nearest_event = event
            break
    
    if not nearest_event:
        nearest_event = upcoming[0]
        
    # Analyze historical impact for this event
    hist_impact = analyze_historical_impact(pair, nearest_event['title'], lookback_months=6, currency=nearest_event.get('currency'))
    
    status = "AWAITING_NEWS"
    recommended_action = "none"
    
    bias_info = None
    if hist_impact and not hist_impact.get("insufficient_data"):
        # Let's say we check if actual beats forecast generally leads to a certain direction with high confidence
        beat_summary = hist_impact.get('when_actual_beats_forecast')
        miss_summary = hist_impact.get('when_actual_misses_forecast')
        
        # Simple rule for preparation: if beat and miss both are heavily confident in one direction
        # Or if we just rely on AI decision later, we just set the historical bias info
        
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
            reason = "High-impact news approaching"
        else:
            reason = ""
            
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

def get_news_signal(pair: str) -> dict:
    watch_data = watch_upcoming_news(pair, minutes_ahead=60)
    
    cot_data = get_cot_trend(pair)
    
    # We might add logic for POST_NEWS_VOLATILE if we had the last news time.
    # For simplicity, if it's not AWAITING_NEWS, it's CLEAR.
    status = watch_data["status"]
    
    signal = {
        "current_status": status,
        "next_event": watch_data["next_event"],
        "historical_bias": watch_data["historical_bias"] if watch_data["historical_bias"] else {
            "direction": "Neutral", "confidence": 0.0, "sample_size": 0, "avg_move_pct": 0.0
        },
        "institutional_context": {
            "cot_trend": cot_data.get("cot_trend", "Unknown"),
            "note": cot_data.get("note", "")
        },
        "recommendation": watch_data.get("recommended_action", "neutral"),
        "reason": watch_data.get("reason", "")
    }
    
    return signal

if __name__ == "__main__":
    print("Testing get_news_signal for XAUUSD:")
    import json
    print(json.dumps(get_news_signal("XAUUSD"), indent=2))
