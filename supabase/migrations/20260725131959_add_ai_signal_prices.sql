-- Add entry_price, sl_price, tp_price, and rr_ratio to ai_signals
ALTER TABLE "public"."ai_signals"
ADD COLUMN "entry_price" numeric,
ADD COLUMN "sl_price" numeric,
ADD COLUMN "tp_price" numeric,
ADD COLUMN "rr_ratio" numeric;
