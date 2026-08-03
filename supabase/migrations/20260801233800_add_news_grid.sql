-- Add news_breakout_grid_enabled boolean column to bot_settings table
ALTER TABLE bot_settings 
ADD COLUMN IF NOT EXISTS news_breakout_grid_enabled BOOLEAN DEFAULT false;
