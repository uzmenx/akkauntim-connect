ALTER TABLE public.bot_settings
  ADD COLUMN IF NOT EXISTS realtime_enabled boolean NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS loop_interval_seconds integer NOT NULL DEFAULT 15;