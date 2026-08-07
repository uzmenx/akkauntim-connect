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
    
    PENDING_TTL_BY_TIMEFRAME = {
        "M1": 2 * 3600,       # 2 soat
        "M5": 6 * 3600,       # 6 soat
        "M15": 48 * 3600,     # 48 soat
        "H1": 10 * 24 * 3600, # 10 kun
        "H4": 30 * 24 * 3600  # 30 kun
    }

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

    def _is_near_market_close(self, symbol: str) -> bool:
        """
        Bozor yopilishiga 2 soat (yoki undan kam) qolganini tekshiradi.
        """
        tick = self.mt5.symbol_info_tick(symbol)
        if not tick:
            return False
            
        import datetime
        # tick.time broker server vaqti hisoblanadi (Epoch formatida)
        broker_time = datetime.datetime.fromtimestamp(tick.time, datetime.timezone.utc)
        
        # Forexda odatda broker soati bo'yicha 23:59 da rollover bo'ladi.
        # Demak broker soati bo'yicha 22:00 va 23:59 oralig'ida trade ochishni bloklaymiz.
        if broker_time.hour >= 22:
            return True
            
        return False

    def _is_in_blackout_window(self, tick_time: Optional[float] = None) -> Tuple[bool, str]:
        """
        Sessiyalar o'zgarishi, rollover hamda spred kengayishi (illiquid windows) atrofida 
        yangi order joylashtirishni taqiqlovchi Session-Blackout tekshiruvi.
        
        Default UTC oynalari:
        - 21:45 - 22:15 UTC (NY Close / Daily Rollover & Swap spike)
        - 23:55 - 00:15 UTC (Sydney Open / Date boundary reset)
        - 07:55 - 08:05 UTC (London Open volatility surge)
        """
        if not getattr(self.config, "session_blackout_enabled", True):
            return False, ""
            
        default_windows = [
            {"start": "21:45", "end": "22:15", "name": "NY_Close_Rollover"},
            {"start": "23:55", "end": "00:15", "name": "Sydney_Open_Reset"},
            {"start": "07:55", "end": "08:05", "name": "London_Open_Vol"}
        ]
        windows = getattr(self.config, "session_blackout_windows", default_windows)
        if not windows:
            return False, ""
            
        import datetime
        if tick_time and tick_time > 0:
            dt = datetime.datetime.fromtimestamp(tick_time, datetime.timezone.utc)
        else:
            dt = datetime.datetime.now(datetime.timezone.utc)
            
        current_min = dt.hour * 60 + dt.minute
        
        for window in windows:
            try:
                start_h, start_m = map(int, window["start"].split(":"))
                end_h, end_m = map(int, window["end"].split(":"))
                
                start_min = start_h * 60 + start_m
                end_min = end_h * 60 + end_m
                
                name = window.get("name", f"{window['start']}-{window['end']}")
                
                if start_min <= end_min:
                    if start_min <= current_min <= end_min:
                        return True, f"Session blackout active ({name}: {window['start']}-{window['end']} UTC)"
                else:
                    # Midnight crossing (e.g. 23:55 to 00:15)
                    if current_min >= start_min or current_min <= end_min:
                        return True, f"Session blackout active ({name}: {window['start']}-{window['end']} UTC)"
            except (ValueError, KeyError, AttributeError):
                continue
                
        return False, ""


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

    def _check_spread_ok(self, symbol: str, current_spread_points: int) -> Tuple[bool, str]:
        """
        Dinamik spread filtri: M15 dagi so'nggi 50 ta candle spreadining Median va MAD 
        (Median Absolute Deviation) qiymatini hisoblab, joriy spread anomal emasligini tekshiradi.
        """
        rates = self.mt5.copy_rates_from_pos(symbol, self.mt5.TIMEFRAME_M15, 1, 50)
        if rates is None or len(rates) == 0:
            return True, ""
            
        spreads = [r['spread'] for r in rates if r['spread'] > 0]
        if not spreads:
            return True, ""
            
        import statistics
        median_spread = statistics.median(spreads)
        
        abs_deviations = [abs(s - median_spread) for s in spreads]
        mad = statistics.median(abs_deviations)
        
        if mad == 0:
            mad = max(median_spread * 0.1, 1.0)
            
        max_multiplier = getattr(self.config, "max_spread_multiplier", 4.0)
        max_allowed_spread = median_spread + (max_multiplier * mad)
        
        if max_allowed_spread < median_spread * 1.5:
            max_allowed_spread = median_spread * 1.5
            
        if current_spread_points > max_allowed_spread:
            msg = f"Spread anomal: {current_spread_points} pt (Limit: {max_allowed_spread:.1f}, Median: {median_spread}, MAD: {mad:.1f})"
            return False, msg
            
        return True, ""

    def place_order(self, symbol: str, signal: str, lot_size: float, stop_loss_pips: float, take_profit_pips: float, entry_price: Optional[float] = None, take_profit_1_pips: Optional[float] = None, signal_timeframe: Optional[str] = None) -> Tuple[bool, str, Optional[dict]]:
        """
        Tasdiqlangan signal asosida MT5'ga order (Market yoki Pending) yuboradi.
        Agar `take_profit_1_pips` berilsa, hajm 70/30 ga bo'lib 2 ta alohida order joylashtiriladi (TP1 broker tomonida).
        """
        # --- Portfolio guardlari ---
        if self._in_cooldown(symbol):
            return False, f"[{symbol}] cooldown ({self.COOLDOWN_SECONDS}s) ichida", None
        if self._open_count(symbol) >= self.MAX_POSITIONS_PER_SYMBOL:
            return False, f"[{symbol}] {self.MAX_POSITIONS_PER_SYMBOL} pozitsiya limiti to'ldi", None
        if self._is_near_market_close(symbol):
            return False, f"[{symbol}] Bozor yopilishiga (rollover) 2 soatdan kam qolganligi sababli bitim rad etildi", None

        is_blackout, blackout_reason = self._is_in_blackout_window()
        if is_blackout:
            logger.warning(f"[{symbol}] Trade aborted due to Session Blackout: {blackout_reason}")
            return False, f"[{symbol}] {blackout_reason}", None

        symbol_info = self.mt5.symbol_info(symbol)
        if symbol_info is None:
            return False, f"{symbol} topilmadi", None

        if not symbol_info.visible:
            if not self.mt5.symbol_select(symbol, True):
                return False, f"{symbol} tanlab bo'lmadi", None


        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None:
            return False, "Narx ma'lumotini olib bo'lmadi", None

        is_blackout, blackout_reason = self._is_in_blackout_window(tick.time)
        if is_blackout:
            logger.warning(f"[{symbol}] Trade aborted due to Session Blackout (tick timestamp): {blackout_reason}")
            return False, f"[{symbol}] {blackout_reason}", None

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
        
        is_ok, msg = self._check_spread_ok(symbol, current_spread_points)
        if not is_ok:
            return False, msg, None
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
        elif signal in ("BUY_LIMIT", "SELL_LIMIT", "BUY_STOP", "SELL_STOP"):
            if entry_price is None:
                return False, f"Pending order ({signal}) uchun entry_price majburiy", None
            action = self.mt5.TRADE_ACTION_PENDING
            # Auto-flip LIMIT<->STOP entry_price joriy narxga nisbatan mos kelmasa.
            is_buy = "BUY" in signal
            current = tick.ask if is_buy else tick.bid
            wants_limit = "LIMIT" in signal
            price_below = entry_price < current
            # BUY_LIMIT quyida, BUY_STOP tepada; SELL_LIMIT tepada, SELL_STOP quyida.
            correct_limit = (is_buy and price_below) or ((not is_buy) and (not price_below))
            if wants_limit != correct_limit:
                new_signal = signal.replace("LIMIT", "STOP") if wants_limit else signal.replace("STOP", "LIMIT")
                logger.info(f"[{symbol}] pending auto-flip {signal} -> {new_signal} (entry={entry_price}, market={current})")
                signal = new_signal
            if signal == "BUY_LIMIT":
                order_type = self.mt5.ORDER_TYPE_BUY_LIMIT
            elif signal == "SELL_LIMIT":
                order_type = self.mt5.ORDER_TYPE_SELL_LIMIT
            elif signal == "BUY_STOP":
                order_type = self.mt5.ORDER_TYPE_BUY_STOP
            else:
                order_type = self.mt5.ORDER_TYPE_SELL_STOP
            price = entry_price
        else:
            return False, f"Noto'g'ri signal turi: {signal}", None


        # SL va TP ni hisoblash (digits yuqorida allaqachon o'rnatildi)
        if order_type in [self.mt5.ORDER_TYPE_BUY, self.mt5.ORDER_TYPE_BUY_LIMIT, self.mt5.ORDER_TYPE_BUY_STOP]:
            virtual_sl = round(price - stop_loss_pips * pip_size, digits)
            broker_sl = round(price - (stop_loss_pips * 2) * pip_size, digits) # Catastrophic SL
            tp = round(price + take_profit_pips * pip_size, digits)
            tp1 = round(price + take_profit_1_pips * pip_size, digits) if take_profit_1_pips else None
        else:  # SELL*
            virtual_sl = round(price + stop_loss_pips * pip_size, digits)
            broker_sl = round(price + (stop_loss_pips * 2) * pip_size, digits) # Catastrophic SL
            tp = round(price - take_profit_pips * pip_size, digits)
            tp1 = round(price - take_profit_1_pips * pip_size, digits) if take_profit_1_pips else None

        # TP1 broker-side: hajmni 70/30 ga bo'lib ikki alohida order yuboramiz.
        vol_step = getattr(symbol_info, "volume_step", 0.01) or 0.01
        vol_min = getattr(symbol_info, "volume_min", 0.01) or 0.01
        
        step_str = f"{vol_step:.8f}".rstrip('0')
        if '.' in step_str:
            vol_decimals = len(step_str.split('.')[1])
        else:
            vol_decimals = 2
        vol_decimals = max(2, vol_decimals)
        
        def _q(v: float) -> float:
            return max(vol_min, round(round(v / vol_step) * vol_step, vol_decimals))

        splits: list = []  # (volume, tp_price)
        if tp1 is not None:
            vol_tp1 = _q(lot_size * self.TP1_PORTION)
            vol_tp2 = _q(lot_size - vol_tp1)
            if vol_tp1 >= vol_min and vol_tp2 >= vol_min:
                splits.append((vol_tp1, tp1))
                splits.append((vol_tp2, tp))
        if not splits:
            splits.append((lot_size, tp))

        pending_ttl = None
        if action == self.mt5.TRADE_ACTION_PENDING:
            pending_ttl = int(time.time()) + self.PENDING_TTL_SECONDS

        tickets: list = []
        first_result = None
        for vol, tp_price in splits:
            request = {
                "action": action,
                "symbol": symbol,
                "volume": vol,
                "type": order_type,
                "price": price,
                "sl": broker_sl,
                "tp": tp_price,
                "deviation": self._symbol_deviation(symbol),
                "magic": self.magic_number,
                "comment": "AI forex bot",
                "type_filling": 2 if action == self.mt5.TRADE_ACTION_PENDING else self._get_filling_mode(symbol),
            }
            # Ko'p brokerlar ORDER_TIME_SPECIFIED ni qo'llab-quvvatlamaydi va 10030/10013 xato beradi.
            # Shuning uchun barcha pending orderlar uchun GTC ishlatamiz.
            request["type_time"] = self.mt5.ORDER_TIME_GTC

            if is_virtual is None:
                is_virtual = getattr(self.config, "shadow_mode", False)
            if is_virtual:
                import time
                class DummyResult:
                    def __init__(self, retcode, ticket):
                        self.retcode = retcode
                        self.ticket = ticket
                        self.deal = ticket
                        self.order = ticket
                
                # Shadow bazaga yozamiz
                import sqlite3
                import os
                try:
                    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'bot_learning.db')
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    cursor.execute('''CREATE TABLE IF NOT EXISTS shadow_live_trades (
                        ticket INTEGER PRIMARY KEY, symbol TEXT, type TEXT, volume REAL, price_open REAL, sl REAL, tp REAL, status TEXT
                    )''')
                    ticket_id = int(time.time()) + len(tickets) + int(vol * 100)
                    is_buy_trade = "BUY" in signal
                    cursor.execute("INSERT INTO shadow_live_trades (ticket, symbol, type, volume, price_open, sl, tp, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN')", 
                                   (ticket_id, symbol, "BUY" if is_buy_trade else "SELL", vol, price, virtual_sl, tp_price))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    logger.error(f"Shadow trade yozishda xato: {e}")
                
                result = DummyResult(self.mt5.TRADE_RETCODE_DONE, ticket_id)
                logger.info(f"[{symbol}] 👻 SHADOW MODE: Virtual {signal} order placed. Ticket: {ticket_id}")
            else:
                result = self.mt5.order_send(request)

            if result is None:
                return False, f"Order yuborilmadi: {self.mt5.last_error()}", None
            if result.retcode != self.mt5.TRADE_RETCODE_DONE:
                return False, f"Order rad etildi, kod: {result.retcode}, komment: {result.comment}", None
            tickets.append(result.order)
            if first_result is None:
                first_result = result

            one_r_dist = stop_loss_pips * pip_size
            
            pending_ttl = self.PENDING_TTL_BY_TIMEFRAME.get(signal_timeframe, 24*3600) if signal_timeframe else 24*3600
            
            self.state_manager.set_trade_info(result.order, {
                "status": "OPEN",
                "1r_dist": one_r_dist,
                "entry_price": price,
                "signal": signal,
                "partial_closed": tp_price == tp1,  # TP1 leg — kichik hajmli qism
                "trailing_mode": None,
                "current_sl_level": 0,
                "virtual_sl": virtual_sl,
                "signal_timeframe": signal_timeframe,
                "pending_expires_at": time.time() + pending_ttl
            })

        order_info = {
            "ticket": first_result.order,
            "tickets": tickets,
            "symbol": symbol,
            "signal": signal,
            "volume": lot_size,
            "price": price,
            "sl": virtual_sl,
            "tp": tp,
            "tp1": tp1,
        }
        return True, "Order muvaffaqiyatli ochildi", order_info


    def close_partial_position(self, ticket: int, percent: float) -> Tuple[bool, str]:
        positions = self.mt5.positions_get(ticket=ticket)
        if not positions:
            return False, "Position topilmadi"
        position = positions[0]
        
        symbol_info = self.mt5.symbol_info(position.symbol)
        vol_step = getattr(symbol_info, "volume_step", 0.01) or 0.01
        step_str = f"{vol_step:.8f}".rstrip('0')
        if '.' in step_str:
            vol_decimals = len(step_str.split('.')[1])
        else:
            vol_decimals = 2
        vol_decimals = max(2, vol_decimals)
        
        close_volume = round(round((position.volume * (percent / 100.0)) / vol_step) * vol_step, vol_decimals)
        vol_min = getattr(symbol_info, "volume_min", 0.01) or 0.01
        if close_volume < vol_min:
            return False, f"Hajm kichik (minimum {vol_min})"
            
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
            # SL ni brokerdan yashirganimiz uchun (Virtual SL), SL o'zgartirish broker tomonida amalga oshmaydi.
            # Biz Virtual SL ni o'zimizning state_manager da yangilashimiz kerak.
            pass
            
        self.state_manager.set_trade_info(ticket, {"virtual_sl": new_sl})
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

    def place_pending_order(self, symbol: str, order_type_str: str, price: float, lot_size: float, stop_loss_pips: float, take_profit_pips: float, magic: int = 234000, comment: str = "Pending Order", expiration_minutes: Optional[int] = None, signal_timeframe: Optional[str] = None) -> Tuple[bool, str, Optional[dict]]:
        # --- Portfolio guardlari ---
        if self._in_cooldown(symbol):
            return False, f"[{symbol}] cooldown ({self.COOLDOWN_SECONDS}s) ichida", None
        if self._open_count(symbol) >= self.MAX_POSITIONS_PER_SYMBOL:
            return False, f"[{symbol}] {self.MAX_POSITIONS_PER_SYMBOL} pozitsiya limiti to'ldi", None
        if self._is_near_market_close(symbol):
            return False, f"[{symbol}] Bozor yopilishiga (rollover) 2 soatdan kam qolganligi sababli pending order rad etildi", None

        is_blackout, blackout_reason = self._is_in_blackout_window()
        if is_blackout:
            logger.warning(f"[{symbol}] Pending trade aborted due to Session Blackout: {blackout_reason}")
            return False, f"[{symbol}] {blackout_reason}", None

        symbol_info = self.mt5.symbol_info(symbol)
        if symbol_info is None:
            return False, f"{symbol} topilmadi", None

        if not symbol_info.visible:
            if not self.mt5.symbol_select(symbol, True):
                return False, f"{symbol} tanlab bo'lmadi", None
                
        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None:
            return False, "Narx ma'lumotini olib bo'lmadi", None

        is_blackout, blackout_reason = self._is_in_blackout_window(tick.time)
        if is_blackout:
            logger.warning(f"[{symbol}] Pending trade aborted due to Session Blackout (tick timestamp): {blackout_reason}")
            return False, f"[{symbol}] {blackout_reason}", None

        point = symbol_info.point
        digits = symbol_info.digits
        if digits in (3, 5):
            pip_size = point * 10
        elif digits == 2:
            pip_size = point * 10
        else:
            pip_size = point

        pip_mul = pip_size / point if point > 0 else 10

        # --- SPREAD FILTER ---
        current_spread_points = round((tick.ask - tick.bid) / point)
        
        is_ok, msg = self._check_spread_ok(symbol, current_spread_points)
        if not is_ok:
            return False, msg, None
        # ---------------------
        stop_level_pips = symbol_info.trade_stops_level / pip_mul if pip_mul > 0 else 0
        if stop_loss_pips < stop_level_pips:
            stop_loss_pips = stop_level_pips
        if take_profit_pips < stop_level_pips:
            take_profit_pips = stop_level_pips

        # Auto-flip LIMIT<->STOP based on CURRENT market price (prevents 10015 Invalid Price)
        is_buy = "BUY" in order_type_str
        current_market_price = tick.ask if is_buy else tick.bid
        wants_limit = "LIMIT" in order_type_str
        price_below = price < current_market_price
        correct_limit = (is_buy and price_below) or (not is_buy and not price_below)
        
        if wants_limit != correct_limit:
            new_type = order_type_str.replace("LIMIT", "STOP") if wants_limit else order_type_str.replace("STOP", "LIMIT")
            logger.info(f"[{symbol}] pending_order auto-flip {order_type_str} -> {new_type} (entry={price}, market={current_market_price})")
            order_type_str = new_type

        if order_type_str == "BUY_STOP":
            order_type = self.mt5.ORDER_TYPE_BUY_STOP
            virtual_sl = round(price - stop_loss_pips * pip_size, digits)
            tp = round(price + take_profit_pips * pip_size, digits)
        elif order_type_str == "SELL_STOP":
            order_type = self.mt5.ORDER_TYPE_SELL_STOP
            virtual_sl = round(price + stop_loss_pips * pip_size, digits)
            tp = round(price - take_profit_pips * pip_size, digits)
        elif order_type_str == "BUY_LIMIT":
            order_type = self.mt5.ORDER_TYPE_BUY_LIMIT
            virtual_sl = round(price - stop_loss_pips * pip_size, digits)
            tp = round(price + take_profit_pips * pip_size, digits)
        elif order_type_str == "SELL_LIMIT":
            order_type = self.mt5.ORDER_TYPE_SELL_LIMIT
            virtual_sl = round(price + stop_loss_pips * pip_size, digits)
            tp = round(price - take_profit_pips * pip_size, digits)
        else:
            return False, f"Noto'g'ri pending order turi: {order_type_str}", None
            
        if order_type in [self.mt5.ORDER_TYPE_BUY, self.mt5.ORDER_TYPE_BUY_LIMIT, self.mt5.ORDER_TYPE_BUY_STOP]:
            broker_sl = round(price - (stop_loss_pips * 2) * pip_size, digits)
        else:
            broker_sl = round(price + (stop_loss_pips * 2) * pip_size, digits)

        request = {
            "action": self.mt5.TRADE_ACTION_PENDING,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "sl": broker_sl,
            "tp": tp,
            "deviation": self._symbol_deviation(symbol),
            "magic": magic,
            "comment": comment,
            "type_filling": self._get_filling_mode(symbol),
        }
        
        if expiration_minutes:
            import time
            request["type_time"] = self.mt5.ORDER_TIME_SPECIFIED
            request["expiration"] = int(time.time() + (expiration_minutes * 60))
        else:
            request["type_time"] = self.mt5.ORDER_TIME_GTC

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
            "sl": virtual_sl,
            "tp": tp,
            "1r_dist": stop_loss_pips * pip_size
        }

        pending_ttl = self.PENDING_TTL_BY_TIMEFRAME.get(signal_timeframe, 24*3600) if signal_timeframe else 24*3600
        
        self.state_manager.set_trade_info(result.order, {
            "status": "PENDING", 
            "1r_dist": stop_loss_pips * pip_size,
            "entry_price": price,
            "signal": "BUY" if "BUY" in order_type_str else "SELL",
            "partial_closed": False,
            "trailing_mode": None,
            "current_sl_level": 0,
            "is_straddle": True,
            "virtual_sl": virtual_sl,
            "signal_timeframe": signal_timeframe,
            "pending_expires_at": time.time() + pending_ttl
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
        2. Order o'ziga belgilangan TF-based TTL dan oshib qolsa, eskirgan hisoblanib o'chiriladi.
        """
        orders = self.mt5.orders_get()
        if not orders:
            return

        import time
        now_ts = time.time()

        for order in orders:
            ticket = order.ticket
            symbol = order.symbol
            order_type = order.type
            sl = order.sl
            
            # Faqat limit/stop orderlarni tekshiramiz
            if order_type not in [self.mt5.ORDER_TYPE_BUY_LIMIT, self.mt5.ORDER_TYPE_SELL_LIMIT, self.mt5.ORDER_TYPE_BUY_STOP, self.mt5.ORDER_TYPE_SELL_STOP]:
                continue
                
            tick = self.mt5.symbol_info_tick(symbol)
            if not tick:
                continue
                
            trade_info = self.state_manager.get_trade_info(ticket)
            expires_at = trade_info.get("pending_expires_at") if trade_info else None
            
            # Agar expires_at topilmasa, fallback 24 soat
            if not expires_at:
                expires_at = order.time_setup + 86400

            if now_ts > expires_at:
                tf_label = trade_info.get("signal_timeframe", "Noma'lum") if trade_info else "Noma'lum"
                logger.info(f"[{symbol}] Pending order #{ticket} (TF: {tf_label}) eskirgan (TTL tugadi). O'chirilmoqda...")
                self.delete_pending_order(ticket)
                continue
                
            # Invalidation tekshiruvi (Virtual SL or Broker SL)
            virtual_sl = trade_info.get("virtual_sl") if trade_info else 0
            check_sl = sl if sl > 0 else virtual_sl
            
            if check_sl > 0:
                if order_type == self.mt5.ORDER_TYPE_BUY_LIMIT:
                    if tick.ask <= check_sl:
                        logger.info(f"[{symbol}] Buy Limit #{ticket} uchun narx SL ni urib o'tdi (setup invalid). O'chirilmoqda...")
                        self.delete_pending_order(ticket)
                elif order_type == self.mt5.ORDER_TYPE_SELL_LIMIT:
                    if tick.bid >= check_sl:
                        logger.info(f"[{symbol}] Sell Limit #{ticket} uchun narx SL ni urib o'tdi (setup invalid). O'chirilmoqda...")
                        self.delete_pending_order(ticket)
                elif order_type == self.mt5.ORDER_TYPE_BUY_STOP:
                    if tick.bid <= check_sl:
                        logger.info(f"[{symbol}] Buy Stop #{ticket} uchun narx SL ni urib o'tdi (setup invalid). O'chirilmoqda...")
                        self.delete_pending_order(ticket)
                elif order_type == self.mt5.ORDER_TYPE_SELL_STOP:
                    if tick.ask >= check_sl:
                        logger.info(f"[{symbol}] Sell Stop #{ticket} uchun narx SL ni urib o'tdi (setup invalid). O'chirilmoqda...")
                        self.delete_pending_order(ticket)
                
    def manage_virtual_shadow_trades(self) -> list:
        """
        SHADOW MODE da ochilgan virtual pozitsiyalarni (SL/TP) boshqarish.
        """
        import sqlite3
        import os
        closed_shadow_trades = []
        try:
            db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'bot_learning.db')
            if not os.path.exists(db_path):
                return closed_shadow_trades
                
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check table exists
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shadow_live_trades'")
            if not cursor.fetchone():
                conn.close()
                return closed_shadow_trades
                
            cursor.execute("SELECT ticket, symbol, type, volume, price_open, sl, tp FROM shadow_live_trades WHERE status='OPEN'")
            open_trades = cursor.fetchall()
            
            for trade in open_trades:
                ticket, symbol, trade_type, volume, price_open, sl, tp = trade
                tick = self.mt5.symbol_info_tick(symbol)
                if not tick:
                    continue
                    
                current_price = tick.ask if trade_type == "SELL" else tick.bid
                
                closed = False
                profit = 0.0
                reason = ""
                
                if trade_type == "BUY":
                    if sl and current_price <= sl:
                        closed, reason = True, "SL"
                        profit = (sl - price_open) * volume * 1000 # Dummy calc
                    elif tp and current_price >= tp:
                        closed, reason = True, "TP"
                        profit = (tp - price_open) * volume * 1000
                elif trade_type == "SELL":
                    if sl and current_price >= sl:
                        closed, reason = True, "SL"
                        profit = (price_open - sl) * volume * 1000
                    elif tp and current_price <= tp:
                        closed, reason = True, "TP"
                        profit = (price_open - tp) * volume * 1000
                        
                if closed:
                    cursor.execute("UPDATE shadow_live_trades SET status='CLOSED' WHERE ticket=?", (ticket,))
                    logger.info(f"[{symbol}] 👻 SHADOW MODE: Trade {ticket} closed by {reason}. P/L: {profit:.2f}")
                    
                    # AI xotirasiga o'tkazish (analiz u-n)
                    try:
                        cursor.execute('''CREATE TABLE IF NOT EXISTS shadow_trade_history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            symbol TEXT,
                            profit REAL,
                            close_reason TEXT,
                            timestamp TEXT
                        )''')
                        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sth_symbol ON shadow_trade_history(symbol)')
                        cursor.execute('CREATE INDEX IF NOT EXISTS idx_sth_symbol_profit ON shadow_trade_history(symbol, profit)')
                        import datetime
                        cursor.execute("INSERT INTO shadow_trade_history (symbol, profit, close_reason, timestamp) VALUES (?, ?, ?, ?)", 
                                       (symbol, profit, reason, datetime.datetime.now().isoformat()))
                    except Exception as e:
                        logger.error(f"Shadow history saqlashda xato: {e}")
                        
                    closed_shadow_trades.append({
                        "ticket": ticket,
                        "symbol": symbol,
                        "profit": profit,
                        "reason": reason
                    })
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"manage_virtual_shadow_trades error: {e}")
            
        return closed_shadow_trades

    def close_position(self, position: Any, comment: str = "AI Close") -> bool:
        symbol = position.symbol
        tick = self.mt5.symbol_info_tick(symbol)
        if not tick:
            return False
            
        if position.type == self.mt5.ORDER_TYPE_BUY:
            order_type = self.mt5.ORDER_TYPE_SELL
            price = tick.bid
        else:
            order_type = self.mt5.ORDER_TYPE_BUY
            price = tick.ask
            
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": position.volume,
            "type": order_type,
            "position": position.ticket,
            "price": price,
            "deviation": 20,
            "magic": self.magic_number,
            "comment": comment,
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self._get_filling_mode(symbol),
        }
        
        result = self.mt5.order_send(request)
        if result is None or result.retcode != self.mt5.TRADE_RETCODE_DONE:
            logger.error(f"Pozitsiyani yopishda xato: {self.mt5.last_error()}")
            return False
            
        self.record_closed(symbol)
        return True

    def manage_virtual_sl(self):
        """
        Virtual Stop Loss ni doimiy tekshirish va spred filtri yordamida himoyalanish.
        Agar narx Virtual SL ga yetgan bo'lsa va joriy spred me'yordan oshmagan bo'lsa, bitim to'liq yopiladi.
        """
        positions = self.mt5.positions_get()
        if not positions:
            return

        for pos in positions:
            if pos.magic != self.magic_number:
                continue

            ticket = pos.ticket
            info = self.state_manager.get_trade_info(ticket)
            if not info:
                continue
                
            signal = info.get("signal")
            virtual_sl = info.get("virtual_sl")
            
            if not virtual_sl or virtual_sl == 0:
                continue

            symbol = pos.symbol
            tick = self.mt5.symbol_info_tick(symbol)
            if not tick:
                continue
                
            symbol_info = self.mt5.symbol_info(symbol)
            if not symbol_info:
                continue
                
            # Spred filtri
            point = symbol_info.point
            current_spread_points = round((tick.ask - tick.bid) / point) if point > 0 else 0
            
            # Dinamik spread tekshiruvi
            is_spread_ok, _ = self._check_spread_ok(symbol, current_spread_points)
            is_spread_high = not is_spread_ok

            # Narx SL ga yetdimi?
            sl_hit = False
            disaster_hit = False
            close_price = 0.0
            order_type = None
            
            # Disaster masofasi (masalan, joriy spredning o'rtachasidan 3 baravar katta harakat bo'lsa yoki 20 pip = 200 point)
            # Default qilib 300 point (30 pip) beramiz, narx shu darajada SL dan o'tib ketsa spredga qaramay yopadi.
            disaster_threshold_points = 300 
            
            if signal == "BUY":
                if tick.bid <= virtual_sl:
                    sl_hit = True
                    if tick.bid <= (virtual_sl - disaster_threshold_points * point):
                        disaster_hit = True
                close_price = tick.bid
                order_type = self.mt5.ORDER_TYPE_SELL
            else: # SELL
                if tick.ask >= virtual_sl:
                    sl_hit = True
                    if tick.ask >= (virtual_sl + disaster_threshold_points * point):
                        disaster_hit = True
                close_price = tick.ask
                order_type = self.mt5.ORDER_TYPE_BUY

            if sl_hit:
                if is_spread_high and not disaster_hit:
                    logger.warning(f"[{symbol}] Virtual SL ga yetdi, lekin Spread yopish uchun juda katta ({current_spread_points} pt). Yopilmaydi, kutilmoqda...")
                else:
                    if disaster_hit:
                        logger.critical(f"[{symbol}] DISASTER HIT! Narx SL dan juda uzoqlashib ketdi. Spredga qaramay majburiy yopilmoqda!")
                    else:
                        logger.info(f"[{symbol}] Virtual SL urildi (Narx: {close_price}, V-SL: {virtual_sl}). Bitim yopilmoqda...")
                    
                    request = {
                        "action": self.mt5.TRADE_ACTION_DEAL,
                        "symbol": symbol,
                        "volume": pos.volume,
                        "type": order_type,
                        "position": ticket,
                        "price": close_price,
                        "deviation": 20,
                        "magic": self.magic_number,
                        "comment": "Virtual SL Closed",
                        "type_time": self.mt5.ORDER_TIME_GTC,
                        "type_filling": 2 if action == self.mt5.TRADE_ACTION_PENDING else self._get_filling_mode(symbol),
                    }
                    result = self.mt5.order_send(request)
                    if result is None or result.retcode != self.mt5.TRADE_RETCODE_DONE:
                        error_msg = self.mt5.last_error() if hasattr(self.mt5, 'last_error') else "Unknown"
                        logger.error(f"[{symbol}] Virtual SL yopishda xatolik: {error_msg}")
                    else:
                        self.state_manager.set_trade_info(ticket, {"status": "CLOSED_VIRTUAL_SL"})
                        logger.info(f"[{symbol}] Bitim muvaffaqiyatli yopildi.")
