-- Extra columns for bot settings to support advanced configuration via UI
ALTER TABLE public.bot_settings 
ADD COLUMN IF NOT EXISTS timeframe_major text NOT NULL DEFAULT 'H1',
ADD COLUMN IF NOT EXISTS timeframe_minor text NOT NULL DEFAULT 'M5',
ADD COLUMN IF NOT EXISTS ai_model text NOT NULL DEFAULT 'claude-3-5-sonnet-20241022',
ADD COLUMN IF NOT EXISTS system_prompt text NOT NULL DEFAULT 'Sen professional Forex treyderi va fundamental tahlilchisisan. Texnik SMC va Garmonik patternlar hamda iqtisodiy yangiliklarni birlashtirib, optimal savdo qarorini qabul qilasan.',
ADD COLUMN IF NOT EXISTS risk_level_single_confirmation numeric NOT NULL DEFAULT 0.01,
ADD COLUMN IF NOT EXISTS risk_level_multiple_confirmation numeric NOT NULL DEFAULT 0.02,
ADD COLUMN IF NOT EXISTS mt5_login text,
ADD COLUMN IF NOT EXISTS mt5_password text,
ADD COLUMN IF NOT EXISTS mt5_server text,
ADD COLUMN IF NOT EXISTS mt5_terminal_path text;
