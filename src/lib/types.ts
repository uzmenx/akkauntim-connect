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
  system_prompt?: string;
  risk_level_single_confirmation?: number;
  risk_level_multiple_confirmation?: number;
  mt5_login?: string;
  mt5_password?: string;
  mt5_server?: string;
  mt5_terminal_path?: string;
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
};

export type AISignal = {
  id: string;
  symbol: string;
  signal: "BUY" | "SELL" | "HOLD" | string;
  confidence: number;
  reasoning: string | null;
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
};
