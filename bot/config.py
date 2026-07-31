import os
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

@dataclass
class BotConfig:
    # .env values
    anthropic_api_key: str = ""
    kimi_api_key: str = ""
    openrouter_api_key: str = ""
    mt5_login: int = 0
    mt5_password: str = ""
    mt5_server: str = ""
    
    supabase_url: str = ""
    supabase_key: str = ""
    bot_sync_secret: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # config.json values
    trading_symbols: List[str] = field(default_factory=list)
    timeframe_major: str = "H1"
    timeframe_minor: str = "M5"
    loop_interval_minutes: int = 5
    risk_level_single_confirmation: float = 1.0
    risk_level_multiple_confirmation: float = 2.0
    ai_enabled: bool = True
    ai_model_medium: str = "kimi-k3"
    ai_model_weak: str = "kimi-k3"
    ai_model: str = "kimi-k3"
    ai_system_prompt: str = ""
    
    # Hardcoded defaults
    magic_number: int = 234000
    max_daily_loss_pct: float = 0.10
    min_confidence: int = 50
    max_lot_size: float = 5.0
    risk_per_trade: float = 0.02
    deviation: int = 20
    strategy_weight_smc: int = 60
    strategy_weight_pattern: int = 60
    strategy_weight_news: int = 60
    allow_single_strategy_trade: bool = False
    news_lookback_hours: int = 24
    max_spread_multiplier: float = 4.0
    ai_max_tokens: int = 4000
    
    # Yangi xususiyatlar
    auto_discover_symbols: bool = True
    batch_size: int = 3
    
    # Drawdown-based risk reduction
    drawdown_threshold_pct: float = 0.05
    drawdown_risk_multiplier: float = 0.5
    
    # 4-Bosqich: Live Shadow Mode
    shadow_mode: bool = True

    @classmethod
    def load(cls, env_path: str = ".env", config_path: str = "config.json") -> "BotConfig":
        config = cls()
        config.load_env(env_path)
        config.load_config(config_path)
        return config

    def load_env(self, env_path: str = ".env") -> None:
        load_dotenv(env_path)
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.kimi_api_key = os.environ.get("KIMI_API_KEY", "")
        self.openrouter_api_key = os.environ.get("OPENROUTER_API_KEY", "")
        
        try:
            self.mt5_login = int(os.environ.get("MT5_LOGIN", "0"))
        except ValueError:
            self.mt5_login = 0
            
        self.mt5_password = os.environ.get("MT5_PASSWORD", "")
        self.mt5_server = os.environ.get("MT5_SERVER", "")
        
        self.supabase_url = os.environ.get("SUPABASE_URL", os.environ.get("VITE_SUPABASE_URL", ""))
        self.supabase_key = os.environ.get("SUPABASE_PUBLISHABLE_KEY", os.environ.get("VITE_SUPABASE_PUBLISHABLE_KEY", ""))
        self.bot_sync_secret = os.environ.get("BOT_SYNC_SECRET", "")
        self.telegram_bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        self.telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "@avlodona")

    def load_config(self, config_path: str = "config.json") -> None:
        try:
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
                    trading = data.get("trading", {})
                    if "symbols" in trading:
                        self.trading_symbols = trading["symbols"]
                    self.timeframe_major = trading.get("timeframe_major", self.timeframe_major)
                    self.timeframe_minor = trading.get("timeframe_minor", self.timeframe_minor)
                    self.loop_interval_minutes = trading.get("loop_interval_minutes", self.loop_interval_minutes)
                    self.risk_level_single_confirmation = trading.get("risk_level_single_confirmation", self.risk_level_single_confirmation)
                    self.risk_level_multiple_confirmation = trading.get("risk_level_multiple_confirmation", self.risk_level_multiple_confirmation)
                    
                    ai = data.get("ai", {})
                    self.ai_model_medium = ai.get("model_medium", self.ai_model_medium)
                    self.ai_model_weak = ai.get("model_weak", self.ai_model_weak)
                    self.ai_system_prompt = ai.get("system_prompt", self.ai_system_prompt)
                    
                    self.shadow_mode = data.get("shadow_mode", self.shadow_mode)
        except Exception as e:
            import logging
            logging.error(f"Error loading config.json: {e}")

    def update_from_dict(self, data: dict) -> None:
        """Supabase'dan kelgan sozlamalar bilan config ni yangilash."""
        if not data:
            return
            
        if "symbols" in data and isinstance(data["symbols"], list):
            self.trading_symbols = data["symbols"]
            if "AUTO" in [s.upper() for s in self.trading_symbols]:
                self.auto_discover_symbols = True
            else:
                self.auto_discover_symbols = False
            
        if "timeframe_major" in data:
            self.timeframe_major = data["timeframe_major"]
            
        if "timeframe_minor" in data:
            self.timeframe_minor = data["timeframe_minor"]
            
        if "loop_interval_minutes" in data:
            self.loop_interval_minutes = int(data["loop_interval_minutes"])
            
        if "ai_enabled" in data:
            self.ai_enabled = bool(data["ai_enabled"])
            
        if data.get("ai_model"):
            self.ai_model = data["ai_model"]
            
        if data.get("ai_model_medium"):
            self.ai_model_medium = data["ai_model_medium"]
            
        if data.get("ai_model_weak"):
            self.ai_model_weak = data["ai_model_weak"]
            
        if "max_daily_loss" in data:
            self.max_daily_loss_pct = float(data["max_daily_loss"])
            
        if "max_lot_size" in data:
            self.max_lot_size = float(data["max_lot_size"])
            
        if "risk_per_trade" in data:
            self.risk_per_trade = float(data["risk_per_trade"])
            
        if "min_confidence" in data:
            self.min_confidence = int(data["min_confidence"])
            
        if "strategy_weight_smc" in data:
            self.strategy_weight_smc = int(data["strategy_weight_smc"])
            
        if "strategy_weight_pattern" in data:
            self.strategy_weight_pattern = int(data["strategy_weight_pattern"])
            
        if "strategy_weight_news" in data:
            self.strategy_weight_news = int(data["strategy_weight_news"])
            
        if "max_spread_multiplier" in data:
            self.max_spread_multiplier = float(data["max_spread_multiplier"])
            
        if "drawdown_threshold_pct" in data:
            self.drawdown_threshold_pct = float(data["drawdown_threshold_pct"])
            
        if "drawdown_risk_multiplier" in data:
            self.drawdown_risk_multiplier = float(data["drawdown_risk_multiplier"])
            
        if "prompt_identity" in data or "prompt_strategy" in data or "prompt_output" in data:
            identity = data.get("prompt_identity", "")
            strategy = data.get("prompt_strategy", "")
            output = data.get("prompt_output", "")
            temp = data.get("prompt_temporary", "")
            
            sys_prompt = f"{identity}\n\nQOIDALAR:\n{strategy}\n\n"
            if temp:
                sys_prompt += f"QO'SHIMCHA KO'RSATMA: {temp}\n\n"
            sys_prompt += f"FORMAT: {output}"
            self.ai_system_prompt = sys_prompt
