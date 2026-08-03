"""
news_coverage_check.py
=======================
Savdo qilinayotgan juftlikning valyutalari NewsDetector.target_currencies
ro'yxatida bormi, tekshiradi. Yo'q bo'lsa, bu degani — news moduli shu
juftlik uchun HECH QANDAY yangilikni ko'rmagan, garchi signal "yangilik yo'q,
toza" deb ko'rsatgan bo'lsa ham.
"""

from typing import List

DEFAULT_TARGET_CURRENCIES = ["USD", "EUR", "GBP", "JPY"]

def split_pair_currencies(symbol: str) -> tuple:
    """'NZDCAD' -> ('NZD', 'CAD'). Standart 6-harfli forex juftlik formatini kutadi."""
    symbol = symbol.upper().replace("/", "").strip()
    if len(symbol) < 6:
        return (symbol, "")
    return (symbol[:3], symbol[3:6])

def check_news_coverage_gap(symbol: str, target_currencies: List[str] = None) -> bool:
    """
    True qaytaradi — agar juftlikning ikkala valyutasi ham
    target_currencies ro'yxatida bo'lmasa (ya'ni to'liq coverage gap bor).
    """
    target_currencies = target_currencies or DEFAULT_TARGET_CURRENCIES
    base, quote = split_pair_currencies(symbol)
    base_covered = base in target_currencies
    quote_covered = quote in target_currencies
    return not (base_covered or quote_covered)
