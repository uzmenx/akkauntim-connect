import json
import logging
import re
import time
from typing import Dict, Any, Optional
import requests
from anthropic import Anthropic

# HTTP statuses that mean "this account/key cannot use this model right now"
# (bad/missing key, no credits, forbidden). These are account-level and will
# NOT resolve by retrying the same request — unlike 429 (rate limit, transient)
# or 5xx (server-side, transient). Retrying these wastes time and, worse, does
# it again for every symbol in the scan loop.
PERMANENT_ERROR_CODES = {401, 402, 403}

# How long to stop trying a model after it fails with a permanent error,
# before giving it another chance (e.g. in case credits get topped up).
MODEL_COOLDOWN_SECONDS = 900  # 15 daqiqa


class PermanentAPIError(Exception):
    """Raised for account-level API errors (401/402/403) that retrying won't fix."""
    pass


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
        self.consecutive_failures = 0
        # model_name -> epoch time until which we skip it (see PermanentAPIError)
        self._model_cooldown_until: Dict[str, float] = {}
        # Dedup timestamp so get_simple_response doesn't spam Telegram once per symbol
        self._last_simple_response_alert = 0.0

    def _is_model_cooling_down(self, model: str) -> bool:
        return time.time() < self._model_cooldown_until.get(model, 0)

    def _start_cooldown(self, model: str, reason: str):
        self._model_cooldown_until[model] = time.time() + MODEL_COOLDOWN_SECONDS
        self.logger.warning(
            f"{model} {MODEL_COOLDOWN_SECONDS // 60} daqiqaga cooldown'ga qo'yildi (sabab: {reason})"
        )

    @staticmethod
    def _raise_if_permanent(resp, provider: str):
        """Call right after a requests.post — raises PermanentAPIError for
        account-level failures instead of the generic retryable Exception."""
        if resp.status_code in PERMANENT_ERROR_CODES:
            raise PermanentAPIError(f"{provider} Error {resp.status_code}: {resp.text}")
        if resp.status_code != 200:
            raise Exception(f"{provider} Error {resp.status_code}: {resp.text}")

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
        elif "openrouter" in m:
            in_price, out_price = 0.5, 2.0  # Default approx for OpenRouter
        else:  # Sonnet 3.5 / 4.x default
            in_price, out_price = 3.0, 15.0
        return (input_tokens * in_price / 1_000_000.0) + (output_tokens * out_price / 1_000_000.0)

    def get_decision(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: Optional[int] = None, model_tier: str = "auto") -> Dict[str, Any]:
        sys_prompt = system_prompt or self.config.ai_system_prompt
        max_tok = max_tokens or self.config.ai_max_tokens

        selected_model = getattr(self.config, "ai_model", "auto")
        medium = getattr(self.config, "ai_model_medium", "claude-sonnet-5")
        weak = getattr(self.config, "ai_model_weak", "claude-haiku-4-5-20251001")
        
        if model_tier == "weak":
            models_to_try = [weak]
        elif "," in selected_model:
            models_to_try = [m.strip() for m in selected_model.split(",") if m.strip()]
        elif selected_model == "auto":
            models_to_try = [medium, weak]
        elif selected_model == "claude-sonnet-5":
            models_to_try = [medium]
        elif selected_model == "claude-haiku-4-5":
            models_to_try = [weak]
        elif selected_model == "kimi-k3":
            models_to_try = ["kimi-k3"]
        else:
            models_to_try = [selected_model, weak]
            
        models_to_try = [m for m in dict.fromkeys(models_to_try) if m]  # Remove duplicates and empty strings

        import anthropic
        
        last_exception = None
        for model in models_to_try:
            if self._is_model_cooling_down(model):
                self.logger.debug(f"{model} cooldown'da, o'tkazib yuborilmoqda.")
                continue
            retries = 2
            for attempt in range(retries + 1):
                try:
                    response = None
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
                            
                        resp = requests.post("https://api.moonshot.ai/v1/chat/completions", headers=headers, json=payload, timeout=180)
                        self._raise_if_permanent(resp, "Moonshot")
                            
                        rdata = resp.json()
                        content = rdata["choices"][0]["message"]["content"]
                        in_tok = rdata.get("usage", {}).get("prompt_tokens", 0)
                        out_tok = rdata.get("usage", {}).get("completion_tokens", 0)
                    elif model.startswith("openrouter/"):
                        if not getattr(self.config, "openrouter_api_key", None):
                            raise Exception("OPENROUTER_API_KEY is required for OpenRouter models")
                        
                        or_model = model.replace("openrouter/", "")
                        headers = {
                            "Authorization": f"Bearer {self.config.openrouter_api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://akkauntim-connect.com", 
                            "X-Title": "Akkauntim Connect Bot"
                        }
                        msgs = []
                        if sys_prompt:
                            msgs.append({"role": "system", "content": sys_prompt})
                        msgs.append({"role": "user", "content": prompt})
                        
                        payload = {
                            "model": or_model,
                            "messages": msgs
                        }
                        if max_tok:
                            payload["max_tokens"] = max_tok
                            
                        resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=180)
                        self._raise_if_permanent(resp, "OpenRouter")
                            
                        rdata = resp.json()
                        content = rdata["choices"][0]["message"]["content"]
                        in_tok = rdata.get("usage", {}).get("prompt_tokens", 0)
                        out_tok = rdata.get("usage", {}).get("completion_tokens", 0)
                        
                        # Use total_cost if openrouter provides it, else fallback
                        or_cost = rdata.get("usage", {}).get("total_cost", 0)
                        if or_cost > 0:
                            self._or_cost = or_cost
                    else:
                        if not self.client:
                            raise Exception("Anthropic API key is not configured or invalid.")
                        kwargs = {
                            "model": model,
                            "max_tokens": max_tok,
                            "messages": [{"role": "user", "content": prompt}],
                            "timeout": 180,
                            "tools": [{
                                "type": "web_search_20250305",
                                "name": "web_search",
                                "max_uses": 2,
                            }],
                        }
                        if sys_prompt:
                            kwargs["system"] = [
                                {
                                    "type": "text",
                                    "text": sys_prompt,
                                    "cache_control": {"type": "ephemeral"}
                                }
                            ]
                            
                        response = self.client.messages.create(**kwargs)
                        
                        content = "".join(b.text for b in response.content if getattr(b, "type", "") == "text")
                        
                        # Tracking tokens and cost
                        in_tok = response.usage.input_tokens
                        out_tok = response.usage.output_tokens

                    self.total_tokens_in += in_tok
                    self.total_tokens_out += out_tok
                    
                    cost = getattr(self, "_or_cost", None)
                    if cost is not None:
                        delattr(self, "_or_cost")
                    else:
                        cost = self._calculate_cost(model, in_tok, out_tok)
                    
                    # To'g'ri web search cost hisob-kitobi (response.usage.server_tool_use orqali)
                    web_searches = 0
                    if hasattr(response, "usage") and response.usage:
                        usage_dict = response.usage.model_dump() if hasattr(response.usage, "model_dump") else (response.usage.__dict__ if hasattr(response.usage, "__dict__") else (response.usage if isinstance(response.usage, dict) else {}))
                        server_tool_usage = usage_dict.get("server_tool_use", {})
                        if getattr(response.usage, "server_tool_use", None):
                            # In newer anthropic versions, server_tool_use might be an object
                            stu = response.usage.server_tool_use
                            stu_dict = stu.model_dump() if hasattr(stu, "model_dump") else (stu.__dict__ if hasattr(stu, "__dict__") else (stu if isinstance(stu, dict) else {}))
                            web_searches = stu_dict.get("web_search_requests", 0)
                        elif isinstance(server_tool_usage, dict):
                            web_searches = server_tool_usage.get("web_search_requests", 0)
                            
                    # Eski formatdagi tool_use fallback
                    if web_searches == 0 and response and hasattr(response, "content"):
                        for b in response.content:
                            b_type = getattr(b, "type", "")
                            if b_type == "tool_use" and getattr(b, "name", "") == "web_search":
                                web_searches += 1
                                
                    search_cost = web_searches * 0.01
                            
                    cost += search_cost
                    self.total_cost += cost
                    self.logger.info(f"AI Call tokens: in={in_tok}, out={out_tok}, search_cost=${search_cost:.3f}, cost=${cost:.5f}")
                    
                    parsed_json = self._extract_json(content)
                    if parsed_json and isinstance(parsed_json, dict):
                        parsed_json["_web_search_used"] = int(search_cost / 0.01)
                    
                    self.consecutive_failures = 0
                    return parsed_json
                    
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
                except PermanentAPIError as e:
                    # 401/402/403 — hisob darajasidagi xato, qayta urinish foyda bermaydi.
                    # Modelni cooldown'ga qo'yib, darhol keyingi modelga o'tamiz.
                    self._start_cooldown(model, str(e))
                    last_exception = e
                    break
                except Exception as e:
                    # Boshqa xatoliklar (masalan API key xato bo'lsa yoki 500 error)
                    # not_found_error bo'lsa tekshiramiz
                    err_str = str(e)
                    if "not_found_error" in err_str or "No endpoints found" in err_str or "404" in err_str:
                        self.logger.warning(f"Model {model} mavjud emas. Keyingi modelga o'tilmoqda...")
                        last_exception = e
                        break
                        
                    self.logger.warning(f"Model {model} bilan ulanishda xato: {e}")
                    last_exception = e
                    if attempt < retries:
                        time.sleep(2)
                
        self.logger.error(f"Hech qaysi AI modeli ishlamadi. Oxirgi xato: {last_exception}")
        
        self.consecutive_failures += 1
        # ESLATMA: avval bu shart `len(models_to_try) == 1` bilan cheklangan edi —
        # amalda models_to_try deyarli hech qachon 1 ta bo'lmagani uchun (odatda
        # asosiy + zaxira model) bu xavfsizlik mexanizmi hech qachon ishga
        # tushmagan. Endi nechta model sinalganidan qat'iy nazar, 3 marta
        # ketma-ket muvaffaqiyatsizlikdan keyin ishga tushadi.
        if self.consecutive_failures >= 3:
            self.logger.critical("Ketma-ket 3 marta AI ishlamadi. Avtomatik AI-siz rejimga o'tilmoqda!")
            self.config.ai_enabled = False
            
            # Sinxronlash (frontend va database uchun)
            if hasattr(self, 'sync_callback') and self.sync_callback:
                self.sync_callback({"ai_enabled": False})
                
            self.consecutive_failures = 0
            if getattr(self, "telegram", None):
                try:
                    self.telegram.send_message("⚠️ AI Ketma-ket 3 marta ishlamadi. Bot avtomatik AI-siz rejimga o'tdi.")
                except Exception:
                    pass
                    
        self._trigger_all_models_failed_alert(last_exception, models_to_try)
        return None

    def _trigger_all_models_failed_alert(self, last_exception: Optional[Exception], models_tried: list = None):
        if not models_tried:
            models_tried = []
        msg = f"Quyidagi modellar ishlamadi: {', '.join(models_tried)} — savdo qarorlari to'xtatildi"
        
        self.logger.critical(msg)
        
        telegram = getattr(self, "telegram", None)
        if telegram:
            try:
                telegram.send_message(f"🚨 AI MODELLAR ISHLAMAYAPTI ({', '.join(models_tried)})\nXato: {last_exception}")
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

    def get_simple_response(self, prompt: str, system_prompt: Optional[str] = None, max_tokens: int = 10, model_tier: str = "auto") -> str:
        selected_model = getattr(self.config, "ai_model", "auto")
        medium = getattr(self.config, "ai_model_medium", "claude-sonnet-5")
        weak = getattr(self.config, "ai_model_weak", "claude-haiku-4-5-20251001")
        
        if model_tier == "weak":
            models_to_try = [weak]
        elif "," in selected_model:
            models_to_try = [m.strip() for m in selected_model.split(",") if m.strip()]
        elif selected_model == "auto":
            models_to_try = [weak, medium]
        elif selected_model == "claude-sonnet-5":
            models_to_try = [medium]
        elif selected_model == "claude-haiku-4-5":
            models_to_try = [weak]
        elif selected_model == "kimi-k3":
            models_to_try = ["kimi-k3"]
        else:
            models_to_try = [selected_model, weak]
            
        models_to_try = [m for m in dict.fromkeys(models_to_try) if m]  # Remove duplicates and empty strings

        import anthropic
        
        last_exception = None
        any_model_attempted = False
        for model in models_to_try:
            if self._is_model_cooling_down(model):
                self.logger.debug(f"{model} cooldown'da, o'tkazib yuborilmoqda (get_simple_response).")
                continue
            any_model_attempted = True
            retries = 2
            for attempt in range(retries):
                try:
                    response = None
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
                        self._raise_if_permanent(resp, "Moonshot")
                        content = resp.json()["choices"][0]["message"]["content"]
                        return content.strip()
                    elif model.startswith("openrouter/"):
                        if not getattr(self.config, "openrouter_api_key", None):
                            raise Exception("OPENROUTER_API_KEY is required for OpenRouter models")
                        
                        or_model = model.replace("openrouter/", "")
                        headers = {
                            "Authorization": f"Bearer {self.config.openrouter_api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://akkauntim-connect.com", 
                            "X-Title": "Akkauntim Connect Bot"
                        }
                        msgs = []
                        if system_prompt:
                            msgs.append({"role": "system", "content": system_prompt})
                        msgs.append({"role": "user", "content": prompt})
                        
                        payload = {
                            "model": or_model,
                            "messages": msgs,
                            "max_tokens": max_tokens
                        }
                        resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=120)
                        self._raise_if_permanent(resp, "OpenRouter")
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
                            kwargs["system"] = [
                                {
                                    "type": "text",
                                    "text": system_prompt,
                                    "cache_control": {"type": "ephemeral"}
                                }
                            ]
                            
                        response = self.client.messages.create(**kwargs)
                        content = "".join(b.text for b in response.content if getattr(b, "type", "") == "text")
                        return content.strip()
                except anthropic.RateLimitError as e:
                    self.logger.warning(f"Rate limit for {model}: {e}")
                    last_exception = e
                    time.sleep(3)
                except PermanentAPIError as e:
                    # Hisob darajasidagi xato (masalan kredit tugagan) — qayta
                    # urinish foyda bermaydi. Modelni cooldown'ga qo'yamiz va
                    # BU CHAQIRUV ICHIDA darhol keyingi modelga o'tamiz, shu
                    # bilan birga keyingi 94 juftlik/tsikl davomida ham bu
                    # model qayta-qayta urinilmaydi.
                    self.logger.error(f"{model}: {e}")
                    self._start_cooldown(model, str(e))
                    last_exception = e
                    break
                except Exception as e:
                    self.logger.error(f"Failed to get simple response with {model} (attempt {attempt+1}): {e}")
                    last_exception = e
                    err_str = str(e)
                    if "not_found_error" in err_str or "No endpoints found" in err_str or "404" in err_str:
                        break
                    if attempt < retries - 1:
                        time.sleep(2)

        if any_model_attempted:
            self.logger.error(f"Hech qaysi AI modeli oddiy javob bera olmadi. Oxirgi xato: {last_exception}")
            # Telegramga faqat 30 daqiqada bir marta ogohlantiramiz — 94 juftlik
            # tsiklida har safar spam qilmaslik uchun. Oldin bu funksiya
            # umuman Telegram'ga xabar bermas edi.
            now = time.time()
            if now - self._last_simple_response_alert > 1800:
                self._last_simple_response_alert = now
                telegram = getattr(self, "telegram", None)
                if telegram:
                    try:
                        telegram.send_message(
                            f"⚠️ AI (oddiy javob) ishlamayapti: {', '.join(models_to_try)}\nOxirgi xato: {last_exception}"
                        )
                    except Exception as tg_err:
                        self.logger.error(f"Telegram alert xatosi (get_simple_response): {tg_err}")
        return ""
