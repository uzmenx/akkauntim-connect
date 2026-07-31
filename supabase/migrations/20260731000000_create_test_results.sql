create table if not exists public.test_results (
    id uuid default gen_random_uuid() primary key,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    type text not null,
    symbol text not null,
    timeframe text not null,
    total_trades integer not null default 0,
    win_rate numeric not null default 0,
    total_profit numeric not null default 0,
    reasoning text
);

alter table public.test_results enable row level security;

create policy "Enable read access for all users" on public.test_results
    for select using (true);
    
create policy "Enable insert for all users" on public.test_results
    for insert with check (true);
