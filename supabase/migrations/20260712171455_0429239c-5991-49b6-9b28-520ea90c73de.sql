
-- 1) bot_settings
CREATE TABLE public.bot_settings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  symbols text[] NOT NULL DEFAULT ARRAY['EURUSD']::text[],
  risk_per_trade numeric NOT NULL DEFAULT 0.02,
  max_daily_loss numeric NOT NULL DEFAULT 0.10,
  min_confidence integer NOT NULL DEFAULT 50,
  max_lot_size numeric NOT NULL DEFAULT 5.0,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id)
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.bot_settings TO authenticated;
GRANT ALL ON public.bot_settings TO service_role;
ALTER TABLE public.bot_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own bot_settings" ON public.bot_settings FOR ALL
  USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- 2) bot_status
CREATE TABLE public.bot_status (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  is_running boolean NOT NULL DEFAULT false,
  last_heartbeat timestamptz,
  account_balance numeric,
  account_equity numeric,
  account_currency text,
  broker text,
  message text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id)
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.bot_status TO authenticated;
GRANT ALL ON public.bot_status TO service_role;
ALTER TABLE public.bot_status ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own bot_status" ON public.bot_status FOR ALL
  USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- 3) positions (ochiq savdolar)
CREATE TABLE public.positions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  ticket bigint NOT NULL,
  symbol text NOT NULL,
  side text NOT NULL,
  volume numeric NOT NULL,
  open_price numeric NOT NULL,
  current_price numeric,
  stop_loss numeric,
  take_profit numeric,
  profit numeric DEFAULT 0,
  opened_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, ticket)
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.positions TO authenticated;
GRANT ALL ON public.positions TO service_role;
ALTER TABLE public.positions ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own positions" ON public.positions FOR ALL
  USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- 4) ai_signals
CREATE TABLE public.ai_signals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  symbol text NOT NULL,
  signal text NOT NULL,
  confidence integer NOT NULL,
  reasoning text,
  stop_loss_pips numeric,
  take_profit_pips numeric,
  executed boolean NOT NULL DEFAULT false,
  rejection_reason text,
  created_at timestamptz NOT NULL DEFAULT now()
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.ai_signals TO authenticated;
GRANT ALL ON public.ai_signals TO service_role;
ALTER TABLE public.ai_signals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own ai_signals" ON public.ai_signals FOR ALL
  USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE INDEX ai_signals_user_created_idx ON public.ai_signals(user_id, created_at DESC);

-- 5) trade_history (yopilgan)
CREATE TABLE public.trade_history (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  ticket bigint NOT NULL,
  symbol text NOT NULL,
  side text NOT NULL,
  volume numeric NOT NULL,
  open_price numeric NOT NULL,
  close_price numeric NOT NULL,
  stop_loss numeric,
  take_profit numeric,
  profit numeric NOT NULL DEFAULT 0,
  opened_at timestamptz NOT NULL,
  closed_at timestamptz NOT NULL DEFAULT now(),
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(user_id, ticket)
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.trade_history TO authenticated;
GRANT ALL ON public.trade_history TO service_role;
ALTER TABLE public.trade_history ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own trade_history" ON public.trade_history FOR ALL
  USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE INDEX trade_history_user_closed_idx ON public.trade_history(user_id, closed_at DESC);

-- updated_at trigger
CREATE OR REPLACE FUNCTION public.tg_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql SET search_path = public AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END; $$;

CREATE TRIGGER trg_bot_settings_upd BEFORE UPDATE ON public.bot_settings
  FOR EACH ROW EXECUTE FUNCTION public.tg_set_updated_at();
CREATE TRIGGER trg_bot_status_upd BEFORE UPDATE ON public.bot_status
  FOR EACH ROW EXECUTE FUNCTION public.tg_set_updated_at();
CREATE TRIGGER trg_positions_upd BEFORE UPDATE ON public.positions
  FOR EACH ROW EXECUTE FUNCTION public.tg_set_updated_at();
