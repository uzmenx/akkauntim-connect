import logging
import time
from typing import Tuple, Optional, Any, Callable, Dict

logger = logging.getLogger(__name__)


class OrderManager:
    # Portfolio guards (rejadagi qarorlar bo'yicha)
    MAX_POSITIONS_PER_SYMBOL = 2
    COOLDOWN_SECONDS = 60           # yopilgandan keyin 1 daqiqa
    PENDING_TTL_SECONDS = 6 * 3600  # 6 soat
    TP1_PORTION = 0.70              # umumiy hajmning 70% TP1'ga ketadi

    def __init__(self, mt5_client: Any, state_manager: Any, config: Any):
        self.mt5 = mt5_client
        self.state_manager = state_manager
        self.config = config
        self.magic_number = getattr(self.config, "magic_number", 234000)
        # symbol -> yopilgan-vaqt (epoch) — cooldown uchun
        self._last_closed: Dict[str, float] = {}

    def _symbol_deviation(self, symbol: str) -> int:
        """Symbol-aware slippage/deviation (points)."""
        s = symbol.upper()
        if "XAU" in s or "GOLD" in s or "BTC" in s:
            return 50
        if "JPY" in s:
            return 30
        return 20

    def record_closed(self, symbol: str) -> None:
        """Yopilgan pozitsiyadan keyin cooldown boshlash."""
        self._last_closed[symbol] = time.time()

    def _in_cooldown(self, symbol: str) -> bool:
        ts = self._last_closed.get(symbol)
        if not ts:
            return False
        return (time.time() - ts) < self.COOLDOWN_SECONDS

    def _open_count(self, symbol: str) -> int:
        try:
            positions = self.mt5.positions_get(symbol=symbol) or []
            return sum(1 for p in positions if p.magic == self.magic_number)
        except Exception:
            return 0


    def _get_filling_mode(self, symbol: str) -> int:
        """Broker qo'llab-quvvatlaydigan filling mode ni aniqlash."""
        try:
            import MetaTrader5 as mt5
            FILLING_FOK = mt5.ORDER_FILLING_FOK
            FILLING_IOC = mt5.ORDER_FILLING_IOC
            FILLING_RETURN = mt5.ORDER_FILLING_RETURN
            SYMBOL_FOK = getattr(mt5, 'SYMBOL_FILLING_FOK', 1)
            SYMBOL_IOC = getattr(mt5, 'SYMBOL_FILLING_IOC', 2)
        except (ImportError, AttributeError):
            # Fallback constants
            FILLING_FOK, FILLING_IOC, FILLING_RETURN = 0, 1, 2
            SYMBOL_FOK, SYMBOL_IOC = 1, 2
        
        symbol_info = self.mt5.symbol_info(symbol)
        if not symbol_info:
            return FILLING_FOK
        filling_mode = symbol_info.filling_mode
        if filling_mode & SYMBOL_FOK:
            return FILLING_FOK
        elif filling_mode & SYMBOL_IOC:
            return FILLING_IOC
        return FILLING_RETURN

    def place_order(self, symbol: str, signal: str, lot_size: float, stop_loss_pips: float, take_profit_pips: float, entry_price: Optional[float] = None) -> Tuple[bool, str, Optional[dict]]:
        """
        Tasdiqlangan signal asosida MT5'ga order (Market yoki Pending) yuboradi.
        """
        symbol_info = self.mt5.symbol_info(symbol)
        if symbol_info is None:
            return False, f"{symbol} topilmadi", None

        if not symbol_info.visible:
            if not self.mt5.symbol_select(symbol, True):
                return False, f"{symbol} tanlab bo'lmadi", None

        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None:
            return False, "Narx ma'lumotini olib bo'lmadi", None

        point = symbol_info.point
        digits = symbol_info.digits
        # pip_size: 5-xonali forex va 3-xonali JPY uchun 1 pip = 10 point.
        # 4-xonali forex (kam uchraydi) va 2-xonali indeks/gold uchun 1 pip = 1 point (gold da point=0.01, pip=0.1 → mul=10, alohida ishlaymiz).
        if digits in (3, 5):
            pip_size = point * 10
        elif digits == 2:
            # Gold/silver: point=0.01, pip=0.1
            pip_size = point * 10
        else:
            pip_size = point
        pip_mul = pip_size / point if point > 0 else 10  # necha "point" = 1 "pip"

        # --- SPREAD FILTER ---
        current_spread_points = round((tick.ask - tick.bid) / point)
        max_multiplier = getattr(self.config, "max_spread_multiplier", 4.0)
        
        # Get spread from the last 10 M15 candles from MT5
        rates = self.mt5.copy_rates_from_pos(symbol, self.mt5.TIMEFRAME_M15, 1, 10)
        if rates is not None and len(rates) > 0:
            avg_spread_points = sum(r['spread'] for r in rates) / len(rates)
            if avg_spread_points > 0:
                max_allowed_spread_points = avg_spread_points * max_multiplier
                if current_spread_points > max_allowed_spread_points:
                    logger.warning(f"[{symbol}] Spread filter triggered: Current spread ({current_spread_points} points) is {max_multiplier}x larger than average ({avg_spread_points:.1f} points). Trade aborted.")
                    return False, f"Spread is too high ({current_spread_points} points)", None
        # ---------------------

        # trade_stops_level broker tomonidan POINT birlikda beriladi — pip'ga o'girish uchun pip_mul ga bo'lamiz.
        stop_level_pips = symbol_info.trade_stops_level / pip_mul if pip_mul > 0 else 0
        if stop_loss_pips < stop_level_pips:
            stop_loss_pips = stop_level_pips
        if take_profit_pips < stop_level_pips:
            take_profit_pips = stop_level_pips

        # Signal va narxlarni hisoblash
        action = self.mt5.TRADE_ACTION_DEAL
        order_type = None
        price = None
        
        if signal == "BUY":
            order_type = self.mt5.ORDER_TYPE_BUY
            price = tick.ask
        elif signal == "SELL":
            order_type = self.mt5.ORDER_TYPE_SELL
            price = tick.bid
        elif signal == "BUY_LIMIT":
            if entry_price is None:
                logger.warning(f"Pending order ({signal}) uchun entry_price berilmagan, o'tkazib yuborildi.")
                return False, f"Pending order uchun entry_price majburiy", None
            action = self.mt5.TRADE_ACTION_PENDING
            order_type = self.mt5.ORDER_TYPE_BUY_LIMIT
            price = entry_price
        elif signal == "SELL_LIMIT":
            if entry_price is None:
                logger.warning(f"Pending order ({signal}) uchun entry_price berilmagan, o'tkazib yuborildi.")
                return False, f"Pending order uchun entry_price majburiy", None
            action = self.mt5.TRADE_ACTION_PENDING
            order_type = self.mt5.ORDER_TYPE_SELL_LIMIT
            price = entry_price
        elif signal == "BUY_STOP":
            if entry_price is None:
                logger.warning(f"Pending order ({signal}) uchun entry_price berilmagan, o'tkazib yuborildi.")
                return False, f"Pending order uchun entry_price majburiy", None
            action = self.mt5.TRADE_ACTION_PENDING
            order_type = self.mt5.ORDER_TYPE_BUY_STOP
            price = entry_price
        elif signal == "SELL_STOP":
            if entry_price is None:
                logger.warning(f"Pending order ({signal}) uchun entry_price berilmagan, o'tkazib yuborildi.")
                return False, f"Pending order uchun entry_price majburiy", None
            action = self.mt5.TRADE_ACTION_PENDING
            order_type = self.mt5.ORDER_TYPE_SELL_STOP
            price = entry_price
        else:
            return False, f"Noto'g'ri signal turi: {signal}", None

        # SL va TP ni hisoblash (digits yuqorida allaqachon o'rnatildi)
        if "BUY" in signal:
            sl = round(price - stop_loss_pips * pip_size, digits)
            tp = round(price + take_profit_pips * pip_size, digits)
        elif "SELL" in signal:
            sl = round(price + stop_loss_pips * pip_size, digits)
            tp = round(price - take_profit_pips * pip_size, digits)

        request = {
            "action": action,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": self.magic_number,
            "comment": "AI forex bot",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self._get_filling_mode(symbol),
        }

        result = self.mt5.order_send(request)

        if result is None:
            return False, f"Order yuborilmadi: {self.mt5.last_error()}", None

        if result.retcode != self.mt5.TRADE_RETCODE_DONE:
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
        self.state_manager.set_trade_info(result.order, {
            "status": "OPEN", 
            "1r_dist": one_r_dist,
            "entry_price": price,
            "signal": signal,
            "partial_closed": False,
            "trailing_mode": None,
            "current_sl_level": 0
        })

        return True, "Order muvaffaqiyatli ochildi", order_info

    def close_partial_position(self, ticket: int, percent: float) -> Tuple[bool, str]:
        positions = self.mt5.positions_get(ticket=ticket)
        if not positions:
            return False, "Position topilmadi"
        position = positions[0]
        
        symbol_info = self.mt5.symbol_info(position.symbol)
        close_volume = round(round((position.volume * (percent / 100.0)) / symbol_info.volume_step) * symbol_info.volume_step, 2)
        if close_volume <= 0:
            return False, "Hajm kichik"
            
        symbol = position.symbol
        tick = self.mt5.symbol_info_tick(symbol)
        if not tick:
            return False, "Tick ma'lumoti topilmadi"
        
        if position.type == self.mt5.ORDER_TYPE_BUY:
            order_type = self.mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            order_type = self.mt5.ORDER_TYPE_BUY
            price = tick.ask
            
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": close_volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": self.magic_number,
            "comment": f"Partial close ({percent}%)",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self._get_filling_mode(symbol),
        }
        
        result = self.mt5.order_send(request)
        if result is None or result.retcode != self.mt5.TRADE_RETCODE_DONE:
            return False, f"Partial close error: {self.mt5.last_error()}"
        return True, f"Partial close {percent}% qilingan"

    def update_sl(self, ticket: int, new_sl: float) -> Tuple[bool, str]:
        positions = self.mt5.positions_get(ticket=ticket)
        if not positions:
            return False, "Position topilmadi"
        position = positions[0]
        
        symbol_info = self.mt5.symbol_info(position.symbol)
        digits = symbol_info.digits
        new_sl = round(new_sl, digits)
        
        request = {
            "action": self.mt5.TRADE_ACTION_SLTP,
            "symbol": position.symbol,
            "sl": new_sl,
            "tp": position.tp,
            "position": ticket,
            "magic": self.magic_number
        }
        result = self.mt5.order_send(request)
        if result is None or result.retcode != self.mt5.TRADE_RETCODE_DONE:
            return False, "SL update error"
        return True, "SL surildi"

    def manage_open_trades(self, trailing_decision_fn: Callable[[str], str]):
        """
        Ochiq pozitsiyalarni tekshiradi va 2R ga yetganlarni 70% yopadi.
        Qolgan 30% uchun callback yordamida AI dan trailing rejimini so'raydi.
        """
        positions = self.mt5.positions_get()
        if not positions:
            return

        for pos in positions:
            ticket = pos.ticket
            info = self.state_manager.get_trade_info(ticket)
            if not info:
                continue
                
            signal = info.get("signal")
            entry_price = info.get("entry_price")
            one_r = info.get("1r_dist")
            
            if not one_r or one_r <= 0:
                continue
                
            current_price = pos.price_current
            
            if signal == "BUY":
                profit_r = (current_price - entry_price) / one_r
            else:
                profit_r = (entry_price - current_price) / one_r
                
            if profit_r < 0:
                continue
                
            # TP1 (2R) ga yetdimi?
            if profit_r >= 2.0 and not info.get("partial_closed"):
                logger.info(f"[{pos.symbol}] 2R foydaga yetdi! 70% yopilyapti...")
                success, msg = self.close_partial_position(ticket, 70)
                if success:
                    if signal == "BUY":
                        new_sl = entry_price + one_r
                    else:
                        new_sl = entry_price - one_r
                        
                    self.update_sl(ticket, new_sl)
                    self.state_manager.set_trade_info(ticket, {
                        "partial_closed": True,
                        "current_sl_level": 1
                    })
                    logger.info(f"[{pos.symbol}] 70% yopildi, SL +1R ga surildi.")
                continue

            # BREAKEVEN_FAST (1R ga yetganda riskni yo'q qilish)
            if profit_r >= 1.0 and not info.get("partial_closed") and info.get("current_sl_level", 0) < 0.5:
                trailing_mode = info.get("trailing_mode", "STEP")
                if trailing_mode == "BREAKEVEN_FAST":
                    new_sl = entry_price + (one_r * 0.1) if signal == "BUY" else entry_price - (one_r * 0.1)
                    if (signal == "BUY" and new_sl > pos.sl) or (signal == "SELL" and (pos.sl == 0 or new_sl < pos.sl)):
                        self.update_sl(ticket, new_sl)
                        self.state_manager.set_trade_info(ticket, {"current_sl_level": 0.5})
                        logger.info(f"[{pos.symbol}] BREAKEVEN_FAST: SL entry price ga surildi.")
                
            # Trailing logikasi (faqat 70% yopilgandan keyin qolgan 30% uchun)
            if info.get("partial_closed") and profit_r >= 2.0:
                trailing_mode = info.get("trailing_mode")
                if not trailing_mode:
                    try:
                        trailing_mode = trailing_decision_fn(pos.symbol)
                        if not trailing_mode or trailing_mode not in ["STEP", "ATR_TRAIL", "CLOSE_ALL", "BREAKEVEN_FAST", "STRUCTURE"]:
                            trailing_mode = "STEP"
                            
                        self.state_manager.set_trade_info(ticket, {"trailing_mode": trailing_mode})
                        logger.info(f"[{pos.symbol}] AI Trailing rejimini tanladi: {trailing_mode}")
                    except Exception as e:
                        logger.error(f"Trailing qarori olishda xato: {e}")
                        trailing_mode = "STEP"
                
                if trailing_mode == "CLOSE_ALL":
                    logger.info(f"[{pos.symbol}] AI bozor xavfli deb topdi, pozitsiya to'liq yopilmoqda.")
                    self.close_partial_position(ticket, 100)
                    self.state_manager.set_trade_info(ticket, {"status": "CLOSED"})
                    
                elif trailing_mode in ["STEP", "BREAKEVEN_FAST"]:
                    # STEP trailing — har bir yangi R da SL ni 1R ortga surish
                    expected_sl_level = int(profit_r) - 1
                    if expected_sl_level > info.get("current_sl_level", 0):
                        if signal == "BUY":
                            new_sl = entry_price + (expected_sl_level * one_r)
                        else:
                            new_sl = entry_price - (expected_sl_level * one_r)
                            
                        if (signal == "BUY" and new_sl > pos.sl) or (signal == "SELL" and (pos.sl == 0 or new_sl < pos.sl)):
                            self.update_sl(ticket, new_sl)
                            self.state_manager.set_trade_info(ticket, {"current_sl_level": expected_sl_level})
                            logger.info(f"[{pos.symbol}] STEP Trailing: SL +{expected_sl_level}R ga surildi.")
                
                elif trailing_mode == "ATR_TRAIL":
                    # ATR bazasida surish (narxdan 1.5R uzoqlikda ushlab borish)
                    if signal == "BUY":
                        new_sl = current_price - (one_r * 1.5)
                    else:
                        new_sl = current_price + (one_r * 1.5)
                        
                    # Faqatgina foyda tomon suramiz (orqaga qaytmaydi)
                    if (signal == "BUY" and new_sl > pos.sl) or (signal == "SELL" and (pos.sl == 0 or new_sl < pos.sl)):
                        self.update_sl(ticket, new_sl)
                        logger.info(f"[{pos.symbol}] ATR_TRAIL: SL surildi.")
                
                elif trailing_mode == "STRUCTURE":
                    # Kelajakda M5 tuzilishi asosida suriladi, hozircha STEP kabi ishlaydi
                    pass

    def place_pending_order(self, symbol: str, order_type_str: str, price: float, lot_size: float, stop_loss_pips: float, take_profit_pips: float, magic: int = 234000, comment: str = "News Straddle") -> Tuple[bool, str, Optional[dict]]:
        symbol_info = self.mt5.symbol_info(symbol)
        if symbol_info is None:
            return False, f"{symbol} topilmadi", None

        if not symbol_info.visible:
            if not self.mt5.symbol_select(symbol, True):
                return False, f"{symbol} tanlab bo'lmadi", None

        point = symbol_info.point
        pip_size = point * 10
        digits = symbol_info.digits

        stop_level_pips = symbol_info.trade_stops_level / 10.0
        if stop_loss_pips < stop_level_pips:
            stop_loss_pips = stop_level_pips
        if take_profit_pips < stop_level_pips:
            take_profit_pips = stop_level_pips

        if order_type_str == "BUY_STOP":
            order_type = self.mt5.ORDER_TYPE_BUY_STOP
            sl = round(price - stop_loss_pips * pip_size, digits)
            tp = round(price + take_profit_pips * pip_size, digits)
        elif order_type_str == "SELL_STOP":
            order_type = self.mt5.ORDER_TYPE_SELL_STOP
            sl = round(price + stop_loss_pips * pip_size, digits)
            tp = round(price - take_profit_pips * pip_size, digits)
        else:
            return False, "Noto'g'ri pending order turi", None

        request = {
            "action": self.mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": magic,
            "comment": comment,
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self._get_filling_mode(symbol),
        }

        result = self.mt5.order_send(request)

        if result is None:
            return False, f"Pending order yuborilmadi: {self.mt5.last_error()}", None

        if result.retcode != self.mt5.TRADE_RETCODE_DONE:
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

        self.state_manager.set_trade_info(result.order, {
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

    def delete_pending_order(self, ticket: int) -> Tuple[bool, str]:
        request = {
            "action": self.mt5.TRADE_ACTION_REMOVE,
            "order": ticket
        }
        result = self.mt5.order_send(request)
        if result is None or result.retcode != self.mt5.TRADE_RETCODE_DONE:
            return False, f"O'chirishda xatolik: {self.mt5.last_error()}"
        
        self.state_manager.set_trade_info(ticket, {"status": "DELETED"})
        return True, "O'chirildi"

    def manage_pending_orders(self):
        """
        Pending (Limit/Stop) orderlarni tekshirish va yaroqsiz bo'lsa o'chirish.
        1. Narx limit_entry ga bormasdan oldin stop_loss gacha yetib borsa, setup invalid bo'ladi.
        2. Order 24 soatdan oshib qolsa, eskirgan hisoblanib o'chiriladi.
        """
        orders = self.mt5.orders_get()
        if not orders:
            return

        import datetime
        now = datetime.datetime.now()

        for order in orders:
            ticket = order.ticket
            symbol = order.symbol
            order_type = order.type
            time_setup = order.time_setup
            sl = order.sl
            
            # Faqat limit orderlarni tekshiramiz
            if order_type not in [self.mt5.ORDER_TYPE_BUY_LIMIT, self.mt5.ORDER_TYPE_SELL_LIMIT]:
                continue
                
            tick = self.mt5.symbol_info_tick(symbol)
            if not tick:
                continue
                
            # Setup vaqti (24 soat = 86400 sek)
            setup_time_dt = datetime.datetime.fromtimestamp(time_setup)
            if (now - setup_time_dt).total_seconds() > 86400:
                logger.info(f"[{symbol}] Pending order #{ticket} eskirgan (24 soat). O'chirilmoqda...")
                self.delete_pending_order(ticket)
                continue
                
            # Invalidation tekshiruvi
            if sl > 0:
                if order_type == self.mt5.ORDER_TYPE_BUY_LIMIT:
                    # Agar narx buy limit olinmasdan SL ga tushib ketgan bo'lsa
                    if tick.ask <= sl:
                        logger.info(f"[{symbol}] Buy Limit #{ticket} uchun narx SL ni urib o'tdi (setup invalid). O'chirilmoqda...")
                        self.delete_pending_order(ticket)
                elif order_type == self.mt5.ORDER_TYPE_SELL_LIMIT:
                    # Agar narx sell limit olinmasdan SL dan oshib ketgan bo'lsa
                    if tick.bid >= sl:
                        logger.info(f"[{symbol}] Sell Limit #{ticket} uchun narx SL ni urib o'tdi (setup invalid). O'chirilmoqda...")
                        self.delete_pending_order(ticket)
