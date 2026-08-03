import logging
import threading
from functools import wraps

def mt5_sync(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.lock:
            return func(self, *args, **kwargs)
    return wrapper

import MetaTrader5 as mt5
import time
from typing import Optional, List, Dict, Any, Tuple

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
        self._rates_cache: Dict[str, Tuple[float, Any]] = {}
        self._rates_cache_ttl: float = 3.0
        if not hasattr(self.__class__, 'lock'):
            self.__class__.lock = threading.RLock()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @mt5_sync
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

    @mt5_sync
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


    @mt5_sync
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

    @mt5_sync
    def clear_rates_cache(self):
        """MT5 rates keshini tozalash."""
        self._rates_cache.clear()

    @mt5_sync
    def set_rates_cache_ttl(self, ttl_seconds: float):
        """Kesh umrini (seconds) belgilash."""
        self._rates_cache_ttl = max(0.0, float(ttl_seconds))

    @mt5_sync
    def get_rates(self, symbol: str, timeframe_str: str, count: int, use_cache: bool = True):
        self._check_connection()
        
        now = time.time()
        cache_key = f"{symbol}_{timeframe_str.upper()}"

        # Periodic eviction of expired rates cache entries to prevent memory growth
        if use_cache and len(self._rates_cache) > 20:
            expired_keys = [k for k, (ts, _) in self._rates_cache.items() if now - ts > max(10.0, self._rates_cache_ttl * 2)]
            for k in expired_keys:
                del self._rates_cache[k]
        
        if use_cache and cache_key in self._rates_cache:
            cached_time, cached_rates = self._rates_cache[cache_key]
            if (now - cached_time <= self._rates_cache_ttl) and (len(cached_rates) >= count):
                return cached_rates[-count:].copy()

        tf = self._get_timeframe_const(timeframe_str)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None:
            self.logger.error(f"Failed to get rates for {symbol}, error code: {mt5.last_error()}")
            return rates
            
        if use_cache and rates is not None and len(rates) > 0:
            self._rates_cache[cache_key] = (now, rates.copy())
            
        return rates

    @mt5_sync
    def get_account_info(self):
        self._check_connection()
        info = mt5.account_info()
        if info is None:
            self.logger.error(f"Failed to get account info, error code: {mt5.last_error()}")
        return info

    @mt5_sync
    def get_symbol_info(self, symbol: str):
        self._check_connection()
        info = mt5.symbol_info(symbol)
        if info is None:
            if mt5.symbol_select(symbol, True):
                info = mt5.symbol_info(symbol)
        if info is None:
            self.logger.error(f"Failed to get symbol info for {symbol}, error code: {mt5.last_error()}")
        return info

    @mt5_sync
    def get_tick(self, symbol: str):
        self._check_connection()
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            self.logger.error(f"Failed to get tick for {symbol}, error code: {mt5.last_error()}")
        return tick

    @mt5_sync
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

    @mt5_sync
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

    @mt5_sync
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

    @mt5_sync
    def get_tradeable_symbols(self) -> List[str]:
        """MT5 dan barcha savdo qilish mumkin bo'lgan juftliklarni oladi."""
        self._check_connection()
        symbols = mt5.symbols_get()
        if symbols is None:
            self.logger.error(f"Failed to get symbols, error code: {mt5.last_error()}")
            return []
            
        tradeable = []
        for s in symbols:
            # Faqat savdo taqiqlanmagan juftliklarni olamiz
            if s.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED:
                tradeable.append(s.name)
                
        return tradeable

    @mt5_sync
    def get_crypto_symbols(self) -> List[str]:
        """MT5 dan faqat Kriptovalyuta juftliklarini oladi (path yoki nom orqali)."""
        self._check_connection()
        symbols = mt5.symbols_get()
        if symbols is None:
            self.logger.error(f"Failed to get symbols for crypto, error code: {mt5.last_error()}")
            return []
            
        crypto = []
        for s in symbols:
            if s.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED:
                nm = s.name.lower()
                pt = s.path.lower()
                if "crypto" in pt or "btc" in nm or "eth" in nm or "sol" in nm or "xrp" in nm or "bnb" in nm:
                    crypto.append(s.name)
        return crypto

    @mt5_sync
    def resolve_symbols(self, requested_symbols: List[str]) -> List[str]:
        """Requested simvollarni MT5 dagi haqiqiy ismlari (case, suffix, format) bilan taqqoslab qaytaradi va select qiladi."""
        self._check_connection()
        symbols = mt5.symbols_get()
        if symbols is None:
            return requested_symbols
            
        def normalize(name: str) -> str:
            return name.lower().replace("/", "").replace("_", "").replace("-", "").replace(".", "").replace(" ", "")

        resolved = []
        normalized_requested = [normalize(s) for s in requested_symbols]
        
        for req_raw, req_norm in zip(requested_symbols, normalized_requested):
            found_symbol = None
            # 1. Exact match (normalized)
            for s in symbols:
                if s.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
                    continue
                s_name = s.name
                if normalize(s_name) == req_norm:
                    found_symbol = s_name
                    break
                    
            # 2. Suffix / prefix match (masalan, BTCUSD brokerda BTCUSD.m bo'lsa)
            if not found_symbol:
                for s in symbols:
                    if s.trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
                        continue
                    s_name = s.name
                    s_name_norm = normalize(s_name)
                    if s_name_norm.startswith(req_norm) or req_norm.startswith(s_name_norm):
                        found_symbol = s_name
                        break
                        
            if found_symbol:
                if not mt5.symbol_select(found_symbol, True):
                    self.logger.warning(f"Failed to select resolved symbol {found_symbol}")
                resolved.append(found_symbol)
            else:
                resolved.append(req_raw)
                        
        return resolved

    @mt5_sync
    def get_grouped_symbols(self) -> Dict[str, List[str]]:
        """MT5 dan barcha ruxsat etilgan juftliklarni kategoriyalar bo'yicha guruhlab oladi."""
        self._check_connection()
        symbols = mt5.symbols_get()
        if symbols is None:
            self.logger.error(f"Failed to get symbols for grouping, error code: {mt5.last_error()}")
            return {}
            
        grouped = {}
        for s in symbols:
            if s.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED:
                parts = s.path.split('\\')
                if not parts:
                    continue
                category = parts[0]
                if len(parts) == 1:
                    category = "Boshqalar"
                    
                if category not in grouped:
                    grouped[category] = []
                grouped[category].append(s.name)
                
        return grouped

    # === Alias methods for backward compatibility ===
    # OrderManager va boshqa modullar to'g'ridan-to'g'ri MT5 metodlarini chaqiradi
    @mt5_sync
    def symbol_info(self, symbol: str):
        self._check_connection()
        return self.get_symbol_info(symbol)

    @mt5_sync
    def symbol_info_tick(self, symbol: str):
        self._check_connection()
        return self.get_tick(symbol)

    @mt5_sync
    def symbol_select(self, symbol: str, enable: bool = True) -> bool:
        self._check_connection()
        return mt5.symbol_select(symbol, enable)

    @mt5_sync
    def positions_get(self, **kwargs):
        self._check_connection()
        positions = mt5.positions_get(**kwargs)
        if positions is None:
            self.logger.error(f"Failed to get positions, error code: {mt5.last_error()}")
            return ()
        return positions

    @mt5_sync
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
