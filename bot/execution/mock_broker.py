class MockBroker:
    def __init__(self, initial_balance: float = 10000.0):
        self.balance = initial_balance
        self.equity = initial_balance
        self.open_positions = []
        self.trade_history = []
        self.current_price = 0.0

    def update_price(self, row):
        """Kandelstik narxlarini yangilash va StopLoss/TakeProfit larni tekshirish"""
        self.current_price = row['close']
        
        # Ochiq pozitsiyalarni tekshirish (SL/TP)
        for pos in self.open_positions[:]:
            if pos['type'] == 'BUY':
                if pos['sl'] and row['low'] <= pos['sl']:
                    self._close_position(pos, pos['sl'], "SL", row['time'])
                elif pos['tp'] and row['high'] >= pos['tp']:
                    self._close_position(pos, pos['tp'], "TP", row['time'])
            
            elif pos['type'] == 'SELL':
                if pos['sl'] and row['high'] >= pos['sl']:
                    self._close_position(pos, pos['sl'], "SL", row['time'])
                elif pos['tp'] and row['low'] <= pos['tp']:
                    self._close_position(pos, pos['tp'], "TP", row['time'])

    def open_order(self, symbol: str, order_type: str, volume: float, price: float, sl: float = None, tp: float = None, time=None):
        pos = {
            'id': len(self.trade_history) + len(self.open_positions) + 1,
            'symbol': symbol,
            'type': order_type,
            'volume': volume,
            'open_price': price,
            'sl': sl,
            'tp': tp,
            'open_time': time
        }
        self.open_positions.append(pos)
        print(f"[MockBroker] {order_type} ochildi: {symbol} @ {price}")

    def _close_position(self, pos, close_price, reason, time):
        """Pozitsiyani yopish va foyda/zararni hisoblash"""
        is_buy = pos['type'] == 'BUY'
        diff = (close_price - pos['open_price']) if is_buy else (pos['open_price'] - close_price)
        
        # Sodda profit hisoblash (1 pip = $10 deb hisoblasak standart lot uchun)
        # Haqiqiy botda bu yerda to'g'ri hisoblash bo'ladi
        profit = (diff * 100000) * pos['volume'] 
        
        self.balance += profit
        self.equity = self.balance
        
        self.open_positions.remove(pos)
        
        history_record = {
            **pos,
            'close_price': close_price,
            'close_time': time,
            'reason': reason,
            'profit': profit
        }
        self.trade_history.append(history_record)
        print(f"[MockBroker] {pos['type']} yopildi ({reason}): {profit:.2f}$")

    def get_stats(self):
        wins = sum(1 for t in self.trade_history if t['profit'] > 0)
        total = len(self.trade_history)
        win_rate = (wins / total * 100) if total > 0 else 0
        total_profit = sum(t['profit'] for t in self.trade_history)
        
        return {
            'initial_balance': 10000.0,
            'final_balance': self.balance,
            'total_trades': total,
            'win_rate': win_rate,
            'total_profit': total_profit
        }
