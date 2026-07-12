import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { Card, CardStrong } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { fmtMoney, fmtNum, timeAgo } from "@/lib/utils";
import type { BotStatus, Position, TradeHistory } from "@/lib/types";
import {
  Play, Pause, TrendingUp, TrendingDown, Activity, Wallet, Zap, Loader2,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useMemo } from "react";

export function DashboardPage() {
  const { user } = useAuth();

  const status = useQuery({
    queryKey: ["bot_status", user?.id],
    queryFn: async () => {
      const { data } = await supabase.from("bot_status").select("*").maybeSingle();
      return data as BotStatus | null;
    },
    refetchInterval: 5000,
  });

  const positions = useQuery({
    queryKey: ["positions", user?.id],
    queryFn: async () => {
      const { data } = await supabase.from("positions").select("*").order("opened_at", { ascending: false });
      return (data ?? []) as Position[];
    },
    refetchInterval: 5000,
  });

  const history = useQuery({
    queryKey: ["history_today", user?.id],
    queryFn: async () => {
      const since = new Date(); since.setHours(0, 0, 0, 0);
      const { data } = await supabase
        .from("trade_history")
        .select("*")
        .gte("closed_at", since.toISOString())
        .order("closed_at", { ascending: false });
      return (data ?? []) as TradeHistory[];
    },
    refetchInterval: 15000,
  });

  const stats = useMemo(() => {
    const open = positions.data ?? [];
    const done = history.data ?? [];
    const openPL = open.reduce((s, p) => s + (Number(p.profit) || 0), 0);
    const todayPL = done.reduce((s, t) => s + (Number(t.profit) || 0), 0);
    const wins = done.filter((t) => Number(t.profit) > 0).length;
    const wr = done.length ? Math.round((wins / done.length) * 100) : null;
    return { openPL, todayPL, wr, openCount: open.length, todayCount: done.length };
  }, [positions.data, history.data]);

  async function toggleBot() {
    const running = !!status.data?.is_running;
    await supabase.from("bot_status").upsert(
      { user_id: user!.id, is_running: !running, message: !running ? "Panel started" : "Panel paused" },
      { onConflict: "user_id" },
    );
    status.refetch();
  }

  const running = !!status.data?.is_running;
  const equity = status.data?.account_equity ?? status.data?.account_balance ?? null;
  const currency = status.data?.account_currency ?? "USD";

  return (
    <div className="space-y-4">
      {/* Hero equity card */}
      <CardStrong className="relative overflow-hidden p-6">
        <div className="pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-brand/25 blur-3xl" />
        <p className="text-xs font-medium text-fg-dim">Hisob equity</p>
        <div className="mt-1 flex items-baseline gap-2">
          <h2 className="tabular text-4xl font-black tracking-tight">
            {equity != null ? fmtMoney(Number(equity), currency) : "—"}
          </h2>
        </div>
        <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
          <span
            className={`inline-flex items-center gap-1 rounded-full px-2 py-1 font-semibold ${
              stats.todayPL >= 0 ? "bg-success/20 text-success" : "bg-danger/20 text-danger"
            }`}
          >
            {stats.todayPL >= 0 ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
            {fmtMoney(stats.todayPL, currency)} bugun
          </span>
          <span className="rounded-full bg-white/10 px-2 py-1 text-fg-muted">
            {stats.todayCount} savdo · WR {stats.wr ?? "—"}%
          </span>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-2">
          <Button
            variant={running ? "danger" : "success"}
            size="lg"
            onClick={toggleBot}
            disabled={!user}
          >
            {running ? <Pause size={18} /> : <Play size={18} />}
            {running ? "To'xtatish" : "Ishga tushirish"}
          </Button>
          <div className="grid place-items-center rounded-2xl bg-black/25 px-3 py-2 text-center">
            <p className="text-[10px] uppercase tracking-wider text-fg-dim">Holat</p>
            <p className="text-sm font-bold">
              <span
                className={`mr-1.5 inline-block h-2 w-2 rounded-full ${
                  running ? "bg-success animate-pulse" : "bg-fg-dim"
                }`}
              />
              {running ? "Ishlayapti" : "To'xtatilgan"}
            </p>
            <p className="mt-0.5 text-[10px] text-fg-dim">
              Heartbeat {timeAgo(status.data?.last_heartbeat)}
            </p>
          </div>
        </div>
      </CardStrong>

      {/* KPI grid */}
      <div className="grid grid-cols-2 gap-3">
        <Kpi
          icon={<Activity size={16} />}
          label="Ochiq"
          value={String(stats.openCount)}
          sub={`${fmtMoney(stats.openPL, currency)} P/L`}
          tone={stats.openPL >= 0 ? "success" : "danger"}
        />
        <Kpi
          icon={<Wallet size={16} />}
          label="Balance"
          value={fmtMoney(status.data?.account_balance ?? null, currency)}
          sub={status.data?.broker ?? "MT5"}
        />
        <Kpi
          icon={<Zap size={16} />}
          label="Bugungi P/L"
          value={fmtMoney(stats.todayPL, currency)}
          sub={`${stats.todayCount} savdo`}
          tone={stats.todayPL >= 0 ? "success" : "danger"}
        />
        <Kpi
          icon={<TrendingUp size={16} />}
          label="Win rate"
          value={stats.wr != null ? `${stats.wr}%` : "—"}
          sub="Bugun"
        />
      </div>

      {/* Open positions preview */}
      <Card>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="font-bold">Ochiq savdolar</h3>
          <span className="text-xs text-fg-dim">{positions.data?.length ?? 0} ta</span>
        </div>
        {positions.isLoading ? (
          <Loader2 className="mx-auto my-6 animate-spin text-brand-soft" size={20} />
        ) : !positions.data?.length ? (
          <EmptyLine text="Hozircha ochiq savdo yo'q" />
        ) : (
          <ul className="space-y-2">
            {positions.data.slice(0, 3).map((p) => (
              <PositionRow key={p.id} p={p} />
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function Kpi({
  icon, label, value, sub, tone,
}: {
  icon: React.ReactNode; label: string; value: string; sub?: string;
  tone?: "success" | "danger";
}) {
  const toneCls =
    tone === "success" ? "text-success" : tone === "danger" ? "text-danger" : "text-fg-muted";
  return (
    <Card className="p-4">
      <div className="mb-2 flex items-center gap-2 text-fg-dim">
        <span className="grid h-7 w-7 place-items-center rounded-xl bg-white/10">{icon}</span>
        <span className="text-xs font-medium">{label}</span>
      </div>
      <p className="tabular text-xl font-black tracking-tight">{value}</p>
      {sub && <p className={`mt-0.5 text-xs font-medium ${toneCls}`}>{sub}</p>}
    </Card>
  );
}

export function PositionRow({ p }: { p: Position }) {
  const isBuy = p.side?.toUpperCase() === "BUY";
  const profit = Number(p.profit ?? 0);
  return (
    <li className="flex items-center justify-between rounded-2xl bg-black/20 px-3 py-2.5">
      <div className="flex min-w-0 items-center gap-3">
        <span
          className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl text-xs font-black ${
            isBuy ? "bg-success/20 text-success" : "bg-danger/20 text-danger"
          }`}
        >
          {isBuy ? "B" : "S"}
        </span>
        <div className="min-w-0">
          <p className="truncate text-sm font-bold">{p.symbol}</p>
          <p className="truncate text-[11px] text-fg-dim">
            {fmtNum(p.volume, 2)} lot · {fmtNum(p.open_price, 5)}
          </p>
        </div>
      </div>
      <div className="text-right">
        <p className={`tabular text-sm font-bold ${profit >= 0 ? "text-success" : "text-danger"}`}>
          {profit >= 0 ? "+" : ""}{fmtMoney(profit)}
        </p>
        <p className="text-[10px] text-fg-dim">{timeAgo(p.opened_at)} oldin</p>
      </div>
    </li>
  );
}

export function EmptyLine({ text }: { text: string }) {
  return <p className="py-6 text-center text-sm text-fg-dim">{text}</p>;
}
