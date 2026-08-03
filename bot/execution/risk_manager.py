import logging
from typing import Tuple, Optional, Any

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, mt5_client: Any, config: Any, state_manager: Any = None):
        self.mt5 = mt5_client
        self.config = config
        self.state_manager = state_manager

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
        # BotConfig maydoni `max_daily_loss_pct`; Cloud `max_daily_loss` bilan ham keladi — ikkalasini ham qo'llab-quvvatlaymiz.
        max_loss = getattr(self.config, "max_daily_loss_pct",
                           getattr(self.config, "max_daily_loss", 0.10))

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

    def check_max_positions(self, symbol: str) -> Tuple[bool, str]:
        """Bitta juftlik uchun maksimal ochiq pozitsiyalar sonini tekshiradi."""
        open_positions = self.mt5.get_positions(symbol=symbol)
        # Config dan olamiz, topilmasa standart 10
        max_pos = getattr(self.config, "max_positions_per_symbol", 10)
        
        if open_positions and len(open_positions) >= max_pos:
            return False, f"Max ochiq pozitsiyalar limitiga yetildi: {len(open_positions)} (Limit: {max_pos})"
            
        return True, "OK"

    def check_signal_cooldown(self, symbol: str, signal: str) -> Tuple[bool, str]:
        """Oxirgi marta shu juftlikda savdo ochilganiga qancha vaqt bo'lganini tekshiradi (cooldown)."""
        open_positions = self.mt5.get_positions(symbol=symbol)
        if not open_positions:
            return True, "OK"
            
        import time
        current_time = time.time()
        # Config dan olamiz, topilmasa standart 15 daqiqa
        cooldown_minutes = getattr(self.config, "signal_cooldown_minutes", 15)
        cooldown_seconds = cooldown_minutes * 60
        
        # BUY yoki BUY_LIMIT/BUY_STOP farqi yo'q asosiy yo'nalishni olamiz
        is_buy = "BUY" in signal.upper()
        signal_type = self.mt5.ORDER_TYPE_BUY if is_buy else self.mt5.ORDER_TYPE_SELL
        
        for pos in open_positions:
            if pos.type == signal_type:
                time_since_open = current_time - pos.time
                if time_since_open < cooldown_seconds:
                    minutes_passed = int(time_since_open / 60)
                    return False, f"Anti-spam: Aynan shu yo'nalishda {minutes_passed} daqiqa oldin bitim ochilgan. (Kutish kerak: {cooldown_minutes} daqiqa)"
                    
        return True, "OK"

    def calculate_lot_size(self, symbol: str, stop_loss_price_diff: float, risk_pct: Optional[float] = None) -> Tuple[Optional[float], str]:
        """Risk foiziga asoslanib lot hajmini hisoblaydi (Aniq formula)"""
        if risk_pct is None:
            risk_pct = getattr(self.config, "risk_per_trade", 0.02)
            
        account_info = self.mt5.account_info()
        if account_info is None:
            return None, "Hisob ma'lumotini olib bo'lmadi"
            
        balance = account_info.balance
        
        # Drawdown-based risk reduction (Kelly)
        if self.state_manager:
            peak_balance = self.state_manager.get_peak_balance()
            if peak_balance is None or balance > peak_balance:
                self.state_manager.update_peak_balance(balance)
                peak_balance = balance
                
            drawdown_pct = (peak_balance - balance) / peak_balance if peak_balance > 0 else 0
            drawdown_threshold = getattr(self.config, "drawdown_threshold_pct", 0.05)
            drawdown_multiplier = getattr(self.config, "drawdown_risk_multiplier", 0.5)
            
            if drawdown_pct >= drawdown_threshold:
                original_risk = risk_pct
                risk_pct = risk_pct * drawdown_multiplier
                logger.warning(
                    f"[{symbol}] Drawdown limitga yetdi! Peak: ${peak_balance:.2f}, Balance: ${balance:.2f} "
                    f"({drawdown_pct*100:.2f}% drawdown). Risk {original_risk*100:.2f}% dan {risk_pct*100:.2f}% ga tushirildi."
                )
        
        # 1. Risk qilinayotgan summa
        risk_amount = balance * risk_pct

        symbol_info = self.mt5.symbol_info(symbol)
        if symbol_info is None:
            return None, "Symbol ma'lumoti topilmadi"

        tick_value = symbol_info.trade_tick_value
        tick_size = symbol_info.trade_tick_size
        
        if tick_size <= 0 or tick_value <= 0 or stop_loss_price_diff <= 0:
            return None, "Noto'g'ri parametrlar: tick_size, tick_value yoki SL masofasi 0."

        # 2. 1 lot uchun risk qilinayotgan zarar
        loss_for_1_lot = (stop_loss_price_diff / tick_size) * tick_value
        
        if loss_for_1_lot <= 0:
            return None, "1 lot uchun zarar 0 yoki undan kichik chiqdi."

        # 3. Lot formulasini qo'llash
        raw_lot_size = risk_amount / loss_for_1_lot

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
        
        # Yakuniy xavfsizlik tekshiruvi: broker cheklovlari yoki lot yaxlitlash natijasida dollar zarar oshib ketmasligi
        actual_risk_amount = lot_size * loss_for_1_lot
        if actual_risk_amount > risk_amount * 1.25:  # 25% gacha farqqa ruxsat beramiz
            return None, f"Haqiqiy zarar (${actual_risk_amount:.2f}) ruxsat etilgan riskdan (${risk_amount:.2f}) juda yuqori! Katta ehtimol SL masofasi hisoblangan lot uchun juda katta."

        logger.info(
            f"[{symbol}] Risk Hisob-kitobi: Balans=${balance:.2f}, Risk={risk_pct*100:.2f}% (${risk_amount:.2f}), "
            f"SL Masofasi={stop_loss_price_diff:.5f}, 1 Lot SL Zarari=${loss_for_1_lot:.2f} -> "
            f"Kerakli Lot: {raw_lot_size:.4f}, Yaxlitlangan Lot: {lot_size}"
        )

        return lot_size, "OK"

    def validate_trade(self, symbol: str, signal: str, confidence: int, stop_loss_price_diff: float, risk_pct: Optional[float] = None) -> Tuple[bool, str, Optional[float]]:
        """
        Barcha risk tekshiruvlarini birlashtiradi.
        Qaytaradi: (ruxsat_bermi: bool, xabar: str, lot_size: float yoki None)
        """
        if signal == "HOLD":
            return False, "Signal HOLD — savdo qilinmaydi", None

        ok, msg = self.check_daily_loss_limit()
        if not ok:
            logger.warning(f"Risk tekshiruvi xatosi: {msg}")
            return False, msg, None

        ok, msg = self.check_confidence(confidence)
        if not ok:
            logger.warning(f"Risk tekshiruvi xatosi: {msg}")
            return False, msg, None

        # Max bitimlar tekshiruvi
        ok, msg = self.check_max_positions(symbol)
        if not ok:
            logger.warning(f"Risk tekshiruvi xatosi (Max Positions): {msg}")
            return False, msg, None

        # Cooldown / Anti-spam tekshiruvi
        ok, msg = self.check_signal_cooldown(symbol, signal)
        if not ok:
            logger.warning(f"Risk tekshiruvi xatosi (Cooldown): {msg}")
            return False, msg, None

        lot_size, msg = self.calculate_lot_size(symbol, stop_loss_price_diff, risk_pct=risk_pct)
        if lot_size is None:
            logger.warning(f"Risk tekshiruvi xatosi (Lot hisoblash): {msg}")
            return False, msg, None

        ok, msg = self.check_free_margin(symbol, lot_size)
        if not ok:
            logger.warning(f"Risk tekshiruvi xatosi (Free Margin): {msg}")
            return False, msg, None

        logger.info(f"Savdo uchun tasdiqlandi: lot {lot_size}")
        return True, "Savdo uchun tasdiqlandi", lot_size
