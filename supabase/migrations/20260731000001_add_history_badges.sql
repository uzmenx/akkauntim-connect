-- Add agreed_strategies and ai_used to trade_history table

ALTER TABLE public.trade_history
ADD COLUMN IF NOT EXISTS agreed_strategies text[] DEFAULT '{}'::text[],
ADD COLUMN IF NOT EXISTS ai_used boolean DEFAULT false;
