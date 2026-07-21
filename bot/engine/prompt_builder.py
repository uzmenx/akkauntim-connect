import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class PromptBuilder:
    def __init__(self, config: Any):
        self.config = config
        
    def build_context_summary(self, 
                              smc_result: Optional[Dict[str, Any]], 
                              patterns: Optional[Dict[str, Any]], 
                              news: Optional[Dict[str, Any]], 
                              voting: Dict[str, Any], 
                              memory_bank: Optional[str] = None) -> Dict[str, Any]:
        """
        Gathers context components into a structured dictionary.
        """
        return {
            "smc_structure": smc_result or {},
            "harmonic_pattern": patterns or {},
            "news_context": news or {},
            "voting_result": voting or {},
            "memory_bank": memory_bank or ""
        }

    def build_trading_prompt(self, context: Dict[str, Any], pair: str, current_price: float) -> str:
        """
        Builds the main trade decision prompt combining technical, fundamental, and memory bank inputs.
        """
        smc = context.get('smc_structure', {})
        trend = smc.get('trend', {})
        smc_summary = f"Trend: {trend.get('internal', 'N/A')} (Internal) / {trend.get('external', 'N/A')} (External)"
        last_bos = smc.get('last_bos', {})
        if last_bos:
            smc_summary += f"\nOxirgi BoS: {last_bos.get('type', '')} at {last_bos.get('price', '')}"
            
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
            
        vote = context.get('voting_result', {})
        
        memory_bank = context.get('memory_bank', "SMC Memory Bank: Joriy narx atrofida kuchli tarixiy zonalar topilmadi.\n")
        
        system_prompt = getattr(self.config, "ai_system_prompt", "Sen professional Forex treyderi va Quantitative Analistisan.")
        
        prompt = f"""{system_prompt}
Sening asosiy ustunliging: xom ma'lumotlarni o'qishdan tashqari, tizim tomonidan berilgan "Tarixiy Xotira" (Memory Bank) xulosalariga tayanasan.

=== 1. JORIY HOLAT ({pair}) ===
Hozirgi narx: {current_price}
{memory_bank}

=== 2. TEXNIK SMC TAHLILI ===
{smc_summary}

=== 3. HARMONIC PATTERN DETECTOR ===
{pat_summary}

=== 4. YANGILIKLAR KONTEKSTI ===
{news_summary}

=== 5. VOTING ENGINE XULOSASI ===
Yo'nalish (Direction): {vote.get('signal', 'HOLD')}
Risk (fraction): {vote.get('risk_pct', 0.0)}
Kelishgan strategiyalar: {', '.join(vote.get('agreed_strategies') or [])}

=== VAZIFA ===
Voting Engine allaqachon yo'nalish va risk darajasini tasdiqlagan. Sening vazifang:
1. Optimal Stop Loss (pips) va Take Profit (pips) ni texnik tahlil asosida aniqlash
2. Savdoni HOZIR ochish mumkinligini tasdiqlash

Qoidalar:
1. Agar kamida 1 ta strategiya signal bergan va bozor sharoiti ochiq TESKARI bo'lmasa → EXECUTE.
2. Agar bozorda kuchli trend TESKARI yo'nalishda bo'lsa (masalan, BUY signal lekin kuchli bearish trend) → REJECT.
3. Agar kuchli yangilik 5 daqiqa ichida bo'lsa → WAIT.
4. Stop Loss va Take Profit ni texnik darajalar asosida aniqla (minimum 1:1.5 ratio).
5. Yo'nalish va risk_pct ni O'ZGARTIRMA — ular Voting Engine tomonidan belgilangan.

MUHIM: Voting Engine allaqachon tasdiqlagan. Faqat OCHIQ xavf bo'lsa REJECT qil. Shubha bo'lsa EXECUTE qil, chunki risk allaqachon boshqarilgan.

JAVOBNI FAQAT quyidagi JSON formatida qaytar, boshqa hech qanday qo'shimcha matn yozma:
```json
{{
  "final_decision": "EXECUTE",
  "direction": "{vote.get('signal', 'BUY')}",
  "confidence": 75,
  "entry_price": null,
  "stop_loss_pips": 30,
  "take_profit_pips": 60,
  "risk_pct": {vote.get('risk_pct', 0.02)},
  "reasoning": "Savdo sababi...",
  "warnings": []
}}
```
Eslatma: final_decision qiymati "EXECUTE", "REJECT", yoki "WAIT" bo'lishi mumkin.
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
        
        prompt = f"""Sen avtonom Trading AIsan. Hozirda foydada bo'lgan (TP1 2R ga yetgan va 70% yopilgan) pozitsiyani boshqaryapsan.
Sening vazifang qolgan 30% pozitsiya uchun trailing rejimini tanlash.

Bozor holati:
SMC Trend: {trend.get('internal', 'Unknown')}
Yangiliklar: {next_event.get('name', 'None')}

QOIDALAR:
1. Agar kuchli impuls yoki yangilik bo'lsa -> "STEP" (har 1R da SL ni surish)
2. Agar barqaror trend bo'lsa -> "STRUCTURE" (yangi High/Low da SL ni surish)
3. Agar trend keskin o'zgargan yoki bozor xavfli bo'lsa -> "CLOSE_ALL" (hammasini yopish)

JAVOBNI FAQAT SHU UCHTASIDAN BIRI SIFATIDA QAYTAR (Hech qanday qo'shimcha matnsiz):
STEP
STRUCTURE
CLOSE_ALL
"""
        return prompt
