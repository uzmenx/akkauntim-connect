import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { Card } from "@/components/ui/Card";
import { fmtNum, timeAgo } from "@/lib/utils";
import type { AISignal, PendingOrder } from "@/lib/types";
import { Brain, Check, X, Loader2, CircleMinus, Clock } from "lucide-react";
import { EmptyLine } from "./DashboardPage";
import { useAuth } from "@/hooks/useAuth";
import { guestMock } from "@/lib/guestMock";

export function SignalsPage() {
  const { user } = useAuth();
  const isGuest = user?.id === "guest";

  const { data: signals, isLoading: loadingSignals } = useQuery({
    queryKey: ["ai_signals", user?.id],
    queryFn: async () => {
      if (isGuest) return guestMock.getSignals();
      const { data } = await supabase
        .from("ai_signals")
        .select("*")
        .order("created_at", { ascending: false });
      return (data ?? []) as AISignal[];
    },
    refetchInterval: 8000,
  });

  const { data: pending, isLoading: loadingPending } = useQuery({
    queryKey: ["pending_orders", user?.id],
    queryFn: async () => {
      if (isGuest) return guestMock.getPendingOrders();
      const { data } = await supabase
        .from("pending_orders")
        .select("*")
        .order("created_at", { ascending: false });
      return (data ?? []) as PendingOrder[];
    },
    refetchInterval: 8000,
  });

  if (loadingSignals || loadingPending) {
    return <Loader2 className="mx-auto my-10 animate-spin text-brand-soft" size={22} />;
  }

  const hasSignals = signals && signals.length > 0;
  const hasPending = pending && pending.length > 0;

  if (!hasSignals && !hasPending) {
    return (
      <Card>
        <EmptyLine text="AI hali signal chiqarmadi va kutilayotgan limit qarorlari yo'q." />
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {hasPending && (
        <div>
          <h3 className="mb-3 text-xs font-bold text-fg-muted ml-1 uppercase tracking-wider">Kutilayotgan Qarorlar (Limit)</h3>
          <div className="space-y-3">
            {pending.map((p) => (
              <PendingCard key={p.id} p={p} />
            ))}
          </div>
        </div>
      )}

      {hasSignals && (
        <div>
          <h3 className="mb-3 text-xs font-bold text-fg-muted ml-1 uppercase tracking-wider">AI Signallar</h3>
          <div className="space-y-3">
            {signals.map((s) => (
              <SignalCard key={s.id} s={s} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function PendingCard({ p }: { p: PendingOrder }) {
  const isBuy = p.type.toLowerCase().includes("buy");
  const tone = isBuy ? "success" : "danger";
  const badge = isBuy ? "bg-success/20 text-success" : "bg-danger/20 text-danger";
  
  return (
    <Card className="p-4 border-l-2 border-brand/50">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-white/5 text-brand shadow-lg">
            <Clock size={18} />
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <p className="truncate text-base font-bold">{p.symbol}</p>
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-black tracking-wider uppercase ${badge}`}>
                {p.type.replace("_", " ")}
              </span>
            </div>
            {p.created_at && (
              <p className="text-[11px] text-fg-dim">{timeAgo(p.created_at)} oldin yaratilgan</p>
            )}
          </div>
        </div>
        <div className="text-right">
          <p className="tabular text-lg font-black">{p.price}</p>
          <p className="text-[10px] uppercase tracking-wider text-fg-dim">KIRISH NARXI</p>
        </div>
      </div>
      
      <div className="mt-4 flex flex-wrap items-center gap-2 text-[11px]">
        <span className="rounded-full bg-white/10 px-2 py-1 text-fg-muted">
          Hajm: {p.volume} lot
        </span>
        {p.stop_loss != null && p.stop_loss > 0 && (
          <span className="rounded-full bg-white/10 px-2 py-1 text-fg-muted">
            SL: {p.stop_loss}
          </span>
        )}
        {p.take_profit != null && p.take_profit > 0 && (
          <span className="rounded-full bg-white/10 px-2 py-1 text-fg-muted">
            TP: {p.take_profit}
          </span>
        )}
      </div>
    </Card>
  );
}

function SignalCard({ s }: { s: AISignal }) {
  const sig = s.signal?.toUpperCase();
  const tone =
    sig === "BUY" ? "success" : sig === "SELL" ? "danger" : "muted";
  const badge =
    tone === "success"
      ? "bg-success/20 text-success"
      : tone === "danger"
      ? "bg-danger/20 text-danger"
      : "bg-white/10 text-fg-muted";
  const StatusIcon = s.executed ? Check : s.rejection_reason ? X : CircleMinus;
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-brand-strong to-brand text-white shadow-lg shadow-brand-strong/30">
            <Brain size={18} />
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <p className="truncate text-base font-bold">{s.symbol}</p>
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-black tracking-wider ${badge}`}>
                {sig}
              </span>
            </div>
            <p className="text-[11px] text-fg-dim">{timeAgo(s.created_at)} oldin</p>
          </div>
        </div>
        <div className="text-right">
          <p className="tabular text-xl font-black">{s.confidence}%</p>
          <p className="text-[10px] uppercase tracking-wider text-fg-dim">confidence</p>
        </div>
      </div>

      <div className="mt-3">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-black/30">
          <div
            className="h-full rounded-full bg-gradient-to-r from-brand to-brand-soft"
            style={{ width: `${Math.min(100, Math.max(0, s.confidence))}%` }}
          />
        </div>
      </div>

      {s.reasoning && (
        <p className="mt-3 rounded-2xl bg-black/20 p-3 text-xs leading-relaxed text-fg-muted">
          {s.reasoning}
        </p>
      )}

      <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs">
        <div className="rounded-lg bg-black/20 py-2 border border-white/5 flex flex-col justify-center">
          <div className="text-[10px] text-fg-dim uppercase tracking-wider">Entry</div>
          <div className="font-bold mt-0.5">{s.entry_price ? s.entry_price : "—"}</div>
        </div>
        <div className="rounded-lg bg-danger/10 py-2 border border-danger/20 flex flex-col justify-center">
          <div className="text-[10px] text-danger/80 uppercase tracking-wider">Stop Loss</div>
          <div className="font-bold text-danger mt-0.5">{s.sl_price ? s.sl_price : "—"}</div>
          {s.stop_loss_pips != null && <div className="text-[9px] text-danger/70">({fmtNum(s.stop_loss_pips, 0)} pip)</div>}
        </div>
        <div className="rounded-lg bg-success/10 py-2 border border-success/20 flex flex-col justify-center">
          <div className="text-[10px] text-success/80 uppercase tracking-wider">Take Profit</div>
          <div className="font-bold text-success mt-0.5">{s.tp_price ? s.tp_price : "—"}</div>
          {s.take_profit_pips != null && <div className="text-[9px] text-success/70">({fmtNum(s.take_profit_pips, 0)} pip)</div>}
        </div>
        <div className="rounded-lg bg-brand-soft/10 py-2 border border-brand-soft/20 flex flex-col justify-center">
          <div className="text-[10px] text-brand-soft uppercase tracking-wider">R:R Ratio</div>
          <div className="font-bold text-brand-soft mt-0.5">{s.rr_ratio ? `1:${s.rr_ratio}` : "—"}</div>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between text-[11px]">
        <span
          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 font-semibold ${
            s.executed
              ? "bg-success/20 text-success"
              : s.rejection_reason
              ? "bg-danger/20 text-danger"
              : "bg-white/10 text-fg-dim"
          }`}
        >
          <StatusIcon size={12} />
          {s.executed ? "Bajarildi" : s.rejection_reason ? "Rad etildi" : "HOLD"}
        </span>
        {s.rejection_reason && (
          <span className="text-[11px] text-danger ml-2 truncate">Sabab: {s.rejection_reason}</span>
        )}
      </div>
    </Card>
  );
}
