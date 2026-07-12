import MetaTrader5 as mt5


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
        "type_filling": mt5.ORDER_FILLING_IOC,
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

    return True, "Order muvaffaqiyatli ochildi", order_info