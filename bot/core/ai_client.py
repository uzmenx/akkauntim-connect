import json
import logging
import re
from typing import Dict, Any, Optional
import requests
from anthropic import Anthropic

class AIClient:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        try:
            self.client = Anthropic(api_key=self.config.anthropic_api_key)
        except Exception:
            self.client = None
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
            return None

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        # Anthropic public pricing per 1M tokens (2025).
        m = model.lower()
        if "kimi" in m or "moonshot" in m:
            in_price, out_price = 0.06, 0.06  # Kimi K3 approximate pricing
        elif "haiku-3" in m or "haiku-3-5" in m or "claude-3-haiku" in m:
            in_price, out_price = 0.25, 1.25
        elif "haiku" in m:  # Haiku 4.x
            in_price, out_price = 0.80, 4.00
        else:  # Sonnet 3.5 / 4.x default
            in_price, out_price = 3.0, 15.0
        return (input_tokens * in_price / 1_000_000.0) + (output_tokens * out_price / 1_000_000.0)

    def get_decision(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        sys_prompt = system_prompt or self.config.ai_system_prompt
        max_tok = max_tokens or self.config.ai_max_tokens

        selected_model = getattr(self.config, "ai_model", "auto")
        medium = getattr(self.config, "ai_model_medium", "claude-sonnet-5")
        weak = getattr(self.config, "ai_model_weak", "claude-haiku-4-5-20251001")
        
        if selected_model == "claude-sonnet-5":
            models_to_try = [medium]
        elif selected_model == "claude-haiku-4-5":
            models_to_try = [weak]
        else: # "auto" or anything else
            models_to_try = [medium, weak]
            
        models_to_try = list(dict.fromkeys(models_to_try))  # Remove duplicates preserving order

        import time
        import anthropic
        
        last_exception = None
        for model in models_to_try:
            retries = 2
            for attempt in range(retries + 1):
                try:
                    self.logger.info(f"Requesting AI decision using model: {model} (Attempt {attempt+1}/{retries+1})")
                    if "moonshot" in model.lower() or "kimi" in model.lower():
                        if not getattr(self.config, "kimi_api_key", None):
                            raise Exception("KIMI_API_KEY is required for moonshot models")
                        
                        headers = {
                            "Authorization": f"Bearer {self.config.kimi_api_key}",
                            "Content-Type": "application/json"
                        }
                        msgs = []
                        if sys_prompt:
                            msgs.append({"role": "system", "content": sys_prompt})
                        msgs.append({"role": "user", "content": prompt})
                        
                        payload = {
                            "model": model,
                            "messages": msgs
                        }
                        if max_tok:
                            payload["max_tokens"] = max_tok
                            
                        resp = requests.post("https://api.moonshot.ai/v1/chat/completions", headers=headers, json=payload, timeout=120)
                        if resp.status_code != 200:
                            raise Exception(f"Moonshot Error {resp.status_code}: {resp.text}")
                            
                        rdata = resp.json()
                        content = rdata["choices"][0]["message"]["content"]
                        in_tok = rdata.get("usage", {}).get("prompt_tokens", 0)
                        out_tok = rdata.get("usage", {}).get("completion_tokens", 0)
                    else:
                        if not self.client:
                            raise Exception("Anthropic API key is not configured or invalid.")
                        kwargs = {
                            "model": model,
                            "max_tokens": max_tok,
                            "messages": [{"role": "user", "content": prompt}],
                        }
                        if sys_prompt:
                            kwargs["system"] = sys_prompt
                            
                        response = self.client.messages.create(**kwargs)
                        
                        content = "".join(b.text for b in response.content if getattr(b, "type", "") == "text")
                        
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
                except anthropic.NotFoundError as e:
                    # Model mavjud emas, darhol keyingi modelga o'tish (qayta urinmasdan)
                    self.logger.warning(f"Model {model} topilmadi (404). Keyingi modelga o'tilmoqda...")
                    last_exception = e
                    break
                except Exception as e:
                    # Boshqa xatoliklar (masalan API key xato bo'lsa yoki 500 error)
                    # not_found_error bo'lsa tekshiramiz
                    if "not_found_error" in str(e):
                        self.logger.warning(f"Model {model} mavjud emas. Keyingi modelga o'tilmoqda...")
                        last_exception = e
                        break
                        
                    self.logger.warning(f"Model {model} bilan ulanishda xato: {e}")
                    last_exception = e
                    if attempt < retries:
                        time.sleep(2)
                
        self.logger.error(f"Hech qaysi AI modeli ishlamadi. Oxirgi xato: {last_exception}")
        self._trigger_all_models_failed_alert(last_exception)
        return None

    def _trigger_all_models_failed_alert(self, last_exception: Optional[Exception]):
        medium = getattr(self.config, "ai_model_medium", "claude-sonnet-5")
        weak = getattr(self.config, "ai_model_weak", "claude-haiku-4-5-20251001")
        msg = f"Ikkala model (o'rta: {medium}, kuchsiz: {weak}) ham ishlamadi — savdo qarorlari to'xtatildi"
        
        self.logger.critical(msg)
        
        telegram = getattr(self, "telegram", None)
        if telegram:
            try:
                telegram.send_message(f"🚨 IKKALA AI MODEL ISHLAMAYAPTI (o'rta va kuchsiz) — savdo qarorlari to'xtatildi\nXato: {last_exception}")
            except Exception as e:
                self.logger.error(f"Telegram alert xatosi: {e}")
                
        sync = getattr(self, "sync", None)
        if sync:
            try:
                sync.insert("ai_signals", {
                    "symbol": "SYSTEM",
                    "signal": "AI_OFFLINE",
                    "reasoning": f"{msg}: {last_exception}"
                })
            except Exception as e:
                self.logger.error(f"Supabase alert xatosi: {e}")

    def get_simple_response(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 10) -> str:
        selected_model = getattr(self.config, "ai_model", "auto")
        medium = getattr(self.config, "ai_model_medium", "claude-sonnet-5")
        weak = getattr(self.config, "ai_model_weak", "claude-haiku-4-5-20251001")
        
        if selected_model == "claude-sonnet-5":
            models_to_try = [medium]
        elif selected_model == "claude-haiku-4-5":
            models_to_try = [weak]
        else: # "auto"
            models_to_try = [weak, medium]
            
        models_to_try = list(dict.fromkeys(models_to_try))  # Remove duplicates preserving order

        import time
        import anthropic
        
        last_exception = None
        for model in models_to_try:
            retries = 2
            for attempt in range(retries):
                try:
                    if "moonshot" in model.lower() or "kimi" in model.lower():
                        if not getattr(self.config, "kimi_api_key", None):
                            raise Exception("KIMI_API_KEY is required for moonshot models")
                        headers = {
                            "Authorization": f"Bearer {self.config.kimi_api_key}",
                            "Content-Type": "application/json"
                        }
                        msgs = []
                        if system_prompt:
                            msgs.append({"role": "system", "content": system_prompt})
                        msgs.append({"role": "user", "content": prompt})
                        payload = {
                            "model": model,
                            "messages": msgs,
                            "max_tokens": max_tokens
                        }
                        resp = requests.post("https://api.moonshot.ai/v1/chat/completions", headers=headers, json=payload, timeout=120)
                        if resp.status_code != 200:
                            raise Exception(f"Moonshot Error {resp.status_code}: {resp.text}")
                        content = resp.json()["choices"][0]["message"]["content"]
                        return content.strip()
                    else:
                        if not self.client:
                            raise Exception("Anthropic API key is not configured or invalid.")
                        kwargs = {
                            "model": model,
                            "max_tokens": max_tokens,
                            "messages": [{"role": "user", "content": prompt}],
                        }
                        if system_prompt:
                            kwargs["system"] = system_prompt
                            
                        response = self.client.messages.create(**kwargs)
                        content = "".join(b.text for b in response.content if getattr(b, "type", "") == "text")
                        return content.strip()
                except anthropic.RateLimitError as e:
                    self.logger.warning(f"Rate limit for {model}: {e}")
                    last_exception = e
                    time.sleep(3)
                except Exception as e:
                    self.logger.error(f"Failed to get simple response with {model} (attempt {attempt+1}): {e}")
                    last_exception = e
                    if attempt < retries - 1:
                        time.sleep(2)
        
        self.logger.error(f"Hech qaysi AI modeli oddiy javob bera olmadi. Oxirgi xato: {last_exception}")
        return ""
