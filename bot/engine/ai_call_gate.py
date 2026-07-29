"""
ai_call_gate.py
================
AI chaqiruvi kerakmi, yoki bozor strukturasi o'zgarmagani uchun
o'tkazib yuborish mumkinmi, aniqlaydi. Bu SIGNAL FILTRI EMAS — faqat
tejash filtri. Shubha bo'lsa, har doim True (chaqirish) qaytaradi.
"""

import datetime
from typing import Optional, Dict, Any, Tuple

# Xavfsizlik zaxirasi: bu vaqtdan ko'p o'tgan bo'lsa, struktura
# o'zgarmagan taqdirda ham AI baribir chaqiriladi.
MAX_WAIT_MINUTES = 45

# BoS narxi bu chegaradan ko'p farq qilsa, "o'zgardi" hisoblanadi.
# Juda kichik chegara (masalan 0.00001) shovqinni ham "o'zgarish"
# deb hisoblab, gate'ni foydasiz qiladi — shuning uchun ATR asosida
# emas, oddiy nisbiy chegara ishlatiladi (keyingi bosqichda ATR bilan
# yaxshilash mumkin, lekin MVP uchun bu yetarli).
BOS_PRICE_CHANGE_THRESHOLD = 0.00005


def should_call_ai(
    symbol: str,
    current_trend_internal: str,
    current_bos_price: Optional[float],
    current_regime: str,
    gate_state: Optional[Dict[str, Any]],
) -> Tuple[bool, str]:
    """
    Returns (should_call: bool, reason: str)

    should_call=True bo'lsa, main.py odatdagidek AI'ni chaqiradi.
    should_call=False bo'lsa, main.py oldingi last_ai_decision'ni
    qayta ishlatadi (yoki oddiy HOLD, agar oldingi qaror bo'lmasa).
    """
    # Xavfsizlik zaxirasi #1: hech qanday oldingi holat yo'q bo'lsa,
    # bu — birinchi marta bu symbol tekshirilyapti, albatta chaqirish kerak.
    if gate_state is None:
        return True, "birinchi_chaqiruv_holat_yoq"

    # Xavfsizlik zaxirasi #2: max wait vaqti o'tgan bo'lsa, majburiy chaqirish.
    last_call_str = gate_state.get("last_ai_call_at")
    if last_call_str:
        try:
            last_call = datetime.datetime.fromisoformat(last_call_str)
            elapsed_min = (datetime.datetime.now() - last_call).total_seconds() / 60.0
            if elapsed_min >= MAX_WAIT_MINUTES:
                return True, f"max_wait_oshdi_{elapsed_min:.0f}min"
        except (ValueError, TypeError):
            # Vaqtni parse qila olmasak, xavfsiz tomonga o'tamiz: chaqiramiz.
            return True, "vaqt_parse_xatosi_xavfsiz_chaqiruv"
    else:
        return True, "last_call_vaqti_yoq"

    # Struktura o'zgarishini tekshirish
    trend_changed = gate_state.get("last_trend_internal") != current_trend_internal
    regime_changed = gate_state.get("last_regime") != current_regime

    bos_changed = False
    last_bos = gate_state.get("last_bos_price")
    if current_bos_price is not None and last_bos is not None:
        if abs(current_bos_price - last_bos) >= BOS_PRICE_CHANGE_THRESHOLD:
            bos_changed = True
    elif (current_bos_price is None) != (last_bos is None):
        # Biri bor, biri yo'q — bu ham o'zgarish hisoblanadi (masalan,
        # yangi BoS paydo bo'lgan, avval umuman bo'lmagan holat)
        bos_changed = True

    if trend_changed:
        return True, f"trend_ozgardi_{gate_state.get('last_trend_internal')}->{current_trend_internal}"
    if regime_changed:
        return True, f"regime_ozgardi_{gate_state.get('last_regime')}->{current_regime}"
    if bos_changed:
        return True, "yangi_bos_aniqlandi"

    # Hech narsa o'zgarmagan, va max_wait hali o'tmagan — o'tkazib yuborish xavfsiz
    return False, "ozgarish_yoq_otkazib_yuborildi"
