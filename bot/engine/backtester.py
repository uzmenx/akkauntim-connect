from datetime import datetime
from bot.core.data_loader import BacktestDataLoader
from bot.execution.mock_broker import MockBroker

from bot.strategy.smc.engine import analyze_market_structure
from bot.strategy.harmonic.engine import analyze_harmonic_patterns
from bot.strategy.wyckoff.engine import analyze_wyckoff
from bot.strategy.sr_volume.engine import analyze_sr_volume
from bot.strategy.auto_patterns.engine import analyze_auto_patterns
from bot.strategy.kill_zones.engine import analyze_kill_zones
from bot.engine.confluence import calculate_confluence, compute_atr

class Backtester:
    def __init__(self, symbol: str, timeframe: int):
        self.strategy_name = "Confluence Engine"
        self.symbol = symbol
        self.timeframe = timeframe
        self.data_loader = BacktestDataLoader()
        self.broker = MockBroker(initial_balance=10000.0)

    def run(self, start_date: datetime, end_date: datetime):
        print(f"--- Backtest Boshlandi: {self.strategy_name} on {self.symbol} ---")
        
        # 1. Ma'lumotlarni yuklash
        df = self.data_loader.fetch_history(self.symbol, self.timeframe, start_date, end_date)
        if df is None or df.empty:
            print("Ma'lumot topilmadi!")
            return
            
        print(f"Jami {len(df)} ta kandel yuklandi.")
        
        # 2. Asosiy tsikl (Candle by Candle simulyatsiyasi)
        min_bars = 100
        for i in range(min_bars, len(df)):
            # "Hozirgi vaqtgacha bo'lgan" qismini ajratib olish (look-ahead bias ni oldini olish)
            current_df = df.iloc[:i+1].copy()
            current_row = current_df.iloc[-1]
            current_price = float(current_row['close'])
            
            # Brokerni yangilash (SL/TP larni tekshirish)
            self.broker.update_price(current_row)
            
            # Strategiyadan signal kutish
            try:
                smc_data = analyze_market_structure(current_df)
                harmonic_data = analyze_harmonic_patterns(current_df)
                wyckoff_data = analyze_wyckoff(current_df)
                sr_data = analyze_sr_volume(current_df)
                atr = compute_atr(current_df)
                auto_patterns_data = analyze_auto_patterns(current_df, current_price, atr)
                kill_zones_data = analyze_kill_zones(current_df)
                
                result = calculate_confluence(
                    smc_data=smc_data,
                    harmonic_data=harmonic_data,
                    news_data={},
                    df=current_df,
                    current_price=current_price,
                    wyckoff_data=wyckoff_data,
                    sr_volume_data=sr_data,
                    auto_pattern_data=auto_patterns_data,
                    kill_zones_data=kill_zones_data
                )
                
                # Signal tahlili (70+ score = EXECUTE)
                # Yoki AI qarorisiz backtest uchun o'rtacha ballarni ham qabul qilishimiz mumkin
                if result.decision == "EXECUTE" or result.score >= 50:
                    if result.signal == 'BUY':
                        # Oddiy SL/TP hisoblash (ATR asosida yoki fix)
                        sl = current_price - (atr * 2) if atr > 0 else current_price * 0.99
                        tp = current_price + (atr * 4) if atr > 0 else current_price * 1.02
                        self.broker.open_order(
                            self.symbol, 'BUY', 0.1, current_price, 
                            sl=sl, tp=tp, time=current_row['time']
                        )
                    elif result.signal == 'SELL':
                        sl = current_price + (atr * 2) if atr > 0 else current_price * 1.01
                        tp = current_price - (atr * 4) if atr > 0 else current_price * 0.98
                        self.broker.open_order(
                            self.symbol, 'SELL', 0.1, current_price, 
                            sl=sl, tp=tp, time=current_row['time']
                        )
            except Exception as e:
                # print(f"Tahlil xatosi (index {i}): {e}")
                pass

        print("--- Backtest Yakunlandi ---")
        stats = self.broker.get_stats()
        print(f"Natijalar: {stats}")
        return stats

if __name__ == "__main__":
    # Test qilib ko'rish uchun
    from datetime import timedelta
    end = datetime.now()
    start = end - timedelta(days=30)
    bt = Backtester('EURUSD', 16384) # 16384 = mt5.TIMEFRAME_H1
    bt.run(start, end)
