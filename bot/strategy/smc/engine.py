"""
smc_engine.py
=============
Python modul — TradingView Pine Script "Smart Money Concept [TradingFinder]
Major Minor OB + FVG (SMC)" indikatorining to'liq mantiqiy tarjimasi.

Bu modul trading bot uchun "ko'z" vazifasini bajaradi:
  OHLC ma'lumotlarini qabul qilib, bozor strukturasi haqida
  JSON formatidagi faktlarni chiqaradi.

ARXITEKTURA:
  smc_structure.py (mavjud) → Pivot/ZigZag/BoS/ChoCh
  smc_engine.py    (yangi)  → Order Block + FVG + Liquidity + Orchestrator

MODULLAR:
  1. OrderBlockDetector  — Demand/Supply OB'larni aniqlaydi
  2. OBRefiner           — OB zonasini optimallashtiradi (Defensive/Aggressive)
  3. FVGDetector         — Fair Value Gap'larni topadi
  4. LiquidityDetector   — Statik/Dinamik likvidlik darajalarini topadi
  5. analyze_market_structure() — Yagona orchestrator funksiya

QAROR QABUL QILMAYDI — faqat struktura faktlarini chiqaradi.
ORDER YUBORMAYDI — faqat tahlil moduli.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple

from bot.strategy.smc.structure import SMCStructure, StructureEvent, SwingPoint, compute_pivot_events


# ====================================================================
# Default Configuration
# Pine Script'dagi barcha muhim parametrlar shu yerda sozlanadi
# ====================================================================

DEFAULT_CONFIG: Dict[str, Any] = {
    # ---- Pivot / Structure ----
    # Pine: PP = input.int(5, 'Pivot Period of Order Blocks Detector')
    "pivot_period": 5,

    # ---- Order Block ----
    # Pine: OBVaP = input.int(500, 'Order Block Validity Period (Bar)')
    "ob_validity_bars": 500,
    # Pine: RefineDmainCh, RefineMeDmainCh va boshqalar
    "ob_refine": True,
    "ob_refine_method": "Defensive",  # "Defensive" | "Aggressive"

    # ---- FVG ----
    # Pine: PFVGFilter = input.bool(true), PFVGFilterType = input.string(...)
    "fvg_filter": True,
    "fvg_filter_type": "Very Defensive",
    # "Very Aggressive" | "Aggressive" | "Defensive" | "Very Defensive"

    # ---- Liquidity ----
    # Pine: SPP = input.int(8, 'Statics Period Pivot')
    "static_pivot_period": 8,
    # Pine: DPP = input.int(3, 'Dynamics Period Pivot')
    "dynamic_pivot_period": 3,
    # Pine: SLLS = input.float(0.30, 'Statics Liquidity Line Sensitivity')
    "static_liquidity_sensitivity": 0.30,
    # Pine: DLLS = input.float(1.00, 'Dynamics Liquidity Line Sensitivity')
    "dynamic_liquidity_sensitivity": 1.00,
}


# ====================================================================
# Data Classes
# ====================================================================

@dataclass
class OrderBlock:
    """
    Bitta Order Block zonasini ifodalaydi.

    Pine reference: Drawing.OBDrawing() funksiyasiga uzatiladigan
    Yd12 (top), Yp12 (bottom), Xd1 (bar_index), OBVaP (validity).
    """
    top: float              # OB zonasining yuqori chegarasi
    bottom: float           # OB zonasining quyi chegarasi
    ob_type: str            # "demand" | "supply"
    origin: str             # "ChoCh Main" | "ChoCh Sub" | "BoS"
    level: str              # "Major" | "Minor"
    bar_index: int          # OB origin shamining bar indeksi
    event_bar_index: int    # BoS/ChoCh event yuz bergan bar indeksi
    status: str = "fresh"   # "fresh" | "mitigated"
    distance_pct: float = 0.0  # Joriy narxdan masofa (%)
    timestamp: Any = None

    def to_dict(self) -> dict:
        return {
            "top": round(self.top, 5),
            "bottom": round(self.bottom, 5),
            "origin": self.origin,
            "level": self.level,
            "status": self.status,
            "distance_pct": round(self.distance_pct, 4),
            "bar_index": self.bar_index,
            "timestamp": str(self.timestamp) if self.timestamp is not None else None,
        }


@dataclass
class FairValueGap:
    """
    Fair Value Gap — 3 ta ketma-ket sham orasidagi narx bo'shlig'i.

    Pine reference: FVG.FVGDetector() kutubxonasi.
    Demand FVG: low[i] > high[i-2]  (pastdan yuqoriga gap)
    Supply FVG: high[i] < low[i-2]  (yuqoridan pastga gap)
    """
    top: float              # Gap yuqori chegarasi
    bottom: float           # Gap quyi chegarasi
    fvg_type: str           # "demand" | "supply"
    bar_index: int          # O'rta shamning (2-sham) bar indeksi
    gap_size: float         # Gap kengligi (top - bottom)
    status: str = "fresh"   # "fresh" | "filled"
    timestamp: Any = None

    def to_dict(self) -> dict:
        return {
            "top": round(self.top, 5),
            "bottom": round(self.bottom, 5),
            "type": self.fvg_type,
            "gap_size": round(self.gap_size, 5),
            "status": self.status,
            "bar_index": self.bar_index,
            "timestamp": str(self.timestamp) if self.timestamp is not None else None,
        }


# ====================================================================
# Order Block Detector
# ====================================================================

class OrderBlockDetector:
    """
    Order Block'larni BoS/ChoCh hodisalari asosida aniqlaydi.

    Pine Script reference:
      - Demand (Bullish): BuMChMain_Trigger, BuMChSub_Trigger, BuMBoS_Trigger
      - Supply (Bearish): BeMChMain_Trigger, BeMChSub_Trigger, BeMBoS_Trigger
      - Refinement: Refiner.OBRefiner('Demand'/'Supply', ...)
      - Mitigation: Drawing.OBDrawing() ichida narx OB zonasiga qaytganda

    Mantiq:
      ChoCh yuz berganda → uning "origin" shamini topish (eng past/eng baland nuqta)
      BoS yuz berganda → oxirgi pivot low/high shamini topish
      Shu shamning high/low diapazoni = OB zonasi
    """

    def __init__(self, config: dict):
        # Pine: OBVaP
        self.validity_bars = config.get("ob_validity_bars", 500)
        self.refine = config.get("ob_refine", True)
        self.refine_method = config.get("ob_refine_method", "Defensive")

    def detect(
        self,
        df: pd.DataFrame,
        smc: SMCStructure,
        events: List[StructureEvent],
    ) -> List[OrderBlock]:
        """
        Barcha BoS/ChoCh hodisalari uchun Order Block'larni aniqlaydi.

        Pine: Har bir bar'da BuMChMain_Trigger, BuMBoS_Trigger va boshqa
        trigger'lar tekshiriladi. Biz esa hodisalar ro'yxatidan iteratsiya qilamiz.
        """
        order_blocks: List[OrderBlock] = []
        n = len(df)
        current_bar = n - 1

        highs = df["high"].values
        lows = df["low"].values
        opens = df["open"].values
        closes = df["close"].values

        # timestamp ustuni mavjud bo'lsa ishlatamiz
        if "timestamp" in df.columns:
            timestamps = df["timestamp"].values
        elif "time" in df.columns:
            timestamps = df["time"].values
        else:
            timestamps = np.arange(n)

        for event in events:
            obs = self._create_obs_for_event(
                event, smc, highs, lows, opens, closes, timestamps, n
            )
            order_blocks.extend(obs)

        # ---- Muddati o'tgan OB'larni olib tashlash (Pine: OBVaP) ----
        order_blocks = [
            ob for ob in order_blocks
            if current_bar - ob.bar_index <= self.validity_bars
        ]

        # ---- Mitigation tekshiruvi ----
        for ob in order_blocks:
            self._check_mitigation(ob, highs, lows, current_bar)

        # ---- Joriy narxdan masofa ----
        if n > 0:
            current_price = float(closes[current_bar])
            for ob in order_blocks:
                mid = (ob.top + ob.bottom) / 2
                if current_price != 0:
                    ob.distance_pct = (current_price - mid) / current_price * 100

        return order_blocks

    def _create_obs_for_event(
        self,
        event: StructureEvent,
        smc: SMCStructure,
        highs: np.ndarray,
        lows: np.ndarray,
        opens: np.ndarray,
        closes: np.ndarray,
        timestamps: np.ndarray,
        n: int,
    ) -> List[OrderBlock]:
        """Bitta BoS/ChoCh hodisasi uchun OB'lar yaratadi."""

        ob_type = "demand" if event.direction == "Bullish" else "supply"

        # Shu hodisa vaqtigacha bo'lgan advance pivotlar
        relevant_pivots = [
            (smc.adv_type[j], smc.adv_value[j], smc.adv_index[j])
            for j in range(len(smc.adv_index))
            if smc.adv_index[j] < event.bar_index
        ]
        if not relevant_pivots:
            return []

        if event.kind == "ChoCh":
            return self._choch_obs(
                event, ob_type, relevant_pivots,
                highs, lows, opens, closes, timestamps, n
            )
        elif event.kind == "BoS":
            return self._bos_obs(
                event, ob_type, relevant_pivots,
                highs, lows, opens, closes, timestamps, n
            )
        return []

    # ----------------------------------------------------------------
    # ChoCh Origin OB
    # Pine: BuMChMain_Trigger / BuMChSub_Trigger / BeMChMain_Trigger / BeMChSub_Trigger
    # ----------------------------------------------------------------

    def _choch_obs(
        self,
        event: StructureEvent,
        ob_type: str,
        pivots: list,
        highs: np.ndarray,
        lows: np.ndarray,
        opens: np.ndarray,
        closes: np.ndarray,
        timestamps: np.ndarray,
        n: int,
    ) -> List[OrderBlock]:
        """
        ChoCh hodisasi uchun Main va Sub Order Block'lar yaratadi.

        Pine mantiq:
          Bullish ChoCh → LastMLL (oxirgi Major Low Low) indeksidagi shamdan
                          ChBuLowest (eng past narx) topiladi → OB origin
          Bearish ChoCh → LastMHH (oxirgi Major High High) indeksidagi shamdan
                          ChBeHighest (eng yuqori narx) topiladi → OB origin
        """
        obs: List[OrderBlock] = []

        if ob_type == "demand":
            obs.extend(
                self._demand_choch_obs(event, pivots, highs, lows, opens, closes, timestamps, n)
            )
        else:
            obs.extend(
                self._supply_choch_obs(event, pivots, highs, lows, opens, closes, timestamps, n)
            )

        return obs

    def _demand_choch_obs(self, event, pivots, highs, lows, opens, closes, ts, n):
        """
        Bullish ChoCh → Demand OB.
        Pine: ChBuLowest = ta.lowest(bar_index - LastMLL)
              CorrectBuIndex = ketma-ket eng past nuqtadan keyingi barlar soni
        """
        obs = []

        # Oxirgi Major Low pivot (MLL, MHL, ML)
        major_lows = [
            (t, v, idx) for t, v, idx in pivots
            if t in ("MLL", "MHL", "ML")
        ]
        if not major_lows:
            return obs

        main_pivot_idx = major_lows[-1][2]

        # Pine: ta.lowest(bar_index - LastMLL) — diapazon ichidagi eng past sham
        range_start = max(0, main_pivot_idx)
        range_end = min(event.bar_index, n)

        if range_end <= range_start:
            ob_idx = main_pivot_idx
        else:
            range_lows = lows[range_start:range_end]
            actual_lowest_offset = int(np.argmin(range_lows))
            ob_idx = range_start + actual_lowest_offset

        # ---- Main OB ----
        if 0 <= ob_idx < n:
            top, bottom = self._refine_zone(
                ob_type="demand",
                high=float(highs[ob_idx]),
                low=float(lows[ob_idx]),
                open_=float(opens[ob_idx]),
                close=float(closes[ob_idx]),
            )
            obs.append(OrderBlock(
                top=top, bottom=bottom, ob_type="demand",
                origin="ChoCh Main", level=event.level,
                bar_index=ob_idx, event_bar_index=event.bar_index,
                status="fresh",
                timestamp=ts[ob_idx] if ob_idx < len(ts) else None,
            ))

        # ---- Sub OB ----
        # Minor low pivotlar main va event orasida (Pine: BuMChSub_Trigger)
        sub_candidates = [
            (t, v, idx) for t, v, idx in pivots
            if t in ("mHL", "mLL", "MHL")
            and idx > main_pivot_idx
            and idx < event.bar_index
            and idx != ob_idx
        ]
        if sub_candidates:
            sub_idx = sub_candidates[-1][2]
            if 0 <= sub_idx < n:
                top, bottom = self._refine_zone(
                    ob_type="demand",
                    high=float(highs[sub_idx]),
                    low=float(lows[sub_idx]),
                    open_=float(opens[sub_idx]),
                    close=float(closes[sub_idx]),
                )
                obs.append(OrderBlock(
                    top=top, bottom=bottom, ob_type="demand",
                    origin="ChoCh Sub", level=event.level,
                    bar_index=sub_idx, event_bar_index=event.bar_index,
                    status="fresh",
                    timestamp=ts[sub_idx] if sub_idx < len(ts) else None,
                ))

        return obs

    def _supply_choch_obs(self, event, pivots, highs, lows, opens, closes, ts, n):
        """
        Bearish ChoCh → Supply OB.
        Pine: ChBeHighest = ta.highest(bar_index - LastMHH)
              CorrectBeIndex = ketma-ket eng yuqori nuqtadan keyingi barlar soni
        """
        obs = []

        # Oxirgi Major High pivot (MHH, MLH, MH)
        major_highs = [
            (t, v, idx) for t, v, idx in pivots
            if t in ("MHH", "MLH", "MH")
        ]
        if not major_highs:
            return obs

        main_pivot_idx = major_highs[-1][2]

        range_start = max(0, main_pivot_idx)
        range_end = min(event.bar_index, n)

        if range_end <= range_start:
            ob_idx = main_pivot_idx
        else:
            range_highs = highs[range_start:range_end]
            actual_highest_offset = int(np.argmax(range_highs))
            ob_idx = range_start + actual_highest_offset

        # ---- Main OB ----
        if 0 <= ob_idx < n:
            top, bottom = self._refine_zone(
                ob_type="supply",
                high=float(highs[ob_idx]),
                low=float(lows[ob_idx]),
                open_=float(opens[ob_idx]),
                close=float(closes[ob_idx]),
            )
            obs.append(OrderBlock(
                top=top, bottom=bottom, ob_type="supply",
                origin="ChoCh Main", level=event.level,
                bar_index=ob_idx, event_bar_index=event.bar_index,
                status="fresh",
                timestamp=ts[ob_idx] if ob_idx < len(ts) else None,
            ))

        # ---- Sub OB ----
        sub_candidates = [
            (t, v, idx) for t, v, idx in pivots
            if t in ("mLH", "mHH", "MLH")
            and idx > main_pivot_idx
            and idx < event.bar_index
            and idx != ob_idx
        ]
        if sub_candidates:
            sub_idx = sub_candidates[-1][2]
            if 0 <= sub_idx < n:
                top, bottom = self._refine_zone(
                    ob_type="supply",
                    high=float(highs[sub_idx]),
                    low=float(lows[sub_idx]),
                    open_=float(opens[sub_idx]),
                    close=float(closes[sub_idx]),
                )
                obs.append(OrderBlock(
                    top=top, bottom=bottom, ob_type="supply",
                    origin="ChoCh Sub", level=event.level,
                    bar_index=sub_idx, event_bar_index=event.bar_index,
                    status="fresh",
                    timestamp=ts[sub_idx] if sub_idx < len(ts) else None,
                ))

        return obs

    # ----------------------------------------------------------------
    # BoS Origin OB
    # Pine: BuMBoS_Trigger / BeMBoS_Trigger
    # ----------------------------------------------------------------

    def _bos_obs(
        self,
        event: StructureEvent,
        ob_type: str,
        pivots: list,
        highs: np.ndarray,
        lows: np.ndarray,
        opens: np.ndarray,
        closes: np.ndarray,
        timestamps: np.ndarray,
        n: int,
    ) -> List[OrderBlock]:
        """
        BoS hodisasi uchun Order Block yaratadi.

        Pine mantiq:
          Bullish BoS → oxirgi low pivot → eng past shamni topish → OB
          Bearish BoS → oxirgi high pivot → eng yuqori shamni topish → OB
        """
        obs: List[OrderBlock] = []

        if ob_type == "demand":
            # Pine: LastPivotType low turlarida (MHL, mHL, MLL, mLL)
            low_pivots = [
                (t, v, idx) for t, v, idx in pivots
                if t[1:] in ("HL", "LL", "L") and idx < event.bar_index
            ]
            if not low_pivots:
                return obs

            last_low_idx = low_pivots[-1][2]

            # Pine correction: eng past shamni aniqlash
            range_start = max(0, last_low_idx)
            range_end = min(event.bar_index, n)

            if range_end <= range_start:
                ob_idx = last_low_idx
            else:
                range_lows = lows[range_start:range_end]
                ob_idx = range_start + int(np.argmin(range_lows))

            if 0 <= ob_idx < n:
                top, bottom = self._refine_zone(
                    ob_type="demand",
                    high=float(highs[ob_idx]),
                    low=float(lows[ob_idx]),
                    open_=float(opens[ob_idx]),
                    close=float(closes[ob_idx]),
                )
                obs.append(OrderBlock(
                    top=top, bottom=bottom, ob_type="demand",
                    origin="BoS", level=event.level,
                    bar_index=ob_idx, event_bar_index=event.bar_index,
                    status="fresh",
                    timestamp=timestamps[ob_idx] if ob_idx < len(timestamps) else None,
                ))

        else:  # supply
            # Pine: LastPivotType high turlarida (MLH, mLH, MHH, mHH)
            high_pivots = [
                (t, v, idx) for t, v, idx in pivots
                if t[1:] in ("LH", "HH", "H") and idx < event.bar_index
            ]
            if not high_pivots:
                return obs

            last_high_idx = high_pivots[-1][2]

            range_start = max(0, last_high_idx)
            range_end = min(event.bar_index, n)

            if range_end <= range_start:
                ob_idx = last_high_idx
            else:
                range_highs = highs[range_start:range_end]
                ob_idx = range_start + int(np.argmax(range_highs))

            if 0 <= ob_idx < n:
                top, bottom = self._refine_zone(
                    ob_type="supply",
                    high=float(highs[ob_idx]),
                    low=float(lows[ob_idx]),
                    open_=float(opens[ob_idx]),
                    close=float(closes[ob_idx]),
                )
                obs.append(OrderBlock(
                    top=top, bottom=bottom, ob_type="supply",
                    origin="BoS", level=event.level,
                    bar_index=ob_idx, event_bar_index=event.bar_index,
                    status="fresh",
                    timestamp=timestamps[ob_idx] if ob_idx < len(timestamps) else None,
                ))

        return obs

    # ----------------------------------------------------------------
    # OB Refinement
    # Pine: Refiner.OBRefiner('Demand'/'Supply', 'On'/'Off', 'Defensive'/'Aggressive', ...)
    # ----------------------------------------------------------------

    def _refine_zone(
        self,
        ob_type: str,
        high: float,
        low: float,
        open_: float,
        close: float,
    ) -> Tuple[float, float]:
        """
        OB zonasini optimallashtiradi.

        Pine: Refiner.OBRefiner() — yopiq kutubxona, mantiq SMC nazariyasidan
        qayta yaratilgan:
          - Refine OFF : to'liq sham diapazoni (high → low)
          - Defensive  : tana diapazoni (body). Demand: max(O,C)→low.
                         Supply: high→min(O,C).
          - Aggressive : tor diapazon. Demand: min(O,C)→low (faqat pastki qism).
                         Supply: high→max(O,C) (faqat yuqori qism).
        """
        if not self.refine:
            return high, low

        if self.refine_method == "Defensive":
            if ob_type == "demand":
                # Demand Defensive: body qismini qo'shib, pastki wick'ni saqlaymiz
                return max(open_, close), low
            else:
                # Supply Defensive: body qismini qo'shib, yuqori wick'ni saqlaymiz
                return high, min(open_, close)

        elif self.refine_method == "Aggressive":
            if ob_type == "demand":
                # Demand Aggressive: faqat pastki qism (body edge → low)
                return min(open_, close), low
            else:
                # Supply Aggressive: faqat yuqori qism (high → body edge)
                return high, max(open_, close)

        return high, low

    # ----------------------------------------------------------------
    # Mitigation tekshiruvi
    # Pine: Drawing.OBDrawing() ichida box mitigatsiyasi
    # ----------------------------------------------------------------

    def _check_mitigation(
        self,
        ob: OrderBlock,
        highs: np.ndarray,
        lows: np.ndarray,
        current_bar: int,
    ) -> None:
        """
        OB mitigatsiya holatini tekshiradi.

        Mitigatsiya = narx OB zonasiga qaytib kelishi.
          Demand OB: narx pastga tushib OB zonasiga kirsa (low <= ob.top)
          Supply OB: narx yuqoriga ko'tarilib OB zonasiga kirsa (high >= ob.bottom)

        OB faqat event_bar_index'dan keyin mitigatsiya bo'lishi mumkin —
        chunki OB hodisa vaqtida "aktivlashadi".
        """
        # OB event'dan keyin tekshiramiz
        start = ob.event_bar_index + 1
        end = min(current_bar + 1, len(highs))

        if start >= end:
            return

        if ob.ob_type == "demand":
            # Demand OB: narx qaytib tushib zonaga tegsa → mitigated
            segment_lows = lows[start:end]
            if len(segment_lows) > 0 and np.min(segment_lows) <= ob.top:
                ob.status = "mitigated"
        else:
            # Supply OB: narx qaytib ko'tarilib zonaga tegsa → mitigated
            segment_highs = highs[start:end]
            if len(segment_highs) > 0 and np.max(segment_highs) >= ob.bottom:
                ob.status = "mitigated"


# ====================================================================
# FVG (Fair Value Gap) Detector
# ====================================================================

class FVGDetector:
    """
    Fair Value Gap (narx bo'shlig'i) detektori.

    Pine reference: FVG.FVGDetector() kutubxonasi.

    3 ta ketma-ket sham orasidagi gap:
      Demand FVG (bullish): low[i] > high[i-2]
        → gap = low[i] dan high[i-2] gacha (pastdan yuqoriga bo'shliq)
      Supply FVG (bearish): high[i] < low[i-2]
        → gap = low[i-2] dan high[i] gacha (yuqoridan pastga bo'shliq)

    Filter:
      gap_size / ATR nisbati bo'yicha filtrlash:
        Very Aggressive : nisbat > 0     (barcha FVG'lar)
        Aggressive      : nisbat > 0.10
        Defensive        : nisbat > 0.25
        Very Defensive   : nisbat > 0.50
    """

    # Pine: FVGFilterType parametrlari bo'yicha ATR nisbat chegaralari
    FILTER_THRESHOLDS = {
        "Very Aggressive": 0.0,
        "Aggressive": 0.10,
        "Defensive": 0.25,
        "Very Defensive": 0.50,
    }

    def __init__(self, config: dict):
        self.filter_enabled = config.get("fvg_filter", True)
        self.filter_type = config.get("fvg_filter_type", "Very Defensive")
        self.threshold = self.FILTER_THRESHOLDS.get(self.filter_type, 0.50)

    def detect(self, df: pd.DataFrame) -> List[FairValueGap]:
        """
        DataFrame'dan barcha FVG'larni aniqlaydi.

        Pine: FVG.FVGDetector(PFVGFilter ? 'On' : 'Off', PFVGFilterType,
              PShowDeFVG, PShowSuFVG)
        """
        n = len(df)
        if n < 3:
            return []

        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values

        # timestamp ustuni
        if "timestamp" in df.columns:
            timestamps = df["timestamp"].values
        elif "time" in df.columns:
            timestamps = df["time"].values
        else:
            timestamps = np.arange(n)

        # ATR(14) hisoblash (FVG filter uchun)
        atr = self._compute_atr(highs, lows, closes, period=14)

        fvgs: List[FairValueGap] = []

        for i in range(2, n):
            # ---- Demand FVG (Bullish) ----
            # Pine: low[0] > high[2] (Pine'da [0]=current, [2]=2 bar oldingi)
            # Python'da: lows[i] > highs[i-2]
            if lows[i] > highs[i - 2]:
                gap_top = float(lows[i])
                gap_bottom = float(highs[i - 2])
                gap_size = gap_top - gap_bottom

                if self._passes_filter(gap_size, atr[i] if i < len(atr) else 0):
                    fvg = FairValueGap(
                        top=gap_top,
                        bottom=gap_bottom,
                        fvg_type="demand",
                        bar_index=i - 1,  # o'rta sham
                        gap_size=gap_size,
                        timestamp=timestamps[i - 1] if i - 1 < len(timestamps) else None,
                    )
                    # FVG to'ldirilganligini tekshirish
                    self._check_fill(fvg, highs, lows, i, n)
                    fvgs.append(fvg)

            # ---- Supply FVG (Bearish) ----
            # Pine: high[0] < low[2]
            # Python'da: highs[i] < lows[i-2]
            if highs[i] < lows[i - 2]:
                gap_top = float(lows[i - 2])
                gap_bottom = float(highs[i])
                gap_size = gap_top - gap_bottom

                if self._passes_filter(gap_size, atr[i] if i < len(atr) else 0):
                    fvg = FairValueGap(
                        top=gap_top,
                        bottom=gap_bottom,
                        fvg_type="supply",
                        bar_index=i - 1,  # o'rta sham
                        gap_size=gap_size,
                        timestamp=timestamps[i - 1] if i - 1 < len(timestamps) else None,
                    )
                    self._check_fill(fvg, highs, lows, i, n)
                    fvgs.append(fvg)

        return fvgs

    def _passes_filter(self, gap_size: float, atr_value: float) -> bool:
        """FVG filtri — gap kengligi / ATR nisbatini tekshiradi."""
        if not self.filter_enabled:
            return True
        if atr_value <= 0:
            return gap_size > 0
        ratio = gap_size / atr_value
        return ratio > self.threshold

    def _check_fill(
        self,
        fvg: FairValueGap,
        highs: np.ndarray,
        lows: np.ndarray,
        creation_bar: int,
        n: int,
    ) -> None:
        """FVG to'ldirilganligini tekshiradi (narx gap ichiga kirganmi)."""
        start = creation_bar + 1
        if start >= n:
            return

        if fvg.fvg_type == "demand":
            # Demand FVG to'ldiriladi agar narx pastga tushib gap'ga kirsa
            segment_lows = lows[start:n]
            if len(segment_lows) > 0 and np.min(segment_lows) <= fvg.top:
                fvg.status = "filled"
        else:
            # Supply FVG to'ldiriladi agar narx yuqoriga ko'tarilib gap'ga kirsa
            segment_highs = highs[start:n]
            if len(segment_highs) > 0 and np.max(segment_highs) >= fvg.bottom:
                fvg.status = "filled"

    @staticmethod
    def _compute_atr(
        highs: np.ndarray,
        lows: np.ndarray,
        closes: np.ndarray,
        period: int = 14,
    ) -> np.ndarray:
        """
        ATR (Average True Range) hisoblash.
        Pine: ta.atr(55) — bizda 14 periodli ATR ishlatamiz.
        """
        n = len(highs)
        tr = np.zeros(n)
        tr[0] = highs[0] - lows[0]

        for i in range(1, n):
            tr[i] = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )

        # Simple Moving Average of TR
        atr = np.zeros(n)
        if n >= period:
            atr[period - 1] = np.mean(tr[:period])
            for i in range(period, n):
                atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
        else:
            atr[:] = np.mean(tr) if n > 0 else 0

        return atr


# ====================================================================
# Liquidity Detector
# ====================================================================

class LiquidityDetector:
    """
    Likvidlik darajalarini aniqlaydi — narx bir necha marta tegib qaytgan
    nuqtalar, ularning ortida stop-loss'lar yig'ilgan bo'lishi mumkin.

    Pine reference: Liq.LLF(SPP, DPP, SLLS, DLLS, ...) kutubxonasi.

    Statik (Static): katta period (SPP=8) bilan aniqlangan, uzoq muddatli
                      likvidlik darajalari.
    Dinamik (Dynamic): kichik period (DPP=3) bilan aniqlangan, qisqa muddatli
                        likvidlik darajalari.

    Sensitivity: bir-biriga yaqin pivot'lar guruhlashtiriladi.
      SLLS=0.30 → narx diapazonining 0.30% ichidagi pivot'lar bitta daraja
      DLLS=1.00 → narx diapazonining 1.00% ichidagi pivot'lar bitta daraja
    """

    def __init__(self, config: dict):
        # Pine: SPP, DPP
        self.static_period = config.get("static_pivot_period", 8)
        self.dynamic_period = config.get("dynamic_pivot_period", 3)
        # Pine: SLLS, DLLS
        self.static_sensitivity = config.get("static_liquidity_sensitivity", 0.30)
        self.dynamic_sensitivity = config.get("dynamic_liquidity_sensitivity", 1.00)

    def detect(self, df: pd.DataFrame) -> Dict[str, Optional[float]]:
        """
        Statik va dinamik likvidlik darajalarini qaytaradi.

        Pine: Liq.LLF(SPP, DPP, SLLS, DLLS, ShowSHLL, ShowSLLL, ShowDHLL, ShowDLLL)

        Return format:
          {
            "static_high": float | None,
            "static_low": float | None,
            "dynamic_high": float | None,
            "dynamic_low": float | None,
          }
        """
        highs = df["high"].values
        lows = df["low"].values
        n = len(highs)

        result = {
            "static_high": None,
            "static_low": None,
            "dynamic_high": None,
            "dynamic_low": None,
        }

        if n < 3:
            return result

        # ---- Statik likvidlik (uzoq muddatli) ----
        s_highs, s_lows = self._find_pivot_levels(
            highs, lows, self.static_period
        )
        if s_highs:
            result["static_high"] = self._find_liquidity_level(
                s_highs, self.static_sensitivity, highs, lows
            )
        if s_lows:
            result["static_low"] = self._find_liquidity_level(
                s_lows, self.static_sensitivity, highs, lows, is_high=False
            )

        # ---- Dinamik likvidlik (qisqa muddatli) ----
        d_highs, d_lows = self._find_pivot_levels(
            highs, lows, self.dynamic_period
        )
        if d_highs:
            result["dynamic_high"] = self._find_liquidity_level(
                d_highs, self.dynamic_sensitivity, highs, lows
            )
        if d_lows:
            result["dynamic_low"] = self._find_liquidity_level(
                d_lows, self.dynamic_sensitivity, highs, lows, is_high=False
            )

        return result

    def _find_pivot_levels(
        self,
        highs: np.ndarray,
        lows: np.ndarray,
        period: int,
    ) -> Tuple[List[float], List[float]]:
        """
        Berilgan period bilan pivot high/low narxlarini topadi.
        Pine: ta.pivothigh(period, period) / ta.pivotlow(period, period)
        """
        n = len(highs)
        pivot_highs: List[float] = []
        pivot_lows: List[float] = []

        for i in range(period, n - period):
            # Pivot High
            window_h = highs[i - period: i + period + 1]
            if highs[i] == np.max(window_h):
                pivot_highs.append(float(highs[i]))

            # Pivot Low
            window_l = lows[i - period: i + period + 1]
            if lows[i] == np.min(window_l):
                pivot_lows.append(float(lows[i]))

        return pivot_highs, pivot_lows

    def _find_liquidity_level(
        self,
        pivot_values: List[float],
        sensitivity: float,
        highs: np.ndarray,
        lows: np.ndarray,
        is_high: bool = True,
    ) -> Optional[float]:
        """
        Bir-biriga yaqin (sensitivity ichida) pivot'larni guruhlaydi
        va eng ko'p tegishli darajani qaytaradi.

        Pine: SLLS / DLLS sensitivity parametrlari.
        """
        if not pivot_values:
            return None

        # Narx diapazoni
        price_range = float(np.max(highs) - np.min(lows))
        if price_range <= 0:
            return pivot_values[-1] if pivot_values else None

        # Sensitivity chegarasi
        threshold = price_range * sensitivity / 100.0

        # Pivot'larni guruhlash
        groups: List[List[float]] = []
        sorted_pivots = sorted(pivot_values)

        current_group: List[float] = [sorted_pivots[0]]
        for i in range(1, len(sorted_pivots)):
            if sorted_pivots[i] - sorted_pivots[i - 1] <= threshold:
                current_group.append(sorted_pivots[i])
            else:
                groups.append(current_group)
                current_group = [sorted_pivots[i]]
        groups.append(current_group)

        if not groups:
            return pivot_values[-1] if pivot_values else None

        # Eng ko'p a'zoli guruhni topish (eng kuchli likvidlik)
        best_group = max(groups, key=len)

        # Guruh o'rtacha qiymatini qaytarish
        if is_high:
            return round(max(best_group), 5)
        else:
            return round(min(best_group), 5)


# ====================================================================
# Orchestrator — Yagona entry point
# ====================================================================

def analyze_market_structure(
    df: pd.DataFrame,
    config: Optional[dict] = None,
) -> dict:
    """
    Bozor strukturasini to'liq tahlil qiladi va JSON-mos dict qaytaradi.

    Bu funksiya barcha detektorlarni tartib bilan ishga tushiradi:
      1. SMCStructure → Pivot/ZigZag/BoS/ChoCh
      2. OrderBlockDetector → OB'lar
      3. FVGDetector → FVG'lar
      4. LiquidityDetector → Likvidlik darajalari

    Parameters:
      df : pd.DataFrame
          Columns = [timestamp, open, high, low, close, volume]
          volume ixtiyoriy. Har qanday timeframe bilan ishlaydi.
      config : dict, optional
          Parametrlar (DEFAULT_CONFIG ga merge qilinadi).

    Returns:
      dict — quyidagi formatda:
      {
        "current_price": float,
        "trend": {"external": "Up Trend"|"Down Trend"|"No Trend",
                  "internal": "Up Trend"|"Down Trend"|"No Trend"},
        "last_bos": {...} | None,
        "last_choch": {...} | None,
        "order_blocks": {"demand": [...], "supply": [...]},
        "fvg": {"demand": [...], "supply": [...]},
        "liquidity": {"static_high": float, ...}
      }
    """
    # ---- Config ----
    cfg = {**DEFAULT_CONFIG}
    if config:
        cfg.update(config)

    # ---- DataFrame validatsiyasi ----
    required_cols = {"open", "high", "low", "close"}
    actual_cols = set(df.columns.str.lower())
    missing = required_cols - actual_cols
    if missing:
        raise ValueError(
            f"DataFrame'da quyidagi ustunlar yo'q: {missing}. "
            f"Kerakli ustunlar: timestamp, open, high, low, close"
        )

    # Ustun nomlarini kichik harfga o'tkazish (agar kerak bo'lsa)
    df = df.copy()
    df.columns = df.columns.str.lower()

    n = len(df)
    if n < 3:
        return _empty_result()

    # ---- 1. SMC Structure (Pivot/ZigZag/BoS/ChoCh) ----
    # Pine: PP parametri bilan SMCStructure
    smc = SMCStructure(pivot_period=cfg["pivot_period"])
    smc.run(
        df["high"].tolist(),
        df["low"].tolist(),
        df["close"].tolist(),
    )

    # ---- 2. Order Blocks ----
    ob_detector = OrderBlockDetector(cfg)
    order_blocks = ob_detector.detect(df, smc, smc.events)

    # ---- 3. FVG ----
    fvg_detector = FVGDetector(cfg)
    fvgs = fvg_detector.detect(df)

    # ---- 4. Liquidity ----
    liq_detector = LiquidityDetector(cfg)
    liquidity = liq_detector.detect(df)

    # ---- Natijani shakllantirish ----
    current_price = float(df["close"].iloc[-1])

    # Oxirgi BoS va ChoCh topish
    last_bos = _find_last_event(smc.events, "BoS")
    last_choch = _find_last_event(smc.events, "ChoCh")

    # OB'larni demand/supply bo'yicha ajratish
    demand_obs = [ob.to_dict() for ob in order_blocks if ob.ob_type == "demand"]
    supply_obs = [ob.to_dict() for ob in order_blocks if ob.ob_type == "supply"]

    # FVG'larni demand/supply bo'yicha ajratish
    demand_fvgs = [fvg.to_dict() for fvg in fvgs if fvg.fvg_type == "demand"]
    supply_fvgs = [fvg.to_dict() for fvg in fvgs if fvg.fvg_type == "supply"]

    return {
        "current_price": round(current_price, 5),
        "trend": {
            "external": smc.external_trend,
            "internal": smc.internal_trend,
        },
        "last_bos": _format_event(last_bos),
        "last_choch": _format_event(last_choch),
        "order_blocks": {
            "demand": demand_obs,
            "supply": supply_obs,
        },
        "fvg": {
            "demand": demand_fvgs,
            "supply": supply_fvgs,
        },
        "liquidity": liquidity,
        "summary": {
            "total_events": len(smc.events),
            "total_obs": len(order_blocks),
            "fresh_obs": sum(1 for ob in order_blocks if ob.status == "fresh"),
            "total_fvgs": len(fvgs),
            "fresh_fvgs": sum(1 for fvg in fvgs if fvg.status == "fresh"),
        },
    }


# ====================================================================
# Yordamchi funksiyalar
# ====================================================================

def _find_last_event(
    events: List[StructureEvent],
    kind: str,
) -> Optional[StructureEvent]:
    """Hodisalar ro'yxatidan oxirgi BoS yoki ChoCh'ni topadi."""
    for event in reversed(events):
        if event.kind == kind:
            return event
    return None


def _format_event(event: Optional[StructureEvent]) -> Optional[dict]:
    """StructureEvent'ni dict formatiga o'tkazadi."""
    if event is None:
        return None
    return {
        "type": event.direction,
        "level": event.level,
        "kind": event.kind,
        "price": round(event.price, 5),
        "bar_index": event.bar_index,
    }


def _empty_result() -> dict:
    """Ma'lumot yetarli bo'lmaganda bo'sh natija."""
    return {
        "current_price": 0.0,
        "trend": {"external": "No Trend", "internal": "No Trend"},
        "last_bos": None,
        "last_choch": None,
        "order_blocks": {"demand": [], "supply": []},
        "fvg": {"demand": [], "supply": []},
        "liquidity": {
            "static_high": None, "static_low": None,
            "dynamic_high": None, "dynamic_low": None,
        },
        "summary": {
            "total_events": 0, "total_obs": 0, "fresh_obs": 0,
            "total_fvgs": 0, "fresh_fvgs": 0,
        },
    }
