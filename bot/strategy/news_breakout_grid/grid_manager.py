import time
import logging

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from .pause_detector import PauseDetector
from .risk_guard import GridRiskGuard

logger = logging.getLogger(__name__)

class NewsBreakoutGridManager:
    def __init__(self, config, risk_guard: GridRiskGuard):
        self.config = config
        self.risk_guard = risk_guard
        # High volatility threshold and pause threshold should ideally be based on ATR or symbol properties.
        # We use hardcoded defaults that should be tuned per symbol.
        self.pause_detector = PauseDetector(
            pause_threshold_sec=2.0, 
            high_vol_threshold=2.0, 
            pause_vol_threshold=0.5
        )
        
        self.is_active = False
        self.grid_placed = False
        self.grid_start_time = 0
        self.tickets = []  # Stores all tickets (pending and open) for the current grid
        self.symbol = ""
        self.magic_number = self.config.magic_number + 999 # Unique magic for grid
        
    def activate(self, symbol: str):
        """Called when a high-impact news event is detected/active."""
        if not self.risk_guard.can_trade():
            return
        self.is_active = True
        self.symbol = symbol
        self.pause_detector.reset()
        logger.info(f"NewsBreakoutGridManager activated for {symbol}.")
        
    def deactivate(self):
        self.is_active = False
        self._close_all_grid_orders()
        logger.info("NewsBreakoutGridManager deactivated.")

    def tick(self, current_price: float, ask: float, bid: float, point: float):
        """Called on every tick for the whitelisted symbol."""
        if not self.is_active:
            return
            
        if not self.risk_guard.can_trade():
            self.deactivate()
            return
            
        if self.grid_placed:
            self._manage_grid(ask, bid)
        else:
            # We haven't placed a grid, look for a pause
            is_pause = self.pause_detector.update(current_price)
            if is_pause:
                self._place_grid(ask, bid, point)
                
    def _place_grid(self, ask: float, bid: float, point: float):
        logger.info(f"Placing grid for {self.symbol}...")
        self.risk_guard.record_attempt()
        self.tickets.clear()
        
        order_count = self.config.news_breakout_grid_order_count
        step_points = self.config.news_breakout_grid_step_points
        lot_size = self.config.news_breakout_grid_lot_size
        
        # --- DYNAMIC SCALING ---
        if getattr(self.config, "news_breakout_grid_dynamic_scaling", False) and mt5:
            acc_info = mt5.account_info()
            if acc_info:
                balance = acc_info.balance
                base_balance = getattr(self.config, "news_breakout_grid_base_balance", 100.0)
                
                # 1. Scale lot size linearly with balance growth
                # Example: balance = 200, base = 100 -> multiplier = 2.0 -> lot = 0.02
                if balance > base_balance:
                    multiplier = int(balance / base_balance)
                    lot_size = self.config.news_breakout_grid_lot_size * multiplier
                    # Ensure lot size respects broker step
                    sym_info = mt5.symbol_info(self.symbol)
                    if sym_info:
                        lot_step = sym_info.volume_step
                        lot_size = round(lot_size / lot_step) * lot_step
                        
                # 2. Adjust order count if balance is too small to open all orders
                # Estimate margin per order for the calculated lot size
                sym_info = mt5.symbol_info(self.symbol)
                if sym_info:
                    margin_per_order = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, self.symbol, lot_size, ask)
                    if margin_per_order and margin_per_order > 0:
                        max_orders_possible = int((balance * 0.9) / margin_per_order) # Use 90% of balance to be safe
                        # We need 'order_count' buys and 'order_count' sells, so total 2 * order_count
                        if max_orders_possible < (order_count * 2):
                            adjusted_count = max(1, max_orders_possible // 2)
                            logger.warning(f"Balance too small for {order_count} orders. Adjusting to {adjusted_count} orders.")
                            order_count = adjusted_count
                            
        logger.info(f"Grid Params: Orders={order_count} per side, Lot={lot_size}, Step={step_points} pts")
        
        # BUY STOPS
        for i in range(1, order_count + 1):
            price = ask + (i * step_points * point)
            ticket = self._send_order(mt5.ORDER_TYPE_BUY_STOP if mt5 else 4, price, lot_size)
            if ticket: self.tickets.append(ticket)
            
        # SELL STOPS
        for i in range(1, order_count + 1):
            price = bid - (i * step_points * point)
            ticket = self._send_order(mt5.ORDER_TYPE_SELL_STOP if mt5 else 5, price, lot_size)
            if ticket: self.tickets.append(ticket)
            
        self.grid_placed = True
        self.grid_start_time = time.time()
        self.pause_detector.reset()
        logger.info(f"Grid placed. Total tickets: {len(self.tickets)}")
        
    def _manage_grid(self, ask: float, bid: float):
        # 1. Check hard timeout
        if time.time() - self.grid_start_time > self.config.news_breakout_grid_hard_timeout_sec:
            logger.warning("Grid hard timeout reached. Closing all grid orders.")
            self._close_all_grid_orders()
            return

        # 2. Check PnL condition
        buy_profit = 0.0
        sell_profit = 0.0
        
        if mt5:
            for ticket in self.tickets:
                pos = mt5.positions_get(ticket=ticket)
                if pos and len(pos) > 0:
                    pnl = pos[0].profit
                    if pos[0].type == mt5.ORDER_TYPE_BUY:
                        buy_profit += pnl
                    elif pos[0].type == mt5.ORDER_TYPE_SELL:
                        sell_profit += pnl
        
        total_pnl = buy_profit + sell_profit
        closed = False
        margin = 0.1 # 10%
        
        # Ensure we have some profit to cover spread/commissions
        min_profit_threshold = 0.5 
        
        if buy_profit > 0 and sell_profit < 0:
            if buy_profit > abs(sell_profit) * (1 + margin) and total_pnl > min_profit_threshold:
                logger.info(f"Closing grid: BUY won. BuyProfit={buy_profit:.2f}, SellProfit={sell_profit:.2f}")
                closed = True
        elif sell_profit > 0 and buy_profit < 0:
            if sell_profit > abs(buy_profit) * (1 + margin) and total_pnl > min_profit_threshold:
                logger.info(f"Closing grid: SELL won. SellProfit={sell_profit:.2f}, BuyProfit={buy_profit:.2f}")
                closed = True
        elif buy_profit > min_profit_threshold and sell_profit == 0:
            logger.info(f"Closing grid: Only BUY triggered and profitable. BuyProfit={buy_profit:.2f}")
            closed = True
        elif sell_profit > min_profit_threshold and buy_profit == 0:
            logger.info(f"Closing grid: Only SELL triggered and profitable. SellProfit={sell_profit:.2f}")
            closed = True
                
        if closed:
            self._close_all_grid_orders()
            self.risk_guard.record_pnl(total_pnl)
            
    def _close_all_grid_orders(self):
        """Closes all open positions and deletes pending orders associated with this grid."""
        logger.info(f"Closing {len(self.tickets)} grid tickets.")
        
        if mt5:
            for ticket in self.tickets:
                # 1. Check if it's a pending order
                order = mt5.orders_get(ticket=ticket)
                if order and len(order) > 0:
                    request = {
                        "action": mt5.TRADE_ACTION_REMOVE,
                        "order": ticket,
                        "magic": self.magic_number,
                    }
                    mt5.order_send(request)
                    continue
                
                # 2. Check if it's an open position
                pos = mt5.positions_get(ticket=ticket)
                if pos and len(pos) > 0:
                    position = pos[0]
                    tick = mt5.symbol_info_tick(position.symbol)
                    if not tick: continue
                    
                    price = tick.bid if position.type == mt5.ORDER_TYPE_BUY else tick.ask
                    type_close = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
                    
                    request = {
                        "action": mt5.TRADE_ACTION_DEAL,
                        "symbol": position.symbol,
                        "volume": position.volume,
                        "type": type_close,
                        "position": ticket,
                        "price": price,
                        "deviation": 20,
                        "magic": self.magic_number,
                        "comment": "Grid close",
                        "type_time": mt5.ORDER_TIME_GTC,
                        "type_filling": mt5.ORDER_FILLING_IOC,
                    }
                    mt5.order_send(request)
                    
        self.tickets.clear()
        self.grid_placed = False
        self.grid_start_time = 0
        # Wait a little bit before allowing next grid
        time.sleep(1.0)
        self.pause_detector.reset()
        
    def _send_order(self, order_type, price, lot_size) -> int:
        """Helper to send MT5 pending order. Returns ticket or None."""
        if not mt5:
            # Mock mode
            return int(time.time() * 1000) % 1000000
            
        request = {
            "action": mt5.TRADE_ACTION_PENDING,
            "symbol": self.symbol,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "deviation": 20,
            "magic": self.magic_number,
            "comment": "News Grid",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,
        }
        
        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return result.order
        else:
            if result:
                logger.error(f"Failed to place grid order: {result.retcode}")
            return None
