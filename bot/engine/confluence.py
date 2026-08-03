"""
confluence.py
=============
SMC + Harmonic Confluence Engine — ball tizimi asosida savdoga kirish qarorini
qabul qiladi.

MANTIQ:
  1. SMC dan fresh Order Block / FVG zonalarini olish
  2. Harmonic dan D nuqtasi (PRZ — Potential Reversal Zone) olish
  3. Agar Harmonic PRZ ↔ SMC OB/FVG orasidagi masofa < ATR*0.5:
     → CONFLUENCE = True (kuchli signal, risk 3-4%)
  4. Agar faqat bittasi bor:
     → risk 1-2%, faqat AI tasdiq bilan

BALL TIZIMI (0—140):
  | Omil                                   | Ball |
  |----------------------------------------|------|
  | Fresh Order Block narxga yaqin          | +40  |
  | Harmonic PRZ overlap (OB/FVG bilan)     | +40  |
  | FVG ichida yoki yaqinida narx           | +20  |
  | Trend mos keladi (internal)             | +15  |
  | Liquidity sweep bo'lgan                 | +15  |
  | News bias mos                           | +10  |
  |                                          |      |
  | Jami 70+  = EXECUTE (avtomatik)          |      |
  | Jami 50-69 = AI QAROR (Claude tasdiq)    |      |
  | Jami <50   = REJECT (savdo qilinmaydi)   |      |

ORDER YUBORMAYDI — faqat confluence ball va yo'nalishni qaytaradi.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from bot.engine.mtf_confirm import check_mtf_confirmation

logger = logging.getLogger(__name__)


# ====================================================================
# Data Classes
# ====================================================================

@dataclass
class ConfluenceZone:
    """Bitta confluence zonasini ifodalaydi — OB/FVG va PRZ ning uchrashuvi."""
    zone_top: float
    zone_bottom: float
    zone_type: str          # "ob" | "smc_fvg"
    direction: str          # "demand" | "supply"
    prz_overlap: bool       # Harmonic PRZ bilan overlap bormi
    overlap_pct: float      # Overlap foizi (0.0 - 1.0)
    distance_atr: float     # Joriy narxdan masofa (ATR birligida)
    ob_origin: str = ""     # "ChoCh Main" | "ChoCh Sub" | "BoS" (faqat OB uchun)
    ob_level: str = ""      # "Major" | "Minor" (faqat OB uchun)


@dataclass
class ConfluenceResult:
    """Confluence tahlil natijasi."""
    signal: str             # "BUY" | "SELL" | "HOLD"
    score: int              # 0-140 oralig'ida confluence ball
    decision: str           # "EXECUTE" | "AI_DECIDE" | "PENDING_LIMIT" | "REJECT"
    risk_pct: float         # Tavsiya etilgan risk foizi (0.01 - 0.04)
    direction: str          # "Bullish" | "Bearish" | "Neutral"

    # Tafsilotlar
    score_breakdown: Dict[str, int] = field(default_factory=dict)
    best_zone: Optional[Dict[str, Any]] = None
    harmonic_info: Optional[Dict[str, Any]] = None
    reasoning: str = ""
    warnings: List[str] = field(default_factory=list)
    suggested_limit_entry: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "signal": self.signal,
            "score": self.score,
            "decision": self.decision,
            "risk_pct": self.risk_pct,
            "direction": self.direction,
            "score_breakdown": self.score_breakdown,
            "best_zone": self.best_zone,
            "harmonic_info": self.harmonic_info,
            "reasoning": self.reasoning,
            "warnings": self.warnings,
            "suggested_limit_entry": self.suggested_limit_entry,
        }


# ====================================================================
# ATR Hisoblash
# ====================================================================

def compute_atr(df: pd.DataFrame, period: int = 14) -> float:
    """
    ATR (Average True Range) ni hisoblaydi.
    Confluence scoring uchun masofalarni normalizatsiya qilishda ishlatiladi.
    """
    if df is None or len(df) < period + 1:
        return 0.0

    highs = df["high"].values
    lows = df["low"].values
    closes = df["close"].values
    n = len(highs)

    tr = np.zeros(n)
    tr[0] = highs[0] - lows[0]

    for i in range(1, n):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )

    if n >= period:
        atr_val = np.mean(tr[-period:])
    else:
        atr_val = np.mean(tr) if n > 0 else 0.0

    return float(atr_val)


# ====================================================================
# Zone Overlap / Masofa Hisoblash
# ====================================================================

def _zones_overlap(
    zone_top: float,
    zone_bottom: float,
    prz_top: float,
    prz_bottom: float,
) -> Tuple[bool, float]:
    """
    Ikkita narx zonasi o'rtasida overlap borligini tekshiradi.

    Returns:
        (overlap_bor: bool, overlap_foizi: float)
        overlap_foizi: kichikroq zonaga nisbatan overlap qismi (0.0 - 1.0)
    """
    overlap_top = min(zone_top, prz_top)
    overlap_bottom = max(zone_bottom, prz_bottom)

    if overlap_top <= overlap_bottom:
        # Overlap yo'q
        return False, 0.0

    overlap_size = overlap_top - overlap_bottom
    zone_size = zone_top - zone_bottom
    prz_size = prz_top - prz_bottom

    # Kichikroq zona bo'yicha normalizatsiya (nisbiy overlap)
    min_size = min(zone_size, prz_size)
    if min_size <= 0:
        return True, 1.0  # Nuqtaviy zona — to'liq overlap

    overlap_pct = overlap_size / min_size
    return True, min(overlap_pct, 1.0)


def _zone_distance_atr(
    zone_top: float,
    zone_bottom: float,
    current_price: float,
    atr: float,
) -> float:
    """
    Joriy narxdan zonagacha bo'lgan masofani ATR birligida hisoblaydi.

    Agar narx zona ichida bo'lsa, masofa = 0.
    Agar narx zonadan tashqarida bo'lsa, eng yaqin chegaragacha masofa.
    """
    if atr <= 0:
        return 999.0  # ATR 0 bo'lsa, xavfsiz qiymat

    if zone_bottom <= current_price <= zone_top:
        return 0.0  # Narx zona ichida

    if current_price > zone_top:
        return (current_price - zone_top) / atr
    else:
        return (zone_bottom - current_price) / atr


# ====================================================================
# SMC Zonalarni Olish — OB va FVG
# ====================================================================

def _extract_fresh_zones(
    smc_data: Dict[str, Any],
    direction: str,
    current_price: float,
    atr: float,
    max_distance_atr: float = 3.0,
) -> List[Dict[str, Any]]:
    """
    SMC tahlil natijasidan fresh (mitigated bo'lmagan) OB va FVG zonalarini
    ajratib, masofa bo'yicha filtrlaydi.

    Parameters:
        smc_data: analyze_market_structure() natijalari
        direction: "demand" (BUY uchun) | "supply" (SELL uchun)
        current_price: joriy narx
        atr: ATR qiymati
        max_distance_atr: maksimal masofa (ATR birligida)

    Returns:
        Filtrlangan fresh zonalar ro'yxati, masofasi bo'yicha tartiblangan
    """
    zones = []

    # 1. Order Block'lar
    obs = smc_data.get("order_blocks", {}).get(direction, [])
    for ob in obs:
        if ob.get("status") != "fresh":
            continue

        top = ob.get("top", 0)
        bottom = ob.get("bottom", 0)
        if top <= 0 or bottom <= 0 or top <= bottom:
            continue

        dist = _zone_distance_atr(top, bottom, current_price, atr)
        if dist > max_distance_atr:
            continue

        zones.append({
            "type": "ob",
            "direction": direction,
            "top": top,
            "bottom": bottom,
            "distance_atr": round(dist, 3),
            "origin": ob.get("origin", ""),
            "level": ob.get("level", ""),
            "bar_index": ob.get("bar_index", 0),
        })

    # 2. Fair Value Gap'lar
    fvgs = smc_data.get("smc_fvg", {}).get(direction, [])
    for fvg in fvgs:
        if fvg.get("status") != "fresh":
            continue

        top = fvg.get("top", 0)
        bottom = fvg.get("bottom", 0)
        if top <= 0 or bottom <= 0 or top <= bottom:
            continue

        dist = _zone_distance_atr(top, bottom, current_price, atr)
        if dist > max_distance_atr:
            continue

        zones.append({
            "type": "smc_fvg",
            "direction": direction,
            "top": top,
            "bottom": bottom,
            "distance_atr": round(dist, 3),
            "origin": "",
            "level": "",
            "bar_index": fvg.get("bar_index", 0),
        })

    # Masofasi bo'yicha tartiblash (eng yaqinlari birinchi)
    zones.sort(key=lambda z: z["distance_atr"])
    return zones


# ====================================================================
# Harmonic PRZ (Potential Reversal Zone) Olish
# ====================================================================

def _extract_harmonic_prz(
    harmonic_data: Dict[str, Any],
    current_price: float,
    atr: float,
) -> Optional[Dict[str, Any]]:
    """
    Harmonic pattern tahlil natijasidan PRZ (Potential Reversal Zone) ni
    ajratib chiqaradi.

    PRZ manbalari (ustunlik tartibi):
    1. Active pattern — D nuqtasi allaqachon shakllanib, fib_levels mavjud
    2. Emerging patterns — D nuqtasi hali shakllanmagan, PRZ bashorat qilingan

    Returns:
        PRZ ma'lumotlari: {prz_top, prz_bottom, direction, source, pattern_name, ...}
        yoki None (agar hech narsa topilmasa)
    """
    if not harmonic_data:
        return None

    # === 1. Active Pattern — eng yuqori ustunlik ===
    active = harmonic_data.get("active_pattern")
    fib_levels = harmonic_data.get("fib_levels", {})

    if active and active.get("xabcd_points"):
        d_price = active["xabcd_points"].get("d")
        c_price = active["xabcd_points"].get("c")
        direction = active.get("direction", "")
        bars_since = active.get("bars_since_d", 999)

        # Active pattern faqat yaqin vaqtda (oxirgi 20 bar ichida) shakllanganini tekshirish
        # Juda eski patternlar ishonchli emas
        if d_price is not None and bars_since <= 20:
            entry_level = fib_levels.get("entry")
            sl_level = fib_levels.get("sl")

            # PRZ = D nuqtasi atrofidagi zona
            # Agar entry va sl mavjud bo'lsa, ulardan foydalanish
            if entry_level and sl_level:
                if direction == "Bullish":
                    # Bullish: D pastda, PRZ = SL dan Entry gacha
                    prz_bottom = min(d_price, sl_level)
                    prz_top = max(d_price, entry_level)
                else:
                    # Bearish: D yuqorida, PRZ = Entry dan SL gacha
                    prz_bottom = min(d_price, entry_level)
                    prz_top = max(d_price, sl_level)
            else:
                # fib_levels yo'q — D nuqtasi atrofida ATR*0.5 zona yaratamiz
                prz_buffer = atr * 0.5
                prz_top = d_price + prz_buffer
                prz_bottom = d_price - prz_buffer

            dist = _zone_distance_atr(prz_top, prz_bottom, current_price, atr)

            return {
                "prz_top": prz_top,
                "prz_bottom": prz_bottom,
                "d_price": d_price,
                "direction": direction,
                "source": "active",
                "pattern_name": active.get("name", "Unknown"),
                "bars_since_d": bars_since,
                "distance_atr": round(dist, 3),
                "fib_entry": entry_level,
                "fib_tp": fib_levels.get("tp"),
                "fib_sl": sl_level,
            }

    # === 2. Emerging Patterns — bashorat qilingan D nuqtasi ===
    emerging = harmonic_data.get("emerging_patterns", [])
    if emerging:
        # Eng kuchli emerging patternni tanlash (narxga eng yaqin PRZ)
        best_emerging = None
        best_dist = 999.0

        for ep in emerging:
            prz_min = ep.get("prz_min")
            prz_max = ep.get("prz_max")
            if prz_min is None or prz_max is None:
                continue

            # PRZ hajmi manfiy bo'lmasligi kerak
            if prz_max < prz_min:
                prz_min, prz_max = prz_max, prz_min

            dist = _zone_distance_atr(prz_max, prz_min, current_price, atr)

            # Faqat ATR*5 dan yaqinroq emerging patternlarni hisobga olish
            if dist < best_dist and dist <= 5.0:
                best_dist = dist
                best_emerging = ep

        if best_emerging:
            prz_min = best_emerging["prz_min"]
            prz_max = best_emerging["prz_max"]
            if prz_max < prz_min:
                prz_min, prz_max = prz_max, prz_min

            return {
                "prz_top": prz_max,
                "prz_bottom": prz_min,
                "d_price": best_emerging.get("prz_mid"),
                "direction": best_emerging.get("direction", ""),
                "source": "emerging",
                "pattern_name": best_emerging.get("name", "Unknown"),
                "bars_since_d": None,  # Hali shakllanmagan
                "distance_atr": round(best_dist, 3),
                "fib_entry": None,
                "fib_tp": None,
                "fib_sl": None,
            }

    return None


# ====================================================================
# Liquidity Sweep Tekshiruvi
# ====================================================================

def _check_liquidity_sweep(
    smc_data: Dict[str, Any],
    direction: str,
    current_price: float,
    df: pd.DataFrame,
    atr: float,
    lookback_bars: int = 10,
) -> bool:
    """
    Liquidity sweep yuz berganligini tekshiradi.

    Liquidity sweep — narx likvidlik darajasini qisqa muddatga o'tib,
    keyin qaytib kelishi. Bu Smart Money pozitsiya ochish belgisidir.

    BUY signal uchun:
      - Narx static_low yoki dynamic_low ni pastga sindirganmi (sweep)?
      - So'ngra qaytib ko'tarilganmi?

    SELL signal uchun:
      - Narx static_high yoki dynamic_high ni yuqoriga sindirganmi?
      - So'ngra qaytib tushganmi?
    """
    liquidity = smc_data.get("liquidity", {})
    if not liquidity:
        return False

    if df is None or len(df) < lookback_bars + 1:
        return False

    recent_lows = df["low"].values[-lookback_bars:]
    recent_highs = df["high"].values[-lookback_bars:]

    if direction == "demand":
        # BUY uchun — pastki likvidlik sweep
        liq_levels = []
        if liquidity.get("static_low") is not None:
            liq_levels.append(liquidity["static_low"])
        if liquidity.get("dynamic_low") is not None:
            liq_levels.append(liquidity["dynamic_low"])

        for liq_level in liq_levels:
            # Narx likvidlik darajasini pastga sindirib, keyin yuqoriga qaytganmi?
            swept_below = np.any(recent_lows < liq_level)
            recovered = current_price > liq_level
            if swept_below and recovered:
                return True

    elif direction == "supply":
        # SELL uchun — yuqori likvidlik sweep
        liq_levels = []
        if liquidity.get("static_high") is not None:
            liq_levels.append(liquidity["static_high"])
        if liquidity.get("dynamic_high") is not None:
            liq_levels.append(liquidity["dynamic_high"])

        for liq_level in liq_levels:
            # Narx likvidlik darajasini yuqoriga sindirib, keyin pastga qaytganmi?
            swept_above = np.any(recent_highs > liq_level)
            recovered = current_price < liq_level
            if swept_above and recovered:
                return True

    return False


# ====================================================================
# Asosiy Confluence Scoring
# ====================================================================

def calculate_confluence(
    smc_data: Dict[str, Any],
    harmonic_data: Dict[str, Any],
    news_data: Optional[Dict[str, Any]],
    df: pd.DataFrame,
    current_price: Optional[float] = None,
    config: Optional[Dict[str, Any]] = None,
    wyckoff_data: Optional[Dict[str, Any]] = None,
    sr_volume_data: Optional[Dict[str, Any]] = None,
    auto_pattern_data: Optional[Dict[str, Any]] = None,
    kill_zones_data: Optional[Dict[str, Any]] = None,
    df_minor: Optional[pd.DataFrame] = None,
    smc_minor: Optional[Dict[str, Any]] = None,
) -> ConfluenceResult:
    """
    SMC + Harmonic + News + Wyckoff ma'lumotlarini birlashtirgan Confluence Ball Tizimi.

    Bu funksiya botning "miyasi" — barcha tahlil natijalarini oladi va
    yagona savdo qarorini shakllantiradi.

    Parameters:
        smc_data: analyze_market_structure() natijasi
        harmonic_data: analyze_harmonic_patterns() natijasi
        news_data: get_news_signal() natijasi (optional)
        df: OHLC DataFrame (ATR hisoblash uchun)
        current_price: Joriy narx (agar berilmasa df dan olinadi)
        config: Qo'shimcha sozlamalar (thresholdlar va h.k.)
        wyckoff_data: analyze_wyckoff() natijasi (optional)

    Returns:
        ConfluenceResult — signal, score, decision, risk_pct, tafsilotlar
    """
    # ---- Default config ----
    cfg = {
        "score_threshold_execute": 30,    # 30+ = avtomatik EXECUTE
        "score_threshold_ai": 20,         # 20-29 = AI qaror bersin
        "max_zone_distance_atr": 2.0,     # OB/FVG max masofa (ATR birligida)
        "prz_overlap_threshold": 0.5,     # ATR*0.5 masofa = overlap hisoblanadi
        "smc_ob_weight": 10,
        "harmonic_prz_weight": 10,
        "smc_fvg_weight": 10,
        "smc_trend_weight": 10,
        "smc_liquidity_weight": 10,
        "news_bias_weight": 10,
        "wyckoff_spring_weight": 10,
        "wyckoff_phase_weight": 10,
        "sr_volume_weight": 10,
        "auto_pattern_weight": 10,
        "kill_zone_weight": 10,
        "overlap_bonus_weight": 10,
        "mtf_weight": 10,
    }
    if config:
        cfg.update(config)

    def get_weight(key: str) -> int:
        return max(5, min(20, cfg.get(key, 10)))

    # ---- Natija uchun tayyorgarlik ----
    score_breakdown: Dict[str, int] = {}
    warnings: List[str] = []
    reasoning_parts: List[str] = []
    total_score = 0
    best_zone_info: Optional[Dict[str, Any]] = None
    harmonic_info: Optional[Dict[str, Any]] = None

    # ---- Asosiy tekshiruvlar ----
    if smc_data is None or not isinstance(smc_data, dict):
        smc_data = {}
    if harmonic_data is None or not isinstance(harmonic_data, dict):
        harmonic_data = {}
    if news_data is None or not isinstance(news_data, dict):
        news_data = {}
    if wyckoff_data is None or not isinstance(wyckoff_data, dict):
        wyckoff_data = {}
    if sr_volume_data is None or not isinstance(sr_volume_data, dict):
        sr_volume_data = {}
    if auto_pattern_data is None or not isinstance(auto_pattern_data, dict):
        auto_pattern_data = {}
    if kill_zones_data is None or not isinstance(kill_zones_data, dict):
        kill_zones_data = {}

    if df is None or df.empty or len(df) < 20:
        return ConfluenceResult(
            signal="HOLD", score=0, decision="REJECT", risk_pct=0.0,
            direction="Neutral", reasoning="Ma'lumot yetarli emas (< 20 sham).",
            warnings=["Insufficient data"]
        )

    # ---- ATR va joriy narx ----
    atr = compute_atr(df, period=14)
    if atr <= 0:
        return ConfluenceResult(
            signal="HOLD", score=0, decision="REJECT", risk_pct=0.0,
            direction="Neutral", reasoning="ATR 0 ga teng — bozor harakatsiz.",
            warnings=["ATR is zero"]
        )

    if current_price is None:
        current_price = float(df["close"].iloc[-1])

    # ---- Trend aniqlash ----
    trend = smc_data.get("trend", {})
    internal_trend = trend.get("internal", "No Trend") if isinstance(trend, dict) else str(trend)
    external_trend = trend.get("external", "No Trend") if isinstance(trend, dict) else "No Trend"

    # ================================================================
    # QADAM 1: Yo'nalishni aniqlash
    # ================================================================
    #
    # Yo'nalish uchta manba asosida aniqlanadi:
    #   1. SMC trend (internal va external)
    #   2. Harmonic signal/pattern direction
    #   3. Yaqin zonalar (demand yuqorida = SELL emas)
    #
    # Eng katta ustunlik: fresh zonalar yo'nalishi
    # ================================================================

    # Ikkala yo'nalishda ham zonalarni olish (keyin taqqoslaymiz)
    demand_zones = _extract_fresh_zones(
        smc_data, "demand", current_price, atr,
        max_distance_atr=cfg["max_zone_distance_atr"]
    )
    supply_zones = _extract_fresh_zones(
        smc_data, "supply", current_price, atr,
        max_distance_atr=cfg["max_zone_distance_atr"]
    )

    # Harmonic PRZ
    prz_info = _extract_harmonic_prz(harmonic_data, current_price, atr)

    # Yo'nalish qaror uchun vektorlar
    bullish_score = 0
    bearish_score = 0

    # SMC trend bo'yicha
    if "Up" in internal_trend:
        bullish_score += 2
    elif "Down" in internal_trend:
        bearish_score += 2

    if "Up" in external_trend:
        bullish_score += 1
    elif "Down" in external_trend:
        bearish_score += 1

    # Yaqin demand zonalar bor = BUY ga yordam
    # Yaqin supply zonalar bor = SELL ga yordam
    if demand_zones:
        nearest_demand = demand_zones[0]["distance_atr"]
        if nearest_demand <= 1.0:
            bullish_score += 3  # Narx demand zonaga juda yaqin
        elif nearest_demand <= 2.0:
            bullish_score += 1

    if supply_zones:
        nearest_supply = supply_zones[0]["distance_atr"]
        if nearest_supply <= 1.0:
            bearish_score += 3
        elif nearest_supply <= 2.0:
            bearish_score += 1

    # Harmonic yo'nalishi
    if prz_info:
        if prz_info["direction"] == "Bullish":
            bullish_score += 2
        elif prz_info["direction"] == "Bearish":
            bearish_score += 2

    # Harmonic oddiy signal
    harm_signal = harmonic_data.get("signal", "NEUTRAL")
    if harm_signal == "BUY":
        bullish_score += 1
    elif harm_signal == "SELL":
        bearish_score += 1

    # Yo'nalish qaror
    if bullish_score > bearish_score:
        direction = "Bullish"
        signal = "BUY"
        target_direction = "demand"
        target_zones = demand_zones
    elif bearish_score > bullish_score:
        direction = "Bearish"
        signal = "SELL"
        target_direction = "supply"
        target_zones = supply_zones
    else:
        # Teng — HOLD
        return ConfluenceResult(
            signal="HOLD", score=0, decision="REJECT", risk_pct=0.0,
            direction="Neutral",
            score_breakdown={"bullish_vector": bullish_score, "bearish_vector": bearish_score},
            reasoning=f"Yo'nalish aniqlanmadi: Bullish={bullish_score}, Bearish={bearish_score}.",
            warnings=["Direction unclear"]
        )

    reasoning_parts.append(
        f"Yo'nalish: {direction} (Bullish={bullish_score}, Bearish={bearish_score})"
    )

    # ================================================================
    # QADAM 2: BALL HISOBLASH
    # ================================================================

    # -------- 2A: FRESH ORDER BLOCK (max +40 ball) --------
    ob_score = 0
    best_ob = None

    for zone in target_zones:
        if zone["type"] != "ob":
            continue
        dist = zone["distance_atr"]

        if dist <= 0.3:
            # Narx OB ichida yoki juda yaqin
            base = get_weight("smc_ob_weight")  # 40
        elif dist <= 0.7:
            # Narx OB ga yaqin
            base = int(get_weight("smc_ob_weight") * 0.75)  # 30
        elif dist <= 1.0:
            base = int(get_weight("smc_ob_weight") * 0.5)   # 20
        elif dist <= 1.5:
            base = int(get_weight("smc_ob_weight") * 0.3)   # 12
        else:
            base = int(get_weight("smc_ob_weight") * 0.1)   # 4

        # Major OB ga bonus
        if zone.get("level") == "Major":
            base = int(base * 1.15)  # +15% bonus

        # ChoCh Origin OB ga bonus (kuchli zona)
        if "ChoCh" in zone.get("origin", ""):
            base = int(base * 1.1)  # +10% bonus

        if base > ob_score:
            ob_score = base
            best_ob = zone

    if ob_score > 0:
        # 40 dan oshmasligi uchun
        ob_score = min(ob_score, get_weight("smc_ob_weight"))
        total_score += ob_score
        score_breakdown["smc_fresh_ob"] = ob_score

        origin_text = f" ({best_ob['origin']} {best_ob['level']})" if best_ob.get("origin") else ""
        reasoning_parts.append(
            f"Fresh {target_direction} OB topildi{origin_text}: "
            f"masofa {best_ob['distance_atr']:.2f} ATR → +{ob_score} ball"
        )
        best_zone_info = best_ob
    else:
        score_breakdown["smc_fresh_ob"] = 0
        reasoning_parts.append(f"Yaqin fresh {target_direction} OB topilmadi → +0 ball")

    # -------- 2B: HARMONIC PRZ OVERLAP (max +40 ball) --------
    prz_score = 0

    if prz_info:
        harmonic_info = prz_info
        prz_direction = prz_info["direction"]

        # PRZ yo'nalishi mos kelishini tekshirish
        direction_match = (
            (direction == "Bullish" and prz_direction == "Bullish") or
            (direction == "Bearish" and prz_direction == "Bearish")
        )

        if not direction_match:
            # PRZ teskari yo'nalishda — bu ogohlantirish, lekin 0 ball
            warnings.append(
                f"Harmonic PRZ ({prz_direction}) confluence yo'nalishi ({direction}) "
                f"bilan mos kelmaydi!"
            )
            score_breakdown["harmonic_prz_overlap"] = 0
        else:
            # PRZ mos yo'nalishda — overlap tekshirish
            has_overlap = False
            best_overlap_pct = 0.0

            # Barcha target zonalar bilan PRZ overlap ni tekshirish
            for zone in target_zones:
                overlap, overlap_pct = _zones_overlap(
                    zone["top"], zone["bottom"],
                    prz_info["prz_top"], prz_info["prz_bottom"]
                )

                if overlap and overlap_pct > best_overlap_pct:
                    has_overlap = True
                    best_overlap_pct = overlap_pct
                    if best_zone_info is None:
                        best_zone_info = zone

            if has_overlap:
                # OVERLAP BOR — kuchli signal!
                if best_overlap_pct >= 0.5:
                    prz_score = get_weight("harmonic_prz_weight")  # 40 (to'liq overlap)
                elif best_overlap_pct >= 0.2:
                    prz_score = int(get_weight("harmonic_prz_weight") * 0.75)  # 30
                else:
                    prz_score = int(get_weight("harmonic_prz_weight") * 0.5)   # 20

                reasoning_parts.append(
                    f"✅ CONFLUENCE: {prz_info['pattern_name']} PRZ "
                    f"({prz_info['source']}) + SMC zona OVERLAP! "
                    f"(overlap {best_overlap_pct:.0%}) → +{prz_score} ball"
                )
            else:
                # Overlap yo'q — PRZ va zonalar orasidagi masofani tekshirish
                prz_mid = (prz_info["prz_top"] + prz_info["prz_bottom"]) / 2
                min_prz_zone_dist = 999.0

                for zone in target_zones:
                    zone_mid = (zone["top"] + zone["bottom"]) / 2
                    dist_atr = abs(prz_mid - zone_mid) / atr if atr > 0 else 999.0
                    if dist_atr < min_prz_zone_dist:
                        min_prz_zone_dist = dist_atr

                if min_prz_zone_dist <= cfg["prz_overlap_threshold"]:
                    # ATR*0.5 ichida — yaqin confluence
                    prz_score = int(get_weight("harmonic_prz_weight") * 0.6)  # 24
                    reasoning_parts.append(
                        f"Harmonic PRZ ({prz_info['pattern_name']}) SMC zonaga yaqin "
                        f"({min_prz_zone_dist:.2f} ATR) → +{prz_score} ball"
                    )
                elif min_prz_zone_dist <= 1.5:
                    # ATR*1.5 ichida — zaif confluence
                    prz_score = int(get_weight("harmonic_prz_weight") * 0.3)  # 12
                    reasoning_parts.append(
                        f"Harmonic PRZ ({prz_info['pattern_name']}) SMC zonadan "
                        f"o'rtacha masofada ({min_prz_zone_dist:.2f} ATR) → +{prz_score} ball"
                    )
                else:
                    # Juda uzoq — bu PRZ dan ball yo'q
                    prz_score = 5  # Minimal ball (pattern mavjud, lekin overlap yo'q)
                    reasoning_parts.append(
                        f"Harmonic PRZ ({prz_info['pattern_name']}) SMC zonadan uzoq "
                        f"({min_prz_zone_dist:.2f} ATR) → +{prz_score} ball (zaif)"
                    )

            total_score += prz_score
            score_breakdown["harmonic_prz_overlap"] = prz_score

    elif prz_info is None and harmonic_data.get("signal") != "NEUTRAL":
        # PRZ topilmadi lekin harmonic signal bor — minimal ball
        prz_score = 5
        total_score += prz_score
        score_breakdown["harmonic_prz_overlap"] = prz_score
        reasoning_parts.append(
            f"Harmonic signal ({harmonic_data.get('signal')}) bor, "
            f"lekin aniq PRZ topilmadi → +{prz_score} ball"
        )
    else:
        score_breakdown["harmonic_prz_overlap"] = 0
        reasoning_parts.append("Harmonic pattern/PRZ topilmadi → +0 ball")

    # -------- 2C: FVG ICHIDA YOKI YAQINIDA (max +20 ball) --------
    fvg_score = 0
    best_fvg = None

    for zone in target_zones:
        if zone["type"] != "smc_fvg":
            continue
        dist = zone["distance_atr"]

        if dist <= 0.1:
            # Narx FVG ichida
            fvg_score = get_weight("smc_fvg_weight")  # 20
            best_fvg = zone
            break
        elif dist <= 0.5:
            # FVG ga juda yaqin
            score_candidate = int(get_weight("smc_fvg_weight") * 0.75)  # 15
            if score_candidate > fvg_score:
                fvg_score = score_candidate
                best_fvg = zone
        elif dist <= 1.0:
            score_candidate = int(get_weight("smc_fvg_weight") * 0.4)  # 8
            if score_candidate > fvg_score:
                fvg_score = score_candidate
                best_fvg = zone

    total_score += fvg_score
    score_breakdown["smc_fvg"] = fvg_score
    if fvg_score > 0 and best_fvg:
        reasoning_parts.append(
            f"Fresh {target_direction} FVG: masofa {best_fvg['distance_atr']:.2f} ATR → +{fvg_score} ball"
        )
    else:
        reasoning_parts.append(f"Yaqin fresh {target_direction} FVG topilmadi → +0 ball")

    # -------- 2D: TREND MOS KELADI (max +15 ball) --------
    trend_score = 0

    if direction == "Bullish":
        if "Up" in internal_trend:
            trend_score += 10
        if "Up" in external_trend:
            trend_score += 5
        if "Down" in internal_trend:
            trend_score -= 5
            warnings.append("Internal trend bearish — bullish confluence ga teskari!")
    else:  # Bearish
        if "Down" in internal_trend:
            trend_score += 10
        if "Down" in external_trend:
            trend_score += 5
        if "Up" in internal_trend:
            trend_score -= 5
            warnings.append("Internal trend bullish — bearish confluence ga teskari!")

    trend_score = max(0, min(trend_score, get_weight("smc_trend_weight")))
    total_score += trend_score
    score_breakdown["trend"] = trend_score
    reasoning_parts.append(
        f"Trend: Internal={internal_trend}, External={external_trend} → +{trend_score} ball"
    )

    # -------- 2E: LIQUIDITY SWEEP (max +15 ball) --------
    liq_score = 0
    liq_swept = _check_liquidity_sweep(
        smc_data, target_direction, current_price, df, atr
    )

    if liq_swept:
        liq_score = get_weight("smc_liquidity_weight")  # 15
        reasoning_parts.append(
            f"✅ Liquidity sweep aniqlandi ({target_direction} tomonda) → +{liq_score} ball"
        )
    else:
        reasoning_parts.append("Liquidity sweep aniqlanmadi → +0 ball")

    total_score += liq_score
    score_breakdown["smc_liquidity_sweep"] = liq_score

    # -------- 2F: NEWS BIAS MOS (max +10 ball) --------
    news_score = 0

    hist_bias = news_data.get("historical_bias") or {}
    bias_direction = hist_bias.get("direction", "Neutral")
    bias_confidence = hist_bias.get("confidence", 0)

    # Institutsional kontekst (COT)
    inst_ctx = news_data.get("institutional_context", {})
    cot_trend = inst_ctx.get("cot_trend", "Unknown")

    if bias_direction != "Neutral" and bias_confidence > 0:
        bias_matches = (
            (direction == "Bullish" and bias_direction == "Bullish") or
            (direction == "Bearish" and bias_direction == "Bearish")
        )

        if bias_matches and bias_confidence >= 0.6:
            news_score += 6
        elif bias_matches and bias_confidence >= 0.4:
            news_score += 3
        elif not bias_matches and bias_confidence >= 0.6:
            news_score -= 3
            warnings.append(
                f"News bias ({bias_direction}, {bias_confidence:.0%}) "
                f"confluence yo'nalishi bilan mos kelmaydi!"
            )

    # COT (institutsional yo'nalish)
    if cot_trend != "Unknown":
        cot_matches = (
            (direction == "Bullish" and cot_trend == "Net Long") or
            (direction == "Bearish" and cot_trend == "Net Short")
        )
        if cot_matches:
            news_score += 4
        # COT teskari bo'lsa ball ayirmaymiz — u uzoq muddatli ko'rsatkich

    news_score = max(0, min(news_score, get_weight("news_bias_weight")))
    total_score += news_score
    score_breakdown["news_bias_align"] = news_score

    if news_score > 0:
        reasoning_parts.append(
            f"News bias: {bias_direction} ({bias_confidence:.0%}), "
            f"COT: {cot_trend} → +{news_score} ball"
        )
    else:
        reasoning_parts.append("News bias mos emas yoki ma'lumot yo'q → +0 ball")

    # -------- 2G: OGOHLANTIRUVCHI TEKSHIRUVLAR --------

    # Yaqin kuchli yangilik bo'lsa ogohlantirish
    next_event = news_data.get("next_event") or {}
    mins_to_news = next_event.get("minutes_to_release", 999)
    if mins_to_news is not None and mins_to_news <= 15:
        news_impact = next_event.get("impact", "")
        if news_impact in ["High", "Medium"]:
            warnings.append(
                f"⚠️ {news_impact}-impact yangilik {mins_to_news:.0f} daqiqadan so'ng! "
                f"({next_event.get('name', 'Unknown')})"
            )
            # Ball kamaytirish emas, faqat ogohlantirish

    # Oxirgi ChoCh tekshirish — teskari ChoCh kuchli ogohlantirish
    last_choch = smc_data.get("last_choch")
    if last_choch:
        choch_type = last_choch.get("type", "")
        if direction == "Bullish" and "Bearish" in choch_type:
            warnings.append("Oxirgi ChoCh Bearish — trend o'zgarishi xavfi!")
        elif direction == "Bearish" and "Bullish" in choch_type:
            warnings.append("Oxirgi ChoCh Bullish — trend o'zgarishi xavfi!")

    # -------- 2H: WYCKOFF METHOD ALIGNMENT --------
    wyckoff_score = 0
    phase = wyckoff_data.get("phase", "Unknown")
    spring_upthrust = wyckoff_data.get("spring_upthrust", "None")
    momentum = wyckoff_data.get("momentum_sign", "None")

    if phase != "Unknown":
        # Phase Alignment
        if direction == "Bullish":
            if phase in ["Accumulation", "Markup"]:
                wyckoff_score += get_weight("wyckoff_phase_weight")
                reasoning_parts.append(f"Wyckoff: {phase} faza (Bullish) → +{get_weight('wyckoff_phase_weight')} ball")
            elif phase == "Distribution":
                wyckoff_score += -10
                warnings.append("Wyckoff: Bozor Distribution fazasida, Buy qilish juda xavfli!")
                reasoning_parts.append(f"Wyckoff: {phase} faza (Penalty) → -10 ball")
        elif direction == "Bearish":
            if phase in ["Distribution", "Markdown"]:
                wyckoff_score += get_weight("wyckoff_phase_weight")
                reasoning_parts.append(f"Wyckoff: {phase} faza (Bearish) → +{get_weight('wyckoff_phase_weight')} ball")
            elif phase == "Accumulation":
                wyckoff_score += -10
                warnings.append("Wyckoff: Bozor Accumulation fazasida, Sell qilish juda xavfli!")
                reasoning_parts.append(f"Wyckoff: {phase} faza (Penalty) → -10 ball")

        # Spring / Upthrust (Liquidity Trap)
        if direction == "Bullish" and spring_upthrust == "Spring":
            wyckoff_score += get_weight("wyckoff_spring_weight")
            reasoning_parts.append(f"Wyckoff: Spring (Liquidity Trap) aniqlandi → +{get_weight('wyckoff_spring_weight')} ball")
        elif direction == "Bearish" and spring_upthrust == "Upthrust":
            wyckoff_score += get_weight("wyckoff_spring_weight")
            reasoning_parts.append(f"Wyckoff: Upthrust (Liquidity Trap) aniqlandi → +{get_weight('wyckoff_spring_weight')} ball")

        # SOS / SOW
        if direction == "Bullish" and momentum == "SOS":
            wyckoff_score += 5
            reasoning_parts.append("Wyckoff: Sign of Strength (SOS) momentum → +5 ball")
        elif direction == "Bearish" and momentum == "SOW":
            wyckoff_score += 5
            reasoning_parts.append("Wyckoff: Sign of Weakness (SOW) momentum → +5 ball")

    total_score += wyckoff_score
    score_breakdown["wyckoff"] = wyckoff_score

    # -------- 2I: SR VOLUME ALIGNMENT --------
    sr_score = 0
    sr_signal = sr_volume_data.get("signal", "HOLD")
    
    if sr_signal not in ["NEUTRAL", "HOLD"]:
        if direction == "Bullish" and sr_signal == "BUY":
            sr_score += get_weight("sr_volume_weight")
            reasoning_parts.append(f"SR Volume: Bullish signal ({sr_volume_data.get('reasoning', '')}) → +{get_weight('sr_volume_weight')} ball")
        elif direction == "Bearish" and sr_signal == "SELL":
            sr_score += get_weight("sr_volume_weight")
            reasoning_parts.append(f"SR Volume: Bearish signal ({sr_volume_data.get('reasoning', '')}) → +{get_weight('sr_volume_weight')} ball")
        elif direction == "Bullish" and sr_signal == "SELL":
            sr_score -= int(get_weight("sr_volume_weight") / 2)
            warnings.append(f"SR Volume teskari (Bearish): {sr_volume_data.get('reasoning', '')}")
            reasoning_parts.append(f"SR Volume: Bearish signal (Penalty) → -{int(get_weight('sr_volume_weight')/2)} ball")
        elif direction == "Bearish" and sr_signal == "BUY":
            sr_score -= int(get_weight("sr_volume_weight") / 2)
            warnings.append(f"SR Volume teskari (Bullish): {sr_volume_data.get('reasoning', '')}")
            reasoning_parts.append(f"SR Volume: Bullish signal (Penalty) → -{int(get_weight('sr_volume_weight')/2)} ball")

    total_score += sr_score
    score_breakdown["sr_volume_breakout"] = sr_score

    # -------- 2J: AUTO CHART PATTERNS ALIGNMENT --------
    pattern_score = 0
    pattern_signal = auto_pattern_data.get("signal", "NEUTRAL")
    
    if pattern_signal != "NEUTRAL" and pattern_signal != "HOLD":
        if direction == "Bullish" and pattern_signal == "BUY":
            pattern_score += get_weight("auto_pattern_weight")
            reasoning_parts.append(f"Auto Pattern: Bullish tasdiq ({auto_pattern_data.get('reasoning', '')}) → +{get_weight('auto_pattern_weight')} ball")
        elif direction == "Bearish" and pattern_signal == "SELL":
            pattern_score += get_weight("auto_pattern_weight")
            reasoning_parts.append(f"Auto Pattern: Bearish tasdiq ({auto_pattern_data.get('reasoning', '')}) → +{get_weight('auto_pattern_weight')} ball")
        elif direction == "Bullish" and pattern_signal == "SELL":
            pattern_score -= int(get_weight("auto_pattern_weight") / 2)
            warnings.append(f"Auto Pattern teskari (Bearish): {auto_pattern_data.get('reasoning', '')}")
            reasoning_parts.append(f"Auto Pattern: Bearish signal (Penalty) → -{int(get_weight('auto_pattern_weight')/2)} ball")
        elif direction == "Bearish" and pattern_signal == "BUY":
            pattern_score -= int(get_weight("auto_pattern_weight") / 2)
            warnings.append(f"Auto Pattern teskari (Bullish): {auto_pattern_data.get('reasoning', '')}")
            reasoning_parts.append(f"Auto Pattern: Bullish signal (Penalty) → -{int(get_weight('auto_pattern_weight')/2)} ball")

    total_score += pattern_score
    score_breakdown["auto_pattern"] = pattern_score

    # -------- 2K: KILL ZONES (TIME MULTIPLIER) --------
    kz_score = 0
    is_kill_zone = kill_zones_data.get("is_kill_zone", False)
    is_overlap = kill_zones_data.get("is_overlap", False)
    is_dead_zone = kill_zones_data.get("is_dead_zone", False)
    active_sessions = kill_zones_data.get("active_sessions", [])

    if direction in ["Bullish", "Bearish"]:
        if is_kill_zone:
            kz_score += get_weight("kill_zone_weight")
            reasoning_parts.append(f"Kill Zone Active: Yuqori volatillik (Momentum tasdiqlandi) → +{get_weight('kill_zone_weight')} ball")
        
        if is_overlap:
            kz_score += get_weight("overlap_bonus_weight")
            reasoning_parts.append(f"Session Overlap (London/NY): Maksimal likvidlik → +{get_weight('overlap_bonus_weight')} ball")
            
        if is_dead_zone:
            warnings.append("Savdo uchun noqulay vaqt (Sessiyalar yopiq). Flet bo'lish xavfi yuqori.")
        elif active_sessions == ["Asian"] and direction in ["Bullish", "Bearish"]:
            warnings.append("Osiyo sessiyasi (Asian Session) - ko'pincha flet bo'ladi, ehtiyot bo'ling.")

    total_score += kz_score
    score_breakdown["kill_zones"] = kz_score

    # 3.1.5. MTF TASDIQLASH (Kichik taymfreym)
    mtf_score = 0
    if df_minor is not None and not df_minor.empty:
        signal_dir = "BUY" if direction == "Bullish" else "SELL"
        mtf_approved, mtf_msg = check_mtf_confirmation(signal_dir, df_minor, smc_minor or {})
        if mtf_approved:
            mtf_score += get_weight("mtf_weight")
            reasoning_parts.append(f"MTF Tasdiq: {mtf_msg} → +{get_weight('mtf_weight')} ball")
        else:
            mtf_score -= int(get_weight("mtf_weight") / 2)
            warnings.append(f"MTF xavf (qarshi trend): {mtf_msg}")
            reasoning_parts.append(f"MTF Tasdiqlamadi (Penalty) → -{int(get_weight('mtf_weight')/2)} ball")
            
    total_score += mtf_score
    score_breakdown["mtf_confirmation"] = mtf_score

    # ================================================================
    # QADAM 3: QAROR VA RISK
    # ================================================================

    total_score = max(0, total_score)
    reasoning = " | ".join(reasoning_parts)

    # QAROR (EXECUTE / AI_DECIDE / REJECT / PENDING_LIMIT)
    suggested_limit_entry = None
    if total_score >= cfg["score_threshold_ai"]:
        decision = "EXECUTE" if total_score >= cfg["score_threshold_execute"] else "AI_DECIDE"
        
        # Check distance to best zone or PRZ
        min_dist_atr = 999.0
        limit_candidate = None
        
        if best_zone_info:
            min_dist_atr = best_zone_info.get("distance_atr", 999.0)
            if direction == "Bullish":
                limit_candidate = best_zone_info.get("top") # Enter at the top of demand zone
            else:
                limit_candidate = best_zone_info.get("bottom") # Enter at the bottom of supply zone
                
        if harmonic_info:
            dist = harmonic_info.get("distance_atr", 999.0)
            if dist < min_dist_atr:
                min_dist_atr = dist
                if direction == "Bullish":
                    limit_candidate = harmonic_info.get("prz_top")
                else:
                    limit_candidate = harmonic_info.get("prz_bottom")

        # If price is far from optimal entry (> 0.5 ATR), switch to PENDING_LIMIT
        if min_dist_atr > 0.5 and limit_candidate is not None:
            decision = "PENDING_LIMIT"
            suggested_limit_entry = limit_candidate
            reasoning_parts.append(f"Joriy narx optimal zonadan uzoq ({min_dist_atr:.2f} ATR). PENDING_LIMIT tavsiya etiladi (Entry: {suggested_limit_entry:.5f}).")
    else:
        decision = "REJECT"
        signal = "HOLD"

    # RISK HISOBLASH
    risk_pct = _calculate_risk_pct(total_score, score_breakdown, cfg)

    reasoning = " | ".join(reasoning_parts)

    logger.info(
        f"Confluence: {signal} | Score: {total_score}/200 | "
        f"Decision: {decision} | Risk: {risk_pct:.1%} | "
        f"Breakdown: {score_breakdown}"
    )

    return ConfluenceResult(
        signal=signal,
        score=total_score,
        decision=decision,
        risk_pct=risk_pct,
        direction=direction,
        score_breakdown=score_breakdown,
        best_zone=best_zone_info,
        harmonic_info=harmonic_info,
        reasoning=reasoning,
        warnings=warnings,
        suggested_limit_entry=suggested_limit_entry,
    )


# ====================================================================
# Risk Hisoblash
# ====================================================================

def _calculate_risk_pct(
    total_score: int,
    breakdown: Dict[str, int],
    cfg: Dict[str, Any],
) -> float:
    """
    Confluence ball asosida risk foizini hisoblaydi.

    Mantiq:
      - SMC + Harmonic OVERLAP (ob + prz_overlap >= 60):
          Score 100+ → 4.0% risk (uchta strategiya + overlap)
          Score 70-99 → 3.0% risk (kuchli confluence)
      - Faqat bitta strategiya:
          Score 50-69 → 2.0% risk (AI tasdiq bilan)
      - Zaif signal:
          Score < 50 → 0.0% risk (savdo qilinmaydi)
    """
    ob_score = breakdown.get("smc_fresh_ob", 0)
    prz_score = breakdown.get("harmonic_prz_overlap", 0)
    combined_core = ob_score + prz_score

    if total_score >= 100 and combined_core >= 60:
        return 0.04  # 4% — uchta strategiya + kuchli overlap
    elif total_score >= cfg.get("score_threshold_execute", 70):
        if combined_core >= 50:
            return 0.03  # 3% — kuchli confluence
        else:
            return 0.025  # 2.5% — yaxshi confluence lekin zaifroq
    elif total_score >= cfg.get("score_threshold_ai", 50):
        return 0.02  # 2% — AI tasdiq bilan
    elif total_score >= 30:
        return 0.01  # 1% — juda zaif signal, minimal risk
    else:
        return 0.0  # Savdo yo'q
