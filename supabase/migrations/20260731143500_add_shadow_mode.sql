-- bot_settings jadvaliga shadow_mode ustunini qo'shish
ALTER TABLE public.bot_settings 
ADD COLUMN IF NOT EXISTS shadow_mode BOOLEAN DEFAULT true;

-- Schema cache ni yangilash (PostgREST uchun)
NOTIFY pgrst, 'reload schema';
