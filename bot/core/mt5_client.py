import logging
import MetaTrader5 as mt5
from typing import Optional, List, Dict, Any

class MT5Client:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(MT5Client, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config=None):
        if self._initialized:
            return
        self.config = config
        self._initialized = True
        self.logger = logging.getLogger(__name__)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _check_connection(self):
        ti = mt5.terminal_info()
        if ti and ti.connected:
            return
        self.logger.warning("MT5 disconnected, trying to reconnect...")
        import time
        for i in range(5):
            if self.connect():
                self.logger.info(f"MT5 reconnected (attempt {i+1})")
                return
            delay = min(30, 2 ** i)
            self.logger.warning(f"MT5 reconnect failed, retrying in {delay}s...")
            time.sleep(delay)
        self.logger.error("MT5 reconnect failed after 5 attempts")

    def connect(self) -> bool:
        try:
            if not mt5.initialize():
                self.logger.error(f"MT5 initialize failed: {mt5.last_error()}")
                return False
            if self.config and self.config.mt5_login and self.config.mt5_password and self.config.mt5_server:
                if not mt5.login(self.config.mt5_login, password=self.config.mt5_password, server=self.config.mt5_server):
                    self.logger.error(f"MT5 login failed: {mt5.last_error()}")
                    return False
            return True
        except Exception as e:
            self.logger.error(f"MT5 connect exception: {e}")
            return False


    def disconnect(self):
        mt5.shutdown()

    def _get_timeframe_const(self, timeframe_str: str) -> int:
        tf_map = {
            "M1": mt5.TIMEFRAME_M1,
            "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30,
            "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1,
            "W1": mt5.TIMEFRAME_W1,
            "MN1": mt5.TIMEFRAME_MN1,
        }
        return tf_map.get(timeframe_str.upper(), mt5.TIMEFRAME_H1)

    def get_rates(self, symbol: str, timeframe_str: str, count: int):
        self._check_connection()
        tf = self._get_timeframe_const(timeframe_str)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None:
            self.logger.error(f"Failed to get rates for {symbol}, error code: {mt5.last_error()}")
        return rates

    def get_account_info(self):
        self._check_connection()
        info = mt5.account_info()
        if info is None:
            self.logger.error(f"Failed to get account info, error code: {mt5.last_error()}")
        return info

    def get_symbol_info(self, symbol: str):
        self._check_connection()
        info = mt5.symbol_info(symbol)
        if info is None:
            self.logger.error(f"Failed to get symbol info for {symbol}, error code: {mt5.last_error()}")
        return info

    def get_tick(self, symbol: str):
        self._check_connection()
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            self.logger.error(f"Failed to get tick for {symbol}, error code: {mt5.last_error()}")
        return tick

    def get_positions(self, symbol: Optional[str] = None):
        self._check_connection()
        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()
            
        if positions is None:
            self.logger.error(f"Failed to get positions, error code: {mt5.last_error()}")
            return ()
        return positions

    def get_orders(self, symbol: Optional[str] = None):
        self._check_connection()
        if symbol:
            orders = mt5.orders_get(symbol=symbol)
        else:
            orders = mt5.orders_get()
            
        if orders is None:
            self.logger.error(f"Failed to get orders, error code: {mt5.last_error()}")
            return ()
        return orders

    def order_send(self, request: Dict[str, Any]):
        self._check_connection()
        result = mt5.order_send(request)
        if result is None:
            self.logger.error(f"order_send failed for request {request}, error code: {mt5.last_error()}")
            return None
            
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            self.logger.error(f"order_send failed: retcode={result.retcode}, comment={result.comment}")
            return None
            
        return result

    def get_tradeable_symbols(self) -> List[str]:
        """MT5 dan barcha savdo qilish mumkin bo'lgan (FULL ruxsatli) juftliklarni oladi."""
        self._check_connection()
        symbols = mt5.symbols_get()
        if symbols is None:
            self.logger.error(f"Failed to get symbols, error code: {mt5.last_error()}")
            return []
            
        tradeable = []
        for s in symbols:
            # Faqat savdo qilish to'liq ruxsat etilgan va ko'rinadigan juftliklarni olamiz
            if s.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL and s.visible:
                tradeable.append(s.name)
                
        return tradeable

    # === Alias methods for backward compatibility ===
    # OrderManager va boshqa modullar to'g'ridan-to'g'ri MT5 metodlarini chaqiradi
    def symbol_info(self, symbol: str):
        self._check_connection()
        return self.get_symbol_info(symbol)

    def symbol_info_tick(self, symbol: str):
        self._check_connection()
        return self.get_tick(symbol)

    def symbol_select(self, symbol: str, enable: bool = True) -> bool:
        self._check_connection()
        return mt5.symbol_select(symbol, enable)

    def positions_get(self, **kwargs):
        self._check_connection()
        positions = mt5.positions_get(**kwargs)
        if positions is None:
            self.logger.error(f"Failed to get positions, error code: {mt5.last_error()}")
            return ()
        return positions

    def orders_get(self, **kwargs):
        self._check_connection()
        orders = mt5.orders_get(**kwargs)
        if orders is None:
            self.logger.error(f"Failed to get orders, error code: {mt5.last_error()}")
            return ()
        return orders

    def last_error(self):
        return mt5.last_error()

    def __getattr__(self, name: str):
        """MT5 konstantalarini (TRADE_ACTION_DEAL, ORDER_TYPE_BUY, etc.) proxy qilish."""
        if hasattr(mt5, name):
            return getattr(mt5, name)
        raise AttributeError(f"'{type(self).__name__}' has no attribute '{name}'")
