import random

class MockBroker:
    def __init__(self, initial_balance: float = 10000.0, config: dict = None):
        self.initial_balance = initial_balance
        self.config = config or {
            'spread_pips': 1.5,
            'commission_per_lot': 3.0,
            'slippage_pips': 0.5
        }
        self.reset()

    def reset(self):
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.open_positions = []
        self.trade_history = []
        self.current_price = 0.0

    def update_price(self, row):
        """Kandelstik narxlarini yangilash va StopLoss/TakeProfit larni tekshirish"""
        self.current_price = row['close']
        
        # Ochiq pozitsiyalarni tekshirish (SL/TP)
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
                # Ikkalasi ham urilgan bo'lsa, konservativ taxmin: SL birinchi urilgan
                self._close_position(pos, pos['sl'], "SL", row['time'])
            elif sl_hit:
                self._close_position(pos, pos['sl'], "SL", row['time'])
            elif tp_hit:
                self._close_position(pos, pos['tp'], "TP", row['time'])

    def open_order(self, symbol: str, order_type: str, volume: float, price: float, sl: float = None, tp: float = None, time=None):
        pip = 0.0001 if "JPY" not in symbol else 0.01
        spread_cost = (self.config['spread_pips'] / 2) * pip
        
        # Ochilishda spread qo'llash (foydalanuvchi foydasiga emas)
        if order_type == 'BUY':
            execution_price = price + spread_cost
        else:
            execution_price = price - spread_cost
            
        pos = {
            'id': len(self.trade_history) + len(self.open_positions) + 1,
            'symbol': symbol,
            'type': order_type,
            'volume': volume,
            'open_price': execution_price,
            'sl': sl,
            'tp': tp,
            'open_time': time
        }
        self.open_positions.append(pos)
        print(f"[MockBroker] {order_type} ochildi: {symbol} @ {execution_price:.5f} (Spread hisobga olindi)")

    def _close_position(self, pos, close_price, reason, time):
        """Pozitsiyani yopish va foyda/zararni hisoblash"""
        pip = 0.0001 if "JPY" not in pos['symbol'] else 0.01
        
        # Slippage qo'llash (doim yomonlashuv tomoniga, simulyatsiya uchun)
        slippage_val = random.uniform(0, self.config['slippage_pips']) * pip
        if pos['type'] == 'BUY':
            actual_close = close_price - slippage_val
            diff = actual_close - pos['open_price']
        else:
            actual_close = close_price + slippage_val
            diff = pos['open_price'] - actual_close
        
        # Standart lot qiymati (1 pip = $10 deb hisoblash EURUSD uchun)
        multiplier = 100000 if pip == 0.0001 else 1000
        profit = (diff * multiplier) * pos['volume'] 
        
        # Komissiya ayirish
        commission = self.config['commission_per_lot'] * pos['volume']
        profit -= commission
        
        self.balance += profit
        self.equity = self.balance
        
        self.open_positions.remove(pos)
        
        history_record = {
            **pos,
            'close_price': actual_close,
            'close_time': time,
            'reason': reason,
            'profit': profit,
            'commission': commission,
            'slippage_pips': slippage_val / pip
        }
        self.trade_history.append(history_record)
        print(f"[MockBroker] {pos['type']} yopildi ({reason}): {profit:.2f}$ (Kom: {commission:.2f}$, Slip: {slippage_val/pip:.1f}p)")

    def get_stats(self):
        wins = sum(1 for t in self.trade_history if t['profit'] > 0)
        total = len(self.trade_history)
        win_rate = (wins / total * 100) if total > 0 else 0
        total_profit = sum(t['profit'] for t in self.trade_history)
        total_commission = sum(t.get('commission', 0) for t in self.trade_history)
        
        return {
            'initial_balance': 10000.0,
            'final_balance': self.balance,
            'total_trades': total,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'total_commission': total_commission
        }
