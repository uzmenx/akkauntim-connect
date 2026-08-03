import re

with open('bot/core/mt5_client.py', 'r', encoding='utf-8') as f:
    content = f.read()

header_to_add = """import threading
from functools import wraps

def mt5_sync(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with self.lock:
            return func(self, *args, **kwargs)
    return wrapper
"""

content = content.replace("import MetaTrader5 as mt5", header_to_add + "\nimport MetaTrader5 as mt5")

init_to_replace = """    def __init__(self, config=None):
        if self._initialized:
            return
        self.config = config
        self._initialized = True
        self.logger = logging.getLogger(__name__)"""

init_replacement = """    def __init__(self, config=None):
        if self._initialized:
            return
        self.config = config
        self._initialized = True
        self.logger = logging.getLogger(__name__)
        if not hasattr(self.__class__, 'lock'):
            self.__class__.lock = threading.RLock()"""

content = content.replace(init_to_replace, init_replacement)

methods = [
    "connect", "disconnect", "_check_connection", "get_rates", "get_account_info", 
    "get_symbol_info", "get_tick", "get_positions", "get_orders", "order_send",
    "get_tradeable_symbols", "get_crypto_symbols", "resolve_symbols", 
    "get_grouped_symbols", "symbol_info", "symbol_info_tick", "symbol_select",
    "positions_get", "orders_get"
]

for method in methods:
    pattern = r'(    def ' + method + r'\()'
    content = re.sub(pattern, r'    @mt5_sync\n\1', content)

with open('bot/core/mt5_client.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("mt5_client.py patched.")
