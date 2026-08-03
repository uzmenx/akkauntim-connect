-- smc_zones jadvalini qayta yaratish va xavfsizlik qoidalarini sozlash
CREATE TABLE IF NOT EXISTS public.smc_zones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    zone_type TEXT NOT NULL,
    direction TEXT NOT NULL,
    top NUMERIC NOT NULL,
    bottom NUMERIC NOT NULL,
    status TEXT NOT NULL DEFAULT 'fresh',
    formed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.smc_zones ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can access their own smc_zones" ON public.smc_zones;
CREATE POLICY "Users can access their own smc_zones" ON public.smc_zones
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE INDEX IF NOT EXISTS idx_smc_zones_user_symbol_timeframe_status ON public.smc_zones (user_id, symbol, timeframe, status);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.smc_zones TO authenticated;
GRANT ALL ON public.smc_zones TO service_role;
