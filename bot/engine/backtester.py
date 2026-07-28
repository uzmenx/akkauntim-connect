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

    def run(self, start_date: datetime, end_date: datetime, split_ratio: float = 0.5):
        print(f"--- Backtest Boshlandi: {self.strategy_name} on {self.symbol} ---")
        
        # 1. Ma'lumotlarni yuklash
        df = self.data_loader.fetch_history(self.symbol, self.timeframe, start_date, end_date)
        if df is None or df.empty:
            print("Ma'lumot topilmadi!")
            return
            
        print(f"Jami {len(df)} ta kandel yuklandi.")
        
        split_index = int(len(df) * split_ratio)
        is_df = df.iloc[:split_index]
        oos_df = df.iloc[split_index:]
        
        print(f"IS (In-Sample) kandelalar: {len(is_df)}")
        print(f"OOS (Out-of-Sample) kandelalar: {len(oos_df)}")
        
        # In-Sample Run
        print("\n--- IN-SAMPLE (IS) SIMULYATSIYA BOSHLANDI ---")
        self.broker.reset()
        self._run_simulation(is_df)
        is_stats = self.broker.get_stats()
        print(f"IS Natijalar: {is_stats}")
        
        # Out-of-Sample Run
        print("\n--- OUT-OF-SAMPLE (OOS) SIMULYATSIYA BOSHLANDI ---")
        self.broker.reset()
        self._run_simulation(oos_df)
        oos_stats = self.broker.get_stats()
        print(f"OOS Natijalar: {oos_stats}")
        
        return {"IS": is_stats, "OOS": oos_stats}

    def _run_simulation(self, df):
        min_bars = 100
        if len(df) <= min_bars:
            print("Kandelalar soni yetarli emas (min 100)!")
            return
            
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
                if result.decision == "EXECUTE" or result.score >= 50:
                    if result.signal == 'BUY':
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
                pass

if __name__ == "__main__":
    from datetime import timedelta
    end = datetime.now()
    start = end - timedelta(days=30)
    bt = Backtester('EURUSD', 16384) # 16384 = mt5.TIMEFRAME_H1
    bt.run(start, end, split_ratio=0.5)
