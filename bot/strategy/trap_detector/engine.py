"""
bot/strategy/trap_detector/engine.py
====================================
Trap Detector (Bull/Bear Trap) algoritmi.
Volume va Candlestick (sham) tuzilishini tahlil qilib, 
yolg'on yorib o'tishlar (Fake Breakouts) va rad etishlarni aniqlaydi.
"""

import logging
import pandas as pd
from typing import Dict, Any

logger = logging.getLogger(__name__)

def analyze_trap_detector(df: pd.DataFrame) -> str:
    """
    AI uchun Volume va Sham dumlari (wicks) asosida qopqon (Trap) xavfini tahlil qiladi.
    """
    if df is None or df.empty or len(df) < 21:
        return "Trap Detector: Ma'lumot yetarli emas."
        
    try:
        # Oxirgi 20 ta sham uchun o'rtacha hajm va tana hajmini hisoblash
        recent_df = df.iloc[-21:-1].copy()
        avg_volume = recent_df['tick_volume'].mean() if 'tick_volume' in recent_df.columns else recent_df['real_volume'].mean()
        
        recent_df['body_size'] = abs(recent_df['close'] - recent_df['open'])
        avg_body = recent_df['body_size'].mean()
        
        # Hozirgi (yopilmagan) va undan oldingi (yopilgan) shamlarni olish
        last_closed = df.iloc[-2]
        current = df.iloc[-1]
        
        # 1. Volume Fakeout tekshiruvi (Hajmsiz O'sish)
        fakeout_warnings = []
        
        # Agar oldingi yopilgan sham o'rtachadan kamida 1.5 baravar katta bo'lsa
        last_body = abs(last_closed['close'] - last_closed['open'])
        if avg_body > 0 and last_body > (avg_body * 1.5):
            last_vol = last_closed.get('tick_volume', last_closed.get('real_volume', 0))
            # Katta harakat, lekin hajm o'rtachadan past bo'lsa -> Fakeout xavfi
            if last_vol < avg_volume:
                direction = "O'SISH" if last_closed['close'] > last_closed['open'] else "QULASH"
                fakeout_warnings.append(f"Hajmsiz {direction}: Oxirgi yopilgan yirik sham hajmi (Volume) o'rtachadan past. Bu Retail traderlarni qopqonga tushirish uchun yasalgan (Fake Breakout) bo'lishi mumkin!")

        # 2. Rejection Wicks (Rad etuvchi dumlar) tekshiruvi
        rejection_warnings = []
        def check_rejection(candle, prefix_name):
            _body = abs(candle['close'] - candle['open'])
            _upper_wick = candle['high'] - max(candle['close'], candle['open'])
            _lower_wick = min(candle['close'], candle['open']) - candle['low']
            _total = candle['high'] - candle['low']
            
            if _total == 0:
                return
                
            # Dum (wick) butun shamning 60% idan katta va tana kichik bo'lsa (Pinbar)
            if _upper_wick > (_total * 0.6) and _body < (_total * 0.3):
                rejection_warnings.append(f"Kuchli YUQORIDAN rad etish ({prefix_name}): Katta tepa dum (Bull Trap). Bozorda xaridorlar kuchi tugab, sotuvchilar bosimi boshlangan.")
            elif _lower_wick > (_total * 0.6) and _body < (_total * 0.3):
                rejection_warnings.append(f"Kuchli PASTDAN rad etish ({prefix_name}): Katta pastki dum (Bear Trap). Sotuvchilar kuchi tugab, xaridorlar bosimi boshlangan.")

        check_rejection(last_closed, "Oxirgi yopilgan sham")
        check_rejection(current, "Joriy (shakllanayotgan) sham")

        # Xulosani jamlash
        if not fakeout_warnings and not rejection_warnings:
            return "Trap Detector: Hozircha tuzoq (Fakeout yoki Rejection) belgilari aniqlanmadi. Bozor harakati hajm bilan tasdiqlangan."
            
        messages = ["🪤 TRAP DETECTOR (Tuzoqdan himoya):"]
        for w in fakeout_warnings:
            messages.append(f"- XAVF: {w}")
        for r in rejection_warnings:
            messages.append(f"- REJECTION: {r}")
            
        messages.append(">> Maslahat: Agar SMC yoxud Pattern berayotgan signal ushbu xavflarga qarshi bo'lsa, 'HOLD' rejimini tanlagan ma'qul yoki SL ni qattiq himoyalash kerak.")
        return "\n".join(messages)

    except Exception as e:
        logger.error(f"Trap Detector tahlil xatosi: {e}")
        return f"Trap Detector: Xatolik - {e}"
