-- Add claude_limit and claude_used columns to bot_status table
ALTER TABLE public.bot_status
ADD COLUMN IF NOT EXISTS claude_limit numeric NOT NULL DEFAULT 20.00,
ADD COLUMN IF NOT EXISTS claude_used numeric NOT NULL DEFAULT 0.00;
