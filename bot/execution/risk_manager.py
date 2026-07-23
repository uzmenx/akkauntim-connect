import logging
from typing import Tuple, Optional, Any

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, mt5_client: Any, config: Any):
        self.mt5 = mt5_client
        self.config = config

    def check_daily_loss_limit(self) -> Tuple[bool, str]:
        """Kunlik zarar limiti oshib ketganini tekshiradi"""
        account_info = self.mt5.account_info()
        if account_info is None:
            return False, "Hisob ma'lumotini olib bo'lmadi"

        balance = account_info.balance
        equity = account_info.equity

        import datetime
        today_start = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
        deals = self.mt5.history_deals_get(today_start, datetime.datetime.now())
        realized_loss = sum(d.profit for d in deals if d.profit < 0) if deals else 0
        
        daily_loss_pct = (abs(realized_loss) + max(0, balance - equity)) / balance if balance > 0 else 0
        max_loss = getattr(self.config, "max_daily_loss", 0.10)

        if daily_loss_pct >= max_loss:
            return False, f"Kunlik zarar limiti oshib ketdi: {daily_loss_pct*100:.2f}% (Limit: {max_loss*100:.0f}%)"

        return True, "OK"

    def check_free_margin(self, symbol: str, lot_size: float) -> Tuple[bool, str]:
        """Free marginni tekshiradi"""
        account_info = self.mt5.account_info()
        if account_info is None:
            return False, "Hisob ma'lumotini olib bo'lmadi"
            
        margin_free = account_info.margin_free
        action = self.mt5.ORDER_TYPE_BUY
        symbol_info = self.mt5.symbol_info(symbol)
        if symbol_info is None:
            return False, "Symbol ma'lumotini olib bo'lmadi"
            
        margin_required = self.mt5.order_calc_margin(action, symbol, lot_size, symbol_info.ask)
        if margin_required is None:
            return False, "Marjani hisoblab bo'lmadi"
            
        if margin_free < margin_required:
            return False, f"Yetarli marja yo'q: kerak={margin_required:.2f}, erkin={margin_free:.2f}"
            
        return True, "OK"

    def check_confidence(self, confidence: int) -> Tuple[bool, str]:
        """AI ishonch darajasi yetarli emasligini tekshiradi"""
        min_conf = getattr(self.config, "min_confidence", 50)
        if confidence < min_conf:
            return False, f"Ishonch darajasi past: {confidence}% (minimal {min_conf}% kerak)"
        return True, "OK"

    def calculate_lot_size(self, symbol: str, stop_loss_pips: float, risk_pct: Optional[float] = None) -> Tuple[Optional[float], str]:
        """Risk foiziga asoslanib lot hajmini hisoblaydi"""
        if risk_pct is None:
            risk_pct = getattr(self.config, "risk_per_trade", 0.02)
            
        account_info = self.mt5.account_info()
        if account_info is None:
            return None, "Hisob ma'lumotini olib bo'lmadi"
            
        balance = account_info.balance
        
        # 1. Risk qilinayotgan summa
        risk_amount = balance * risk_pct

        symbol_info = self.mt5.symbol_info(symbol)
        if symbol_info is None:
            return None, "Symbol ma'lumoti topilmadi"

        tick_value = symbol_info.trade_tick_value
        digits = symbol_info.digits
        
        # 2. 1 pip qiymatini hisoblash (1 lot uchun)
        # MT5 da tick_value bu 1 ta point (tick) o'zgarishining 1 lot uchun qiymati.
        # Bizda stop_loss_pips berilgan, shuning uchun pip qadrini topishimiz kerak.
        if digits == 3 or digits == 5:  # JPY (masalan 150.123) yoki standart Forex (1.10543)
            # 1 pip = 10 point (tick)
            pip_value_per_lot = tick_value * 10
        elif digits == 2:  # Oltin (XAUUSD - 2400.50)
            # Oltin uchun pip divisor odatda 0.1 (ya'ni 1 pip = 0.1)
            # Tick o'lchami esa 0.01. Demak 1 pip = 10 tick.
            pip_value_per_lot = tick_value * 10
        else:
            pip_value_per_lot = tick_value * 10 # Standart fallback

        if pip_value_per_lot <= 0 or stop_loss_pips <= 0:
            return None, "Noto'g'ri SL yoki Pip Value parametrlar"

        # 3. Lot formulasini qo'llash
        # Lot = Risk Summasi / (SL pips * 1 lot uchun Pip Value)
        raw_lot_size = risk_amount / (stop_loss_pips * pip_value_per_lot)

        # 4. Broker cheklovlariga (volume step) aniq moslashtirish
        volume_step = symbol_info.volume_step
        if volume_step > 0:
            lot_size = round(raw_lot_size / volume_step) * volume_step
        else:
            lot_size = raw_lot_size
            
        lot_size = round(lot_size, 2)
        
        # Min va Max broker limitlari
        lot_size = max(symbol_info.volume_min, min(lot_size, symbol_info.volume_max))

        # 5. O'zimizning xavfsizlik chegaramiz
        max_lot = getattr(self.config, "max_lot_size", 5.0)
        lot_size = min(lot_size, max_lot)

        logger.info(
            f"[{symbol}] Risk Hisob-kitobi: Balans=${balance:.2f}, Risk={risk_pct*100:.2f}% (${risk_amount:.2f}), "
            f"SL={stop_loss_pips} pip, Pip Value=${pip_value_per_lot:.2f} -> "
            f"Kerakli Lot: {raw_lot_size:.4f}, Yaxlitlangan Lot: {lot_size}"
        )

        return lot_size, "OK"

    def validate_trade(self, symbol: str, signal: str, confidence: int, stop_loss_pips: float, risk_pct: Optional[float] = None) -> Tuple[bool, str, Optional[float]]:
        """
        Barcha risk tekshiruvlarini birlashtiradi.
        Qaytaradi: (ruxsat_bermi: bool, xabar: str, lot_size: float yoki None)
        """
        ok, msg = self.check_daily_loss_limit()
        if not ok:
            logger.warning(f"Risk tekshiruvi xatosi: {msg}")
            return False, msg, None

        ok, msg = self.check_confidence(confidence)
        if not ok:
            logger.warning(f"Risk tekshiruvi xatosi: {msg}")
            return False, msg, None

        if signal == "HOLD":
            return False, "Signal HOLD — savdo qilinmaydi", None

        lot_size, msg = self.calculate_lot_size(symbol, stop_loss_pips, risk_pct=risk_pct)
        if lot_size is None:
            logger.warning(f"Risk tekshiruvi xatosi (Lot hisoblash): {msg}")
            return False, msg, None

        ok, msg = self.check_free_margin(symbol, lot_size)
        if not ok:
            logger.warning(f"Risk tekshiruvi xatosi (Free Margin): {msg}")
            return False, msg, None

        logger.info(f"Savdo uchun tasdiqlandi: lot {lot_size}")
        return True, "Savdo uchun tasdiqlandi", lot_size
