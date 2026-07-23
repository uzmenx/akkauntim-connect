ALTER TABLE public.bot_settings 
  ADD COLUMN IF NOT EXISTS loop_interval_minutes integer DEFAULT 5,
  ADD COLUMN IF NOT EXISTS ai_enabled boolean DEFAULT true;