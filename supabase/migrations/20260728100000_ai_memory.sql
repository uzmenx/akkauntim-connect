-- AI Memory table - Stores lessons learned by AI
CREATE TABLE IF NOT EXISTS public.ai_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lesson_text TEXT NOT NULL,
    category TEXT DEFAULT 'trade_pattern',
    importance INTEGER DEFAULT 5,
    source TEXT DEFAULT 'trade_review',
    success_applications INTEGER DEFAULT 0,
    failed_applications INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.ai_memory ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read access on ai_memory"
ON public.ai_memory FOR SELECT TO public USING (true);

CREATE POLICY "Allow service role to manage ai_memory"
ON public.ai_memory FOR ALL TO service_role
USING (true) WITH CHECK (true);

-- Allow anon/authenticated to insert
CREATE POLICY "Allow public insert on ai_memory"
ON public.ai_memory FOR INSERT TO public
WITH CHECK (true);

-- Strategy Performance table
CREATE TABLE IF NOT EXISTS public.strategy_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_name TEXT NOT NULL,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    total_profit REAL DEFAULT 0.0,
    avg_rr REAL DEFAULT 0.0,
    recommended_weight REAL DEFAULT 1.0,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE public.strategy_performance ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow public read on strategy_performance"
ON public.strategy_performance FOR SELECT TO public USING (true);

CREATE POLICY "Allow service role to manage strategy_performance"
ON public.strategy_performance FOR ALL TO service_role
USING (true) WITH CHECK (true);

CREATE POLICY "Allow public insert on strategy_performance"
ON public.strategy_performance FOR INSERT TO public
WITH CHECK (true);
