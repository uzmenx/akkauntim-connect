-- Create strategy_insights table
CREATE TABLE IF NOT EXISTS public.strategy_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    insight_text TEXT NOT NULL,
    market_condition TEXT DEFAULT 'all',
    setup_type TEXT DEFAULT 'unknown',
    success_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for strategy_insights
ALTER TABLE public.strategy_insights ENABLE ROW LEVEL SECURITY;

-- Allow read access to anyone
CREATE POLICY "Allow public read access on strategy_insights"
ON public.strategy_insights
FOR SELECT
TO public
USING (true);

-- Allow insert/update/delete for authenticated or service role
CREATE POLICY "Allow service role to manage strategy_insights"
ON public.strategy_insights
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Create pending_books table
CREATE TABLE IF NOT EXISTS public.pending_books (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_name TEXT NOT NULL,
    file_url TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable RLS for pending_books
ALTER TABLE public.pending_books ENABLE ROW LEVEL SECURITY;

-- Allow public to insert books
CREATE POLICY "Allow public insert on pending_books"
ON public.pending_books
FOR INSERT
TO public
WITH CHECK (true);

-- Allow public to read books
CREATE POLICY "Allow public read on pending_books"
ON public.pending_books
FOR SELECT
TO public
USING (true);

-- Storage bucket creation for books
INSERT INTO storage.buckets (id, name, public) 
VALUES ('shadow_knowledge', 'shadow_knowledge', true)
ON CONFLICT (id) DO NOTHING;

-- Storage policies for books
CREATE POLICY "Public Access"
ON storage.objects FOR SELECT
USING ( bucket_id = 'shadow_knowledge' );

CREATE POLICY "Public Uploads"
ON storage.objects FOR INSERT
WITH CHECK ( bucket_id = 'shadow_knowledge' );
