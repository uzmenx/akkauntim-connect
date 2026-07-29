"""
close_mechanism_classifier.py
==============================
MT5 deal comment matnidan close_mechanism tegini deterministik aniqlaydi.
AI ishtirok etmaydi — faqat string matching.
"""

from typing import Optional

CLOSE_MECHANISM_UNKNOWN = "unknown"

def classify_close_mechanism(mt5_comment: str, mt5_reason: Optional[int] = None) -> str:
    """
    order_manager.py da qo'yiladigan comment satrlariga asoslanib
    close_mechanism enum qiymatini qaytaradi.

    Agar hech biriga mos kelmasa CLOSE_MECHANISM_UNKNOWN qaytaradi —
    bu holat 0% ga yaqin bo'lishi kerak; agar ko'p chiqsa, demak
    order_manager.py da yangi comment turi qo'shilgan va bu classifier
    yangilanishi kerak.
    """
    comment = (mt5_comment or "").lower()

    if "virtual sl" in comment:
        return "virtual_sl"
    if "catastrophic" in comment:
        return "catastrophic_sl"
    if "partial close" in comment and "70" in comment:
        return "tp1_partial"
    if "partial close" in comment and "100" in comment:
        return "tp1_full_after_partial"
    if "breakeven" in comment:
        return "breakeven_stop"
    if "step" in comment and "trail" in comment:
        return "trailing_step"
    if "atr" in comment and "trail" in comment:
        return "trailing_atr"
    if "expired" in comment or "muddati" in comment:
        return "pending_expired"
    if "invalid" in comment:
        return "pending_invalidated"

    # MT5 standart deal.reason kodlari orqali fallback
    # (faqat mt5_comment orqali aniqlanmasa)
    if mt5_reason == 0:  # DEAL_REASON_CLIENT — qo'lda MT5 terminalda
        return "manual"

    return CLOSE_MECHANISM_UNKNOWN
