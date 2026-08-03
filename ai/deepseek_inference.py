"""
DeepSeek API Inference Module.

Usage:
  - Set DEEPSEEK_API_KEY environment variable.
  - Run `python ai/deepseek_inference.py --test` to self-test API connection.
"""

import os
import json
import argparse
import requests
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

# DeepSeek Chat API endpoint
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"
# Set your API Key here or in .env file
API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

def _clean_json_from_text(text: str) -> str:
    """Extract JSON substring from model output, naive approach."""
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    return text

def generate_signal(market_context: str, prompt_template: str, temperature: float = 0.2) -> Dict[str, Any]:
    if not API_KEY:
        print("WARNING: DEEPSEEK_API_KEY is not set. Please set it in .env file.")
        return {"raw": "API Key not found", "parsed": None}

    prompt = prompt_template.format(context=market_context)

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a professional algorithmic trading AI. Analyze the context and strictly return JSON."},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": 256,
        "top_p": 0.95,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        
        result_json = response.json()
        raw_text = result_json["choices"][0]["message"]["content"]
        
        json_part = _clean_json_from_text(raw_text)
        try:
            parsed = json.loads(json_part)
        except Exception:
            parsed = {"raw": raw_text}
            
        return {"raw": raw_text, "parsed": parsed}
        
    except Exception as e:
        print(f"API Error: {e}")
        return {"raw": str(e), "parsed": None}

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Run a short test prompt and print result')
    args = parser.parse_args()

    if args.test:
        print("Testing DeepSeek API Connection...")
        sample_context = (
            "SYMBOL: EURUSD\nTF: M5\nLast 5 candles (o,h,l,c):\n"
            "[[1,1.1000,1.1005,1.0995,1.1002],[2,1.1002,1.1008,1.0998,1.1006],[3,1.1006,1.1012,1.1000,1.1010]]"
        )
        # Fallback template if prompt_templates is missing
        try:
            from ai.prompt_templates import GENERIC_TEMPLATE
        except ImportError:
            GENERIC_TEMPLATE = "Analyze this data and return JSON with signal (BUY/SELL/HOLD), confidence (0-100), and reason:\n{context}"
            
        res = generate_signal(sample_context, GENERIC_TEMPLATE)
        print('RAW OUTPUT:\n', res.get('raw'))
        print('\nPARSED:\n', res.get('parsed'))
