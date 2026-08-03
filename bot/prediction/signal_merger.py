import math
import numpy as np
import json
import os
from dataclasses import dataclass

@dataclass
class MergedSignal:
    direction: str          # "BUY" | "SELL" | "NEUTRAL"
    confidence: float       # 0.0 - 1.0
    agreement: bool         # ikkala/barcha manba kelishdimi (frontend tooltip uchun foydali)
    lstm_weight_used: float # debug/shaffoflik uchun
    stat_weight_used: float = 0.0 # Statistik edge (uchinchi ovoz) og'irligi
    audit_trail: dict = None # Audit uchun barcha oraliq qiymatlar


def wilson_lower_bound(win_rate: float, n: int, confidence: float = 0.95) -> float:
    """
    Wilson Score Interval'ning quyi chegarasini (lower bound) hisoblaydi.
    Kichik sample size'lar uchun juda mos.
    """
    if n == 0:
        return 0.0
        
    z_dict = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_dict.get(confidence, 1.96)
    
    p = win_rate
    denominator = 1 + z**2/n
    centre_adjusted_probability = p + z**2 / (2*n)
    adjusted_standard_deviation = math.sqrt((p*(1 - p) + z**2 / (4*n)) / n)
    
    lower_bound = (centre_adjusted_probability - z * adjusted_standard_deviation) / denominator
    return max(0.0, lower_bound)


def compute_lstm_weight(symbol: str, timeframe: str, shadow_win_rate: float, actual_trades: int,
                        default_max_weight: float = 0.60) -> float:
    """
    LSTM ovozining og'irligini Wilson Confidence Interval asosida hisoblaydi.
    Har bir symbol va timeframe uchun alohida max_weight qoidalari qo'llanilishi mumkin.
    Avtomatik optimizatsiya qilingan (merger_weights.json) qiymatlarni ustuvor hisoblaydi.
    """
    symbol_upper = symbol.upper()
    
    # 1. Avval dinamik optimizatsiya qilingan og'irliklarni tekshiramiz
    dynamic_weights = _load_dynamic_weights()
    if symbol_upper in dynamic_weights:
        max_base_weight = dynamic_weights[symbol_upper]
    else:
        # 2. Agar yo'q bo'lsa, qat'iy qoidalardan foydalanamiz
        if "XAU" in symbol_upper or "GOLD" in symbol_upper:
            max_base_weight = 0.45  # Oltin volatilroq, LSTM ga kamroq ishonamiz
        elif "BTC" in symbol_upper or "ETH" in symbol_upper:
            max_base_weight = 0.50  # Kripto
        elif "EURUSD" in symbol_upper or "GBPUSD" in symbol_upper:
            max_base_weight = 0.70  # Asosiy forex juftliklari (likvidligi baland)
        else:
            max_base_weight = default_max_weight

    # Timeframe bo'yicha tahrirlash (Kichik timeframe'larda shovqin ko'p)
    tf_upper = timeframe.upper()
    if tf_upper in ["M1", "M5"]:
        max_base_weight *= 0.80  # Kichik TF larda shovqin ko'pligi uchun ishonchni pasaytiramiz
    elif tf_upper in ["H1", "H4", "D1"]:
        max_base_weight *= 1.15  # Katta TF larda trend barqarorroq
        
    max_base_weight = min(1.0, max_base_weight)

    # 95% ishonch bilan win_rate'ning quyi chegarasi
    w_lb = wilson_lower_bound(shadow_win_rate, actual_trades, confidence=0.95)
    
    # Agar ishonchli quyi chegara 50% dan katta bo'lsa, bizda statistik edge bor
    edge = max(0.0, w_lb - 0.5) * 2.0
    
    if edge <= 0.0:
        # Statistik ahamiyatli ustunlik yo'q. Ehtiyotkorlik bilan qaraymiz.
        if actual_trades < 10 and shadow_win_rate > 0.5:
             return 0.05 * (actual_trades / 10.0)
        return 0.0

    # Edge mavjud. Wilson qanchalik mustahkam bo'lsa, shuncha katta og'irlik
    dynamic_weight = max_base_weight * min(1.0, edge * 1.5)
    
    return min(max_base_weight, dynamic_weight)


def merge_signals(
    symbol: str,
    timeframe: str,
    voting_direction: str, voting_confidence: float,
    lstm_direction: str, lstm_confidence: float,
    shadow_win_rate: float, shadow_trade_count: int,
    min_trades_for_trust: int = 30, # Deprecated: Wilson CI ga o'tildi, lekin API compatibility uchun qoldirildi
    stat_direction: str = "NEUTRAL",
    stat_confidence: float = 0.0,
    stat_weight_base: float = 0.0
) -> MergedSignal:
    v_sign = {"BUY": 1, "SELL": -1}.get(voting_direction.upper(), 0)
    l_sign = {"UP": 1, "DOWN": -1, "BUY": 1, "SELL": -1}.get(lstm_direction.upper(), 0)
    s_sign = {"BUY": 1, "SELL": -1, "UP": 1, "DOWN": -1}.get(stat_direction.upper(), 0)

    lstm_weight = compute_lstm_weight(symbol, timeframe, shadow_win_rate, shadow_trade_count)
    voting_weight = 1.0  # asosiy tizim doim to'liq og'irlikda
    stat_weight = stat_weight_base if s_sign != 0 else 0.0

    # Vaznli ovoz (weighted vote), -1..+1 oralig'ida
    total_weight = voting_weight + lstm_weight + stat_weight
    
    # lstm_confidence foizda bo'lishi mumkin (0..100) yoki 0..1. Uni 0..1 formatga keltiramiz
    l_conf_norm = lstm_confidence / 100.0 if lstm_confidence > 1.0 else lstm_confidence
    
    weighted_score = (
        v_sign * voting_confidence * voting_weight +
        l_sign * l_conf_norm * lstm_weight +
        s_sign * stat_confidence * stat_weight
    ) / max(total_weight, 1e-9)

    # To'liq kelishuv (faqat ishtirok etayotgan va no-neytral signallar orasida)
    active_signs = []
    if voting_weight > 0 and v_sign != 0: active_signs.append(v_sign)
    if lstm_weight > 0 and l_sign != 0: active_signs.append(l_sign)
    if stat_weight > 0 and s_sign != 0: active_signs.append(s_sign)
    
    agreement = len(active_signs) > 1 and len(set(active_signs)) == 1

    conflict_weight = 0.0
    if not agreement:
        if v_sign != 0:
            if l_sign != 0 and l_sign != v_sign: conflict_weight += lstm_weight
            if s_sign != 0 and s_sign != v_sign: conflict_weight += stat_weight

    # Audit trail (Merger natijasini logging qilish uchun)
    audit_trail = {
        "inputs": {
            "symbol": symbol,
            "timeframe": timeframe,
            "voting_direction": voting_direction,
            "voting_confidence": voting_confidence,
            "lstm_direction": lstm_direction,
            "lstm_confidence": lstm_confidence,
            "stat_direction": stat_direction,
            "stat_confidence": stat_confidence,
            "shadow_win_rate": shadow_win_rate,
            "shadow_trade_count": shadow_trade_count
        },
        "weights": {
            "voting_weight": voting_weight,
            "lstm_weight": lstm_weight,
            "stat_weight": stat_weight,
            "total_weight": total_weight
        },
        "scores": {
            "v_sign": v_sign,
            "l_sign": l_sign,
            "s_sign": s_sign,
            "weighted_score": float(weighted_score),
            "conflict_weight": float(conflict_weight)
        }
    }

    if weighted_score > 0.15:
        direction = "BUY"
    elif weighted_score < -0.15:
        direction = "SELL"
    else:
        direction = "NEUTRAL"

    # Kelishilganda confidence oshadi, kelishmaganda ziddiyat darajasiga qarab pasayadi
    if agreement:
        boost = 0.25 * lstm_weight + 0.25 * stat_weight
        combined_confidence = min(1.0, voting_confidence * (1.0 + boost))
    else:
        # Kuchli kelishmovchilikda signalni butunlay bekor qilish (veto)
        if conflict_weight >= 0.45:
            direction = "NEUTRAL"
            combined_confidence = 0.0
            audit_trail["veto"] = f"Strong disagreement (conflict_weight={conflict_weight:.2f} >= 0.45) completely vetoed the signal."
        else:
            combined_confidence = voting_confidence * max(0.2, (1.0 - 0.3 * conflict_weight))

    return MergedSignal(
        direction=direction,
        confidence=round(float(combined_confidence), 3),
        agreement=agreement,
        lstm_weight_used=round(float(lstm_weight), 3),
        stat_weight_used=round(float(stat_weight), 3),
        audit_trail=audit_trail
    )
