import logging
import time
from datetime import datetime, timezone
from bot.strategy.news.detector import NewsDetector
from bot.strategy.news.ai_analyzer import NewsAIAnalyzer
from bot.strategy.news.straddle import CURRENCY_PAIRS_MAP
from bot.engine.decision_logger import DecisionLogger

logger = logging.getLogger(__name__)

# Ochiq qoldirmaslik uchun allaqachon trade qilingan yangiliklar ro'yxati (kesh)
_PROCESSED_EVENTS = {}  # {event_title: last_processed_utc_datetime}

def execute_fundamental_method(mt5_client, order_manager, llm_engine):
    """
    Medium/High yangilik chiqqandan so'ng (0-5 daqiqa ichida),
    Haqiqiy (Actual) natijani kutib, AI yordamida uzoq muddatli qaror qabul qiladi.
    """
    detector = NewsDetector()
    
    # Keshdan o'qimaymiz, API dan tortamiz (chunki raqam chiqishini kutyapmiz)
    if not detector.fetch_calendar(force_refresh=True):
        return
    
    # Oxirgi 1 soat ichidagi yangiliklarni olamiz
    recent_news = detector.get_news_history(hours_back=0.1) # Oxirgi 6 daqiqa
    
    for event in recent_news:
        if event.get('impact') not in ["High", "Medium"]:
            continue
            
        event_title = event.get('title')
        actual = event.get('actual')
        
        # Agar haqiqiy natija hali chiqmagan bo'lsa yoki oldin ishlangan bo'lsa o'tkazib yuboramiz
        if not actual:
            continue
        last_proc = _PROCESSED_EVENTS.get(event_title)
        if last_proc and (datetime.now(timezone.utc) - last_proc).total_seconds() < 7200:
            continue
            
        logger.info(f"[Fundamental] '{event_title}' uchun Actual natija chiqdi: {actual}. AI tahlili boshlandi.")
        _PROCESSED_EVENTS[event_title] = datetime.now(timezone.utc)
        
        country = event.get('country', 'USD')
        forecast = event.get('forecast', 'N/A')
        previous = event.get('previous', 'N/A')
        
        # Asosiy savdo qilinadigan valyutani topamiz (birinchisini olamiz)
        target_symbol = CURRENCY_PAIRS_MAP.get(country, ["EURUSD"])[0]
        
        # AI uchun Prompt yasash
        prompt = NewsAIAnalyzer.get_prompt_for_news(
            symbol=target_symbol,
            news_title=event_title,
            actual=actual,
            forecast=forecast,
            previous=previous
        )
        
        if not llm_engine:
            logger.warning("[Fundamental] LLM Engine topilmadi. AI qarori bekor qilindi.")
            continue
            
        # AI ga jo'natish
        try:
            ai_response = llm_engine.generate(prompt)
        except Exception as e:
            logger.error(f"[Fundamental] AI so'rovida xatolik: {e}")
            continue
        logger.info(f"[Fundamental] AI Javobi:\n{ai_response}")
        
        # Hukmni o'qish (BUY/SELL, TP, SL)
        hukm_data = NewsAIAnalyzer.parse_advanced_hukm(ai_response)
        direction = hukm_data["direction"]
        
        if direction == "NEUTRAL":
            logger.info(f"[Fundamental] AI '{event_title}' bo'yicha NEUTRAL qaror qabul qildi. Trade ochilmaydi.")
            continue
            
        # 0.05% riskni hisoblash va trade ochish
        symbol_info = mt5_client.symbol_info(target_symbol)
        if not symbol_info:
            continue
            
        account_info = mt5_client.account_info()
        if not account_info:
            continue
            
        risk_amount = account_info.balance * 0.0005 # 0.05% Risk
        
        # Pip size
        digits = symbol_info.digits
        pip_size = symbol_info.point * 10 if digits in [3, 5] else (symbol_info.point * 100 if digits == 2 else symbol_info.point)
        
        sl_pips = hukm_data["sl_pips"]
        tp_pips = hukm_data["tp_pips"]
        
        if sl_pips <= 0: sl_pips = 50 # Fallback
        
        # Universal lot size calculation
        tick_value = symbol_info.trade_tick_value
        tick_size = symbol_info.trade_tick_size
        if tick_value > 0 and tick_size > 0:
            pip_value_per_lot = (pip_size / tick_size) * tick_value
            lot_size = round(risk_amount / (sl_pips * pip_value_per_lot), 2) if pip_value_per_lot > 0 else 0.01
        else:
            lot_size = 0.01
        lot_size = max(symbol_info.volume_min, min(lot_size, symbol_info.volume_max))
        if lot_size < symbol_info.volume_min:
            lot_size = symbol_info.volume_min
            
        tick = mt5_client.symbol_info_tick(target_symbol)
        if not tick:
            continue
            
        logger.info(f"[Fundamental] {direction} {target_symbol}. Lot: {lot_size}. SL: {sl_pips}, TP: {tp_pips}")
        
        try:
            if direction == "BUY":
                success, msg, info = order_manager.place_order(
                    symbol=target_symbol,
                    signal="BUY",
                    lot_size=lot_size,
                    stop_loss_pips=sl_pips,
                    take_profit_pips=tp_pips
                )
                if success and info and "ticket" in info:
                    DecisionLogger().log(
                        pair=target_symbol, timeframe="M5", context={"event": event_title},
                        prompt="NEWS_FUNDAMENTAL", response=hukm_data, decision="BUY", risk_pct=0.05,
                        ticket=info["ticket"], news_strategy_type="AFTER_NEWS"
                    )
            elif direction == "SELL":
                success, msg, info = order_manager.place_order(
                    symbol=target_symbol,
                    signal="SELL",
                    lot_size=lot_size,
                    stop_loss_pips=sl_pips,
                    take_profit_pips=tp_pips
                )
                if success and info and "ticket" in info:
                    DecisionLogger().log(
                        pair=target_symbol, timeframe="M5", context={"event": event_title},
                        prompt="NEWS_FUNDAMENTAL", response=hukm_data, decision="SELL", risk_pct=0.05,
                        ticket=info["ticket"], news_strategy_type="AFTER_NEWS"
                    )
        except Exception as e:
            logger.error(f"[Fundamental] Order joylashtirish xatosi ({direction} {target_symbol}): {e}")
