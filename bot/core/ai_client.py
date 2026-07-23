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
        # Approximate pricing per 1M tokens
        if "haiku" in model.lower():
            cost = (input_tokens * 0.8 / 1_000_000.0) + (output_tokens * 4.0 / 1_000_000.0)
        elif "opus" in model.lower():
            cost = (input_tokens * 15.0 / 1_000_000.0) + (output_tokens * 75.0 / 1_000_000.0)
        else:
            # Sonnet: $3.00 per M input, $15.00 per M output
            cost = (input_tokens * 3.0 / 1_000_000.0) + (output_tokens * 15.0 / 1_000_000.0)
        return cost

    def get_decision(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        sys_prompt = system_prompt or self.config.ai_system_prompt
        max_tok = max_tokens or self.config.ai_max_tokens
        
        models_to_try = self.config.ai_models_fallback
        if self.config.ai_model not in models_to_try:
            models_to_try = [self.config.ai_model] + models_to_try
            
        # Force correct model to avoid 404
        if "claude-3-5-sonnet-20240620" not in models_to_try:
            models_to_try.insert(0, "claude-3-5-sonnet-20240620")

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
