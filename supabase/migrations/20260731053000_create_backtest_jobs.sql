-- backtest_jobs jadvalini yaratish
CREATE TABLE IF NOT EXISTS backtest_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    strategy TEXT,
    mode TEXT NOT NULL, -- 'ai_siz' yoki 'ai_bilan'
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Realtime uchun yoqish
ALTER PUBLICATION supabase_realtime ADD TABLE backtest_jobs;

-- Anon/Authenticated kirishga ruxsat
ALTER TABLE backtest_jobs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow anonymous read for backtest_jobs"
ON backtest_jobs FOR SELECT
TO anon, authenticated
USING (true);

CREATE POLICY "Allow anonymous insert for backtest_jobs"
ON backtest_jobs FOR INSERT
TO anon, authenticated
WITH CHECK (true);

CREATE POLICY "Allow anonymous update for backtest_jobs"
ON backtest_jobs FOR UPDATE
TO anon, authenticated
USING (true);
