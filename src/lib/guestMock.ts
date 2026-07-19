import type { BotSettings, BotStatus, Position, AISignal, TradeHistory } from "./types";

const MOCK_STATUS_KEY = "guest_bot_status";
const MOCK_POSITIONS_KEY = "guest_positions";
const MOCK_HISTORY_KEY = "guest_history";
const MOCK_SIGNALS_KEY = "guest_signals";
const MOCK_SETTINGS_KEY = "guest_bot_settings";

const defaultStatus = (): BotStatus => ({
  id: "guest-status",
  user_id: "guest",
  is_running: true,
  last_heartbeat: new Date().toISOString(),
  account_balance: 52002.50,
  account_equity: 52850.20,
  account_currency: "USD",
  broker: "MetaQuotes Software Corp.",
  message: "Panel running in Demo Mode",
  claude_limit: 20.0,
  claude_used: 4.5,
  updated_at: new Date().toISOString(),
});

const defaultPositions = (): Position[] => [
  {
    id: "mock-pos-1",
    ticket: 12345678,
    symbol: "EURUSD",
    side: "BUY",
    volume: 1.5,
    open_price: 1.08500,
    current_price: 1.08780,
    stop_loss: 1.08200,
    take_profit: 1.09200,
    profit: 420.50,
    opened_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: "mock-pos-2",
    ticket: 87654321,
    symbol: "XAUUSD",
    side: "SELL",
    volume: 2.0,
    open_price: 2350.50,
    current_price: 2348.36,
    stop_loss: 2360.00,
    take_profit: 2330.00,
    profit: 428.00,
    opened_at: new Date(Date.now() - 10800000).toISOString(),
  }
];

const defaultHistory = (): TradeHistory[] => [
  {
    id: "mock-hist-1",
    ticket: 11112222,
    symbol: "GBPUSD",
    side: "BUY",
    volume: 1.0,
    open_price: 1.27200,
    close_price: 1.27850,
    profit: 650.00,
    opened_at: new Date(Date.now() - 25000000).toISOString(),
    closed_at: new Date(Date.now() - 18000000).toISOString(),
  },
  {
    id: "mock-hist-2",
    ticket: 33334444,
    symbol: "EURUSD",
    side: "SELL",
    volume: 1.0,
    open_price: 1.08900,
    close_price: 1.08650,
    profit: 250.00,
    opened_at: new Date(Date.now() - 50000000).toISOString(),
    closed_at: new Date(Date.now() - 43200000).toISOString(),
  },
  {
    id: "mock-hist-3",
    ticket: 55556666,
    symbol: "XAUUSD",
    side: "BUY",
    volume: 1.5,
    open_price: 2340.00,
    close_price: 2335.00,
    profit: -750.00,
    opened_at: new Date(Date.now() - 80000000).toISOString(),
    closed_at: new Date(Date.now() - 72000000).toISOString(),
  }
];

const defaultSignals = (): AISignal[] => [
  {
    id: "mock-sig-1",
    symbol: "EURUSD",
    signal: "BUY",
    confidence: 85,
    reasoning: "SMC trend is bullish, H1 harmonic pattern detected at major support. News impact is minimal for the next 4 hours.",
    stop_loss_pips: 30,
    take_profit_pips: 60,
    executed: true,
    rejection_reason: null,
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: "mock-sig-2",
    symbol: "XAUUSD",
    signal: "SELL",
    confidence: 72,
    reasoning: "Resistance block hit on high timeframe. Bearish divergence visible on M5 structures.",
    stop_loss_pips: 50,
    take_profit_pips: 150,
    executed: true,
    rejection_reason: null,
    created_at: new Date(Date.now() - 10800000).toISOString(),
  },
  {
    id: "mock-sig-3",
    symbol: "GBPUSD",
    signal: "BUY",
    confidence: 92,
    reasoning: "Multiple confirmations from harmonic patterns and liquidity sweeps at lower range boundary.",
    stop_loss_pips: 25,
    take_profit_pips: 75,
    executed: false,
    rejection_reason: "Risk limit exceeded (Drawdown protection active)",
    created_at: new Date(Date.now() - 25000000).toISOString(),
  }
];

const defaultSettings = (): BotSettings => ({
  id: "guest-settings",
  user_id: "guest",
  symbols: ["EURUSD", "GBPUSD", "XAUUSD"],
  risk_per_trade: 0.02,
  max_daily_loss: 0.10,
  min_confidence: 50,
  max_lot_size: 5.0,
  timeframe_major: "H1",
  timeframe_minor: "M5",
  ai_model: "claude-3-5-sonnet-20241022",
  prompt_identity: "Sen professional Forex treyderi va fundamental tahlilchisisan.",
  prompt_strategy: "SMC, Garmonik patternlar va Iqtisodiy yangiliklarni birlashtirib eng yaxshi nuqtadan savdoga kirish qarorini qabul qilgin.",
  prompt_output: 'JAVOBNI FAQAT quyidagi JSON formatida qaytar, boshqa hech qanday izoh yoki tushuntirish yozma. Format: {"signal": "BUY" | "SELL" | "HOLD", "confidence": 0-100, "reasoning": "...", "stop_loss_pips": 20, "take_profit_pips": 40}',
  risk_level_single_confirmation: 0.01,
  risk_level_multiple_confirmation: 0.02,
  strategy_weight_smc: 60,
  strategy_weight_pattern: 60,
  strategy_weight_news: 60,
  updated_at: new Date().toISOString(),
});

export const guestMock = {
  getBotStatus: (): BotStatus => {
    const item = localStorage.getItem(MOCK_STATUS_KEY);
    if (!item) {
      const val = defaultStatus();
      localStorage.setItem(MOCK_STATUS_KEY, JSON.stringify(val));
      return val;
    }
    return JSON.parse(item);
  },
  saveBotStatus: (status: Partial<BotStatus>) => {
    const curr = guestMock.getBotStatus();
    const updated = { ...curr, ...status, updated_at: new Date().toISOString() };
    localStorage.setItem(MOCK_STATUS_KEY, JSON.stringify(updated));
    return updated;
  },

  getPositions: (): Position[] => {
    const item = localStorage.getItem(MOCK_POSITIONS_KEY);
    if (!item) {
      const val = defaultPositions();
      localStorage.setItem(MOCK_POSITIONS_KEY, JSON.stringify(val));
      return val;
    }
    return JSON.parse(item);
  },
  savePositions: (positions: Position[]) => {
    localStorage.setItem(MOCK_POSITIONS_KEY, JSON.stringify(positions));
  },

  getHistory: (): TradeHistory[] => {
    const item = localStorage.getItem(MOCK_HISTORY_KEY);
    if (!item) {
      const val = defaultHistory();
      localStorage.setItem(MOCK_HISTORY_KEY, JSON.stringify(val));
      return val;
    }
    return JSON.parse(item);
  },
  saveHistory: (history: TradeHistory[]) => {
    localStorage.setItem(MOCK_HISTORY_KEY, JSON.stringify(history));
  },

  getSignals: (): AISignal[] => {
    const item = localStorage.getItem(MOCK_SIGNALS_KEY);
    if (!item) {
      const val = defaultSignals();
      localStorage.setItem(MOCK_SIGNALS_KEY, JSON.stringify(val));
      return val;
    }
    return JSON.parse(item);
  },
  saveSignals: (signals: AISignal[]) => {
    localStorage.setItem(MOCK_SIGNALS_KEY, JSON.stringify(signals));
  },

  getSettings: (): BotSettings => {
    const item = localStorage.getItem(MOCK_SETTINGS_KEY);
    if (!item) {
      const val = defaultSettings();
      localStorage.setItem(MOCK_SETTINGS_KEY, JSON.stringify(val));
      return val;
    }
    return JSON.parse(item);
  },
  saveSettings: (settings: Partial<BotSettings>) => {
    const curr = guestMock.getSettings();
    const updated = { ...curr, ...settings, updated_at: new Date().toISOString() };
    localStorage.setItem(MOCK_SETTINGS_KEY, JSON.stringify(updated));
    return updated;
  },
};
