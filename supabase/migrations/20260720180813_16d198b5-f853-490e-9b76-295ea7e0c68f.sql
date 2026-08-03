CREATE TABLE IF NOT EXISTS public.pending_orders (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  ticket bigint NOT NULL,
  symbol text NOT NULL,
  type text NOT NULL,
  volume numeric NOT NULL,
  price numeric NOT NULL,
  stop_loss numeric,
  take_profit numeric,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, ticket)
);
GRANT SELECT, INSERT, UPDATE, DELETE ON public.pending_orders TO authenticated;
GRANT ALL ON public.pending_orders TO service_role;
ALTER TABLE public.pending_orders ENABLE ROW LEVEL SECURITY;
CREATE POLICY "own_pending_select" ON public.pending_orders FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "own_pending_all" ON public.pending_orders FOR ALL TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
ALTER TABLE public.pending_orders REPLICA IDENTITY FULL;
ALTER PUBLICATION supabase_realtime ADD TABLE public.pending_orders;