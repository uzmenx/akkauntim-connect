-- candles jadvali
CREATE TABLE IF NOT EXISTS public.candles (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    symbol text NOT NULL,
    timeframe text NOT NULL,
    time timestamptz NOT NULL,
    open numeric NOT NULL,
    high numeric NOT NULL,
    low numeric NOT NULL,
    close numeric NOT NULL,
    volume numeric,
    UNIQUE(user_id, symbol, timeframe, time)
);
ALTER TABLE public.candles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can access their own candles" ON public.candles;
CREATE POLICY "Users can access their own candles" ON public.candles
    FOR ALL USING (auth.uid() = user_id);
CREATE INDEX IF NOT EXISTS idx_candles_user_symbol_timeframe_time ON public.candles (user_id, symbol, timeframe, time DESC);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.candles TO authenticated;
GRANT ALL ON public.candles TO service_role;

-- smc_zones jadvali
CREATE TABLE IF NOT EXISTS public.smc_zones (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    symbol text NOT NULL,
    timeframe text NOT NULL,
    zone_type text NOT NULL,
    direction text NOT NULL,
    top numeric NOT NULL,
    bottom numeric NOT NULL,
    status text NOT NULL DEFAULT 'fresh',
    formed_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE public.smc_zones ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can access their own smc_zones" ON public.smc_zones;
CREATE POLICY "Users can access their own smc_zones" ON public.smc_zones
    FOR ALL USING (auth.uid() = user_id);
CREATE INDEX IF NOT EXISTS idx_smc_zones_user_symbol_timeframe_status ON public.smc_zones (user_id, symbol, timeframe, status);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.smc_zones TO authenticated;
GRANT ALL ON public.smc_zones TO service_role;
