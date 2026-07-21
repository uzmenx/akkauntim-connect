from datetime import datetime
from bot.core.data_loader import BacktestDataLoader
from bot.execution.mock_broker import MockBroker
import importlib

class Backtester:
    def __init__(self, strategy_name: str, symbol: str, timeframe: int):
        self.strategy_name = strategy_name
        self.symbol = symbol
        self.timeframe = timeframe
        self.data_loader = BacktestDataLoader()
        self.broker = MockBroker(initial_balance=10000.0)
        
        # Dinamik ravishda strategiyani yuklash
        try:
            strategy_module = importlib.import_module(f"bot.strategy.{strategy_name}")
            # Botda strategiyani ishga tushirish uchun qandaydir sinf yoki funksiya bo'lishi kutiladi
            # Hozircha dummy logic bilan ishlaymiz
            self.strategy_logic = getattr(strategy_module, 'analyze', self.dummy_strategy)
        except Exception as e:
            print(f"Strategiya yuklanmadi: {e}, default dummy strategiya ishlatilmoqda.")
            self.strategy_logic = self.dummy_strategy

    def run(self, start_date: datetime, end_date: datetime):
        print(f"--- Backtest Boshlandi: {self.strategy_name} on {self.symbol} ---")
        
        # 1. Ma'lumotlarni yuklash
        df = self.data_loader.fetch_history(self.symbol, self.timeframe, start_date, end_date)
        if df.empty:
            print("Ma'lumot topilmadi!")
            return
            
        print(f"Jami {len(df)} ta kandel yuklandi.")
        
        # 2. Asosiy tsikl (Tick by tick yoki Candle by Candle simulyatsiyasi)
        for index, row in df.iterrows():
            # Brokerni yangilash (SL/TP larni tekshirish)
            self.broker.update_price(row)
            
            # Strategiyadan signal kutish
            # Aslida bu yerda joriy vaqtga qadar bo'lgan DF ni uzatish to'g'riroq bo'ladi
            # Hozirgi onlayn muhit uchun soddalashtirilgan
            signal = self.strategy_logic(row, self.broker)
            
            if signal:
                if signal['type'] == 'BUY':
                    self.broker.open_order(
                        self.symbol, 'BUY', 0.1, row['close'], 
                        sl=signal.get('sl'), tp=signal.get('tp'), time=row['time']
                    )
                elif signal['type'] == 'SELL':
                    self.broker.open_order(
                        self.symbol, 'SELL', 0.1, row['close'], 
                        sl=signal.get('sl'), tp=signal.get('tp'), time=row['time']
                    )

        print("--- Backtest Yakunlandi ---")
        stats = self.broker.get_stats()
        print(f"Natijalar: {stats}")
        return stats

    def dummy_strategy(self, current_candle, broker):
        """Strategiya moduli topilmasa ishlatiladigan juda oddiy mantiq"""
        import random
        # Har 100 kandelda 1 ta tasodifiy savdo
        if random.random() < 0.01:
            if random.random() > 0.5:
                return {
                    'type': 'BUY',
                    'sl': current_candle['close'] - 0.005,
                    'tp': current_candle['close'] + 0.010
                }
            else:
                return {
                    'type': 'SELL',
                    'sl': current_candle['close'] + 0.005,
                    'tp': current_candle['close'] - 0.010
                }
        return None

if __name__ == "__main__":
    # Test qilib ko'rish uchun
    from datetime import timedelta
    end = datetime.now()
    start = end - timedelta(days=30)
    bt = Backtester('smc', 'EURUSD', 16384) # 16384 = mt5.TIMEFRAME_H1
    bt.run(start, end)
