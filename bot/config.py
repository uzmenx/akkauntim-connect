import os
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*args, **kwargs):
        pass

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
    ai_model_medium: str = "openrouter/deepseek/deepseek-chat"
    ai_model_weak: str = "openrouter/deepseek/deepseek-chat"
    ai_model: str = "openrouter/deepseek/deepseek-chat"
    ai_system_prompt: str = ""
    
    # Hardcoded defaults
    magic_number: int = 234000
    max_daily_loss_pct: float = 1.00
    min_confidence: int = 40
    max_lot_size: float = 5.0
    risk_per_trade: float = 0.02
    deviation: int = 20
    strategy_weight_smc: int = 40
    strategy_weight_pattern: int = 40
    strategy_weight_news: int = 40
    allow_single_strategy_trade: bool = True
    news_lookback_hours: int = 24
    max_spread_multiplier: float = 4.0
    symbol_spread_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "JPY": 5.0,
        "XAU": 3.0,
        "XAG": 3.0
    })
    ai_max_tokens: int = 300
    
    # Session Blackout (Illiquidity / Rollover / Session Open protection)
    session_blackout_enabled: bool = True
    session_blackout_windows: List[Dict[str, str]] = field(default_factory=lambda: [
        {"start": "21:45", "end": "22:15", "name": "NY_Close_Rollover"},
        {"start": "23:55", "end": "00:15", "name": "Sydney_Open_Reset"},
        {"start": "07:55", "end": "08:05", "name": "London_Open_Vol"}
    ])
    
    # News Breakout Grid Strategy
    news_breakout_grid_enabled: bool = False
    news_breakout_grid_symbols: List[str] = field(default_factory=list)
    news_breakout_grid_max_daily_loss_pct: float = 0.40
    news_breakout_grid_max_attempts_per_day: int = 15
    news_breakout_grid_hard_timeout_sec: int = 60
    news_breakout_grid_order_count: int = 10
    news_breakout_grid_step_points: int = 60
    news_breakout_grid_lot_size: float = 0.01
    news_breakout_grid_dynamic_scaling: bool = True
    news_breakout_grid_base_balance: float = 100.0 # Base balance for 0.01 lot

    # Yangi xususiyatlar
    auto_discover_symbols: bool = False
    batch_size: int = 3
    
    # Drawdown-based risk reduction
    drawdown_threshold_pct: float = 0.05
    drawdown_risk_multiplier: float = 0.5
    
    # 4-Bosqich: Live Shadow Mode
    shadow_mode: bool = True

    # 5-Bosqich: Shadow AI Autonomous Mode
    ai_mode: str = "auto"  # "api" | "hybrid" | "shadow" | "auto"
    shadow_min_confidence: float = 0.55
    shadow_min_agreement_sources: int = 2
    shadow_model_dir: str = "bot/learning"
    shadow_production_min_f1: float = 45.0
    shadow_production_min_samples: int = 500

    # Shadow AI Autonomous Trading parameters
    allow_shadow_trading: bool = True
    shadow_risk_per_trade: float = 0.01
    shadow_max_trades_per_day: int = 1000000

    realtime_enabled: bool = False
    loop_interval_seconds: int = 15

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
        self.supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", os.environ.get("SUPABASE_PUBLISHABLE_KEY", os.environ.get("VITE_SUPABASE_PUBLISHABLE_KEY", "")))
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
                    self.realtime_enabled = trading.get("realtime_enabled", self.realtime_enabled)
                    self.loop_interval_seconds = trading.get("loop_interval_seconds", self.loop_interval_seconds)
                    self.risk_level_single_confirmation = trading.get("risk_level_single_confirmation", self.risk_level_single_confirmation)
                    self.risk_level_multiple_confirmation = trading.get("risk_level_multiple_confirmation", self.risk_level_multiple_confirmation)
                    
                    self.magic_number = trading.get("magic_number", self.magic_number)
                    self.max_daily_loss_pct = trading.get("max_daily_loss_pct", self.max_daily_loss_pct)
                    self.min_confidence = trading.get("min_confidence", self.min_confidence)
                    self.max_lot_size = trading.get("max_lot_size", self.max_lot_size)
                    self.risk_per_trade = trading.get("risk_per_trade", self.risk_per_trade)
                    self.deviation = trading.get("deviation", self.deviation)
                    self.strategy_weight_smc = trading.get("strategy_weight_smc", self.strategy_weight_smc)
                    self.strategy_weight_pattern = trading.get("strategy_weight_pattern", self.strategy_weight_pattern)
                    self.strategy_weight_news = trading.get("strategy_weight_news", self.strategy_weight_news)
                    self.allow_single_strategy_trade = trading.get("allow_single_strategy_trade", self.allow_single_strategy_trade)
                    self.session_blackout_enabled = trading.get("session_blackout_enabled", self.session_blackout_enabled)
                    if "session_blackout_windows" in trading and isinstance(trading["session_blackout_windows"], list):
                        self.session_blackout_windows = trading["session_blackout_windows"]
                    self.max_spread_multiplier = trading.get("max_spread_multiplier", self.max_spread_multiplier)
                    if "symbol_spread_multipliers" in trading and isinstance(trading["symbol_spread_multipliers"], dict):
                        self.symbol_spread_multipliers = trading["symbol_spread_multipliers"]
                    
                    ai = data.get("ai", {})
                    self.ai_model = ai.get("model", self.ai_model)
                    self.ai_model_medium = ai.get("model_medium", self.ai_model_medium)
                    self.ai_model_weak = ai.get("model_weak", self.ai_model_weak)
                    self.ai_system_prompt = ai.get("system_prompt", self.ai_system_prompt)
                    
                    self.shadow_mode = data.get("shadow_mode", self.shadow_mode)

                    # Shadow AI Autonomous Mode sozlamalari
                    shadow = data.get("shadow", {})
                    self.ai_mode = shadow.get("ai_mode", self.ai_mode)
                    self.shadow_min_confidence = shadow.get("min_confidence", self.shadow_min_confidence)
                    self.shadow_min_agreement_sources = shadow.get("min_agreement_sources", self.shadow_min_agreement_sources)
                    self.shadow_model_dir = shadow.get("model_dir", self.shadow_model_dir)
                    self.shadow_production_min_f1 = shadow.get("production_min_f1", self.shadow_production_min_f1)
                    self.shadow_production_min_samples = shadow.get("production_min_samples", self.shadow_production_min_samples)

                    self.allow_shadow_trading = shadow.get("allow_shadow_trading", self.allow_shadow_trading)
                    self.shadow_risk_per_trade = shadow.get("risk_per_trade", self.shadow_risk_per_trade)
                    self.shadow_max_trades_per_day = shadow.get("max_trades_per_day", self.shadow_max_trades_per_day)
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
            
        if "session_blackout_enabled" in data:
            self.session_blackout_enabled = bool(data["session_blackout_enabled"])
            
        if "session_blackout_windows" in data and isinstance(data["session_blackout_windows"], list):
            self.session_blackout_windows = data["session_blackout_windows"]
            
        if "drawdown_threshold_pct" in data:
            self.drawdown_threshold_pct = float(data["drawdown_threshold_pct"])
            
        if "drawdown_risk_multiplier" in data:
            self.drawdown_risk_multiplier = float(data["drawdown_risk_multiplier"])
            
        if "news_breakout_grid_enabled" in data:
            self.news_breakout_grid_enabled = bool(data["news_breakout_grid_enabled"])
            
        if "news_breakout_grid_symbols" in data and isinstance(data["news_breakout_grid_symbols"], list):
            self.news_breakout_grid_symbols = data["news_breakout_grid_symbols"]
            
        if "news_breakout_grid_max_daily_loss_pct" in data:
            self.news_breakout_grid_max_daily_loss_pct = float(data["news_breakout_grid_max_daily_loss_pct"])
            
        if "news_breakout_grid_max_attempts_per_day" in data:
            self.news_breakout_grid_max_attempts_per_day = int(data["news_breakout_grid_max_attempts_per_day"])
            
        if "news_breakout_grid_hard_timeout_sec" in data:
            self.news_breakout_grid_hard_timeout_sec = int(data["news_breakout_grid_hard_timeout_sec"])
            
        if "news_breakout_grid_order_count" in data:
            self.news_breakout_grid_order_count = int(data["news_breakout_grid_order_count"])
            
        if "news_breakout_grid_step_points" in data:
            self.news_breakout_grid_step_points = int(data["news_breakout_grid_step_points"])
            
        if "news_breakout_grid_lot_size" in data:
            self.news_breakout_grid_lot_size = float(data["news_breakout_grid_lot_size"])
            
        if "news_breakout_grid_dynamic_scaling" in data:
            self.news_breakout_grid_dynamic_scaling = bool(data["news_breakout_grid_dynamic_scaling"])
            
        if "shadow_mode" in data:
            self.shadow_mode = bool(data["shadow_mode"])
            
        # Shadow AI Autonomous Mode
        if "ai_mode" in data:
            self.ai_mode = str(data["ai_mode"])
        if "shadow_min_confidence" in data:
            self.shadow_min_confidence = float(data["shadow_min_confidence"])
        if "shadow_min_agreement_sources" in data:
            self.shadow_min_agreement_sources = int(data["shadow_min_agreement_sources"])

        if "allow_shadow_trading" in data:
            self.allow_shadow_trading = bool(data["allow_shadow_trading"])
        if "shadow_risk_per_trade" in data:
            self.shadow_risk_per_trade = float(data["shadow_risk_per_trade"])
        if "shadow_max_trades_per_day" in data:
            self.shadow_max_trades_per_day = int(data["shadow_max_trades_per_day"])
            
        if "realtime_enabled" in data:
            self.realtime_enabled = bool(data["realtime_enabled"])
        if "loop_interval_seconds" in data:
            self.loop_interval_seconds = int(data["loop_interval_seconds"])

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
