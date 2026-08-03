import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { Activity, TrendingUp, TrendingDown, Minus, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

type SignalRow = {
  id: string;
  symbol: string;
  timeframe: string;
  candle_time: string;
  signal: string;
  score: number;
  features: Record<string, unknown> | null;
  shadow_outcomes: { was_correct: boolean | null; pips_result: number | null }[] | null;
};

async function fetchSignals() {
  const { data, error } = await supabase
    .from("shadow_signals")
    .select("id, symbol, timeframe, candle_time, signal, score, features, shadow_outcomes(was_correct, pips_result)")
    .order("candle_time", { ascending: false })
    .limit(200);
  if (error) throw error;
  return (data ?? []) as unknown as SignalRow[];
}

function StatCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-lg">
      <p className="text-[11px] uppercase tracking-wide text-white/50">{label}</p>
      <p className="mt-1 text-2xl font-bold text-white">{value}</p>
      {sub && <p className="mt-0.5 text-[11px] text-white/40">{sub}</p>}
    </div>
  );
}

export function ShadowEdgePage() {
  const qc = useQueryClient();
  const { data: signals, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["shadow_signals"],
    queryFn: fetchSignals,
    refetchInterval: 60_000,
  });

  useEffect(() => {
    const channel = supabase
      .channel("shadow_realtime")
      .on("postgres_changes", { event: "*", schema: "public", table: "shadow_signals" },
        () => qc.invalidateQueries({ queryKey: ["shadow_signals"] }))
      .on("postgres_changes", { event: "*", schema: "public", table: "shadow_outcomes" },
        () => qc.invalidateQueries({ queryKey: ["shadow_signals"] }))
      .subscribe();
    return () => { supabase.removeChannel(channel); };
  }, [qc]);

  const rows = signals ?? [];
  const evaluated = rows.filter((r) => r.shadow_outcomes && r.shadow_outcomes.length > 0);
  const wins = evaluated.filter((r) => r.shadow_outcomes![0].was_correct).length;
  const winRate = evaluated.length ? (wins / evaluated.length) * 100 : 0;
  const totalPips = evaluated.reduce((a, r) => a + Number(r.shadow_outcomes![0].pips_result ?? 0), 0);
  const edge = winRate - 50;

  const bySymbol = Object.entries(
    evaluated.reduce<Record<string, { n: number; w: number; pips: number }>>((acc, r) => {
      const k = r.symbol;
      acc[k] ??= { n: 0, w: 0, pips: 0 };
      acc[k].n++;
      if (r.shadow_outcomes![0].was_correct) acc[k].w++;
      acc[k].pips += Number(r.shadow_outcomes![0].pips_result ?? 0);
      return acc;
    }, {}),
  );

  return (
    <div className="space-y-5 px-5 pb-24 pt-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-white">Shadow Edge</h2>
          <p className="text-xs text-white/50">Statistik ustunlikni (edge) o'z-o'zini kuzatib borish</p>
        </div>
        <button
          onClick={() => refetch()}
          className="grid h-10 w-10 place-items-center rounded-xl border border-white/10 bg-white/5 text-white active:scale-95"
          aria-label="Yangilash"
        >
          <RefreshCw size={16} className={cn(isFetching && "animate-spin")} />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Win rate" value={`${winRate.toFixed(1)}%`} sub={`${evaluated.length} baholangan`} />
        <StatCard
          label="Edge (50% dan)"
          value={`${edge >= 0 ? "+" : ""}${edge.toFixed(1)}%`}
          sub={edge > 2 ? "ijobiy ustunlik" : "hali isbotlanmagan"}
        />
        <StatCard label="Jami pips" value={`${totalPips >= 0 ? "+" : ""}${totalPips.toFixed(1)}`} />
        <StatCard label="Signallar" value={String(rows.length)} sub="oxirgi 200" />
      </div>

      {bySymbol.length > 0 && (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-lg">
          <p className="mb-3 text-xs font-bold uppercase tracking-wide text-white/50">Juftliklar bo'yicha</p>
          <div className="space-y-2">
            {bySymbol.map(([sym, s]) => {
              const wr = (s.w / s.n) * 100;
              return (
                <div key={sym} className="flex items-center gap-3">
                  <span className="w-20 text-sm font-semibold text-white">{sym}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-white/10">
                    <div
                      className={cn("h-full rounded-full", wr >= 50 ? "bg-emerald-400" : "bg-red-400")}
                      style={{ width: `${Math.min(100, wr)}%` }}
                    />
                  </div>
                  <span className="w-14 text-right text-xs text-white/60">{wr.toFixed(0)}%</span>
                  <span className={cn("w-16 text-right text-xs", s.pips >= 0 ? "text-emerald-400" : "text-red-400")}>
                    {s.pips >= 0 ? "+" : ""}{s.pips.toFixed(0)}p
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="space-y-2">
        <p className="text-xs font-bold uppercase tracking-wide text-white/50">Oxirgi signallar</p>
        {isLoading && <p className="text-sm text-white/40">Yuklanmoqda...</p>}
        {!isLoading && rows.length === 0 && (
          <p className="text-sm text-white/40">Hali signal yo'q — fetch-candles va compute-shadow-signal ishga tushgach paydo bo'ladi.</p>
        )}
        {rows.slice(0, 40).map((r) => {
          const out = r.shadow_outcomes?.[0];
          const Icon = r.signal === "BUY" ? TrendingUp : r.signal === "SELL" ? TrendingDown : Minus;
          return (
            <div key={r.id} className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/5 p-3">
              <div className={cn(
                "grid h-9 w-9 place-items-center rounded-xl",
                r.signal === "BUY" ? "bg-emerald-500/15 text-emerald-400"
                  : r.signal === "SELL" ? "bg-red-500/15 text-red-400"
                  : "bg-white/10 text-white/50",
              )}>
                <Icon size={16} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-white">
                  {r.symbol} <span className="text-white/40">· {r.signal}</span>
                </p>
                <p className="truncate text-[11px] text-white/40">
                  {new Date(r.candle_time).toLocaleString()} · score {Number(r.score).toFixed(2)}
                </p>
              </div>
              {out ? (
                <div className="text-right">
                  <p className={cn("text-xs font-bold", out.was_correct ? "text-emerald-400" : "text-red-400")}>
                    {out.was_correct ? "TO'G'RI" : "XATO"}
                  </p>
                  <p className="text-[11px] text-white/40">
                    {Number(out.pips_result ?? 0) >= 0 ? "+" : ""}{Number(out.pips_result ?? 0).toFixed(1)}p
                  </p>
                </div>
              ) : (
                <span className="flex items-center gap-1 text-[11px] text-white/40">
                  <Activity size={12} /> kutilmoqda
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
