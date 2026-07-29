from datetime import datetime, timezone, timedelta
import math
import logging
from bot.strategy.news.detector import NewsDetector
from bot.engine.decision_logger import DecisionLogger

logger = logging.getLogger(__name__)

CURRENCY_PAIRS_MAP = {
    "USD": ["EURUSD", "GBPUSD", "XAUUSD"],
    "EUR": ["EURUSD", "EURGBP", "EURJPY"],
    "GBP": ["GBPUSD", "EURGBP", "GBPJPY"],
    "JPY": ["USDJPY", "EURJPY", "GBPJPY"],
    "AUD": ["AUDUSD", "EURAUD", "GBPAUD"],
    "CAD": ["USDCAD", "EURCAD", "GBPCAD"],
    "NZD": ["NZDUSD", "EURNZD", "GBPNZD"],
    "CHF": ["USDCHF", "EURCHF", "GBPCHF"]
}

def get_atr(mt5_client, symbol, timeframe, period=14):
    """ATR (Average True Range) ni hisoblash."""
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
    
    digits = symbol_info.digits
    pip_size = symbol_info.point * 10 if digits in [3, 5] else (symbol_info.point * 100 if digits == 2 else symbol_info.point)
    
    return atr / pip_size

def spread_check(mt5_client, symbol, atr_pips) -> bool:
    """Spread juda kengayib ketmaganini tekshiradi."""
    symbol_info = mt5_client.symbol_info(symbol)
    if not symbol_info:
        return False
        
    digits = symbol_info.digits
    pip_size = symbol_info.point * 10 if digits in [3, 5] else (symbol_info.point * 100 if digits == 2 else symbol_info.point)
    
    current_spread_pips = (symbol_info.ask - symbol_info.bid) / pip_size
    
    # Agar spread ATR ning yarmidan ko'p bo'lsa, xavfli!
    if current_spread_pips > (atr_pips * 0.5):
        logger.warning(f"[{symbol}] Spread juda keng ({current_spread_pips:.1f} pip). Straddle bekor qilinadi.")
        return False
        
    return True

def check_and_place_straddle(mt5_client, order_manager, symbols, settings):
    """
    1-2 daqiqa qolgan Medium va High yangiliklarni topib, 
    o'sha valyutaga aloqador 3 ta juftlik uchun Buy Stop va Sell Stop o'rnatadi.
    """
    detector = NewsDetector()
    upcoming = detector.get_upcoming_news(impact_filter=["High", "Medium"], minutes_ahead=5)
    
    if not upcoming:
        return # Yangilik yo'q
        
    for event in upcoming:
        mins_left = event.get('minutes_to_release', 99)
        # 1-2 daqiqa qolgan bo'lsa qopqon qo'yamiz
        if 0.5 <= mins_left <= 3:
            logger.info(f"!!! DIQQAT !!! '{event['title']}' yangiligiga {mins_left} daqiqa qoldi. Straddle v2 tayyorlanmoqda.")
            
            # Dinamik 3 ta juftlikni tanlash
            country = event.get("country", "USD")
            dynamic_symbols = CURRENCY_PAIRS_MAP.get(country, ["EURUSD", "GBPUSD", "XAUUSD"])
            
            for symbol in dynamic_symbols:
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
                
                # Masofa hisoblash (ATR asosida)
                atr_pips = get_atr(mt5_client, symbol, mt5_client.TIMEFRAME_M5, 14)
                
                # SPREAD TEKSHIRUVI
                if not spread_check(mt5_client, symbol, atr_pips):
                    continue
                
                # ATR * 2.0 (slippage protection uchun kattaroq masofa)
                distance_pips = max(15.0, atr_pips * 2.0)
                
                account_info = mt5_client.account_info()
                digits = symbol_info.digits
                pip_size = symbol_info.point * 10 if digits in [3, 5] else (symbol_info.point * 100 if digits == 2 else symbol_info.point)
                
                if account_info:
                    risk_amount = account_info.balance * 0.01
                    # Universal lot size calculation using tick_value
                    tick_value = symbol_info.trade_tick_value
                    tick_size = symbol_info.trade_tick_size
                    if tick_value > 0 and tick_size > 0:
                        pip_value_per_lot = (pip_size / tick_size) * tick_value
                        lot_size = round(risk_amount / (distance_pips * pip_value_per_lot), 2) if pip_value_per_lot > 0 else 0.01
                    else:
                        lot_size = 0.01
                    # Enforce broker limits
                    lot_size = max(symbol_info.volume_min, min(lot_size, symbol_info.volume_max))
                    # Round to volume_step
                    if symbol_info.volume_step > 0:
                        lot_size = round(lot_size / symbol_info.volume_step) * symbol_info.volume_step
                        lot_size = round(lot_size, 2)
                    if lot_size < symbol_info.volume_min:
                        lot_size = symbol_info.volume_min
                else:
                    lot_size = 0.01
                
                tick = mt5_client.symbol_info_tick(symbol)
                if not tick: continue
                
                # Buy Stop
                buy_stop_price = tick.ask + (distance_pips * pip_size)
                success_b, msg_b, info_b = order_manager.place_pending_order(
                    symbol=symbol,
                    order_type_str="BUY_STOP",
                    price=buy_stop_price,
                    lot_size=lot_size,
                    stop_loss_pips=distance_pips,  # 1R
                    take_profit_pips=distance_pips * 2.5, # 2.5R TP
                    magic=234000,
                    comment="News Straddle",
                    expiration_minutes=5
                )
                if success_b and info_b and "ticket" in info_b:
                    DecisionLogger().log(
                        pair=symbol, timeframe="M5", context={"event": event.get('title')},
                        prompt="NEWS_STRADDLE", response={}, decision="BUY_STOP", risk_pct=0.01,
                        ticket=info_b["ticket"], news_strategy_type="BEFORE_NEWS"
                    )
                
                # Sell Stop
                sell_stop_price = tick.bid - (distance_pips * pip_size)
                success_s, msg_s, info_s = order_manager.place_pending_order(
                    symbol=symbol,
                    order_type_str="SELL_STOP",
                    price=sell_stop_price,
                    lot_size=lot_size,
                    stop_loss_pips=distance_pips,
                    take_profit_pips=distance_pips * 2.5,
                    magic=234000,
                    comment="News Straddle",
                    expiration_minutes=5
                )
                if success_s and info_s and "ticket" in info_s:
                    DecisionLogger().log(
                        pair=symbol, timeframe="M5", context={"event": event.get('title')},
                        prompt="NEWS_STRADDLE", response={}, decision="SELL_STOP", risk_pct=0.01,
                        ticket=info_s["ticket"], news_strategy_type="BEFORE_NEWS"
                    )
                logger.info(f"[{symbol}] Straddle V2 o'rnatildi. Masofa: {distance_pips:.1f} pip. Lot: {lot_size}")

def cleanup_straddle_orders(mt5_client, order_manager):
    """
    Agar biri ishlab ketgan bo'lsa (Pozitsiyaga aylangan bo'lsa), ikkinchi teskari pending orderni o'chiradi.
    Shuningdek, yangilik chiqib 5 daqiqa o'tgandan keyin ishlamagan qopqonlarni ham tozalaydi.
    YANGI: Agar yangilik kechikayotgan bo'lsa (actual yo'q), orderlarni o'chirmaydi.
    """
    orders = mt5_client.orders_get()
    if not orders:
        return
        
    positions = mt5_client.positions_get()
    active_straddle_symbols = set()
    
    if positions:
        for pos in positions:
            if pos.magic == 234000:
                active_straddle_symbols.add(pos.symbol)
    
    # Kechikayotgan yangiliklar bormi tekshiramiz
    detector = NewsDetector()
    detector.fetch_calendar(force_refresh=True)
    pending_news = detector.get_pending_news(impact_filter=["High", "Medium"], max_delay_minutes=15)
    has_pending_news = len(pending_news) > 0
                
    current_time = datetime.now(timezone.utc)
    
    for ord in orders:
        if ord.magic == 234000 and "Straddle" in ord.comment:
            # Agar teskari tomoni ishlab ketgan bo'lsa
            if ord.symbol in active_straddle_symbols:
                logger.info(f"[{ord.symbol}] Straddle qopqoni ishga tushgan. Teskari Pending order o'chirilmoqda.")
                order_manager.delete_pending_order(ord.ticket)
                continue
            
            # Agar kechikayotgan yangilik bor bo'lsa, orderlarni O'CHIRMAYMIZ
            # (chunki refresh_straddle_for_delayed_news yangilaydi)
            if has_pending_news:
                continue
                
            # Vaqt tekshiruvi (agar 5 daqiqa ichida ishlamagan bo'lsa)
            order_time = datetime.fromtimestamp(ord.time_setup, tz=timezone.utc)
            if (current_time - order_time).total_seconds() > 300: # 5 daqiqa
                logger.info(f"[{ord.symbol}] Straddle eskirdi (>5 min). O'chirilmoqda.")
                order_manager.delete_pending_order(ord.ticket)


# Kechikkan yangiliklar uchun oxirgi yangilash vaqtlarini kuzatish
_LAST_ROLLOVER_TIME = {}  # {event_title: datetime}

def refresh_straddle_for_delayed_news(mt5_client, order_manager):
    """
    Yangilik kechikkan holat uchun Straddle Rollover mexanizmi.
    
    Agar yangilik vaqti o'tgan bo'lsa-da, hali Actual natija chiqmagan bo'lsa:
    1. Har 1 daqiqada mavjud pending orderlarni o'chirib, yangi narx bilan qayta o'rnatadi
    2. Orderlar expiration = 2 daqiqa bilan qo'yiladi (keyingi yangilanishgacha yetadi)
    3. Maksimal 15 daqiqa kutadi, keyin to'liq tozalaydi
    4. Actual natija chiqishi bilan rollover to'xtaydi
    
    Bu funksiya main.py dagi asosiy loopda check_and_place_straddle bilan birga chaqirilishi kerak.
    """
    global _LAST_ROLLOVER_TIME
    
    detector = NewsDetector()
    detector.fetch_calendar(force_refresh=True)
    
    pending_news = detector.get_pending_news(
        impact_filter=["High", "Medium"], 
        max_delay_minutes=15
    )
    
    if not pending_news:
        return
    
    current_time = datetime.now(timezone.utc)
    
    for event in pending_news:
        event_title = event.get('title', 'Unknown')
        minutes_overdue = event.get('minutes_overdue', 0)
        country = event.get('country', 'USD')
        
        # Har 1 daqiqada yangilaymiz (juda tez-tez broker so'rovlariga yuk tushmasligi uchun)
        last_rollover = _LAST_ROLLOVER_TIME.get(event_title)
        if last_rollover:
            seconds_since_last = (current_time - last_rollover).total_seconds()
            if seconds_since_last < 60:  # 1 daqiqadan kam o'tgan bo'lsa, kutamiz
                continue
        
        logger.info(
            f"⏳ YANGILIK KECHIKMOQDA: '{event_title}' — {minutes_overdue:.1f} daqiqa o'tdi, "
            f"hali Actual yo'q. Straddle orderlar yangilanmoqda..."
        )
        
        dynamic_symbols = CURRENCY_PAIRS_MAP.get(country, ["EURUSD", "GBPUSD", "XAUUSD"])
        
        for symbol in dynamic_symbols:
            symbol_info = mt5_client.symbol_info(symbol)
            if not symbol_info:
                continue
            
            # 1. Eski straddle orderlarni topib o'chiramiz (shu symbol uchun)
            existing_orders = mt5_client.orders_get(symbol=symbol)
            if existing_orders:
                for ord in existing_orders:
                    if ord.magic == 234000 and "Straddle" in ord.comment:
                        order_manager.delete_pending_order(ord.ticket)
            
            # 2. Pozitsiya allaqachon ochilganmi tekshiramiz
            positions = mt5_client.positions_get(symbol=symbol)
            has_active_position = False
            if positions:
                for pos in positions:
                    if pos.magic == 234000:
                        has_active_position = True
                        break
            
            if has_active_position:
                # Bu symbol uchun straddle allaqachon ishga tushgan, qayta qo'ymaymiz
                continue
            
            # 3. Yangi narxlar bilan qayta o'rnatamiz
            atr_pips = get_atr(mt5_client, symbol, mt5_client.TIMEFRAME_M5, 14)
            
            if not spread_check(mt5_client, symbol, atr_pips):
                logger.warning(f"[{symbol}] Rollover: Spread keng, bu symbol uchun o'tkazib yuborildi.")
                continue
            
            distance_pips = max(15.0, atr_pips * 2.0)
            
            account_info = mt5_client.account_info()
            digits = symbol_info.digits
            pip_size = symbol_info.point * 10 if digits in [3, 5] else (symbol_info.point * 100 if digits == 2 else symbol_info.point)
            
            if account_info:
                risk_amount = account_info.balance * 0.01
                tick_value = symbol_info.trade_tick_value
                tick_size = symbol_info.trade_tick_size
                if tick_value > 0 and tick_size > 0:
                    pip_value_per_lot = (pip_size / tick_size) * tick_value
                    lot_size = round(risk_amount / (distance_pips * pip_value_per_lot), 2) if pip_value_per_lot > 0 else 0.01
                else:
                    lot_size = 0.01
                lot_size = max(symbol_info.volume_min, min(lot_size, symbol_info.volume_max))
                if symbol_info.volume_step > 0:
                    lot_size = round(lot_size / symbol_info.volume_step) * symbol_info.volume_step
                    lot_size = round(lot_size, 2)
                if lot_size < symbol_info.volume_min:
                    lot_size = symbol_info.volume_min
            else:
                lot_size = 0.01
            
            tick = mt5_client.symbol_info_tick(symbol)
            if not tick:
                continue
            
            # Yangi narxlar bilan Buy Stop va Sell Stop
            buy_stop_price = tick.ask + (distance_pips * pip_size)
            success_b, msg_b, info_b = order_manager.place_pending_order(
                symbol=symbol,
                order_type_str="BUY_STOP",
                price=buy_stop_price,
                lot_size=lot_size,
                stop_loss_pips=distance_pips,
                take_profit_pips=distance_pips * 2.5,
                magic=234000,
                comment="News Straddle",
                expiration_minutes=2  # Keyingi yangilanishgacha 2 daqiqa
            )
            if success_b and info_b and "ticket" in info_b:
                DecisionLogger().log(
                    pair=symbol, timeframe="M5", context={"event": event_title},
                    prompt="NEWS_STRADDLE", response={}, decision="BUY_STOP", risk_pct=0.01,
                    ticket=info_b["ticket"], news_strategy_type="BEFORE_NEWS"
                )
            
            sell_stop_price = tick.bid - (distance_pips * pip_size)
            success_s, msg_s, info_s = order_manager.place_pending_order(
                symbol=symbol,
                order_type_str="SELL_STOP",
                price=sell_stop_price,
                lot_size=lot_size,
                stop_loss_pips=distance_pips,
                take_profit_pips=distance_pips * 2.5,
                magic=234000,
                comment="News Straddle",
                expiration_minutes=2  # Keyingi yangilanishgacha 2 daqiqa
            )
            if success_s and info_s and "ticket" in info_s:
                DecisionLogger().log(
                    pair=symbol, timeframe="M5", context={"event": event_title},
                    prompt="NEWS_STRADDLE", response={}, decision="SELL_STOP", risk_pct=0.01,
                    ticket=info_s["ticket"], news_strategy_type="BEFORE_NEWS"
                )
            
            logger.info(
                f"[{symbol}] ♻️ Straddle YANGILANDI (kechikish: {minutes_overdue:.1f} min). "
                f"Masofa: {distance_pips:.1f} pip. Lot: {lot_size}"
            )
        
        # Yangilash vaqtini belgilaymiz
        _LAST_ROLLOVER_TIME[event_title] = current_time


def post_news_fvg_hunter(mt5_client, symbol, smc_data):
    """
    Yangilikdan keyingi (15-30 daqiqa o'tib) FVG ga qaytishni ovlash logikasi.
    Bu funksiya asosan confluence engine va main.py tomonidan chaqirilishi rejalashtirilgan.
    """
    # Mantiq: 
    # 1. Yangilik o'tganiga qancha bo'ldi?
    # 2. Agar katta impulsive harakat (ATR dan ancha katta) qilingan bo'lsa
    # 3. Katta FVG hosil qilingan bo'lsa
    # 4. Narx orqaga qaytayotgan bo'lsa
    # => Limit order FVG boshiga qo'yiladi.
    pass

