import MetaTrader5 as mt5
from datetime import datetime, timezone
import math
from news_detector import NewsDetector
from order_manager import place_pending_order, delete_pending_order, set_trade_info

def get_atr(symbol, timeframe=mt5.TIMEFRAME_M5, period=14):
    """
    ATR (Average True Range) ni hisoblash, stop masofalarini moslashtirish uchun.
    """
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, period + 1)
    if rates is None or len(rates) < period:
        return 15.0 # Default 15 pips

    tr_list = []
    for i in range(1, len(rates)):
        high = rates[i]['high']
        low = rates[i]['low']
        close_prev = rates[i-1]['close']
        
        tr = max(high - low, abs(high - close_prev), abs(low - close_prev))
        tr_list.append(tr)
        
    atr = sum(tr_list) / len(tr_list)
    symbol_info = mt5.symbol_info(symbol)
    pip_size = symbol_info.point * 10
    
    return atr / pip_size

def check_and_place_straddle(symbols, settings):
    """
    1-2 daqiqa qolgan kuchli yangiliklarni topib, har bir symbol uchun 
    Buy Stop va Sell Stop o'rnatadi.
    """
    detector = NewsDetector()
    upcoming = detector.get_upcoming_news(impact_filter=["High"], minutes_ahead=5)
    
    if not upcoming:
        return # Yangilik yo'q
        
    for event in upcoming:
        mins_left = event.get('minutes_to_release', 99)
        # 1-2 daqiqa qolgan bo'lsa qopqon qo'yamiz
        if 1 <= mins_left <= 2:
            print(f"!!! DIQQAT !!! '{event['title']}' yangiligiga {mins_left} daqiqa qoldi. Straddle tayyorlanmoqda.")
            
            for symbol in symbols:
                symbol_info = mt5.symbol_info(symbol)
                if not symbol_info:
                    continue
                    
                # Eski straddle orderlar osilib qolmaganligini tekshiramiz
                orders = mt5.orders_get(symbol=symbol)
                already_placed = False
                if orders:
                    for ord in orders:
                        if ord.magic == 234000 and "News Straddle" in ord.comment:
                            already_placed = True
                            break
                
                if already_placed:
                    continue
                
                # Masofa hisoblash (ATR asosida yoki fix)
                atr_pips = get_atr(symbol, mt5.TIMEFRAME_M5, 14)
                distance_pips = max(10.0, atr_pips * 1.5) # Kamida 10 pip, yoki ATR * 1.5
                
                account_info = mt5.account_info()
                if account_info:
                    risk_amount = account_info.balance * 0.01
                    lot_size = round(risk_amount / (distance_pips * 10), 2)
                    if lot_size < 0.01: lot_size = 0.01
                else:
                    lot_size = 0.01
                
                tick = mt5.symbol_info_tick(symbol)
                if not tick: continue
                
                # Buy Stop
                buy_stop_price = tick.ask + (distance_pips * symbol_info.point * 10)
                place_pending_order(
                    symbol=symbol,
                    order_type_str="BUY_STOP",
                    price=buy_stop_price,
                    lot_size=lot_size,
                    stop_loss_pips=distance_pips,
                    take_profit_pips=distance_pips * 3 # 3R TP
                )
                
                # Sell Stop
                sell_stop_price = tick.bid - (distance_pips * symbol_info.point * 10)
                place_pending_order(
                    symbol=symbol,
                    order_type_str="SELL_STOP",
                    price=sell_stop_price,
                    lot_size=lot_size,
                    stop_loss_pips=distance_pips,
                    take_profit_pips=distance_pips * 3
                )
                print(f"[{symbol}] Straddle o'rnatildi. Masofa: {distance_pips:.1f} pip. Lot: {lot_size}")

def cleanup_straddle_orders():
    """
    Agar biri ishlab ketgan bo'lsa (Pozitsiyaga aylangan bo'lsa), ikkinchi teskari pending orderni o'chiradi.
    """
    orders = mt5.orders_get()
    if not orders:
        return
        
    positions = mt5.positions_get()
    active_straddle_symbols = set()
    
    if positions:
        for pos in positions:
            if pos.magic == 234000 and "Straddle" in pos.comment:
                active_straddle_symbols.add(pos.symbol)
                
    for ord in orders:
        if ord.magic == 234000 and "Straddle" in ord.comment:
            if ord.symbol in active_straddle_symbols:
                print(f"[{ord.symbol}] Straddle qopqoni ishga tushgan. Teskari Pending order o'chirilmoqda.")
                delete_pending_order(ord.ticket)
                continue
