import os
import sqlite3
from news_impact_analyzer import backfill_historical_data, analyze_historical_impact, init_db, get_cot_trend

def create_mock_csv():
    csv_content = """Date,Time,Currency,Event,Impact,Actual,Forecast,Previous
2026-07-03,12:30,USD,Non-Farm Employment Change,High,150K,180K,297K
2026-06-05,12:30,USD,Non-Farm Employment Change,High,336K,170K,227K
2026-05-01,12:30,USD,Non-Farm Employment Change,High,187K,170K,157K
2026-04-03,12:30,USD,Non-Farm Employment Change,High,187K,200K,185K
2026-03-06,12:30,USD,Non-Farm Employment Change,High,209K,225K,306K
2026-02-06,12:30,USD,Non-Farm Employment Change,High,339K,190K,294K
"""
    with open("mock_news.csv", "w") as f:
        f.write(csv_content)

def mock_fetch_price_move(symbol, event_date_utc):
    dt_str = event_date_utc.strftime("%Y-%m-%d")
    if dt_str == "2026-07-03": 
        return 0.2, 0.5, 0.8, 1.5
    elif dt_str == "2026-06-05": 
        return -0.3, -0.6, -1.0, 2.0
    elif dt_str == "2026-05-01": 
        return -0.2, -0.4, -0.7, 1.2
    elif dt_str == "2026-04-03": 
        return 0.1, 0.4, 0.6, 1.1
    elif dt_str == "2026-03-06": 
        return 0.25, 0.55, 0.9, 1.6
    elif dt_str == "2026-02-06": 
        return -0.4, -0.8, -1.2, 2.5
    return 0, 0, 0, 1.0

class MockResponse:
    def __init__(self):
        self.status_code = 200
        self.text = 'GOLD - COMMODITY EXCHANGE INC.,,,,0,0,0,12345,54321,0'

def mock_requests_get(url, timeout):
    return MockResponse()

if __name__ == "__main__":
    # Override fetch_price_move
    import news_impact_analyzer
    import requests
    news_impact_analyzer.fetch_price_move = mock_fetch_price_move
    requests.get = mock_requests_get
    
    # Remove existing db if it exists
    if os.path.exists("news_history.db"):
        os.remove("news_history.db")
        
    init_db()
    create_mock_csv()
    
    print("Running backfill with mock data...")
    backfill_historical_data("mock_news.csv", "XAUUSD")
    
    print("\nAnalyzing historical impact for Non-Farm Employment Change...")
    res = analyze_historical_impact("XAUUSD", "Non-Farm Employment Change", lookback_months=12)
    import json
    print(json.dumps(res, indent=2))
    
    print("\nTesting COT Trend for XAUUSD...")
    cot = get_cot_trend("XAUUSD")
    print(json.dumps(cot, indent=2))
    
    print("\nCleaning up...")
    os.remove("mock_news.csv")
