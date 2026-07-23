import json
import logging
import re
from typing import Dict, Any, Optional
from anthropic import Anthropic

class AIClient:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.client = Anthropic(api_key=self.config.anthropic_api_key)
        self.total_tokens_in = 0
        self.total_tokens_out = 0
        self.total_cost = 0.0

    @staticmethod
    def _extract_json(text: str) -> Dict[str, Any]:
        # Try ```json ... ``` first
        match = re.search(r'```(?:json)?\s*(.*?)\s*```', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find raw JSON object
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass
        
        # Try full text
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        # Anthropic public pricing per 1M tokens (2025).
        m = model.lower()
        if "haiku-3" in m or "haiku-3-5" in m or "claude-3-haiku" in m:
            in_price, out_price = 0.25, 1.25
        elif "haiku" in m:  # Haiku 4.x
            in_price, out_price = 0.80, 4.00
        elif "opus" in m:
            in_price, out_price = 15.0, 75.0
        else:  # Sonnet 3.5 / 4.x default
            in_price, out_price = 3.0, 15.0
        return (input_tokens * in_price / 1_000_000.0) + (output_tokens * out_price / 1_000_000.0)

    def get_decision(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        sys_prompt = system_prompt or self.config.ai_system_prompt
        max_tok = max_tokens or self.config.ai_max_tokens

        # Faqat haqiqiy Anthropic model-slug'lariga tayanamiz.
        preferred = getattr(self.config, "ai_model", "") or ""
        fallbacks = list(getattr(self.config, "ai_models_fallback", []) or [])
        default_stack = [
            "claude-sonnet-4-5",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
        ]
        seen, models_to_try = set(), []
        for m in [preferred, *fallbacks, *default_stack]:
            if m and m not in seen:
                seen.add(m)
                models_to_try.append(m)

        import time
        import anthropic
        
        last_exception = None
        for model in models_to_try:
            retries = 2
            for attempt in range(retries + 1):
                try:
                    self.logger.info(f"Requesting AI decision using model: {model} (Attempt {attempt+1}/{retries+1})")
                    kwargs = {
                        "model": model,
                        "max_tokens": max_tok,
                        "messages": [{"role": "user", "content": prompt}],
                    }
                    if sys_prompt:
                        kwargs["system"] = sys_prompt
                        
                    response = self.client.messages.create(**kwargs)
                    
                    content = response.content[0].text
                    
                    # Tracking tokens and cost
                    in_tok = response.usage.input_tokens
                    out_tok = response.usage.output_tokens
                    self.total_tokens_in += in_tok
                    self.total_tokens_out += out_tok
                    
                    cost = self._calculate_cost(model, in_tok, out_tok)
                    self.total_cost += cost
                    self.logger.info(f"AI Call tokens: in={in_tok}, out={out_tok}, cost=${cost:.5f}")
                    
                    return self._extract_json(content)
                    
                except anthropic.RateLimitError as e:
                    self.logger.warning(f"Rate limit on {model}: {e}")
                    last_exception = e
                    if attempt < retries:
                        time.sleep(4)  # Wait longer for rate limits
                except Exception as e:
                    self.logger.warning(f"Model {model} failed: {e}")
                    last_exception = e
                    if attempt < retries:
                        time.sleep(2)
                
        self.logger.error(f"All models failed for get_decision. Last error: {last_exception}")
        return None

    def get_simple_response(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 10) -> str:
        # Typically use haiku for simple responses like trailing decisions
        model = "claude-3-haiku-20240307"
        try:
            kwargs = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system_prompt:
                kwargs["system"] = system_prompt
                
            response = self.client.messages.create(**kwargs)
            return response.content[0].text.strip()
        except Exception as e:
            self.logger.error(f"Failed to get simple response: {e}")
            return ""
