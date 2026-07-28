import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { Card } from "@/components/ui/Card";
import { fmtNum, timeAgo } from "@/lib/utils";
import type { AISignal, PendingOrder } from "@/lib/types";
import { Brain, Check, X, Loader2, CircleMinus, Clock, Lock, Sparkles } from "lucide-react";
import { EmptyLine } from "./DashboardPage";
import { useAuth } from "@/hooks/useAuth";
import { guestMock } from "@/lib/guestMock";
import { useState } from "react";
import { PaywallModal } from "@/components/PaywallModal";

export function SignalsPage() {
  const { user } = useAuth();
  const isGuest = user?.id === "guest";
  const [paywallOpen, setPaywallOpen] = useState(isGuest);
  const [unlockedIds, setUnlockedIds] = useState<string[]>([]);
  const [currentUnlockingId, setCurrentUnlockingId] = useState<string | null>(null);

  const { data: signals, isLoading: loadingSignals } = useQuery({
    queryKey: ["ai_signals", user?.id],
    queryFn: async () => {
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

  const handleUnlockClick = (id: string) => {
    setCurrentUnlockingId(id);
    setPaywallOpen(true);
  };

  const handlePaywallClose = () => {
    setPaywallOpen(false);
    if (currentUnlockingId) {
      setUnlockedIds((prev) => [...prev, currentUnlockingId]);
      setCurrentUnlockingId(null);
    } else {
      // Auto-open close: unlock first signal
      if (signals && signals.length > 0) {
        setUnlockedIds((prev) => [...prev, signals[0].id]);
      }
    }
  };

  return (
    <div className="space-y-6 relative pb-10">
      {hasPending && (
        <div>
          <h3 className="mb-3 text-xs font-bold text-fg-muted ml-1 uppercase tracking-wider">Kutilayotgan Qarorlar (Limit)</h3>
          <div className="space-y-3">
            {pending.map((p) => {
              const isLocked = isGuest && !unlockedIds.includes(p.id);
              return (
                <PendingCard 
                  key={p.id} 
                  p={p} 
                  isGuest={isLocked} 
                  onUnlock={() => handleUnlockClick(p.id)} 
                />
              );
            })}
          </div>
        </div>
      )}

      {hasSignals && (
        <div>
          <h3 className="mb-3 text-xs font-bold text-fg-muted ml-1 uppercase tracking-wider">AI Signallar</h3>
          <div className="space-y-3">
            {signals.map((s) => {
              const isLocked = isGuest && !unlockedIds.includes(s.id);
              return (
                <SignalCard 
                  key={s.id} 
                  s={s} 
                  isGuest={isLocked} 
                  onUnlock={() => handleUnlockClick(s.id)} 
                />
              );
            })}
          </div>
        </div>
      )}

      <PaywallModal isOpen={paywallOpen} onClose={handlePaywallClose} />
    </div>
  );
}

function PendingCard({ p, isGuest, onUnlock }: { p: PendingOrder; isGuest: boolean; onUnlock: () => void }) {
  const isBuy = p.type.toLowerCase().includes("buy");
  const badge = isBuy ? "bg-success/20 text-success" : "bg-danger/20 text-danger";
  
  return (
    <div 
      onClick={isGuest ? onUnlock : undefined}
      className={`relative overflow-hidden bg-white/[0.02] border border-white/10 rounded-3xl p-4 shadow-[0_24px_48px_-12px_rgba(0,0,0,0.5),inset_0_1px_1px_rgba(255,255,255,0.15)] backdrop-blur-2xl transition-all duration-300 ${
        isGuest ? "cursor-pointer hover:border-[#00a8ff]/30 active:scale-[0.99]" : "hover:border-white/25 hover:-translate-y-0.5"
      }`}
    >
      <div className="absolute top-[-30px] right-[-30px] w-28 h-28 rounded-full bg-blue-500/10 blur-2xl pointer-events-none" />
      
      <div className="flex items-start justify-between gap-3 relative z-10">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-white/5 text-brand shadow-lg border border-white/5">
            <Clock size={18} />
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <p className="truncate text-base font-bold text-white">{p.symbol}</p>
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-black tracking-wider uppercase ${badge}`}>
                {p.type.replace("_", " ")}
              </span>
            </div>
            {p.created_at && (
              <p className="text-[11px] text-white/40">{timeAgo(p.created_at)} oldin yaratilgan</p>
            )}
          </div>
        </div>
        <div className="text-right">
          <p className={`tabular text-lg font-black text-white ${isGuest ? "blur-sm select-none" : ""}`}>
            {isGuest ? "0.0000" : p.price}
          </p>
          <p className="text-[10px] uppercase tracking-wider text-white/40">KIRISH NARXI</p>
        </div>
      </div>
      
      <div className="mt-4 flex flex-wrap items-center gap-2 text-[11px] relative z-10">
        <span className={`rounded-full bg-white/5 border border-white/5 px-2 py-1 text-white/70 ${isGuest ? "blur-sm select-none" : ""}`}>
          Hajm: {isGuest ? "0.10" : p.volume} lot
        </span>
        {p.stop_loss != null && p.stop_loss > 0 && (
          <span className={`rounded-full bg-white/5 border border-white/5 px-2 py-1 text-white/70 ${isGuest ? "blur-sm select-none" : ""}`}>
            SL: {isGuest ? "0.0000" : p.stop_loss}
          </span>
        )}
        {p.take_profit != null && p.take_profit > 0 && (
          <span className={`rounded-full bg-white/5 border border-white/5 px-2 py-1 text-white/70 ${isGuest ? "blur-sm select-none" : ""}`}>
            TP: {isGuest ? "0.0000" : p.take_profit}
          </span>
        )}
      </div>

      {isGuest && (
        <div className="absolute inset-0 bg-[#060a18]/40 backdrop-blur-[3px] flex items-center justify-center z-20">
          <div className="bg-gradient-to-r from-blue-600 to-cyan-500 rounded-full px-4 py-1.5 flex items-center gap-1.5 shadow-lg border border-white/10 active:scale-95 transition-transform duration-200">
            <Lock size={12} className="text-white animate-pulse" />
            <span className="text-[10px] font-black text-white uppercase tracking-wider">Tarifni ko'rish</span>
          </div>
        </div>
      )}
    </div>
  );
}

function SignalCard({ s, isGuest, onUnlock }: { s: AISignal; isGuest: boolean; onUnlock: () => void }) {
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
    <div 
      onClick={isGuest ? onUnlock : undefined}
      className={`relative overflow-hidden bg-white/[0.02] border border-white/10 rounded-3xl p-4 shadow-[0_24px_48px_-12px_rgba(0,0,0,0.5),inset_0_1px_1px_rgba(255,255,255,0.15)] backdrop-blur-2xl transition-all duration-300 ${
        isGuest ? "cursor-pointer hover:border-[#00a8ff]/30 active:scale-[0.99]" : "hover:border-white/25 hover:-translate-y-0.5"
      }`}
    >
      <div className="absolute top-[-30px] right-[-30px] w-28 h-28 rounded-full bg-indigo-500/10 blur-2xl pointer-events-none" />
      
      <div className="flex items-start justify-between gap-3 relative z-10">
        <div className="flex min-w-0 items-center gap-3">
          <span className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-brand-strong to-brand text-white shadow-lg shadow-brand-strong/30">
            <Brain size={18} />
          </span>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <p className="truncate text-base font-bold text-white">{s.symbol}</p>
              <span className={`rounded-full px-2 py-0.5 text-[10px] font-black tracking-wider ${badge}`}>
                {sig}
              </span>
            </div>
            <p className="text-[11px] text-white/40">{timeAgo(s.created_at)} oldin</p>
          </div>
        </div>
        <div className="text-right">
          <p className="tabular text-xl font-black text-white">{s.confidence}%</p>
          <p className="text-[10px] uppercase tracking-wider text-white/40">confidence</p>
        </div>
      </div>

      <div className="mt-3 relative z-10">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-black/35">
          <div
            className="h-full rounded-full bg-gradient-to-r from-brand to-brand-soft"
            style={{ width: `${Math.min(100, Math.max(0, s.confidence))}%` }}
          />
        </div>
      </div>

      {s.reasoning && (
        <p className={`mt-3 rounded-2xl bg-black/30 border border-white/5 p-3 text-xs leading-relaxed text-white/70 relative z-10 shadow-[inset_0_2px_4px_rgba(0,0,0,0.3)] ${isGuest ? "blur-sm select-none" : ""}`}>
          {s.reasoning}
        </p>
      )}

      <div className={`mt-4 grid grid-cols-2 sm:grid-cols-4 gap-2 text-center text-xs relative z-10 ${isGuest ? "blur-sm select-none" : ""}`}>
        <div className="rounded-xl bg-black/20 py-2 border border-white/5 flex flex-col justify-center shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)]">
          <div className="text-[10px] text-white/40 uppercase tracking-wider">Entry</div>
          <div className="font-bold text-white mt-0.5">{isGuest ? "0.0000" : (s.entry_price ? s.entry_price : "—")}</div>
        </div>
        <div className="rounded-xl bg-danger/10 py-2 border border-danger/20 flex flex-col justify-center">
          <div className="text-[10px] text-danger/80 uppercase tracking-wider">Stop Loss</div>
          <div className="font-bold text-danger mt-0.5">{isGuest ? "0.0000" : (s.sl_price ? s.sl_price : "—")}</div>
          {!isGuest && s.stop_loss_pips != null && <div className="text-[9px] text-danger/70">({fmtNum(s.stop_loss_pips, 0)} pip)</div>}
        </div>
        <div className="rounded-xl bg-success/10 py-2 border border-success/20 flex flex-col justify-center">
          <div className="text-[10px] text-success/80 uppercase tracking-wider">Take Profit</div>
          <div className="font-bold text-success mt-0.5">{isGuest ? "0.0000" : (s.tp_price ? s.tp_price : "—")}</div>
          {!isGuest && s.take_profit_pips != null && <div className="text-[9px] text-success/70">({fmtNum(s.take_profit_pips, 0)} pip)</div>}
        </div>
        <div className="rounded-xl bg-brand-soft/10 py-2 border border-brand-soft/20 flex flex-col justify-center">
          <div className="text-[10px] text-brand-soft uppercase tracking-wider">R:R Ratio</div>
          <div className="font-bold text-brand-soft mt-0.5">{isGuest ? "1:2.0" : (s.rr_ratio ? `1:${s.rr_ratio}` : "—")}</div>
        </div>
      </div>

      <div className={`mt-3 flex items-center justify-between text-[11px] relative z-10 ${isGuest ? "blur-sm select-none" : ""}`}>
        <span
          className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 font-semibold ${
            s.executed
              ? "bg-success/20 text-success"
              : s.rejection_reason
              ? "bg-danger/20 text-danger"
              : "bg-white/10 text-white/50"
          }`}
        >
          <StatusIcon size={12} />
          {s.executed ? "Bajarildi" : s.rejection_reason ? "Rad etildi" : "HOLD"}
        </span>
        {s.rejection_reason && (
          <span className="text-[11px] text-danger ml-2 truncate">Sabab: {s.rejection_reason}</span>
        )}
      </div>

      {isGuest && (
        <div className="absolute inset-0 bg-[#060a18]/45 backdrop-blur-[3px] flex flex-col items-center justify-center z-20 gap-2">
          <div className="bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-500 rounded-full px-5 py-2.5 flex items-center gap-2 shadow-xl border border-white/15 active:scale-95 transition-transform duration-200">
            <Sparkles size={14} className="text-white animate-pulse" />
            <span className="text-xs font-black text-white uppercase tracking-widest">Signallarni ko'rish</span>
          </div>
          <p className="text-[10px] text-white/50 font-medium">Tariflar va obunalarni tekshiring</p>
        </div>
      )}
    </div>
  );
}

