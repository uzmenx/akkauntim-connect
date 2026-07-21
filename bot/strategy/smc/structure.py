"""
smc_structure.py
=================
Python translation of the SWING-STRUCTURE engine inside the Pine Script
indicator "Smart Money Concept [TradingFinder] Major Minor OB + FVG"
(chartda "SMC TFlab" nomi bilan ko'ringan indikator).

QAMROV (1-bosqich, bugungi ish):
  1) Pivot detection            -> ta.pivothigh(PP,PP) / ta.pivotlow(PP,PP)
  2) ZigZag klassifikatsiya      -> H / L / HH / HL / LH / LL
  3) Advance (M/m) massiv        -> "tasdiqlangan" sving nuqtalar
  4) Major / Minor daraja        -> tashqi (katta) va ichki (kichik) struktura
  5) BoS / ChoCh detektor        -> Bullish/Bearish, Major/Minor

QAMROVGA KIRMAGAN (keyingi bosqichlar):
  Order Block box chizish, FVG, Liquidity chiziqlari, Alert matn formatlash —
  bular TFlab'ning yopiq (private) kutubxonalariga (OrderBlockRefiner,
  FVGDetectorLibrary, LiquidityFinderLibrary) tayanadi, manba kodi bizda yo'q.

MUHIM — HALOLLIK BILAN AYTAMAN:
Bu ~350 qatorli, holatga bog'liq (stateful), massiv tarixiga (`[1]`) tayanadigan
Pine Script kodining qo'lda tarjimasi. Men uni juda ehtiyotkorlik bilan,
qator-baqator kuzatib chiqdim, lekin Pine Script'ni o'zim ishga tushirib
tekshira olmayman — shuning uchun 100% bit-baqar bir xil natija berishiga
kafolat bera olmayman. Ishonch darajasi bo'yicha:
  - Pivot detection (1-qism)         -> yuqori ishonch, mexanik logika
  - ZigZag klassifikatsiya (2-qism)  -> yuqori ishonch, diqqat bilan tekshirildi
  - Advance/Major/Minor (3-4-qism)   -> o'rta ishonch, eng zich mantiq shu yerda
  - BoS/ChoCh (5-qism)               -> yuqori qismlarga bog'liq, ular to'g'ri
                                         bo'lsa bu qism ham to'g'ri chiqadi

order_manager.py'ga ulashdan OLDIN validate_smc.py orqali haqiqiy MT5
tarixi bilan ishga tushirib, chiqqan BoS/ChoCh vaqtlarini TradingView
chartingdagi jonli "SMC TFlab" indikatori bilan ko'zdan kechirib solishtir.
"""

from dataclasses import dataclass, field
from typing import Optional, Literal


HIGH_TYPES = {"H", "HH", "LH"}
LOW_TYPES = {"L", "HL", "LL"}


# ---------------------------------------------------------------------
# 1) Pivot detection  (ta.pivothigh(PP,PP) / ta.pivotlow(PP,PP))
# ---------------------------------------------------------------------

def compute_pivot_events(high: list, low: list, pp: int):
    """
    Confirmatsiya bar indeksi bo'yicha kalitlangan lug'atlarni qaytaradi
    (aynan Pine'dagi `ta.valuewhen(HighPivot, High[PP], 0)` /
    `ta.valuewhen(HighPivot, Bar_Index[PP], 0)` singari):
        high_events[i] = (pivot_narxi, original_bar_index)
        low_events[i]  = (pivot_narxi, original_bar_index)

    `p` bar'idagi pivot faqat `pp` bar keyin, ya'ni `i = p + pp`'da
    "tasdiqlanadi" — chunki tasdiqlash uchun keyingi pp ta bar kerak.
    """
    n = len(high)
    high_events, low_events = {}, {}
    for p in range(pp, n - pp):
        window_h = high[p - pp: p + pp + 1]
        if high[p] == max(window_h):
            ci = p + pp
            if ci < n:
                high_events[ci] = (high[p], p)
        window_l = low[p - pp: p + pp + 1]
        if low[p] == min(window_l):
            ci = p + pp
            if ci < n:
                low_events[ci] = (low[p], p)
    return high_events, low_events


@dataclass
class StructureEvent:
    bar_index: int
    level: str        # 'Major' | 'Minor'
    kind: str          # 'BoS' | 'ChoCh'
    direction: str      # 'Bullish' | 'Bearish'
    price: float

    def __repr__(self):
        return f"[{self.bar_index}] {self.level} {self.direction} {self.kind} @ {self.price:.5f}"


@dataclass
class SwingPoint:
    bar_index: int
    raw_type: str       # 'H','L','HH','HL','LH','LL'
    adv_type: str        # 'MHH','mLL', ... (M=Major, m=minor, before promotion)
    value: float

    def __repr__(self):
        return f"[{self.bar_index}] {self.adv_type} @ {self.value:.5f}"


class SMCStructure:
    """
    Bitta instance = bitta symbol/timeframe.
    `.run(high, low, close)` chaqir -> `.events` (BoS/ChoCh) va
    `.swings` (har bir sving nuqtasi tarixi) to'ladi.
    """

    def __init__(self, pivot_period: int = 5):
        self.pp = pivot_period

        # raw zigzag  (ArrayType / ArrayValue / ArrayIndex)
        self.zz_type: list = []
        self.zz_value: list = []
        self.zz_index: list = []

        # advance array  (ArrayTypeAdv / ArrayValueAdv / ArrayIndexAdv)
        self.adv_type: list = []
        self.adv_value: list = []
        self.adv_index: list = []

        # persistent "oxirgi ma'lum" pivot qiymatlari (ta.valuewhen singari —
        # LowPivot ushbu barda yonmasa ham, oldingi tasdiqlangan qiymatini saqlaydi)
        self._hv = self._hi = None   # last known High pivot value/index
        self._lv = self._li = None   # last known Low pivot value/index

        # Major / Minor darajalar
        self.major_high = self.major_low = None
        self.major_high_idx = self.major_low_idx = None
        self.minor_high = self.minor_low = None
        self.minor_high_idx = self.minor_low_idx = None
        self._minor_locked = False

        self.external_trend = "No Trend"   # Major trend
        self.internal_trend = "No Trend"   # Minor trend
        self._lock_break_major = None
        self._lock_break_minor = None

        # ta.crossover(close, level) uchun oldingi bar holatini saqlash
        self._prev_close = None
        self._prev_major_high = None
        self._prev_major_low = None
        self._prev_minor_high = None
        self._prev_minor_low = None

        self.events: list[StructureEvent] = []
        self.swings: list[SwingPoint] = []

        # har bar uchun snapshot (keyinchalik AI kontekstiga yoki grafikka
        # chizish uchun qulay) — bar_index -> dict
        self.trend_history: dict[int, dict] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, high: list, low: list, close: list):
        assert len(high) == len(low) == len(close), "high/low/close uzunligi bir xil bo'lishi kerak"
        high_events, low_events = compute_pivot_events(high, low, self.pp)
        for i in range(len(close)):
            hp = high_events.get(i)
            lp = low_events.get(i)
            self._step(i, close[i], hp, lp)
        return self.events

    def latest_context(self) -> dict:
        """AI qaror qatlamiga (ai_analysis.py) uzatish uchun qulay xulosa."""
        return {
            "external_trend": self.external_trend,
            "internal_trend": self.internal_trend,
            "major_high": self.major_high,
            "major_low": self.major_low,
            "minor_high": self.minor_high,
            "minor_low": self.minor_low,
            "last_events": [repr(e) for e in self.events[-5:]],
        }

    # ------------------------------------------------------------------
    # Bitta bar
    # ------------------------------------------------------------------

    def _step(self, i: int, close: float, hp, lp):
        if hp is not None:
            self._hv, self._hi = hp
        if lp is not None:
            self._lv, self._li = lp

        if hp is not None and lp is not None:
            self._dual_pivot(close)
        elif hp is not None:
            self._single_pivot("H", close)
        elif lp is not None:
            self._single_pivot("L", close)

        self._major_minor_step(close)
        self._bos_choch_step(i, close)

        self._prev_close = close
        self._prev_major_high, self._prev_major_low = self.major_high, self.major_low
        self._prev_minor_high, self._prev_minor_low = self.minor_high, self.minor_low

        self.trend_history[i] = {
            "external_trend": self.external_trend,
            "internal_trend": self.internal_trend,
            "major_high": self.major_high,
            "major_low": self.major_low,
        }

    # ------------------------------------------------------------------
    # 2-qism — ZigZag (H/L/HH/HL/LH/LL)
    # ------------------------------------------------------------------

    def _push_zz(self, kind: str, value: float, index: int, replace: bool):
        if replace:
            self.zz_type.pop(); self.zz_value.pop(); self.zz_index.pop()

        if len(self.zz_value) > 2:
            prevprev = self.zz_value[-2]
            if kind == "H":
                t = "HH" if prevprev < value else "LH"
            else:
                t = "HL" if prevprev < value else "LL"
        else:
            t = kind

        grew = not replace
        self.zz_type.append(t); self.zz_value.append(value); self.zz_index.append(index)
        self._promote_advance(grew)
        self.swings.append(SwingPoint(index, t, self.adv_type[-1] if self.adv_type else t, value))

    def _single_pivot(self, kind: str, close: float):
        if kind == "H":
            value, index = self._hv, self._hi
        else:
            value, index = self._lv, self._li

        if not self.zz_type:
            self._push_zz(kind, value, index, replace=False)
            return

        last = self.zz_type[-1]
        last_value = self.zz_value[-1]

        if kind == "H":
            if last in LOW_TYPES:
                if self._hv > last_value:
                    self._push_zz("H", self._hv, self._hi, replace=False)
                elif self._hv < last_value:
                    self._push_zz("L", self._lv, self._li, replace=True)
            elif last in HIGH_TYPES:
                if last_value < self._hv:
                    self._push_zz("H", self._hv, self._hi, replace=True)
                # aks holda: hech narsa qilinmaydi (yangi pivot kutilayotgan
                # yuqoridan baland emas)
        else:  # kind == "L"
            if last in HIGH_TYPES:
                if self._lv < last_value:
                    self._push_zz("L", self._lv, self._li, replace=False)
                elif self._lv > last_value:
                    self._push_zz("H", self._hv, self._hi, replace=True)
            elif last in LOW_TYPES:
                if last_value > self._lv:
                    self._push_zz("L", self._lv, self._li, replace=True)

    def _dual_pivot(self, close: float):
        """Bir vaqtning o'zida ham High ham Low pivot tasdiqlangan (kam
        uchraydigan holat — juda tor range/doji-ga o'xshash bar uchun)."""
        if not self.zz_type:
            return  # Pine'da PASS := 1, hech narsa o'zgarmaydi

        last = self.zz_type[-1]
        last_value = self.zz_value[-1]

        if last in ("L", "LL"):
            if self._lv < last_value:
                self._push_zz("L", self._lv, self._li, replace=True)
            else:
                self._push_zz("H", self._hv, self._hi, replace=False)
        elif last in ("H", "HH"):
            if self._hv > last_value:
                self._push_zz("H", self._hv, self._hi, replace=True)
            else:
                self._push_zz("L", self._lv, self._li, replace=False)
        elif last == "LH":
            if self._hv < last_value:
                self._push_zz("L", self._lv, self._li, replace=False)
            elif self._hv > last_value:
                if close < last_value:
                    self._push_zz("H", self._hv, self._hi, replace=True)
                elif close > last_value:
                    self._push_zz("L", self._lv, self._li, replace=False)
        elif last == "HL":
            if self._lv > last_value:
                self._push_zz("H", self._hv, self._hi, replace=False)
            elif self._lv < last_value:
                if close > last_value:
                    self._push_zz("L", self._lv, self._li, replace=True)
                elif close < last_value:
                    self._push_zz("H", self._hv, self._hi, replace=False)

    # ------------------------------------------------------------------
    # 3-qism — Advance massiv (M/m tasdiqlash)
    # ------------------------------------------------------------------

    def _promote_advance(self, grew: bool):
        n = len(self.zz_value)
        if n == 1:
            self.adv_type.append("M" + self.zz_type[0])
            self.adv_value.append(self.zz_value[0])
            self.adv_index.append(self.zz_index[0])
            return
        if n == 2 and len(self.adv_value) == 1:
            self.adv_type.append("M" + self.zz_type[1])
            self.adv_value.append(self.zz_value[1])
            self.adv_index.append(self.zz_index[1])
            return
        if not self.adv_value:
            return
        if grew:
            self.adv_type.append("m" + self.zz_type[-1])
            self.adv_value.append(self.zz_value[-1])
            self.adv_index.append(self.zz_index[-1])
        else:
            # xuddi shu sving davomi — yangi nuqta emas, oxirgisini yangilaymiz
            self.adv_value[-1] = self.zz_value[-1]
            self.adv_index[-1] = self.zz_index[-1]
            prefix = self.adv_type[-1][0]  # 'M' yoki 'm' saqlanadi
            self.adv_type[-1] = prefix + self.zz_type[-1]

    # ------------------------------------------------------------------
    # 4-qism — Major / Minor daraja detektori
    # ------------------------------------------------------------------

    def _promote_at(self, pos: int, close: float, is_high: bool):
        """adv_type[pos]'ni 'M...' ga ko'taradi, mos zz_type bilan qayta
        belgilaydi, va Major_High/Low darajasini yangilaydi."""
        raw = self.zz_type[-1] if pos == -1 else self.zz_type[-2] if pos == -2 else None
        if raw is None:
            return
        self.adv_type[pos] = "M" + raw
        if is_high:
            self.major_high = self.adv_value[pos]
            self.major_high_idx = self.adv_index[pos]
        else:
            self.major_low = self.adv_value[pos]
            self.major_low_idx = self.adv_index[pos]

    def _major_minor_step(self, close: float):
        if len(self.adv_value) <= 1:
            # birinchi ikkita nuqta bootstrap paytida Major_High/Low hali
            # to'liq belgilanmagan bo'lishi mumkin — birinchi nuqta kelganda
            # boshlang'ich qiymat sifatida olamiz
            if len(self.adv_value) == 1:
                if self.adv_type[0].endswith(("H", "HH", "LH")):
                    self.major_high = self.adv_value[0]; self.major_high_idx = self.adv_index[0]
                else:
                    self.major_low = self.adv_value[0]; self.major_low_idx = self.adv_index[0]
            return

        last_t, last_v = self.adv_type[-1], self.adv_value[-1]

        # ---- High Major Detector ----
        if self.major_high is not None and close > self.major_high:
            if last_t == "mL":
                self._promote_at(-1, close, is_high=False)
            elif last_t in ("mHL", "mLL"):
                self._promote_at(-1, close, is_high=False)
            elif last_t in ("mLH", "mHH", "MLH", "MHH") and len(self.adv_type) > 1:
                if self.adv_type[-2] in ("mHL", "mLL"):
                    self._promote_at(-2, close, is_high=False)

        if self.major_high is not None and last_v > self.major_high:
            if last_t == "mH":
                self._promote_at(-1, close, is_high=True)
            elif last_t == "mLH":
                self._promote_at(-1, close, is_high=True)
            elif last_t in ("mHH", "MHH"):
                self._promote_at(-1, close, is_high=True)

        # ---- Low Major Detector ----
        if self.major_low is not None and close < self.major_low:
            if last_t == "mH":
                self._promote_at(-1, close, is_high=True)
            elif last_t == "mLH":
                self._promote_at(-1, close, is_high=True)
            elif last_t in ("mHH",):
                self._promote_at(-1, close, is_high=True)
            elif last_t in ("mHL", "mLL", "MHL", "MLL") and len(self.adv_type) > 1:
                if self.adv_type[-2] in ("mLH", "mHH"):
                    self._promote_at(-2, close, is_high=True)

        if self.major_low is not None and last_v < self.major_low:
            if last_t == "mL":
                self._promote_at(-1, close, is_high=False)
            elif last_t == "mHL":
                self._promote_at(-1, close, is_high=False)
            elif last_t in ("mLL", "MLL"):
                self._promote_at(-1, close, is_high=False)

        # ---- Minor daraja (Major ichidagi kichik struktura) ----
        if len(self.adv_type) > 2:
            self._minor_locked = True
            a, b, c = self.adv_type[-1], self.adv_type[-2], self.adv_type[-3]
            if a.startswith("m") and b.startswith("m") and c.startswith("M"):
                if a[1:] in ("H", "HH", "LH"):
                    self.minor_high, self.minor_high_idx = self.adv_value[-1], self.adv_index[-1]
                    self.minor_low, self.minor_low_idx = self.adv_value[-2], self.adv_index[-2]
                else:
                    self.minor_high, self.minor_high_idx = self.adv_value[-2], self.adv_index[-2]
                    self.minor_low, self.minor_low_idx = self.adv_value[-1], self.adv_index[-1]

            if self._minor_locked and self.minor_high is not None:
                if close > self.minor_high:
                    if last_t == "mHL":
                        self.minor_low, self.minor_low_idx = last_v, self.adv_index[-1]
                    elif last_t == "mLL":
                        self.minor_low, self.minor_low_idx = last_v, self.adv_index[-1]
                if last_v > self.minor_high:
                    if last_t == "mLH" and len(self.adv_value) > 1:
                        self.minor_high, self.minor_high_idx = last_v, self.adv_index[-1]
                        self.minor_low, self.minor_low_idx = self.adv_value[-2], self.adv_index[-2]
                    elif last_t == "mHH" and len(self.adv_value) > 1:
                        self.minor_high, self.minor_high_idx = last_v, self.adv_index[-1]
                        self.minor_low, self.minor_low_idx = self.adv_value[-2], self.adv_index[-2]
                if self.minor_low is not None and close < self.minor_low:
                    if last_t == "mLH":
                        self.minor_high, self.minor_high_idx = last_v, self.adv_index[-1]
                    elif last_t == "mHH":
                        self.minor_high, self.minor_high_idx = last_v, self.adv_index[-1]
                if self.minor_low is not None and last_v < self.minor_low:
                    if last_t == "mHL" and len(self.adv_value) > 1:
                        self.minor_low, self.minor_low_idx = last_v, self.adv_index[-1]
                        self.minor_high, self.minor_high_idx = self.adv_value[-2], self.adv_index[-2]
                    elif last_t == "mLL" and len(self.adv_value) > 1:
                        self.minor_low, self.minor_low_idx = last_v, self.adv_index[-1]
                        self.minor_high, self.minor_high_idx = self.adv_value[-2], self.adv_index[-2]

            # Minor darajani reset qilish — oxirgi nuqta Major bo'lib qolsa
            if self.adv_type[-1].startswith("M"):
                self._minor_locked = False
                self.minor_high = self.minor_low = None
                self.minor_high_idx = self.minor_low_idx = None
                self.internal_trend = "No Trend"

    # ------------------------------------------------------------------
    # 5-qism — BoS / ChoCh detektor
    # ------------------------------------------------------------------

    @staticmethod
    def _crossover(prev_close, prev_level, close, level):
        if prev_close is None or prev_level is None or level is None:
            return False
        return prev_close <= prev_level and close > level

    @staticmethod
    def _crossunder(prev_close, prev_level, close, level):
        if prev_close is None or prev_level is None or level is None:
            return False
        return prev_close >= prev_level and close < level

    def _bos_choch_step(self, i: int, close: float):
        # ---- Major (tashqi) ----
        if self._crossover(self._prev_close, self._prev_major_high, close, self.major_high) \
                and self._lock_break_major != self.major_high_idx:
            if self.external_trend in ("No Trend", "Up Trend"):
                self.external_trend = "Up Trend"
                self.events.append(StructureEvent(i, "Major", "BoS", "Bullish", close))
            else:
                self.external_trend = "Up Trend"
                self.events.append(StructureEvent(i, "Major", "ChoCh", "Bullish", close))
            self._lock_break_major = self.major_high_idx

        if self._crossunder(self._prev_close, self._prev_major_low, close, self.major_low) \
                and self._lock_break_major != self.major_low_idx:
            if self.external_trend in ("No Trend", "Down Trend"):
                self.external_trend = "Down Trend"
                self.events.append(StructureEvent(i, "Major", "BoS", "Bearish", close))
            else:
                self.external_trend = "Down Trend"
                self.events.append(StructureEvent(i, "Major", "ChoCh", "Bearish", close))
            self._lock_break_major = self.major_low_idx

        # ---- Minor (ichki) — manba darajaga asoslangan (crossover EMAS) ----
        if self.minor_high is not None and close > self.minor_high \
                and self._lock_break_minor != self.minor_high_idx:
            if self.internal_trend in ("No Trend", "Up Trend"):
                self.internal_trend = "Up Trend"
                self.events.append(StructureEvent(i, "Minor", "BoS", "Bullish", close))
            else:
                self.internal_trend = "Up Trend"
                self.events.append(StructureEvent(i, "Minor", "ChoCh", "Bullish", close))
            self._lock_break_minor = self.minor_high_idx

        if self.minor_low is not None and close < self.minor_low \
                and self._lock_break_minor != self.minor_low_idx:
            if self.internal_trend in ("No Trend", "Down Trend"):
                self.internal_trend = "Down Trend"
                self.events.append(StructureEvent(i, "Minor", "BoS", "Bearish", close))
            else:
                self.internal_trend = "Down Trend"
                self.events.append(StructureEvent(i, "Minor", "ChoCh", "Bearish", close))
            self._lock_break_minor = self.minor_low_idx
