import random

class MockBroker:
    def __init__(self, initial_balance: float = 10000.0, config: dict = None):
        self.initial_balance = initial_balance
        self.config = {
            'spread_pips': 1.5,
            'commission_per_lot': 3.0,
            'slippage_pips': 0.8,
            'dynamic_slippage': True,
            'dynamic_spread': True
        }
        if config:
            self.config.update(config)
        self.reset()

    def reset(self):
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.open_positions = []
        self.pending_orders = []
        self.trade_history = []
        self.current_price = 0.0
        self.current_candle = None

    def update_price(self, row):
        """Kandelstik narxlarini yangilash, pending orderlarni faollashtirish va StopLoss/TakeProfit larni tekshirish"""
        self.current_price = row['close']
        self.current_candle = row
        
        # Calculate dynamic spread and slippage multipliers based on current bar volatility (high-low vs average)
        base_spread = self.config['spread_pips']
        base_slippage = self.config['slippage_pips']
        
        pip_size = 0.0001 if "JPY" not in row.get('symbol', 'EURUSD') else 0.01
        bar_range_pips = (row['high'] - row['low']) / pip_size if 'high' in row and 'low' in row else 10.0
        
        # Volatility expansion multiplier (bounded between 1.0 and 3.5x)
        vol_multiplier = max(1.0, min(3.5, bar_range_pips / 15.0)) if self.config.get('dynamic_spread') else 1.0
        effective_spread = base_spread * vol_multiplier
        
        # 1. Pending orderlarni tekshirish va faollashtirish
        for pending in self.pending_orders[:]:
            is_buy_stop = pending['type'] == 'BUY_STOP'
            is_sell_stop = pending['type'] == 'SELL_STOP'
            triggered = False
            
            if is_buy_stop and row['high'] >= pending['trigger_price']:
                triggered = True
                order_type = 'BUY'
                exec_price = max(pending['trigger_price'], row['open'])
            elif is_sell_stop and row['low'] <= pending['trigger_price']:
                triggered = True
                order_type = 'SELL'
                exec_price = min(pending['trigger_price'], row['open'])
                
            if triggered:
                if pending in self.pending_orders:
                    self.pending_orders.remove(pending)
                pip = 0.0001 if "JPY" not in pending['symbol'] else 0.01
                spread_cost = (effective_spread / 2) * pip
                
                # Dynamic entry slippage
                entry_slip_pips = random.uniform(0.1, base_slippage * vol_multiplier) if self.config.get('dynamic_slippage') else random.uniform(0, base_slippage)
                entry_slip = entry_slip_pips * pip
                
                # Ochilishda spread va slippage qo'llash
                if order_type == 'BUY':
                    execution_price = exec_price + spread_cost + entry_slip
                else:
                    execution_price = exec_price - spread_cost - entry_slip
                    
                pos = {
                    'id': pending['id'],
                    'symbol': pending['symbol'],
                    'type': order_type,
                    'volume': pending['volume'],
                    'open_price': execution_price,
                    'sl': pending['sl'],
                    'tp': pending['tp'],
                    'open_time': row['time'],
                    'entry_slippage_pips': entry_slip_pips,
                    'spread_pips_used': effective_spread
                }
                self.open_positions.append(pos)
                print(f"[MockBroker] Pending order {pending['type']} faollashdi: {pending['symbol']} @ {execution_price:.5f} (Slip: {entry_slip_pips:.1f}p)")

        # 2. Ochiq pozitsiyalarni tekshirish (SL/TP)
        for pos in self.open_positions[:]:
            is_buy = pos['type'] == 'BUY'
            sl_hit = False
            tp_hit = False
            
            if is_buy:
                if pos['sl'] and row['low'] <= pos['sl']:
                    sl_hit = True
                if pos['tp'] and row['high'] >= pos['tp']:
                    tp_hit = True
            else:
                if pos['sl'] and row['high'] >= pos['sl']:
                    sl_hit = True
                if pos['tp'] and row['low'] <= pos['tp']:
                    tp_hit = True
                    
            if sl_hit and tp_hit:
                # Conservative assumption: SL hit first
                self._close_position(pos, pos['sl'], "SL", row['time'])
            elif sl_hit:
                self._close_position(pos, pos['sl'], "SL", row['time'])
            elif tp_hit:
                self._close_position(pos, pos['tp'], "TP", row['time'])

    def open_order(self, symbol: str, order_type: str, volume: float, price: float, sl: float = None, tp: float = None, time=None):
        pip = 0.0001 if "JPY" not in symbol else 0.01
        
        base_spread = self.config['spread_pips']
        base_slippage = self.config['slippage_pips']
        
        # Volatility multiplier if candle data is available
        vol_multiplier = 1.0
        if self.current_candle and self.config.get('dynamic_spread'):
            bar_range_pips = (self.current_candle['high'] - self.current_candle['low']) / pip
            vol_multiplier = max(1.0, min(3.5, bar_range_pips / 15.0))
            
        effective_spread = base_spread * vol_multiplier
        spread_cost = (effective_spread / 2) * pip
        
        # Entry slippage
        entry_slip_pips = random.uniform(0.1, base_slippage * vol_multiplier) if self.config.get('dynamic_slippage') else random.uniform(0, base_slippage)
        entry_slip = entry_slip_pips * pip
        
        if order_type == 'BUY':
            execution_price = price + spread_cost + entry_slip
        else:
            execution_price = price - spread_cost - entry_slip
            
        pos = {
            'id': len(self.trade_history) + len(self.open_positions) + len(self.pending_orders) + 1,
            'symbol': symbol,
            'type': order_type,
            'volume': volume,
            'open_price': execution_price,
            'sl': sl,
            'tp': tp,
            'open_time': time,
            'entry_slippage_pips': entry_slip_pips,
            'spread_pips_used': effective_spread
        }
        self.open_positions.append(pos)
        print(f"[MockBroker] {order_type} ochildi: {symbol} @ {execution_price:.5f} (Spread: {effective_spread:.1f}p, Slip: {entry_slip_pips:.1f}p)")

    def add_pending_order(self, symbol: str, order_type: str, volume: float, trigger_price: float, sl: float = None, tp: float = None, time=None):
        order_id = len(self.trade_history) + len(self.open_positions) + len(self.pending_orders) + 1
        pending = {
            'id': order_id,
            'symbol': symbol,
            'type': order_type, # 'BUY_STOP', 'SELL_STOP'
            'volume': volume,
            'trigger_price': trigger_price,
            'sl': sl,
            'tp': tp,
            'time': time
        }
        self.pending_orders.append(pending)
        print(f"[MockBroker] Pending {order_type} o'rnatildi: {symbol} @ {trigger_price:.5f}")
        return order_id

    def cancel_all_pending(self):
        count = len(self.pending_orders)
        self.pending_orders.clear()
        if count > 0:
            print(f"[MockBroker] Barcha pending orderlar bekor qilindi ({count} ta)")

    def close_all_positions(self, reason: str, time):
        for pos in self.open_positions[:]:
            self._close_position(pos, self.current_price, reason, time)

    def _close_position(self, pos, close_price, reason, time):
        """Pozitsiyani yopish va foyda/zararni hisoblash"""
        pip = 0.0001 if "JPY" not in pos['symbol'] else 0.01
        
        base_slippage = self.config['slippage_pips']
        vol_multiplier = 1.0
        if self.current_candle and self.config.get('dynamic_slippage'):
            bar_range_pips = (self.current_candle['high'] - self.current_candle['low']) / pip
            vol_multiplier = max(1.0, min(3.5, bar_range_pips / 15.0))
            
        # Exit slippage (always penalizing performance realistically)
        exit_slip_pips = random.uniform(0.1, base_slippage * vol_multiplier) if self.config.get('dynamic_slippage') else random.uniform(0, base_slippage)
        exit_slip_val = exit_slip_pips * pip
        
        if pos['type'] == 'BUY':
            actual_close = close_price - exit_slip_val
            diff = actual_close - pos['open_price']
        else:
            actual_close = close_price + exit_slip_val
            diff = pos['open_price'] - actual_close
        
        # Standard lot multiplier ($10/pip for standard FX lot)
        multiplier = 100000 if pip == 0.0001 else 1000
        profit = (diff * multiplier) * pos['volume'] 
        
        # Deduct commission
        commission = self.config['commission_per_lot'] * pos['volume']
        profit -= commission
        
        total_slip_pips = pos.get('entry_slippage_pips', 0.0) + exit_slip_pips
        slip_usd_cost = (total_slip_pips * 10.0) * pos['volume']
        
        self.balance += profit
        self.equity = self.balance
        
        if pos in self.open_positions:
            self.open_positions.remove(pos)
        
        history_record = {
            **pos,
            'close_price': actual_close,
            'close_time': time,
            'reason': reason,
            'profit': profit,
            'commission': commission,
            'slippage_pips': total_slip_pips,
            'slippage_usd': slip_usd_cost
        }
        self.trade_history.append(history_record)
        print(f"[MockBroker] {pos['type']} yopildi ({reason}): {profit:.2f}$ (Kom: {commission:.2f}$, Slip: {total_slip_pips:.1f}p / ${slip_usd_cost:.2f})")

    def get_stats(self):
        wins = sum(1 for t in self.trade_history if t['profit'] > 0)
        total = len(self.trade_history)
        win_rate = (wins / total * 100) if total > 0 else 0
        total_profit = sum(t['profit'] for t in self.trade_history)
        total_commission = sum(t.get('commission', 0) for t in self.trade_history)
        total_slippage_usd = sum(t.get('slippage_usd', 0) for t in self.trade_history)
        avg_slippage_pips = (sum(t.get('slippage_pips', 0) for t in self.trade_history) / total) if total > 0 else 0.0
        
        return {
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'total_trades': total,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'total_commission': total_commission,
            'total_slippage_usd': total_slippage_usd,
            'avg_slippage_pips': avg_slippage_pips,
            'base_spread_pips': self.config['spread_pips']
        }

