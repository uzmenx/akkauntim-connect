import MetaTrader5 as mt5

# ===== Risk parametrlari =====
RISK_PER_TRADE = 0.02      # Har bir savdoda hisobning 2%
MAX_DAILY_LOSS = 0.10      # Kunlik maksimal zarar 10%
MIN_CONFIDENCE = 50        # Minimal ishonch darajasi
MAX_LOT_SIZE = 5.0         # Hech qachon bitta savdoda shu hajmdan oshmaydi


def check_daily_loss_limit():
    """Kunlik zarar limiti oshib ketganini tekshiradi"""
    account_info = mt5.account_info()
    if account_info is None:
        return False, "Hisob ma'lumotini olib bo'lmadi"

    balance = account_info.balance
    equity = account_info.equity

    daily_loss_pct = (balance - equity) / balance if balance > 0 else 0

    if daily_loss_pct >= MAX_DAILY_LOSS:
        return False, f"Kunlik zarar limiti oshib ketdi: {daily_loss_pct*100:.2f}%"

    return True, "OK"


def check_confidence(confidence):
    """AI ishonch darajasi yetarli emasligini tekshiradi"""
    if confidence < MIN_CONFIDENCE:
        return False, f"Ishonch darajasi past: {confidence}% (minimal {MIN_CONFIDENCE}% kerak)"
    return True, "OK"


def calculate_lot_size(symbol, stop_loss_pips):
    """Risk foiziga asoslanib lot hajmini hisoblaydi"""
    account_info = mt5.account_info()
    balance = account_info.balance

    risk_amount = balance * RISK_PER_TRADE

    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        return None, "Symbol ma'lumoti topilmadi"

    tick_value = symbol_info.trade_tick_value
    pip_value_per_lot = tick_value * 10

    if pip_value_per_lot <= 0 or stop_loss_pips <= 0:
        return None, "Noto'g'ri parametrlar"

    lot_size = risk_amount / (stop_loss_pips * pip_value_per_lot)

    # Broker cheklovlariga moslashtirish
    lot_size = max(symbol_info.volume_min, min(lot_size, symbol_info.volume_max))

    # Bizning o'z xavfsizlik chegaramiz — bu hech qachon oshib ketmasligi kerak
    lot_size = min(lot_size, MAX_LOT_SIZE)

    lot_size = round(lot_size / symbol_info.volume_step) * symbol_info.volume_step
    lot_size = round(lot_size, 2)

    return lot_size, "OK"


def validate_trade(symbol, signal, confidence, stop_loss_pips):
    """
    Barcha risk tekshiruvlarini birlashtiradi.
    Qaytaradi: (ruxsat_bermi: bool, xabar: str, lot_size: float yoki None)
    """
    ok, msg = check_daily_loss_limit()
    if not ok:
        return False, msg, None

    ok, msg = check_confidence(confidence)
    if not ok:
        return False, msg, None

    if signal == "HOLD":
        return False, "Signal HOLD — savdo qilinmaydi", None

    lot_size, msg = calculate_lot_size(symbol, stop_loss_pips)
    if lot_size is None:
        return False, msg, None

    return True, "Savdo uchun tasdiqlandi", lot_size