import re

class NewsAIAnalyzer:
    """
    Katta Til Modelidan (LLM) chuqur fundamental tahlil olish uchun promptlar generatori.
    "Smart Money" va "Institutsional o'yinchilar" roliga asoslangan kuchli promptlar beradi.
    """
    
    @staticmethod
    def get_prompt_for_news(symbol: str, news_title: str, actual: str, forecast: str, previous: str, news_content: str = "") -> str:
        """
        Yangilik sarlavhasiga qarab to'g'ri role-playing promptni qaytaradi.
        """
        title_lower = news_title.lower()
        
        # 1. Foiz stavkalari (Interest Rate - FOMC, ECB, BOE)
        if any(kw in title_lower for kw in ["rate", "fomc", "ecb", "boe", "fed", "interest"]):
            return f"""Sen Wall Streetdagi eng tajribali hedge-fond boshqaruvchisi va makroiqtisodiy tahlilchisan. Sen yirik kapital ("Smart Money") oqimini va milliarder investorlarning qaror qabul qilish psixologiyasini mukammal tushunasan. 

Hozirgi vaqtda quyidagi iqtisodiy yangilik e'lon qilindi:
- Savdo qilinayotgan juftlik: {symbol}
- Yangilik nomi: {news_title}
- Chiqqan natija (Actual): {actual}
- Kutilgan natija (Forecast): {forecast}
- Oldingi natija (Previous): {previous}
- Qo'shimcha matn: {news_content}

Shu ma'lumotlarga asoslanib, menga quyidagi formatda o'ta aniq tahlil ber:
1. Fundamental Ta'sir: Ushbu natija {symbol} ga mantiqan qanday ta'sir qiladi?
2. Smart Money Pozitsiyasi: Yirik investorlar ushbu xabardan keyin qaysi tomonga (BUY yoki SELL) katta hajmda pozitsiya ochadi?
3. Likvidlik Ovi (Stop-Hunt): Katta o'yinchilar retail treyderlarni aldash uchun qanday manipulyatsiya qilishi mumkin?
[HUKM]: BUY, SELL, yoki NEUTRAL (faqat bitta so'z yozing)
[TP]: Take Profit uchun masofa pips hisobida (faqat raqam yozing, masalan: 150)
[SL]: Stop Loss uchun masofa pips hisobida (faqat raqam yozing, masalan: 50)"""

        # 2. Inflyatsiya (CPI, PPI, PCE)
        elif any(kw in title_lower for kw in ["cpi", "ppi", "pce", "inflation"]):
            return f"""Sen global moliyaviy bozorlar va inflyatsion risklar bo'yicha yetakchi ekspert va yirik institutsional investitsiya fondi rahbarisan.

Bugun quyidagi inflyatsiya yangiligi chiqdi:
- Savdo juftligi: {symbol}
- Yangilik: {news_title}
- Haqiqiy raqam (Actual): {actual}
- Kutilgan (Forecast): {forecast}
- Oldingi (Previous): {previous}

Menga quyidagilarni aniq tahlil qilib ber:
1. Makro Xulosa: Inflyatsiya raqamlari milliy valyutaga qanday ta'sir qildi?
2. Katta Kapitalning Harakati: BlackRock kabi fondlar bunday sharoitda {symbol} juftligida qaysi tomonga yuzlanadi? (Risk-on yoki Risk-off?)
3. Qisqa Muddatli Reaksiya: Keyingi 4-12 soat ichida bozorda qanday tebranish kutiladi?
[HUKM]: BUY, SELL, yoki NEUTRAL (faqat bitta so'z yozing)
[TP]: Take Profit uchun masofa pips hisobida (faqat raqam yozing, masalan: 120)
[SL]: Stop Loss uchun masofa pips hisobida (faqat raqam yozing, masalan: 40)"""

        # 3. Mehnat bozori (NFP, Employment, Unemployment, Jobless)
        elif any(kw in title_lower for kw in ["nfp", "employment", "unemployment", "jobless", "payroll"]):
            return f"""Sen institutsional savdo algoritmiga va bozorni manipulyatsiya qilish ("Order Block") tahliliga asoslanib savdo qiladigan yuqori toifali treydersan.

Hozirgi yangilik:
- Juftlik: {symbol}
- Yangilik: {news_title}
- Yaratilgan yangi ish o'rinlari (Actual): {actual}
- Kutilma (Forecast): {forecast}
- Oldingi (Previous): {previous}

Sening vazifang - chakana (retail) treyderlar nima qilishini va unga qarshi yirik treyderlar nima qilishini bashorat qilish:
1. Retail Treyderlar Qopqog'i: Oddiy treyderlar bu raqamlarni ko'rib qaysi tomonga yuguradi?
2. Haqiqiy Yo'nalish: Institutsional investorlar {symbol} ni sotib olyaptimi yoki sotyaptimi?
3. Volatillik Xaritasi: Dastlabki shpilka (spike) qaysi tomonga bo'lishi ehtimoli yuqori?
[HUKM]: BUY, SELL, yoki NEUTRAL (faqat bitta so'z yozing)
[TP]: Take Profit uchun masofa pips hisobida (faqat raqam yozing, masalan: 200)
[SL]: Stop Loss uchun masofa pips hisobida (faqat raqam yozing, masalan: 60)"""

        # Boshqa muhim yangiliklar / Universal
        else:
            return f"""Rolingiz: "Market Maker" (Bozorni harakatga keltiruvchi yirik bank), institutsional treyder va algoritmik savdo mantiqchisi.

Kiritilgan ma'lumotlar:
Valyuta juftligi: {symbol}
Yangilik nomi: {news_title}
Haqiqiy natija (Actual): {actual}
Kutilgan (Forecast): {forecast}
Oldingi (Previous): {previous}
Qo'shimcha matn: {news_content}

Quyidagi savollarga javob bering:
1. Yangilik {symbol} bo'yicha "Bullish" (O'sish) yoki "Bearish" (Tushish) mantiqqa egami?
2. Yirik banklar va hedge-fondlar ushbu yangilikdan so'ng qaysi yo'nalishga (BUY/SELL) pul kiritadi?
3. Retail treyderlarning ehtimoliy xatosi nimada bo'ladi (stop-loss hunting qayerda bo'ladi)?
[HUKM]: BUY, SELL, yoki NEUTRAL (faqat bitta so'z yozing)
[TP]: Take Profit uchun masofa pips hisobida (faqat raqam yozing, masalan: 100)
[SL]: Stop Loss uchun masofa pips hisobida (faqat raqam yozing, masalan: 30)"""

    @staticmethod
    def parse_hukm(ai_response: str) -> str:
        """
        AI qaytargan javobdan [HUKM] qismini ajratib oladi.
        Masalan: BUY, SELL yoki NEUTRAL.
        """
        if not ai_response:
            return "NEUTRAL"
            
        match = re.search(r'\[HUKM\][:\s]+(BUY|SELL|NEUTRAL)', ai_response, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        
        # Agar regex topa olmasa, oddiy text qidiruv
        upper_resp = ai_response.upper()
        if "HUKM]: BUY" in upper_resp or "[HUKM] BUY" in upper_resp:
            return "BUY"
        elif "HUKM]: SELL" in upper_resp or "[HUKM] SELL" in upper_resp:
            return "SELL"
            
        return "NEUTRAL"

    @staticmethod
    def parse_advanced_hukm(ai_response: str) -> dict:
        """
        AI qaytargan javobdan HUKM, TP va SL ni ajratib oladi.
        """
        result = {"direction": "NEUTRAL", "tp_pips": 100, "sl_pips": 50} # Defaults
        
        if not ai_response:
            return result
            
        # Parse HUKM
        hukm_match = re.search(r'\[HUKM\][:\s]+(BUY|SELL|NEUTRAL)', ai_response, re.IGNORECASE)
        if hukm_match:
            result["direction"] = hukm_match.group(1).upper()
            
        # Parse TP
        tp_match = re.search(r'\[TP\][:\s]+(\d+)', ai_response, re.IGNORECASE)
        if tp_match:
            result["tp_pips"] = int(tp_match.group(1))
            
        # Parse SL
        sl_match = re.search(r'\[SL\][:\s]+(\d+)', ai_response, re.IGNORECASE)
        if sl_match:
            result["sl_pips"] = int(sl_match.group(1))
            
        if result["sl_pips"] <= 0:
            result["sl_pips"] = 50  # Safety fallback
        if result["tp_pips"] <= 0:
            result["tp_pips"] = 100  # Safety fallback
            
        return result
