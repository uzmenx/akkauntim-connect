"""
backtester.py
=============

MUHIM (2026-07-30 TUZATISH):
Avvalgi versiya `calculate_confluence()` (confluence.py) dan foydalangan edi —
bu funksiya faqat SMC+Harmonic'ni hisobga oladi va LIVE botda umuman ishlatilmaydi.

Live bot (bot/main.py) signalni `aggregate_signals()` (bot/engine/voting.py) orqali
oladi — 7 ta strategiya (SMC, Pattern, News, Wyckoff, SR_Volume, Auto_Pattern,
Kill_Zones) majority-vote qiladi. Bu fayl endi ANIQ SHU FUNKSIYANI chaqiradi,
shunda backtest natijasi haqiqatan live bot mantiqini aks ettiradi.

CHEKLOV: Bu backtest AI (Claude) qatlamisiz ishlaydi — main.py'da voting'dan keyin
Claude yakuniy tasdiq/rad beradi, buni bu yerda simulyatsiya qilmaymiz (720+ bar
uchun API chaqirish qimmat va sekin bo'lardi). Demak bu "voting-only" backtest —
mexanik 7-strategiya qarorini sinaydi, AI filtrini emas. Natijalarni shunga qarab
talqin qiling: bu yerda yaxshi win rate AI qatlamisiz ham signal sifatli ekanini
ko'rsatadi; AI qo'shilsa yanada yaxshilanishi yoki confidence bilan filtrlanishi
mumkin — buni alohida, kichikroq sample'da AI-bilan sinash tavsiya etiladi.

News strategiyasi backtest'da har doim bo'sh ({}) beriladi, chunki tarixiy
yangiliklar ma'lumoti hozircha ulanmagan (real vaqtli AI so'rov talab qiladi).
"""
import logging
from datetime import datetime
from bot.config import BotConfig
from bot.core.data_loader import BacktestDataLoader
from bot.execution.mock_broker import MockBroker

from bot.strategy.smc.engine import analyze_market_structure
from bot.strategy.harmonic.engine import analyze_harmonic_patterns
from bot.strategy.wyckoff.engine import analyze_wyckoff
from bot.strategy.sr_volume.engine import analyze_sr_volume
from bot.strategy.auto_patterns.engine import analyze_auto_patterns
from bot.strategy.kill_zones.engine import analyze_kill_zones
from bot.engine.confluence import compute_atr
from bot.engine.voting import aggregate_signals
from bot.engine.dynamic_levels import calculate_dynamic_levels

logger = logging.getLogger(__name__)


class Backtester:
    def __init__(self, symbol: str, timeframe: int, config: BotConfig = None):
        self.strategy_name = "Voting Engine (Live-Parity)"
        self.symbol = symbol
        self.timeframe = timeframe
        self.data_loader = BacktestDataLoader()
        self.broker = MockBroker(initial_balance=10000.0)
        # Haqiqiy BotConfig ishlatamiz — shu bilan weight/threshold'lar
        # live bot bilan avtomatik sinxron bo'ladi (qo'lda nusxa ko'chirilmaydi).
        self.config = config or BotConfig()
        self.error_counts = {}

    def run(self, start_date: datetime, end_date: datetime, split_ratio: float = 0.5):
        print(f"--- Backtest Boshlandi: {self.strategy_name} on {self.symbol} ---")

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

        print("\n--- IN-SAMPLE (IS) SIMULYATSIYA BOSHLANDI ---")
        self.broker.reset()
        self.error_counts = {}
        self._run_simulation(is_df)
        is_stats = self.broker.get_stats()
        print(f"IS Natijalar: {is_stats}")
        self._print_error_summary("IS")

        print("\n--- OUT-OF-SAMPLE (OOS) SIMULYATSIYA BOSHLANDI ---")
        self.broker.reset()
        self.error_counts = {}
        self._run_simulation(oos_df)
        oos_stats = self.broker.get_stats()
        print(f"OOS Natijalar: {oos_stats}")
        self._print_error_summary("OOS")

        return {"IS": is_stats, "OOS": oos_stats}

    def _print_error_summary(self, label: str):
        """Har bir strategiya moduli qancha marta xato berganini ko'rsatadi.
        Avvalgi versiyada bu xatolar `except: pass` bilan butunlay yashiringan edi —
        agar biror modul (masalan yangi qo'shilgan) doim xato bersa, bu natijaga
        sezmasdan ta'sir qilar edi."""
        if not self.error_counts:
            print(f"[{label}] Strategiya xatolari: yo'q.")
            return
        print(f"[{label}] Strategiya xatolari (modul: son):")
        for module, count in sorted(self.error_counts.items(), key=lambda x: -x[1]):
            print(f"  - {module}: {count} marta")

    def _get_pip_divisor(self) -> float:
        return 0.01 if "JPY" in self.symbol.upper() else 0.0001

    def _run_simulation(self, df):
        min_bars = 100
        if len(df) <= min_bars:
            print("Kandelalar soni yetarli emas (min 100)!")
            return

        pip_divisor = self._get_pip_divisor()

        for i in range(min_bars, len(df)):
            # "Hozirgi vaqtgacha bo'lgan" qismini ajratib olish (look-ahead bias oldini olish)
            current_df = df.iloc[:i + 1].copy()
            current_row = current_df.iloc[-1]
            current_price = float(current_row['close'])

            self.broker.update_price(current_row)

            smc_data = self._safe_call("SMC", analyze_market_structure, current_df)
            harmonic_data = self._safe_call("Harmonic", analyze_harmonic_patterns, current_df)
            wyckoff_data = self._safe_call("Wyckoff", analyze_wyckoff, current_df)
            sr_data = self._safe_call("SR_Volume", analyze_sr_volume, current_df)
            atr = compute_atr(current_df)
            auto_patterns_data = self._safe_call(
                "Auto_Pattern", analyze_auto_patterns, current_df, current_price, atr
            )
            kill_zones_data = self._safe_call("Kill_Zones", analyze_kill_zones, current_df)

            # Bir yoki bir nechta modul xato bergan bo'lsa ham voting davom etadi —
            # aggregate_signals har bir argumentni `or {}` bilan himoyalaydi.
            voting_result = aggregate_signals(
                smc_data=smc_data,
                pattern_data=harmonic_data,
                news_data={},  # Tarixiy yangiliklar hozircha ulanmagan, izohga qarang.
                wyckoff_data=wyckoff_data,
                sr_volume_data=sr_data,
                auto_pattern_data=auto_patterns_data,
                kill_zones_data=kill_zones_data,
                config=self.config,
                active_strategies=None,  # None => barcha strategiyalar aktiv (live default)
            )

            signal = voting_result.get("signal")
            if signal not in ("BUY", "SELL"):
                continue

            risk_pct = voting_result.get("risk_pct", 0.0)
            if risk_pct <= 0:
                continue

            levels = calculate_dynamic_levels(
                signal=signal,
                current_price=current_price,
                smc_data=smc_data or {},
                harmonic_data=harmonic_data or {},
                atr_pips=(atr / pip_divisor) if atr > 0 else 15.0,
                pip_divisor=pip_divisor,
            )

            if not levels.get("is_valid"):
                # dynamic_levels R:R (min 1:1.5) yoki boshqa sabab bilan bitimni rad etdi
                continue
            sl = levels.get("sl_price")
            tp = levels.get("tp1_price")

            # Voting'dagi risk_pct'ga mos lot hajmi (fixed 0.1 emas — bu ham eski
            # versiyaning kamchiligi edi: risk darajasi hech qachon lot'ga ta'sir
            # qilmasdi). Balans asosida oddiy hisob: 10000 boshlang'ich balans.
            lot_size = self._lot_from_risk(risk_pct, current_price, sl)

            self.broker.open_order(
                self.symbol, signal, lot_size, current_price,
                sl=sl, tp=tp, time=current_row['time']
            )

    def _lot_from_risk(self, risk_pct: float, entry: float, sl: float) -> float:
        """Risk foiziga qarab taxminiy lot hajmi (soddalashtirilgan — real tick
        value/margin emas, RiskManager.calculate_lot_size dagi kabi aniq emas,
        lekin fixed 0.1 dan ancha real: kattaroq risk_pct kattaroq lot beradi)."""
        balance = self.broker.balance if self.broker.balance > 0 else 10000.0
        risk_amount = balance * risk_pct
        sl_distance = abs(entry - sl)
        if sl_distance <= 0:
            return 0.1
        pip_divisor = self._get_pip_divisor()
        multiplier = 100000 if pip_divisor == 0.0001 else 1000
        loss_per_lot = sl_distance * multiplier
        if loss_per_lot <= 0:
            return 0.1
        raw_lot = risk_amount / loss_per_lot
        return round(max(0.01, min(raw_lot, 5.0)), 2)

    def _safe_call(self, name: str, fn, *args):
        """Strategiya funksiyasini xavfsiz chaqiradi. Avvalgi versiyada bunday
        xatolar `except: pass` bilan jim yutilar edi — endi kamida sanaladi va
        run() oxirida ko'rsatiladi, shunda biror modul doim buzilib turgani
        ko'rinmasdan qolmaydi."""
        try:
            return fn(*args)
        except Exception as e:
            self.error_counts[name] = self.error_counts.get(name, 0) + 1
            logger.debug(f"[{name}] backtest xatosi: {e}")
            return {}


if __name__ == "__main__":
    from datetime import timedelta
    end = datetime.now()
    start = end - timedelta(days=15)
    bt = Backtester('EURUSD', 16384)  # 16384 = mt5.TIMEFRAME_H1
    bt.run(start, end, split_ratio=0.5)
