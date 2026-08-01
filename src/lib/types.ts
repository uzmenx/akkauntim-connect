export type BotSettings = {
  id: string;
  user_id: string;
  symbols: string[];
  risk_per_trade: number;
  max_daily_loss: number;
  min_confidence: number;
  max_lot_size: number;
  timeframe_major?: string;
  timeframe_minor?: string;
  ai_model?: string;
  ai_enabled?: boolean;
  shadow_mode?: boolean;
  system_prompt?: string;
  prompt_identity?: string;
  prompt_strategy?: string;
  prompt_output?: string;
  risk_level_single_confirmation?: number;
  risk_level_multiple_confirmation?: number;
  mt5_login?: string;
  mt5_password?: string;
  mt5_server?: string;
  mt5_terminal_path?: string;
  prompt_temporary?: string | null;
  prompt_temporary_expires_at?: string | null;
  strategy_weight_smc?: number;
  strategy_weight_pattern?: number;
  strategy_weight_news?: number;
  strategy_weight_wyckoff?: number;
  strategy_weight_sr_volume?: number;
  strategy_weight_auto_pattern?: number;
  loop_interval_minutes?: number;
  updated_at: string;
};

export type BotStatus = {
  id: string;
  user_id: string;
  is_running: boolean;
  last_heartbeat: string | null;
  account_balance: number | null;
  account_equity: number | null;
  account_currency: string | null;
  broker: string | null;
  message: string | null;
  claude_limit: number | null;
  claude_used: number | null;
  available_symbols?: Record<string, string[]> | null;
  market_sentiment?: number | null;
  updated_at: string;
};

export type Position = {
  id: string;
  ticket: number;
  symbol: string;
  side: "BUY" | "SELL" | string;
  volume: number;
  open_price: number;
  current_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  profit: number | null;
  opened_at: string;
  agreed_strategies?: string[];
  ai_used?: boolean;
};

export type PendingOrder = {
  id: string;
  ticket: number;
  symbol: string;
  type: string;
  volume: number;
  price: number;
  stop_loss: number | null;
  take_profit: number | null;
  created_at: string;
};

export type AISignal = {
  id: string;
  symbol: string;
  signal: "BUY" | "SELL" | "HOLD" | string;
  confidence: number;
  reasoning: string | null;
  entry_price: number | null;
  sl_price: number | null;
  tp_price: number | null;
  rr_ratio: number | null;
  stop_loss_pips: number | null;
  take_profit_pips: number | null;
  executed: boolean;
  rejection_reason: string | null;
  created_at: string;
};

export type TradeHistory = {
  id: string;
  ticket: number;
  symbol: string;
  side: string;
  volume: number;
  open_price: number;
  close_price: number;
  profit: number;
  opened_at: string;
  closed_at: string;
  agreed_strategies?: string[];
  ai_used?: boolean;
};
