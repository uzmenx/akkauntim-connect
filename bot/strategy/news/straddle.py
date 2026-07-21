from datetime import datetime, timezone
import math
from bot.strategy.news.detector import NewsDetector

def get_atr(mt5_client, symbol, timeframe, period=14):
    """
    ATR (Average True Range) ni hisoblash, stop masofalarini moslashtirish uchun.
    """
    rates = mt5_client.copy_rates_from_pos(symbol, timeframe, 0, period + 1)
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
    symbol_info = mt5_client.symbol_info(symbol)
    
    def _get_pip_size(symbol_info):
        digits = symbol_info.digits
        if digits == 3 or digits == 5:
            return symbol_info.point * 10
        elif digits == 2:
            return symbol_info.point * 100
        else:
            return symbol_info.point
            
    pip_size = _get_pip_size(symbol_info)
    
    return atr / pip_size

def check_and_place_straddle(mt5_client, order_manager, symbols, settings):
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
                symbol_info = mt5_client.symbol_info(symbol)
                if not symbol_info:
                    continue
                    
                # Eski straddle orderlar osilib qolmaganligini tekshiramiz
                orders = mt5_client.orders_get(symbol=symbol)
                already_placed = False
                if orders:
                    for ord in orders:
                        if ord.magic == 234000 and "News Straddle" in ord.comment:
                            already_placed = True
                            break
                
                if already_placed:
                    continue
                
                # Masofa hisoblash (ATR asosida yoki fix)
                atr_pips = get_atr(mt5_client, symbol, mt5_client.TIMEFRAME_M5, 14)
                distance_pips = max(10.0, atr_pips * 1.5) # Kamida 10 pip, yoki ATR * 1.5
                
                account_info = mt5_client.account_info()
                
                def _get_pip_size(symbol_info):
                    digits = symbol_info.digits
                    if digits == 3 or digits == 5:
                        return symbol_info.point * 10
                    elif digits == 2:
                        return symbol_info.point * 100
                    else:
                        return symbol_info.point
                        
                pip_size = _get_pip_size(symbol_info)
                
                if account_info:
                    risk_amount = account_info.balance * 0.01
                    lot_size = round(risk_amount / (distance_pips * 10), 2)
                    if lot_size < 0.01: lot_size = 0.01
                else:
                    lot_size = 0.01
                
                tick = mt5_client.symbol_info_tick(symbol)
                if not tick: continue
                
                # Buy Stop
                buy_stop_price = tick.ask + (distance_pips * pip_size)
                order_manager.place_pending_order(
                    symbol=symbol,
                    order_type_str="BUY_STOP",
                    price=buy_stop_price,
                    lot_size=lot_size,
                    stop_loss_pips=distance_pips,
                    take_profit_pips=distance_pips * 3, # 3R TP
                    magic=234000,
                    comment="News Straddle"
                )
                
                # Sell Stop
                sell_stop_price = tick.bid - (distance_pips * pip_size)
                order_manager.place_pending_order(
                    symbol=symbol,
                    order_type_str="SELL_STOP",
                    price=sell_stop_price,
                    lot_size=lot_size,
                    stop_loss_pips=distance_pips,
                    take_profit_pips=distance_pips * 3,
                    magic=234000,
                    comment="News Straddle"
                )
                print(f"[{symbol}] Straddle o'rnatildi. Masofa: {distance_pips:.1f} pip. Lot: {lot_size}")

def cleanup_straddle_orders(mt5_client, order_manager):
    """
    Agar biri ishlab ketgan bo'lsa (Pozitsiyaga aylangan bo'lsa), ikkinchi teskari pending orderni o'chiradi.
    """
    orders = mt5_client.orders_get()
    if not orders:
        return
        
    positions = mt5_client.positions_get()
    active_straddle_symbols = set()
    
    if positions:
        for pos in positions:
            if pos.magic == 234000 and "Straddle" in pos.comment:
                active_straddle_symbols.add(pos.symbol)
                
    for ord in orders:
        if ord.magic == 234000 and "Straddle" in ord.comment:
            if ord.symbol in active_straddle_symbols:
                print(f"[{ord.symbol}] Straddle qopqoni ishga tushgan. Teskari Pending order o'chirilmoqda.")
                order_manager.delete_pending_order(ord.ticket)
                continue
