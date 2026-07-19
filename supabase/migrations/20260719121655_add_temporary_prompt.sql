-- bot_settings jadvaliga vaqtinchalik prompt uchun ustunlar qo'shish
ALTER TABLE public.bot_settings 
ADD COLUMN IF NOT EXISTS prompt_temporary TEXT,
ADD COLUMN IF NOT EXISTS prompt_temporary_expires_at TIMESTAMP WITH TIME ZONE;
