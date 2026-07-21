import time
from news_detector import NewsDetector

def main():
    print("--- News/Fundamental Strategy Validation ---")
    detector = NewsDetector()
    
    print("1. Fetching Forex Factory Economic Calendar...")
    success = detector.fetch_calendar()
    
    if success:
        print(f"-> Successfully loaded {len(detector.events)} events for this week.")
        
        print("\n2. Checking High Impact News for EUR/USD in the next 48 hours...")
        detector.target_currencies = ["EUR", "USD"]
        # Look ahead 48 hours (2880 mins)
        upcoming = detector.get_upcoming_news(impact_filter=["High"], minutes_ahead=2880)
        
        if upcoming:
            for event in upcoming:
                print(f"  [!] {event['date']} | {event['country']} | {event['title']} | Impact: {event['impact']}")
                print(f"      Forecast: {event.get('forecast', 'N/A')} | Previous: {event.get('previous', 'N/A')}")
        else:
            print("  -> No High impact news for EUR/USD in the next 48 hours.")
            
        print("\n3. Trading Safety Check (Next 30 mins)")
        is_safe, reason = detector.is_trading_safe("EURUSD")
        if is_safe:
            print(f"-> SAFE: {reason}")
        else:
            print(f"-> UNSAFE: {reason}")
            
    else:
        print("-> Failed to fetch calendar data.")

if __name__ == '__main__':
    main()
