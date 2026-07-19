
-- Unique constraint on mt5_login for lookup from edge function
ALTER TABLE public.bot_settings
  ADD CONSTRAINT bot_settings_mt5_login_unique UNIQUE (mt5_login);

-- Grants
GRANT SELECT, INSERT, UPDATE, DELETE ON public.bot_settings TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.bot_status TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.positions TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.ai_signals TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.trade_history TO authenticated;
GRANT ALL ON public.bot_settings TO service_role;
GRANT ALL ON public.bot_status TO service_role;
GRANT ALL ON public.positions TO service_role;
GRANT ALL ON public.ai_signals TO service_role;
GRANT ALL ON public.trade_history TO service_role;

-- Enable RLS
ALTER TABLE public.bot_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bot_status ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.positions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ai_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trade_history ENABLE ROW LEVEL SECURITY;

-- Drop any old permissive policies if they exist
DO $$
DECLARE r record;
BEGIN
  FOR r IN SELECT schemaname, tablename, policyname FROM pg_policies
           WHERE schemaname = 'public'
             AND tablename IN ('bot_settings','bot_status','positions','ai_signals','trade_history')
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I', r.policyname, r.schemaname, r.tablename);
  END LOOP;
END $$;

-- Per-user policies
CREATE POLICY "Users manage own bot_settings" ON public.bot_settings
  FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users manage own bot_status" ON public.bot_status
  FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users manage own positions" ON public.positions
  FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users manage own ai_signals" ON public.ai_signals
  FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users manage own trade_history" ON public.trade_history
  FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
