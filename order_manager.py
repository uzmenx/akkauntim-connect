import MetaTrader5 as mt5
import json
import os
from ai_analysis import get_trailing_decision, build_decision_context

STATE_FILE = "trades_state.json"

def load_trade_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_trade_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def set_trade_info(ticket, info):
    state = load_trade_state()
    # Merge existing info with new info
    existing = state.get(str(ticket), {})
    existing.update(info)
    state[str(ticket)] = existing
    save_trade_state(state)

def get_trade_info(ticket):
    state = load_trade_state()
    return state.get(str(ticket), {})

def place_order(symbol, signal, lot_size, stop_loss_pips, take_profit_pips):
    """
    Tasdiqlangan signal asosida MT5'ga order yuboradi.
    Qaytaradi: (muvaffaqiyatli_mi: bool, xabar: str, order_ma'lumoti: dict yoki None)
    """
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return False, f"{symbol} topilmadi", None

    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            return False, f"{symbol} tanlab bo'lmadi", None

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return False, "Narx ma'lumotini olib bo'lmadi", None

    point = symbol_info.point
    pip_size = point * 10  # 5-xonali narxlar uchun 1 pip = 10 point

    if signal == "BUY":
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask
        sl = price - stop_loss_pips * pip_size
        tp = price + take_profit_pips * pip_size
    elif signal == "SELL":
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid
        sl = price + stop_loss_pips * pip_size
        tp = price - take_profit_pips * pip_size
    else:
        return False, "Noto'g'ri signal turi", None

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 234000,
        "comment": "AI forex bot",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }

    result = mt5.order_send(request)

    if result is None:
        return False, f"Order yuborilmadi: {mt5.last_error()}", None

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return False, f"Order rad etildi, kod: {result.retcode}, komment: {result.comment}", None

    order_info = {
        "ticket": result.order,
        "symbol": symbol,
        "signal": signal,
        "volume": lot_size,
        "price": price,
        "sl": sl,
        "tp": tp,
    }

    # Holatni saqlash
    one_r_dist = stop_loss_pips * pip_size
    set_trade_info(result.order, {
        "status": "OPEN", 
        "1r_dist": one_r_dist,
        "entry_price": price,
        "signal": signal,
        "partial_closed": False,
        "trailing_mode": None,
        "current_sl_level": 0 # Necha R ga surilgani (masalan 1, 2)
    })

    return True, "Order muvaffaqiyatli ochildi", order_info

def close_partial_position(ticket, percent):
    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        return False, "Position topilmadi"
    position = positions[0]
    
    close_volume = round(position.volume * (percent / 100.0), 2)
    if close_volume <= 0:
        return False, "Hajm kichik"
        
    symbol = position.symbol
    tick = mt5.symbol_info_tick(symbol)
    
    if position.type == mt5.ORDER_TYPE_BUY:
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid
    else:
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask
        
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": close_volume,
        "type": order_type,
        "position": ticket,
        "price": price,
        "deviation": 20,
        "magic": 234000,
        "comment": "Partial close (70%)",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_FOK,
    }
    
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        return False, f"Partial close error: {mt5.last_error()}"
    return True, "Partial close qilingan"

def update_sl(ticket, new_sl):
    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        return False, "Position topilmadi"
    position = positions[0]
    
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": position.symbol,
        "sl": new_sl,
        "tp": position.tp,
        "position": ticket,
        "magic": 234000
    }
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        return False, f"SL update error"
    return True, "SL surildi"

def manage_open_trades():
    """
    Ochiq pozitsiyalarni tekshiradi va 2R ga yetganlarni 70% yopadi.
    Qolgan 30% uchun AI dan trailing rejimini so'raydi.
    """
    positions = mt5.positions_get()
    if not positions:
        return

    for pos in positions:
        ticket = pos.ticket
        info = get_trade_info(ticket)
        if not info:
            continue # Biz ochmagan yoki ma'lumoti yo'q trade
            
        signal = info.get("signal")
        entry_price = info.get("entry_price")
        one_r = info.get("1r_dist")
        
        if not one_r or one_r <= 0:
            continue
            
        current_price = pos.price_current
        
        # Qancha R foydadamiz?
        if signal == "BUY":
            profit_r = (current_price - entry_price) / one_r
        else:
            profit_r = (entry_price - current_price) / one_r
            
        if profit_r < 0:
            continue # Zararda bo'lsak tegmaymiz
            
        # 1. TP1 (2R) ga yetdimi?
        if profit_r >= 2.0 and not info.get("partial_closed"):
            print(f"[{pos.symbol}] 2R foydaga yetdi! 70% yopilyapti...")
            # 70% ni yopish
            success, msg = close_partial_position(ticket, 70)
            if success:
                # SL ni +1R ga surish
                if signal == "BUY":
                    new_sl = entry_price + one_r
                else:
                    new_sl = entry_price - one_r
                    
                update_sl(ticket, new_sl)
                
                # Holatni yangilash
                set_trade_info(ticket, {
                    "partial_closed": True,
                    "current_sl_level": 1
                })
                print(f"[{pos.symbol}] 70% yopildi, SL +1R ga surildi.")
            continue
            
        # 2. Agar oldin 70% yopilgan bo'lsa (runner pozitsiya), Trailing qilamiz
        if info.get("partial_closed") and profit_r >= 2.0:
            # AI dan decision olish
            trailing_mode = info.get("trailing_mode")
            if not trailing_mode:
                # Context yaratish va AI dan so'rash
                try:
                    context = build_decision_context(pos.symbol, "H1")
                    trailing_mode = get_trailing_decision(context)
                    set_trade_info(ticket, {"trailing_mode": trailing_mode})
                    print(f"[{pos.symbol}] AI Trailing rejimini tanladi: {trailing_mode}")
                except Exception as e:
                    print("Trailing qarori olishda xato:", e)
                    trailing_mode = "STEP"
            
            # Trailing logikasi
            if trailing_mode == "CLOSE_ALL":
                print(f"[{pos.symbol}] AI bozor xavfli deb topdi, pozitsiya to'liq yopilmoqda.")
                close_partial_position(ticket, 100)
                set_trade_info(ticket, {"status": "CLOSED"})
                
            elif trailing_mode == "STEP":
                # Har 1R o'sganda SL ni 1R surish
                # Agar profit_r = 3.5 bo'lsa, current_sl_level = 2 bo'lishi kerak
                expected_sl_level = int(profit_r) - 1 # Masalan 3R da SL = +2R
                
                if expected_sl_level > info.get("current_sl_level", 0):
                    if signal == "BUY":
                        new_sl = entry_price + (expected_sl_level * one_r)
                    else:
                        new_sl = entry_price - (expected_sl_level * one_r)
                        
                    # SL ni faqat foyda tomonga surish mumkin
                    if (signal == "BUY" and new_sl > pos.sl) or (signal == "SELL" and (pos.sl == 0 or new_sl < pos.sl)):
                        update_sl(ticket, new_sl)
                        set_trade_info(ticket, {"current_sl_level": expected_sl_level})
                        print(f"[{pos.symbol}] STEP Trailing: SL +{expected_sl_level}R ga surildi.")
            
            elif trailing_mode == "STRUCTURE":
                # Structure or ATR trailing. Hozircha oddiyroq step lekin kattaroq qadam bilan (masalan 2R orqada) qilinishi mumkin.
                # SMC orqali oxirgi High/Low ni olish mumkin.
                try:
                    context = build_decision_context(pos.symbol, "H1")
                    smc_events = context.get("smc_structure", {})
                    # Oddiylik uchun Structure trailingni ham hozircha narxga bog'laymiz
                    # Aslida smc_events dan oxirgi High yoki Low ni olib SL ga qoyish kerak
                    last_low = smc_events.get("low_val")
                    last_high = smc_events.get("high_val")
                    
                    if signal == "BUY" and last_low and last_low > pos.sl:
                        update_sl(ticket, last_low)
                        print(f"[{pos.symbol}] STRUCTURE Trailing: SL yangi Low ga surildi ({last_low}).")
                    elif signal == "SELL" and last_high and (pos.sl == 0 or last_high < pos.sl):
                        update_sl(ticket, last_high)
                        print(f"[{pos.symbol}] STRUCTURE Trailing: SL yangi High ga surildi ({last_high}).")
                except Exception as e:
                    print("Structure trailing xato:", e)

def place_pending_order(symbol, order_type_str, price, lot_size, stop_loss_pips, take_profit_pips):
    """
    Kutilayotgan (Pending) orderlarni joylashtirish (Buy Stop, Sell Stop).
    """
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return False, f"{symbol} topilmadi", None

    if not symbol_info.visible:
        if not mt5.symbol_select(symbol, True):
            return False, f"{symbol} tanlab bo'lmadi", None

    point = symbol_info.point
    pip_size = point * 10

    if order_type_str == "BUY_STOP":
        order_type = mt5.ORDER_TYPE_BUY_STOP
        sl = price - stop_loss_pips * pip_size
        tp = price + take_profit_pips * pip_size
    elif order_type_str == "SELL_STOP":
        order_type = mt5.ORDER_TYPE_SELL_STOP
        sl = price + stop_loss_pips * pip_size
        tp = price - take_profit_pips * pip_size
    else:
        return False, "Noto'g'ri pending order turi", None

    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": lot_size,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 234000,
        "comment": "News Straddle",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN, # PENDING orderlarda FOK ishlamasligi mumkin
    }

    result = mt5.order_send(request)

    if result is None:
        return False, f"Pending order yuborilmadi: {mt5.last_error()}", None

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        return False, f"Pending order rad etildi, kod: {result.retcode}, komment: {result.comment}", None

    order_info = {
        "ticket": result.order,
        "symbol": symbol,
        "signal": order_type_str,
        "volume": lot_size,
        "price": price,
        "sl": sl,
        "tp": tp,
        "1r_dist": stop_loss_pips * pip_size
    }

    set_trade_info(result.order, {
        "status": "PENDING", 
        "1r_dist": stop_loss_pips * pip_size,
        "entry_price": price,
        "signal": "BUY" if "BUY" in order_type_str else "SELL",
        "partial_closed": False,
        "trailing_mode": None,
        "current_sl_level": 0,
        "is_straddle": True
    })

    return True, "Pending order muvaffaqiyatli qo'yildi", order_info

def delete_pending_order(ticket):
    """
    Osilg'liq (Pending) orderni o'chirib yuborish.
    """
    request = {
        "action": mt5.TRADE_ACTION_REMOVE,
        "order": ticket
    }
    result = mt5.order_send(request)
    if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
        return False, f"O'chirishda xatolik: {mt5.last_error()}"
    
    set_trade_info(ticket, {"status": "DELETED"})
    return True, "O'chirildi"

def manage_pending_orders():
    """
    News Straddle uchun qo'yilgan, lekin ishga tushmagan qopqonlarni 
    yangilik o'tgandan keyin bekor qilish.
    """
    orders = mt5.orders_get()
    if not orders:
        return
        
    for ord in orders:
        if ord.magic == 234000 and "News" in ord.comment:
            # Agar bu order uzoq vaqt osilib tursa (biz news_straddle_engine da buni qachon o'chirishni belgilaymiz)
            # Yoki boshqa order ishlab ketgan bo'lsa, ikkinchisini o'chiramiz.
            # Eng oddiysi, news_straddle_engine o'zi chaqiradi buni.
            pass
