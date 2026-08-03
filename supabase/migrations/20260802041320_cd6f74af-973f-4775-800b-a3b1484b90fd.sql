CREATE TABLE public.shadow_candles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol text NOT NULL,
  timeframe text NOT NULL,
  open_time timestamptz NOT NULL,
  open numeric NOT NULL,
  high numeric NOT NULL,
  low numeric NOT NULL,
  close numeric NOT NULL,
  volume numeric,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT shadow_candles_unique UNIQUE (symbol, timeframe, open_time)
);
GRANT SELECT ON public.shadow_candles TO anon, authenticated;
GRANT ALL ON public.shadow_candles TO service_role;
ALTER TABLE public.shadow_candles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "shadow_candles public read" ON public.shadow_candles FOR SELECT TO anon, authenticated USING (true);
CREATE INDEX shadow_candles_lookup ON public.shadow_candles (symbol, timeframe, open_time DESC);
CREATE TRIGGER shadow_candles_updated_at BEFORE UPDATE ON public.shadow_candles FOR EACH ROW EXECUTE FUNCTION public.tg_set_updated_at();

CREATE TABLE public.shadow_signals (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  symbol text NOT NULL,
  timeframe text NOT NULL,
  candle_time timestamptz NOT NULL,
  signal text NOT NULL,
  score numeric NOT NULL,
  features jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT shadow_signals_unique UNIQUE (symbol, timeframe, candle_time)
);
GRANT SELECT ON public.shadow_signals TO anon, authenticated;
GRANT ALL ON public.shadow_signals TO service_role;
ALTER TABLE public.shadow_signals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "shadow_signals public read" ON public.shadow_signals FOR SELECT TO anon, authenticated USING (true);
CREATE INDEX shadow_signals_lookup ON public.shadow_signals (symbol, timeframe, candle_time DESC);
CREATE TRIGGER shadow_signals_updated_at BEFORE UPDATE ON public.shadow_signals FOR EACH ROW EXECUTE FUNCTION public.tg_set_updated_at();

CREATE TABLE public.shadow_outcomes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  signal_id uuid NOT NULL REFERENCES public.shadow_signals(id) ON DELETE CASCADE,
  evaluated_at timestamptz NOT NULL DEFAULT now(),
  price_at_signal numeric NOT NULL,
  price_after_n_candles numeric NOT NULL,
  n_candles integer NOT NULL DEFAULT 3,
  was_correct boolean NOT NULL,
  pips_result numeric,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT shadow_outcomes_signal_unique UNIQUE (signal_id)
);
GRANT SELECT ON public.shadow_outcomes TO anon, authenticated;
GRANT ALL ON public.shadow_outcomes TO service_role;
ALTER TABLE public.shadow_outcomes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "shadow_outcomes public read" ON public.shadow_outcomes FOR SELECT TO anon, authenticated USING (true);
CREATE INDEX shadow_outcomes_signal ON public.shadow_outcomes (signal_id);
CREATE TRIGGER shadow_outcomes_updated_at BEFORE UPDATE ON public.shadow_outcomes FOR EACH ROW EXECUTE FUNCTION public.tg_set_updated_at();