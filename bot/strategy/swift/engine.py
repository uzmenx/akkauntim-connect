"""
bot/strategy/swift/engine.py
============================
SWIFT ALGO (Pine Script v5) -> Python (pandas) konvertatsiyasi.
Original: "SWIFT ALGO" by traderschatroom88 (MPL 2.0).

Bot uchun integratsiya nuqtalari:
  * analyze_swift(df, ...) -> dict          (strategiya tahlili)
  * to_voting_signal(result) -> dict        (PortfolioManager voting formati)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


# -----------------------------------------------------------------------------
# 1) INPUTS
# -----------------------------------------------------------------------------
@dataclass
class Config:
    # === NON REPAINT ===
    res: str = "15"
    use_res: bool = True
    int_res: int = 8

    # === MA ===
    basis_type: str = "ALMA"
    basis_len: int = 2
    offset_sigma: int = 5
    offset_alma: float = 0.85
    delay_offset: int = 0

    trade_type: str = "BOTH"
    heikin_ashi: bool = False

    # === Supply / Demand ===
    swing_length: int = 10
    history_of_demand_to_keep: int = 20
    box_width: float = 2.5
    show_price_action_labels: bool = False

    # === S/R ===
    enable_sr: bool = False
    strength_sr: int = 2
    use_zones: bool = True
    use_hl_zones: bool = True
    zone_width_pct: int = 2
    rb: int = 10
    prd: int = 284
    channel_w: int = 10

    # === Risk Management (%) ===
    lx_lvl_tp1: float = 1.0
    lx_qty_tp1: float = 50.0
    lx_lvl_tp2: float = 1.5
    lx_qty_tp2: float = 30.0
    lx_lvl_tp3: float = 2.0
    lx_qty_tp3: float = 20.0
    lx_lvl_sl: float = 0.5

    @property
    def sx_lvl_tp1(self): return self.lx_lvl_tp1
    @property
    def sx_qty_tp1(self): return self.lx_qty_tp1
    @property
    def sx_lvl_tp2(self): return self.lx_lvl_tp2
    @property
    def sx_qty_tp2(self): return self.lx_qty_tp2
    @property
    def sx_lvl_tp3(self): return self.lx_lvl_tp3
    @property
    def sx_qty_tp3(self): return self.lx_qty_tp3
    @property
    def sx_lvl_sl(self): return self.lx_lvl_sl

    # === Strategy ===
    default_qty_percent: float = 10.0
    initial_capital: float = 10000.0


# -----------------------------------------------------------------------------
# 2) TEXNIK INDIKATORLAR
# -----------------------------------------------------------------------------
def sma(src: pd.Series, length: int) -> pd.Series:
    return src.rolling(length, min_periods=length).mean()


def ema(src: pd.Series, length: int) -> pd.Series:
    return src.ewm(span=length, adjust=False).mean()


def wma(src: pd.Series, length: int) -> pd.Series:
    w = np.arange(1, length + 1, dtype=float)
    return src.rolling(length).apply(lambda x: np.dot(x, w) / w.sum(), raw=True)


def vwma(src: pd.Series, volume: pd.Series, length: int) -> pd.Series:
    vol_sum = volume.rolling(length).sum()
    return (src * volume).rolling(length).sum() / vol_sum.replace(0, np.nan)


def rma(src: pd.Series, length: int) -> pd.Series:
    return src.ewm(alpha=1.0 / length, adjust=False).mean()


def true_range(df: pd.DataFrame) -> pd.Series:
    prev_close = df["close"].shift(1)
    return pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)


def atr(df: pd.DataFrame, length: int) -> pd.Series:
    return rma(true_range(df), length)


def rsi(src: pd.Series, length: int) -> pd.Series:
    delta = src.diff()
    up = rma(delta.clip(lower=0), length)
    down = rma((-delta).clip(lower=0), length)
    rs = up / down.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def alma(src: pd.Series, length: int, offset: float, sigma: float) -> pd.Series:
    m = offset * (length - 1)
    s = length / sigma if sigma else 1.0
    idx = np.arange(length, dtype=float)
    w = np.exp(-((idx - m) ** 2) / (2 * s * s))
    w_sum = w.sum()
    return src.rolling(length).apply(lambda x: np.dot(x, w) / w_sum, raw=True)


def hull_ma(src: pd.Series, length: int) -> pd.Series:
    half = max(int(round(length / 2)), 1)
    sqrt_len = max(int(round(np.sqrt(length))), 1)
    return wma(2 * wma(src, half) - wma(src, length), sqrt_len)


def tema(src: pd.Series, length: int) -> pd.Series:
    e1 = ema(src, length)
    e2 = ema(e1, length)
    e3 = ema(e2, length)
    return 3 * (e1 - e2) + e3


def linreg(src: pd.Series, length: int, offset: int = 0) -> pd.Series:
    x = np.arange(length, dtype=float)

    def _f(y):
        slope, intercept = np.polyfit(x, y, 1)
        return intercept + slope * (length - 1 - offset)

    return src.rolling(length).apply(_f, raw=True)


def supersmoother(src: pd.Series, length: int) -> pd.Series:
    a1 = np.exp(-1.414 * np.pi / length)
    b1 = 2 * a1 * np.cos(1.414 * np.pi / length)
    c2, c3 = b1, -a1 * a1
    c1 = 1 - c2 - c3
    v = np.zeros(len(src))
    arr = src.ffill().bfill().to_numpy()
    if len(arr) == 0:
        return pd.Series(v, index=src.index)
    for i in range(len(arr)):
        prev1 = v[i - 1] if i >= 1 else 0.0
        prev2 = v[i - 2] if i >= 2 else 0.0
        p_src = arr[i - 1] if i >= 1 else arr[i]
        v[i] = c1 * (arr[i] + p_src) / 2 + c2 * prev1 + c3 * prev2
    return pd.Series(v, index=src.index)


def variant(ma_type: str, src: pd.Series, length: int,
            off_sig: float, off_alma: float,
            volume: Optional[pd.Series] = None) -> pd.Series:
    t = str(ma_type).upper()
    if t == "EMA":
        return ema(src, length)
    if t == "DEMA":
        e = ema(src, length)
        return 2 * e - ema(e, length)
    if t == "TEMA":
        return tema(src, length)
    if t == "WMA":
        return wma(src, length)
    if t == "VWMA":
        if volume is None or float(volume.sum()) == 0.0:
            return sma(src, length)
        return vwma(src, volume, length)
    if t == "SMMA":
        return rma(src, length)
    if t == "HULLMA":
        return hull_ma(src, length)
    if t == "LSMA":
        return linreg(src, length, int(off_sig))
    if t == "ALMA":
        return alma(src, length, off_alma, off_sig)
    if t == "TMA":
        return sma(sma(src, length), length)
    if t == "SSMA":
        return supersmoother(src, length)
    return sma(src, length)


def pivot_high(high: pd.Series, left: int, right: int) -> pd.Series:
    out = pd.Series(np.nan, index=high.index)
    v = high.to_numpy()
    n = len(v)
    for i in range(left, n - right):
        window = v[i - left:i + right + 1]
        if v[i] == window.max() and (window[:left] < v[i]).all() and (window[left + 1:] < v[i]).all():
            out.iloc[i + right] = v[i]
    return out


def pivot_low(low: pd.Series, left: int, right: int) -> pd.Series:
    out = pd.Series(np.nan, index=low.index)
    v = low.to_numpy()
    n = len(v)
    for i in range(left, n - right):
        window = v[i - left:i + right + 1]
        if v[i] == window.min() and (window[:left] > v[i]).all() and (window[left + 1:] > v[i]).all():
            out.iloc[i + right] = v[i]
    return out


def crossover(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a > b) & (a.shift(1) <= b.shift(1))


def crossunder(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a < b) & (a.shift(1) >= b.shift(1))


def heikin_ashi_df(df: pd.DataFrame) -> pd.DataFrame:
    ha = pd.DataFrame(index=df.index)
    ha["close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = np.zeros(len(df))
    o = df["open"].to_numpy()
    c = ha["close"].to_numpy()
    if len(df):
        ha_open[0] = o[0]
    for i in range(1, len(df)):
        ha_open[i] = (ha_open[i - 1] + c[i - 1]) / 2
    ha["open"] = ha_open
    ha["high"] = pd.concat([df["high"], ha["open"], ha["close"]], axis=1).max(axis=1)
    ha["low"] = pd.concat([df["low"], ha["open"], ha["close"]], axis=1).min(axis=1)
    return ha


# -----------------------------------------------------------------------------
# 3) MULTI-TIMEFRAME
# -----------------------------------------------------------------------------
def resample_series(src: pd.Series, rule: str, how: str = "last") -> pd.Series:
    agg = {"last": "last", "high": "max", "low": "min", "first": "first"}[how]
    htf = src.resample(rule, label="right", closed="right").agg(agg)
    return htf.reindex(src.index, method="ffill")


def lr_slope(src: pd.Series, length: int) -> Tuple[float, float, float]:
    y = src.iloc[-length:].to_numpy()[::-1]
    per = np.arange(1, length + 1, dtype=float)
    x, y_sum = per.sum(), y.sum()
    x2, xy = (per * per).sum(), (y * per).sum()
    slp = (length * xy - x * y_sum) / (length * x2 - x * x)
    avg = y_sum / length
    intercept = avg - slp * x / length + slp
    return slp, avg, intercept


def lr_dev(df: pd.DataFrame, length: int, slp: float, intercept: float) -> Tuple[float, float]:
    up_dev = dn_dev = 0.0
    val = intercept
    highs = df["high"].iloc[-length:].to_numpy()[::-1]
    lows = df["low"].iloc[-length:].to_numpy()[::-1]
    for j in range(length):
        up_dev = max(up_dev, highs[j] - val)
        dn_dev = max(dn_dev, val - lows[j])
        val += slp
    return up_dev, dn_dev


# -----------------------------------------------------------------------------
# 4) SUPPLY / DEMAND ZONALARI
# -----------------------------------------------------------------------------
@dataclass
class Zone:
    kind: str
    left_index: int
    top: float
    bottom: float
    poi: float
    broken_index: Optional[int] = None

    @property
    def is_broken(self) -> bool:
        return self.broken_index is not None


class SupplyDemand:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.supply: List[Zone] = []
        self.demand: List[Zone] = []
        self.bos: List[Zone] = []

    @staticmethod
    def _overlapping(new_poi: float, zones: List[Zone], atr_value: float) -> bool:
        threshold = atr_value * 2
        for z in zones:
            if z.poi - threshold <= new_poi <= z.poi + threshold:
                return True
        return False

    def add(self, kind: str, level: float, left_index: int, atr_value: float):
        buffer = atr_value * (self.cfg.box_width / 10)
        if kind == "supply":
            top, bottom = level, level - buffer
            zones = self.supply
        else:
            bottom, top = level, level + buffer
            zones = self.demand
        poi = (top + bottom) / 2
        if self._overlapping(poi, zones, atr_value):
            return
        zones.insert(0, Zone(kind, left_index, top, bottom, poi))
        del zones[self.cfg.history_of_demand_to_keep:]

    def check_bos(self, close: float, bar_index: int):
        still_supply = []
        for z in self.supply:
            if close >= z.top:
                z.broken_index = bar_index
                self.bos.insert(0, z)
            else:
                still_supply.append(z)
        self.supply = still_supply

        still_demand = []
        for z in self.demand:
            if close <= z.bottom:
                z.broken_index = bar_index
                self.bos.insert(0, z)
            else:
                still_demand.append(z)
        self.demand = still_demand
        del self.bos[5:]


# -----------------------------------------------------------------------------
# 5) SUPPORT / RESISTANCE
# -----------------------------------------------------------------------------
def perc_width(df: pd.DataFrame, i: int, length: int, perc: float) -> float:
    lo = max(0, i - length + 1)
    return (df["high"].iloc[lo:i + 1].max() - df["low"].iloc[lo:i + 1].min()) * perc / 100.0


def support_resistance(df: pd.DataFrame, cfg: Config, i: int) -> List[float]:
    rb, prd = cfg.rb, cfg.prd
    ph = pivot_high(df["high"], rb, rb)
    pl = pivot_low(df["low"], rb, rb)
    cwidth = perc_width(df, i, prd, cfg.channel_w)

    levels: List[float] = []
    aas = [True] * 41
    countpp = 0
    for x in range(0, min(prd, i) + 1):
        idx = i - x
        p_h = ph.iloc[idx] if idx >= 0 else np.nan
        p_l = pl.iloc[idx] if idx >= 0 else np.nan
        if np.isnan(p_h) and np.isnan(p_l):
            continue
        countpp += 1
        if countpp > 40:
            break
        if not aas[countpp]:
            continue
        base_idx = idx - rb
        if base_idx < 0:
            continue
        base = df["high"].iloc[base_idx] if not np.isnan(p_h) else df["low"].iloc[base_idx]
        upl, dnl = base + cwidth, base - cwidth

        tmp = [True] * 41
        cnt = tpoint = 0
        for xx in range(0, min(prd, i) + 1):
            j = i - xx
            q_h = ph.iloc[j] if j >= 0 else np.nan
            q_l = pl.iloc[j] if j >= 0 else np.nan
            if np.isnan(q_h) and np.isnan(q_l):
                continue
            cnt += 1
            if cnt > 40:
                break
            if not aas[cnt]:
                continue
            b = j - rb
            if b < 0:
                continue
            chg = False
            if not np.isnan(q_h) and dnl <= df["high"].iloc[b] <= upl:
                tpoint += 1
                chg = True
            if not np.isnan(q_l) and dnl <= df["low"].iloc[b] <= upl:
                tpoint += 1
                chg = True
            if chg and cnt < 41:
                tmp[cnt] = False

        if tpoint >= cfg.strength_sr:
            for g in range(41):
                if not tmp[g]:
                    aas[g] = False
            if countpp < 21:
                levels.append(base)
    return levels


# -----------------------------------------------------------------------------
# 6) SAVDO MANTIQI
# -----------------------------------------------------------------------------
@dataclass
class Trade:
    side: str
    entry_index: int
    entry_time: pd.Timestamp
    entry_price: float
    sl: float
    tp1: float
    tp2: float
    tp3: float
    exit_index: Optional[int] = None
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl_pct: Optional[float] = None


@dataclass
class Result:
    signals: pd.DataFrame = field(default_factory=pd.DataFrame)
    trades: pd.DataFrame = field(default_factory=pd.DataFrame)
    supply_zones: List[Zone] = field(default_factory=list)
    demand_zones: List[Zone] = field(default_factory=list)
    bos_zones: List[Zone] = field(default_factory=list)
    equity: Optional[pd.Series] = None


class SwiftStrategy:
    def __init__(self, cfg: Optional[Config] = None):
        self.cfg = cfg or Config()

    def _alt(self, series: pd.Series, base_minutes: int) -> pd.Series:
        if not self.cfg.use_res:
            return series
        if not isinstance(series.index, pd.DatetimeIndex):
            return series
        minutes = max(int(base_minutes * self.cfg.int_res), 1)
        return resample_series(series, f"{minutes}min", "last")

    def run(self, df: pd.DataFrame, base_minutes: int = 15,
            compute_sr: bool = False) -> Result:
        cfg = self.cfg
        df = df.copy()
        df.columns = [str(c).lower() for c in df.columns]
        required = {"open", "high", "low", "close"}
        if not required.issubset(df.columns):
            raise ValueError(f"DataFrame ustunlari kerak: {required}")
        if "volume" not in df.columns:
            df["volume"] = 0.0
        if not isinstance(df.index, pd.DatetimeIndex):
            for col in ("time", "open_time", "date"):
                if col in df.columns:
                    df = df.set_index(pd.to_datetime(df[col]))
                    break

        src_df = heikin_ashi_df(df) if cfg.heikin_ashi else df

        close_s = variant(cfg.basis_type, src_df["close"].shift(cfg.delay_offset),
                          cfg.basis_len, cfg.offset_sigma, cfg.offset_alma, df["volume"])
        open_s = variant(cfg.basis_type, src_df["open"].shift(cfg.delay_offset),
                         cfg.basis_len, cfg.offset_sigma, cfg.offset_alma, df["volume"])

        close_alt = self._alt(close_s, base_minutes)
        open_alt = self._alt(open_s, base_minutes)

        le_trigger = crossover(close_alt, open_alt)
        se_trigger = crossunder(close_alt, open_alt)

        atr50 = atr(df, 50)
        rsi28 = rsi(df["close"], 28)
        rsi_ob = (rsi28 > 65) & (rsi28 > ema(rsi28, 10))
        rsi_os = (rsi28 < 35) & (rsi28 < ema(rsi28, 10))
        ema144 = ema(df["close"], 144)
        ema_bull = df["close"] > ema144

        swing_high = pivot_high(df["high"], cfg.swing_length, cfg.swing_length)
        swing_low = pivot_low(df["low"], cfg.swing_length, cfg.swing_length)

        sd = SupplyDemand(cfg)

        n = len(df)
        condition = 0.0
        entry_line = np.nan
        sl_line = np.nan
        tp1_line = tp2_line = tp3_line = np.nan

        rows = []
        trades: List[Trade] = []
        open_trade: Optional[Trade] = None

        highs = df["high"].to_numpy()
        lows = df["low"].to_numpy()
        closes = df["close"].to_numpy()

        for i in range(n):
            price = closes[i]
            hi, lo = highs[i], lows[i]
            prev_condition = condition

            a = atr50.iloc[i]
            if not np.isnan(a):
                if not np.isnan(swing_high.iloc[i]):
                    sd.add("supply", swing_high.iloc[i], i - cfg.swing_length, a)
                elif not np.isnan(swing_low.iloc[i]):
                    sd.add("demand", swing_low.iloc[i], i - cfg.swing_length, a)
            sd.check_bos(price, i)

            le = bool(le_trigger.iloc[i]) and cfg.trade_type in ("LONG", "BOTH")
            se = bool(se_trigger.iloc[i]) and cfg.trade_type in ("SHORT", "BOTH")

            if le and prev_condition <= 0.0:
                entry_line = price
                sl_line = price - price * (cfg.lx_lvl_sl / 100)
                tp1_line = price + price * (cfg.lx_lvl_tp1 / 100)
                tp2_line = price + price * (cfg.lx_lvl_tp2 / 100)
                tp3_line = price + price * (cfg.lx_lvl_tp3 / 100)
                condition = 1.0
                open_trade = Trade("long", i, df.index[i], price,
                                   sl_line, tp1_line, tp2_line, tp3_line)
            elif se and prev_condition >= 0.0:
                entry_line = price
                sl_line = price + price * (cfg.sx_lvl_sl / 100)
                tp1_line = price - price * (cfg.sx_lvl_tp1 / 100)
                tp2_line = price - price * (cfg.sx_lvl_tp2 / 100)
                tp3_line = price - price * (cfg.sx_lvl_tp3 / 100)
                condition = -1.0
                open_trade = Trade("short", i, df.index[i], price,
                                   sl_line, tp1_line, tp2_line, tp3_line)
            else:
                if condition >= 1.0:
                    if lo <= sl_line:
                        self._close(open_trade, i, df.index[i], sl_line, "SL", trades)
                        open_trade, condition = None, 0.0
                    elif condition == 1.2 and hi >= tp3_line:
                        self._close(open_trade, i, df.index[i], tp3_line, "TP3", trades)
                        open_trade, condition = None, 0.0
                    elif condition == 1.1 and hi >= tp2_line:
                        condition = 1.2
                    elif condition == 1.0 and hi >= tp1_line:
                        condition = 1.1
                elif condition <= -1.0:
                    if hi >= sl_line:
                        self._close(open_trade, i, df.index[i], sl_line, "SL", trades)
                        open_trade, condition = None, 0.0
                    elif condition == -1.2 and lo <= tp3_line:
                        self._close(open_trade, i, df.index[i], tp3_line, "TP3", trades)
                        open_trade, condition = None, 0.0
                    elif condition == -1.1 and lo <= tp2_line:
                        condition = -1.2
                    elif condition == -1.0 and lo <= tp1_line:
                        condition = -1.1

            rows.append({
                "time": df.index[i],
                "close": price,
                "closeSeries": close_alt.iloc[i],
                "openSeries": open_alt.iloc[i],
                "atr50": a,
                "rsi": rsi28.iloc[i],
                "rsiOb": bool(rsi_ob.iloc[i]),
                "rsiOs": bool(rsi_os.iloc[i]),
                "emaBull": bool(ema_bull.iloc[i]),
                "longEntry": le and prev_condition <= 0.0,
                "shortEntry": se and prev_condition >= 0.0,
                "condition": condition,
                "entryLine": entry_line,
                "slLine": sl_line,
                "tp1": tp1_line,
                "tp2": tp2_line,
                "tp3": tp3_line,
            })

        signals = pd.DataFrame(rows)
        if not signals.empty:
            signals = signals.set_index("time")
        trades_df = pd.DataFrame([t.__dict__ for t in trades])

        equity = None
        if not trades_df.empty:
            eq, series = cfg.initial_capital, []
            for pnl in trades_df["pnl_pct"].fillna(0):
                eq *= (1 + (pnl / 100) * (cfg.default_qty_percent / 100))
                series.append(eq)
            equity = pd.Series(series, index=trades_df["exit_time"])

        return Result(
            signals=signals,
            trades=trades_df,
            supply_zones=sd.supply,
            demand_zones=sd.demand,
            bos_zones=sd.bos,
            equity=equity,
        )

    @staticmethod
    def _close(trade: Optional[Trade], i: int, t, price: float,
               reason: str, trades: List[Trade]):
        if trade is None:
            return
        trade.exit_index = i
        trade.exit_time = t
        trade.exit_price = price
        trade.exit_reason = reason
        sign = 1 if trade.side == "long" else -1
        trade.pnl_pct = sign * (price - trade.entry_price) / trade.entry_price * 100
        trades.append(trade)


# -----------------------------------------------------------------------------
# 7) BOT INTEGRATSIYASI
# -----------------------------------------------------------------------------
def analyze_swift(df: pd.DataFrame, base_minutes: int = 15,
                  cfg: Optional[Config] = None) -> Dict[str, Any]:
    """Oxirgi barni SWIFT mantiqi bo'yicha tahlil qilib, bot formatida qaytaradi."""
    if df is None or len(df) < 60:
        return {"signal": "HOLD", "confidence": 0, "details": {"reason": "insufficient_data"}}

    try:
        res = SwiftStrategy(cfg).run(df, base_minutes=base_minutes)
    except Exception as exc:  # pragma: no cover - defensive
        return {"signal": "HOLD", "confidence": 0, "details": {"error": str(exc)}}

    if res.signals.empty:
        return {"signal": "HOLD", "confidence": 0, "details": {}}

    last = res.signals.iloc[-1]
    signal = "HOLD"
    if bool(last.get("longEntry")):
        signal = "BUY"
    elif bool(last.get("shortEntry")):
        signal = "SELL"

    confidence = 0
    if signal != "HOLD":
        confidence = 55
        # Trend filtri (EMA144)
        if signal == "BUY" and bool(last.get("emaBull")):
            confidence += 15
        if signal == "SELL" and not bool(last.get("emaBull")):
            confidence += 15
        # RSI ekstremumlariga qarshi kirmaslik
        if signal == "BUY" and bool(last.get("rsiOb")):
            confidence -= 15
        if signal == "SELL" and bool(last.get("rsiOs")):
            confidence -= 15
        # Zona qo'llovi
        price = float(last.get("close", 0.0))
        if signal == "BUY" and any(z.bottom <= price <= z.top for z in res.demand_zones):
            confidence += 15
        if signal == "SELL" and any(z.bottom <= price <= z.top for z in res.supply_zones):
            confidence += 15
        confidence = int(max(0, min(100, confidence)))

    return {
        "signal": signal,
        "confidence": confidence,
        "entry": float(last.get("entryLine")) if pd.notna(last.get("entryLine")) else None,
        "sl": float(last.get("slLine")) if pd.notna(last.get("slLine")) else None,
        "tp1": float(last.get("tp1")) if pd.notna(last.get("tp1")) else None,
        "tp2": float(last.get("tp2")) if pd.notna(last.get("tp2")) else None,
        "tp3": float(last.get("tp3")) if pd.notna(last.get("tp3")) else None,
        "details": {
            "rsi": None if pd.isna(last.get("rsi")) else float(last.get("rsi")),
            "ema_bull": bool(last.get("emaBull")),
            "supply_zones": len(res.supply_zones),
            "demand_zones": len(res.demand_zones),
            "bos_zones": len(res.bos_zones),
        },
    }


def to_voting_signal(result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """PortfolioManager voting uchun standart format."""
    if not result:
        return {"signal": "HOLD", "confidence": 0}
    return {
        "signal": str(result.get("signal", "HOLD")).upper(),
        "confidence": int(result.get("confidence", 0) or 0),
    }
