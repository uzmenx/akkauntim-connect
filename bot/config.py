import os
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

@dataclass
class BotConfig:
    # .env values
    anthropic_api_key: str = ""
    mt5_login: int = 0
    mt5_password: str = ""
    mt5_server: str = ""
    
    supabase_url: str = ""
    supabase_key: str = ""
    bot_sync_secret: str = ""

    # config.json values
    trading_symbols: List[str] = field(default_factory=list)
    timeframe_major: str = "H1"
    timeframe_minor: str = "M5"
    loop_interval_minutes: int = 5
    risk_level_single_confirmation: float = 1.0
    risk_level_multiple_confirmation: float = 2.0
    ai_model: str = "claude-sonnet-4-6"
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
    allow_single_strategy_trade: bool = True
    news_lookback_hours: int = 24
    ai_max_tokens: int = 2000
    ai_models_fallback: List[str] = field(default_factory=lambda: [
        "claude-sonnet-4-6",
        "claude-sonnet-5",
        "claude-sonnet-4-5-20250929",
        "claude-haiku-4-5-20251001",
        "claude-fable-5"
    ])

    @classmethod
    def load(cls, env_path: str = ".env", config_path: str = "config.json") -> "BotConfig":
        config = cls()
        config.load_env(env_path)
        config.load_config(config_path)
        return config

    def load_env(self, env_path: str = ".env") -> None:
        load_dotenv(env_path)
        self.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        
        try:
            self.mt5_login = int(os.environ.get("MT5_LOGIN", "0"))
        except ValueError:
            self.mt5_login = 0
            
        self.mt5_password = os.environ.get("MT5_PASSWORD", "")
        self.mt5_server = os.environ.get("MT5_SERVER", "")
        
        self.supabase_url = os.environ.get("SUPABASE_URL", os.environ.get("VITE_SUPABASE_URL", ""))
        self.supabase_key = os.environ.get("SUPABASE_PUBLISHABLE_KEY", os.environ.get("VITE_SUPABASE_PUBLISHABLE_KEY", ""))
        self.bot_sync_secret = os.environ.get("BOT_SYNC_SECRET", "")

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
                    self.ai_model = ai.get("model", self.ai_model)
                    self.ai_system_prompt = ai.get("system_prompt", self.ai_system_prompt)
        except Exception as e:
            import logging
            logging.error(f"Error loading config.json: {e}")
