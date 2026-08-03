-- Grant SELECT permissions to anonymous role
GRANT SELECT ON public.ai_signals TO anon;
GRANT SELECT ON public.pending_orders TO anon;

-- Drop existing select restriction if any or create permissive SELECT policies
DROP POLICY IF EXISTS "anon_select_ai_signals" ON public.ai_signals;
CREATE POLICY "anon_select_ai_signals" ON public.ai_signals FOR SELECT USING (true);

DROP POLICY IF EXISTS "anon_select_pending_orders" ON public.pending_orders;
CREATE POLICY "anon_select_pending_orders" ON public.pending_orders FOR SELECT USING (true);
