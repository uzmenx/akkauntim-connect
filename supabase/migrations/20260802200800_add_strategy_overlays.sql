-- harmonic_patterns jadvali
CREATE TABLE IF NOT EXISTS public.harmonic_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    pattern_type TEXT NOT NULL,
    signal TEXT NOT NULL,
    confidence NUMERIC,
    entry_zone JSONB,
    sl NUMERIC,
    tp_zones JSONB,
    status TEXT NOT NULL DEFAULT 'fresh',
    formed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.harmonic_patterns ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can access their own harmonic_patterns" ON public.harmonic_patterns;
CREATE POLICY "Users can access their own harmonic_patterns" ON public.harmonic_patterns
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE INDEX IF NOT EXISTS idx_harmonic_patterns_user_symbol_timeframe_status ON public.harmonic_patterns (user_id, symbol, timeframe, status);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.harmonic_patterns TO authenticated;
GRANT ALL ON public.harmonic_patterns TO service_role;


-- wyckoff_events jadvali
CREATE TABLE IF NOT EXISTS public.wyckoff_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    phase TEXT NOT NULL,
    signal TEXT NOT NULL,
    confidence NUMERIC,
    status TEXT NOT NULL DEFAULT 'fresh',
    formed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.wyckoff_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can access their own wyckoff_events" ON public.wyckoff_events;
CREATE POLICY "Users can access their own wyckoff_events" ON public.wyckoff_events
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE INDEX IF NOT EXISTS idx_wyckoff_events_user_symbol_timeframe_status ON public.wyckoff_events (user_id, symbol, timeframe, status);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.wyckoff_events TO authenticated;
GRANT ALL ON public.wyckoff_events TO service_role;


-- sr_volume_zones jadvali
CREATE TABLE IF NOT EXISTS public.sr_volume_zones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    price NUMERIC NOT NULL,
    type TEXT NOT NULL,
    strength NUMERIC,
    status TEXT NOT NULL DEFAULT 'fresh',
    formed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.sr_volume_zones ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can access their own sr_volume_zones" ON public.sr_volume_zones;
CREATE POLICY "Users can access their own sr_volume_zones" ON public.sr_volume_zones
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE INDEX IF NOT EXISTS idx_sr_volume_zones_user_symbol_timeframe_status ON public.sr_volume_zones (user_id, symbol, timeframe, status);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.sr_volume_zones TO authenticated;
GRANT ALL ON public.sr_volume_zones TO service_role;


-- auto_patterns jadvali
CREATE TABLE IF NOT EXISTS public.auto_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    pattern_type TEXT NOT NULL,
    signal TEXT NOT NULL,
    confidence NUMERIC,
    status TEXT NOT NULL DEFAULT 'fresh',
    formed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.auto_patterns ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Users can access their own auto_patterns" ON public.auto_patterns;
CREATE POLICY "Users can access their own auto_patterns" ON public.auto_patterns
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE INDEX IF NOT EXISTS idx_auto_patterns_user_symbol_timeframe_status ON public.auto_patterns (user_id, symbol, timeframe, status);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.auto_patterns TO authenticated;
GRANT ALL ON public.auto_patterns TO service_role;
