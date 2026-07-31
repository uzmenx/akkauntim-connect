"""
Prompt templates for signal generation.
The model is instructed to return strict JSON only.
"""

GENERIC_TEMPLATE = """
You are a trading signal assistant. Given the market context, analyze and output a JSON object with keys:
signal (BUY/SELL/HOLD), confidence (0.0-1.0), reason (short), entry (number or null), stop (number or null), take_profit (number or null).

Market context:
{context}

Respond ONLY with valid JSON.
"""
