import logging
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class PromptBuilder:
    def __init__(self, config: Any):
        self.config = config
        
    def build_context_summary(self, 
                              smc_result: Optional[Dict[str, Any]], 
                              patterns: Optional[Dict[str, Any]], 
                              news: Optional[Dict[str, Any]], 
                              voting: Optional[Dict[str, Any]] = None, 
                              memory_bank: Optional[str] = None,
                              wyckoff: Optional[Dict[str, Any]] = None,
                              sr_volume: Optional[Dict[str, Any]] = None,
                              auto_patterns: Optional[Dict[str, Any]] = None,
                              kill_zones: Optional[Dict[str, Any]] = None,
                              anti_manipulation: Optional[str] = None,
                              trap_detector: Optional[str] = None) -> Dict[str, Any]:
        """
        Gathers context components into a structured dictionary.
        Voting argumenti eski moslashuvchanlik uchun qoldirildi, lekin u ignor qilinishi mumkin.
        """
        return {
            "smc_structure": smc_result or {},
            "harmonic_pattern": patterns or {},
            "news_context": news or {},
            "memory_bank": memory_bank or "",
            "wyckoff": wyckoff or {},
            "sr_volume": sr_volume or {},
            "auto_patterns": auto_patterns or {},
            "kill_zones": kill_zones or {},
            "anti_manipulation": anti_manipulation or "",
            "trap_detector": trap_detector or ""
        }

    def build_trading_prompt(self, context: Dict[str, Any], pair: str, current_price: float) -> str:
        """
        AI (Claude 3.5 Sonnet) uchun to'liq avtonom agent bo'lishini talab qiluvchi prompt.
        """
        smc = context.get('smc_structure', {})
        trend = smc.get('trend', {})
        smc_summary = f"Trend: {trend.get('internal', 'N/A')} (Internal) / {trend.get('external', 'N/A')} (External)"
        last_bos = smc.get('last_bos', {})
        if last_bos:
            smc_summary += f"\nOxirgi BoS: {last_bos.get('type', '')} at {last_bos.get('price', '')}"
            
        zones = smc.get('zones', [])
        if zones:
            smc_summary += "\nYaqin SMC zonalar (OB/FVG):"
            for z in zones[:3]:
                # Faraz qilamizki z['price'] yoki z['top']/z['bottom'] bor
                z_price = z.get('price', z.get('top', z.get('bottom', 0)))
                dist = abs(current_price - z_price) if z_price else 0
                smc_summary += f"\n- {z.get('type', 'Zone')} at {z_price} (Hozirgi narxdan masofa: {dist:.5f})"
            
        pat = context.get('harmonic_pattern', {})
        pat_summary = f"Pattern signal: {pat.get('signal', 'NEUTRAL')}"
        if pat.get('patterns'):
            pat_summary += f", Patterns: {', '.join([p.get('name', '') for p in pat.get('patterns', [])])}"
            
        news = context.get('news_context', {})
        next_event = news.get('next_event') or {}
        hist_bias = news.get('historical_bias') or {}
        news_summary = f"Keyingi yangilik: {next_event.get('name', 'None')} ({next_event.get('minutes_to_release', 'N/A')} daqiqa qoldi)"
        if hist_bias:
            news_summary += f"\nTarixiy Bias: {hist_bias.get('direction', 'Neutral')} (Ishonch: {hist_bias.get('confidence', 0)})"
            
        wyckoff = context.get('wyckoff', {})
        wyckoff_summary = f"Phase: {wyckoff.get('phase', 'Unknown')}, Signal: {wyckoff.get('signal', 'HOLD')}"
        
        sr_vol = context.get('sr_volume', {})
        sr_summary = f"Signal: {sr_vol.get('signal', 'HOLD')}"
        
        auto_pat = context.get('auto_patterns', {})
        auto_pat_summary = f"Signal: {auto_pat.get('signal', 'HOLD')}"
        
        kz = context.get('kill_zones', {})
        kz_summary = f"Active sessions: {', '.join(kz.get('active_sessions', []))}, Signal: {kz.get('signal', 'HOLD')}"

        anti_manip = context.get('anti_manipulation', "")
        trap_detect = context.get('trap_detector', "")

        memory_bank = context.get('memory_bank', "SMC Memory Bank: Joriy narx atrofida kuchli tarixiy zonalar topilmadi.\n")
        
        system_prompt = getattr(self.config, "ai_system_prompt", "Sen to'liq avtonom AI Treyder Agentisan.")
        
        balance = context.get('balance', 0)
        margin_free = context.get('margin_free', 0)
        open_positions = context.get('open_positions', [])
        open_pos_text = ", ".join(open_positions) if open_positions else "Yo'q (0)"
        
        smc_minor = context.get('smc_minor', {})
        smc_minor_trend = smc_minor.get('trend', {}).get('internal', 'N/A')
        tf_minor = context.get('timeframe_minor', 'Minor')
        
        prompt = f"""Sening maqsading: quyidagi bozordagi barcha fundamental, texnik, SMC, va hajmiy (Wyckoff, SR) holatlarni tahlil qilib, MUSTAQIL ravishda xulosa chiqarish.
Sen boshqa barcha algoritmlardan ustunsan. Senga hech qanday qaror majburlanmagan. Sen "LIMIT_BUY", "LIMIT_SELL" yoki "HOLD" xulosasini berishing kerak.

=== 1. JORIY HOLAT ({pair}) ===
Hozirgi narx: {current_price}
Balans: {balance} | Erkin Marja: {margin_free}
Ochiq pozitsiyalar (aynan shu juftlik bo'yicha): {open_pos_text} 
QAT'IY QOIDA: Agar ushbu juftlikda allaqachon bitim ochilgan bo'lsa va narx tubdan o'zgarmagan bo'lsa, YANA BITTA BITIM OCHMA! Shunchaki "HOLD" xulosasini ber. Faqatgina vaziyat keskin o'zgargandagina yoki mutlaqo boshqa kuchli tasdiq olingandagina qo'shimcha savdoga ruxsat etiladi. Har 5-10 daqiqada bir xil savdo signalini takrorlama.
{context.get("risk_info", "")}
{memory_bank}

=== 2. TEXNIK SMC TAHLILI ===
{smc_summary}
(Foydali bo'lishi mumkin - H1 Zonalar: {json.dumps(smc.get('zones', [])[:2])})

Kichik (Minor) Timeframe ({tf_minor}):
- SMC Trend: {smc_minor_trend}

=== 3. HARMONIC PATTERN DETECTOR ===
{pat_summary}

=== 4. YANGILIKLAR KONTEKSTI ===
{news_summary}

=== 5. QO'SHIMCHA STRATEGIYALAR ===
Wyckoff: {wyckoff_summary}
SR Volume: {sr_summary}
Auto Patterns: {auto_pat_summary}
Kill Zones: {kz_summary}

{anti_manip}
{trap_detect}

=== 6. AI TRADE REVIEWER (O'RGANISH MODULI) XULOSASI ===
Quyidagi tavsiyalar avvalgi xatolaringdan o'rganilgan:
{json.dumps(context.get('learning_adjustments', {}))}

=== 7. KITOBLARDAN O'RGANILGAN QOIDALAR ===
Quyidagi qoidalar sening o'qigan kitoblaringdan olingan. Ularning tarixiy samaradorligiga e'tibor ber:
{context.get('book_knowledge', "Hali kitob o'qilmagan.")}

=== 8. AI XOTIRASI (OLDINGI SABOQLAR) ===
Quyidagi saboqlar sening oldingi savdolaring va xatolaringdan olingan. ULARGA AMAL QIL:
{context.get('ai_memory', "Xotira hali bo'sh.")}

=== VAZIFA ===
Bozor holatini to'liq o'rgan. 
Kirish turini bozor narxining sening eng kuchli "Kirish Zonasi" (OB/FVG/Support/Resistance) ga nisbatan joylashuviga qarab belgilagin:
1. YAQIN (Market Entry): Agar bozor narxi sening tanlagan kuchli kirish zonang ichida yoki unga juda yaqin (masalan 5 pip atrofida) joylashgan bo'lsa — qarorni `BUY` yoki `SELL` (LIMIT prefiksisiz) deb qaytar va `entry_price` ni joriy narxga yaqin joylashtir.
2. UZOQ (Pending Limit): Agar bozor narxi sening kirish zonangdan uzoqda bo'lsa — qarorni `LIMIT_BUY` yoki `LIMIT_SELL` deb qaytar va `entry_price` ni zonaning ustiga aniq joylashtir.

ZAIF TASDIQ QOIDASI: Agar eng asosiy strategiyalar (SMC va Auto Patterns) bir yo'nalishda signal bersa-yu, faqat qo'shimcha strategiyalardan biri (Wyckoff yoki Kill Zone) HOLD yoki qarshi signal bersa — bu qat'iy ziddiyat hisoblanmaydi! Bunday holatda ham (BUY/SELL/LIMIT_BUY/LIMIT_SELL) qarorini bergin, lekin xavfsizlik uchun kirish narxini odatdagidan ehtiyotkorroq (chuqurroq OB/FVG yoki kengroq SL bilan) tanla.

QAT'IY ZIDDIYAT (HOLD): Faqatgina SMC va Auto Patterns ning IKKALASI ham HOLD desa yoki bir-biriga mutlaqo qarama-qarshi signal (biri BUY, ikkinchisi SELL) bersa, yoxud bozor aniq yo'nalishga ega bo'lmay haddan tashqari beqaror bo'lsa — "HOLD" qarorini qaytar.

Barcha strategiyalar xulosasiga asoslanib, kirish narxini (entry_price), SL va TP (aniq narx ko'rinishida) hamda Risk foizini (0.01 - 0.05 atrofida) belgilagin.

JAVOBNI FAQAT quyidagi JSON formatida qaytar, boshqa hech qanday qo'shimcha matn (masalan markdown ```json) yozma! Sof JSON qaytar:
{{
  "decision": "BUY", // yoki "SELL", "LIMIT_BUY", "LIMIT_SELL", "HOLD"
  "entry_price": 1.05000, // HOLD bo'lsa null. O'zing belgilagan kirish narxini yoz.
  "stop_loss": 1.04500, // null agar HOLD bo'lsa
  "take_profit": 1.06000, // null agar HOLD bo'lsa
  "expiration_minutes": 240, // faqat LIMIT orderlar uchun: ushbu limit order qancha daqiqadan so'ng bekor qilinishi kerak? O'zing vaziyatga qarab belgilagin, agar MARKET order bo'lsa null.
  "risk_pct": 0.02, // 1% = 0.01
  "reasoning": "Nima uchun ushbu qarorga kelganing haqida to'liq sabab...",
  "warnings": ["yangilik chiqish arafasida"]
}}
"""
        return prompt

    def build_trailing_prompt(self, context: Dict[str, Any]) -> str:
        """
        Builds the prompt for determining the trailing stop mode.
        """
        smc = context.get('smc_structure', {})
        trend = smc.get('trend', {})
        news = context.get('news_context', {})
        next_event = news.get('next_event') or {}
        
        prompt = f"""Sen avtonom Trading AIsan. Hozirda foydada bo'lgan pozitsiyani boshqaryapsan.
Sening vazifang qolgan pozitsiya uchun trailing rejimini mustaqil tanlash.

Bozor holati:
SMC Trend: {trend.get('internal', 'Unknown')}
Yangiliklar: {next_event.get('name', 'None')}

QOIDALAR:
O'zing hal qil:
- "STEP": Har ma'lum o'sishda SL ni surib borish
- "STRUCTURE": Yangi High/Low struktura asosida SL ni surish
- "CLOSE_ALL": Xavf bo'lsa, zudlik bilan hammasini yopish

JAVOBNI FAQAT SHU UCHTASIDAN BIRI SIFATIDA QAYTAR (Hech qanday qo'shimcha matnsiz):
STEP
STRUCTURE
CLOSE_ALL
"""
        return prompt
