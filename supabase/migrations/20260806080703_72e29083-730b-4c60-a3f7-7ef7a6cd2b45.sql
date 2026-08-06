CREATE TABLE public.password_reset_tokens (
  id uuid NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  mt5_login text NOT NULL,
  token_hash text,
  expires_at timestamptz NOT NULL DEFAULT (now() + interval '10 minutes'),
  used_at timestamptz,
  success boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_prt_login_created ON public.password_reset_tokens (mt5_login, created_at DESC);
CREATE INDEX idx_prt_token_hash ON public.password_reset_tokens (token_hash);

GRANT ALL ON public.password_reset_tokens TO service_role;

ALTER TABLE public.password_reset_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY "No client access to password_reset_tokens"
  ON public.password_reset_tokens FOR SELECT USING (false);