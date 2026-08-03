import os

base_dir = r'c:\Users\PC\Desktop\akkauntim-connect'
strategy_dir = os.path.join(base_dir, 'bot', 'strategy')

# News Impact
with open(os.path.join(base_dir, 'news_impact_analyzer.py'), 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('import MetaTrader5 as mt5\n', '')
content = content.replace('def fetch_price_move(symbol, event_date_utc):', 'def fetch_price_move(mt5_client, symbol, event_date_utc):')
content = content.replace('    if not mt5.initialize():\n        return None, None, None, None\n', '')
content = content.replace('mt5.', 'mt5_client.')
content = content.replace('def backfill_historical_data(csv_path: str, pair: str = "XAUUSD"):', 'def backfill_historical_data(mt5_client, csv_path: str, pair: str = "XAUUSD"):')
content = content.replace('fetch_price_move(pair, dt_utc)', 'fetch_price_move(mt5_client, pair, dt_utc)')
with open(os.path.join(strategy_dir, 'news', 'impact.py'), 'w', encoding='utf-8') as f:
    f.write(content)

# News Scheduler
with open(os.path.join(base_dir, 'news_trade_scheduler.py'), 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('from news_detector import NewsDetector', 'from bot.strategy.news.detector import NewsDetector')
content = content.replace('from news_impact_analyzer import analyze_historical_impact, get_cot_trend', 'from bot.strategy.news.impact import analyze_historical_impact, get_cot_trend')
with open(os.path.join(strategy_dir, 'news', 'scheduler.py'), 'w', encoding='utf-8') as f:
    f.write(content)

# News Straddle
with open(os.path.join(base_dir, 'news_straddle_engine.py'), 'r', encoding='utf-8') as f:
    content = f.read()
content = content.replace('import MetaTrader5 as mt5\n', '')
content = content.replace('from news_detector import NewsDetector', 'from bot.strategy.news.detector import NewsDetector')
content = content.replace('from order_manager import place_pending_order, delete_pending_order, set_trade_info\n', '')
content = content.replace('def get_atr(symbol, timeframe=mt5.TIMEFRAME_M5, period=14):', 'def get_atr(mt5_client, symbol, timeframe, period=14):')
content = content.replace('mt5.', 'mt5_client.')
content = content.replace('def check_and_place_straddle(symbols, settings):', 'def check_and_place_straddle(mt5_client, order_manager, symbols, settings):')
content = content.replace('get_atr(symbol, mt5_client.TIMEFRAME_M5, 14)', 'get_atr(mt5_client, symbol, mt5_client.TIMEFRAME_M5, 14)')
content = content.replace('place_pending_order(', 'order_manager.place_pending_order(')
content = content.replace('def cleanup_straddle_orders():', 'def cleanup_straddle_orders(mt5_client, order_manager):')
content = content.replace('delete_pending_order(', 'order_manager.delete_pending_order(')
with open(os.path.join(strategy_dir, 'news', 'straddle.py'), 'w', encoding='utf-8') as f:
    f.write(content)
