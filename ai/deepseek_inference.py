"""
Minimal DeepSeek-V2-7B inference wrapper.

Usage:
  - Set environment variable DEEPSEEK_MODEL_PATH to local path or HF repo id, or edit MODEL_ID below.
  - Run `python ai/deepseek_inference.py --test` to run a quick self-test (requires the model files).

Notes:
  - This does NOT include model weights. Download them separately and place under the path you choose.
  - For limited VRAM, use 4-bit loading via bitsandbytes (configured here). Adjust compute dtype based on your hardware.
"""

import os
import json
import argparse
from typing import Dict, Any
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

# Default: override with env var DEEPSEEK_MODEL_PATH
MODEL_ID = os.environ.get("DEEPSEEK_MODEL_PATH", "deepseek-v2-7b")
MAX_NEW_TOKENS = 256

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float16,
)

_tokenizer = None
_model = None


def load_model(model_id: str = MODEL_ID):
    global _tokenizer, _model
    if _model is not None and _tokenizer is not None:
        return _model, _tokenizer

    print(f"Loading tokenizer and model from: {model_id} (this may take a while)")
    _tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=False, trust_remote_code=True)

    # Try quantized loading (bitsandbytes). If fails, fall back to normal load.
    try:
        _model = AutoModelForCausalLM.from_pretrained(
            model_id,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
        )
    except Exception as e:
        print("Quantized load failed or not supported on this machine:", e)
        print("Falling back to non-quantized load (may require large VRAM)")
        _model = AutoModelForCausalLM.from_pretrained(model_id, device_map="auto", trust_remote_code=True)

    _model.eval()
    return _model, _tokenizer


def _clean_json_from_text(text: str) -> str:
    """
    Extract JSON substring from model output, naive approach.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end+1]
    # fallback: return original text
    return text


def generate_signal(market_context: str, prompt_template: str, temperature: float = 0.2) -> Dict[str, Any]:
    model, tokenizer = load_model()
    prompt = prompt_template.format(context=market_context)

    inputs = tokenizer(prompt, return_tensors="pt")
    device = next(model.parameters()).device
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=True,
            temperature=temperature,
            top_p=0.95,
            eos_token_id=tokenizer.eos_token_id,
        )
    raw = tokenizer.decode(out[0], skip_special_tokens=True)
    json_part = _clean_json_from_text(raw)
    try:
        parsed = json.loads(json_part)
    except Exception:
        parsed = {"raw": raw}
    return {"raw": raw, "parsed": parsed}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='Run a short test prompt and print result')
    args = parser.parse_args()

    if args.test:
        model, tokenizer = load_model()
        sample_context = (
            "SYMBOL: EURUSD\nTF: M5\nLast 5 candles (o,h,l,c):\n"
            "[[1,1.1000,1.1005,1.0995,1.1002],[2,1.1002,1.1008,1.0998,1.1006],[3,1.1006,1.1012,1.1000,1.1010]]"
        )
        from ai.prompt_templates import GENERIC_TEMPLATE
        res = generate_signal(sample_context, GENERIC_TEMPLATE)
        print('RAW OUTPUT:\n', res.get('raw'))
        print('\nPARSED:\n', res.get('parsed'))
