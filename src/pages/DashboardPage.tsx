import { useQuery, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { guestMock } from "@/lib/guestMock";
import { fmtMoney, fmtNum, timeAgo } from "@/lib/utils";
import type { BotStatus, Position, TradeHistory, PendingOrder } from "@/lib/types";
import {
  Play, Pause, Settings, ArrowUpDown, ChevronRight, TrendingUp, TrendingDown,
  ArrowDownLeft, ArrowUpRight, Crown, LogOut, UserPlus, Clock
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useMemo, useState, useRef, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";

const MoneyCoinDuoIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="shrink-0">
    {/* Bottom/underneath coin */}
    <circle cx="9" cy="14" r="6" fill="#FBBF24" />
    <circle cx="9" cy="14" r="6" stroke="#D97706" strokeWidth="1.2" />
    {/* Top coin */}
    <circle cx="14" cy="10" r="6" fill="#F59E0B" />
    <circle cx="14" cy="10" r="6" stroke="#D97706" strokeWidth="1.2" />
    {/* Inner dashed ring of top coin */}
    <circle cx="14" cy="10" r="3.5" stroke="#FFF" strokeWidth="0.8" strokeDasharray="1.5 1" opacity="0.8" />
    {/* Centered dollar horizontal dashes/line detail */}
    <path d="M14 8.5V11.5M12.5 9.5H15.5M12.5 10.5H15.5" stroke="#FFF" strokeWidth="1" strokeLinecap="round" />
  </svg>
);

export function DashboardPage() {
  const { user, logout } = useAuth();
  const isGuest = user?.id === "guest";

  const status = useQuery({
    queryKey: ["bot_status", user?.id],
    queryFn: async () => {
      if (isGuest) {
        return guestMock.getBotStatus();
      }
      const { data } = await supabase.from("bot_status").select("*").maybeSingle();
      return data as BotStatus | null;
    },
    refetchInterval: 5000,
  });

  const positions = useQuery({
    queryKey: ["positions", user?.id],
    queryFn: async () => {
      if (isGuest) return guestMock.getPositions();
      const { data } = await supabase.from("positions").select("*").order("opened_at", { ascending: false });
      return (data ?? []) as Position[];
    },
    refetchInterval: 5000,
  });

  const pending = useQuery({
    queryKey: ["pending_orders", user?.id],
    queryFn: async () => {
      if (isGuest) return [] as PendingOrder[];
      const { data } = await supabase.from("pending_orders").select("*").order("created_at", { ascending: false });
      return (data ?? []) as PendingOrder[];
    },
    refetchInterval: 5000,
  });

  const history = useQuery({
    queryKey: ["history_today", user?.id],
    queryFn: async () => {
      if (isGuest) return guestMock.getHistory();
      const { data } = await supabase
        .from("trade_history")
        .select("*")
        .order("closed_at", { ascending: false })
        .limit(20);
      return (data ?? []) as TradeHistory[];
    },
    refetchInterval: 5000,
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
    if (isGuest) {
      guestMock.saveBotStatus({ is_running: !running, message: !running ? "Panel started" : "Panel paused" });
    } else {
      await supabase.from("bot_status").upsert(
        { user_id: user!.id, is_running: !running, message: !running ? "Panel started" : "Panel paused" },
        { onConflict: "user_id" },
      );
    }
    status.refetch();
  }

  const [filterMode, setFilterMode] = useState<"all" | "profit" | "loss">("all");
  const [showPrompt, setShowPrompt] = useState(false);
  const [aiPrompt, setAiPrompt] = useState("");
  const [isSendingPrompt, setIsSendingPrompt] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const qc = useQueryClient();
  const navigate = useNavigate();
  const profileMenuRef = useRef<HTMLDivElement>(null);

  // Clicks outside of dropdown close it
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (profileMenuRef.current && !profileMenuRef.current.contains(event.target as Node)) {
        setShowProfileMenu(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Removed Realtime listener (now in App.tsx)

  const bestTrade = useMemo(() => {
    if (!history.data || history.data.length === 0) return null;
    return history.data.reduce((best, curr) => (Number(curr.profit) > Number(best.profit) ? curr : best), history.data[0]);
  }, [history.data]);

  const filteredPositions = useMemo(() => {
    if (!positions.data) return [];
    if (filterMode === "profit") return positions.data.filter(p => Number(p.profit) > 0);
    if (filterMode === "loss") return positions.data.filter(p => Number(p.profit) < 0);
    return positions.data;
  }, [positions.data, filterMode]);

  function toggleFilter() {
    if (filterMode === "all") setFilterMode("profit");
    else if (filterMode === "profit") setFilterMode("loss");
    else setFilterMode("all");
  }

  const running = !!status.data?.is_running;
  const equity = status.data?.account_equity ?? status.data?.account_balance ?? null;
  const currency = status.data?.account_currency ?? "USD";

  const parseNum = (val: any, fallback: number): number => {
    if (val === null || val === undefined) return fallback;
    const num = Number(val);
    return isNaN(num) ? fallback : num;
  };

  const fmtUSD = (val: number): string => {
    if (val === 0) return "$0.00";
    if (val >= 1000) {
      if (val >= 1000000) return `$${(val / 1000000).toFixed(1).replace(/\.0$/, '')}M`;
      return `$${(val / 1000).toFixed(1).replace(/\.0$/, '')}K`;
    }
    if (val < 0.01) {
      // Sub-cent pricing helper
      return `$${val.toFixed(4)}`;
    }
    return `$${val.toFixed(2)}`;
  };

  const limit = parseNum(status.data?.claude_limit, 20.0);
  const used = parseNum(status.data?.claude_used, 0.0);
  const remaining = Math.max(0, limit - used);
  const pct = limit > 0 ? (remaining / limit) * 100 : 0;

  return (
    <div className="flex flex-col items-center min-h-[100dvh] w-full font-sans">
      
      {/* Background Gradient to simulate the bottom green glow */}
      <div className="fixed bottom-0 left-0 right-0 h-[40vh] bg-gradient-to-t from-[#8cb369]/40 to-transparent pointer-events-none" />

      <div className="w-full max-w-md px-4 pt-4 sm:pt-6 pb-8 relative z-10 flex flex-col">
        
        
        {/* Main Blue Card */}
        <div className="w-full bg-gradient-to-b from-[#0a4ed6] to-[#041a5a] rounded-[30px] sm:rounded-[40px] p-4 sm:p-6 shadow-2xl relative overflow-hidden border border-white/10">
          
          {/* Card Top Header */}
          <div className="flex justify-between items-center mb-4 sm:mb-6">
            <div className="relative" ref={profileMenuRef}>
              <div 
                onClick={() => setShowProfileMenu(!showProfileMenu)}
                className="flex items-center gap-2 bg-white/10 px-3 py-1.5 rounded-full backdrop-blur-md cursor-pointer hover:bg-white/20 transition-all border border-white/5"
              >
                <img 
                  src={`https://api.dicebear.com/7.x/notionists/svg?seed=${user?.email || "Ana"}&backgroundColor=f8f9fa`} 
                  alt="Profile" 
                  className="w-6 h-6 rounded-full bg-white object-cover"
                />
                <span className="text-white text-xs font-medium">{user?.email?.split("@")[0] ?? "Ana"}</span>
              </div>
              
              {showProfileMenu && (
                <div className="absolute top-full left-0 mt-2 w-48 bg-[#1e1a1d] border border-white/10 rounded-2xl shadow-xl overflow-hidden z-50 animate-in fade-in slide-in-from-top-2 duration-200">
                  <div className="p-2 space-y-1">
                    <button 
                      onClick={async () => {
                        setShowProfileMenu(false);
                        await logout();
                        navigate("/auth");
                      }}
                      className="w-full flex items-center gap-3 px-3 py-2.5 text-xs font-medium text-white/80 hover:text-white hover:bg-white/5 rounded-xl transition-colors"
                    >
                      <UserPlus size={14} className="text-blue-400" />
                      <span>Akkaunt qo'shish</span>
                    </button>
                    <button 
                      onClick={async () => {
                        setShowProfileMenu(false);
                        await logout();
                        navigate("/auth");
                      }}
                      className="w-full flex items-center gap-3 px-3 py-2.5 text-xs font-medium text-rose-400/80 hover:text-rose-400 hover:bg-rose-500/10 rounded-xl transition-colors"
                    >
                      <LogOut size={14} />
                      <span>Chiqish</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
            
            <Link to="/pricing" className="flex items-center gap-1.5 bg-gradient-to-r from-amber-500/20 to-orange-500/20 hover:from-amber-500/30 hover:to-orange-500/30 px-3 py-1.5 rounded-full backdrop-blur-md transition-all border border-amber-500/30 cursor-pointer shadow-lg shadow-amber-500/10">
              <Crown size={14} className="text-amber-400" />
              <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider">Premium</span>
            </Link>
          </div>

          {/* Balance Area */}
          <div className="text-center mb-4 sm:mb-6 relative">
            <span className="text-[10px] text-blue-200/80 font-semibold tracking-wider uppercase bg-white/10 px-3 py-1 rounded-full inline-block backdrop-blur-sm">
              Your Balance
            </span>
            <h1 className="text-3xl sm:text-4xl font-black text-white mt-2 sm:mt-3 tracking-tight tabular-nums drop-shadow-md">
              {equity != null ? fmtMoney(Number(equity), currency) : "$ 52,002.50"}
            </h1>
          </div>

          {/* Avatars Row (Cute bunny-like faces placeholder) */}
          <a href="https://t.me/Ai_bot_akcume" target="_blank" rel="noopener noreferrer" className="flex justify-center gap-1 sm:gap-2 mb-6 sm:mb-8 cursor-pointer">
            {["Fluffy", "Cotton", "Snow", "Coco", "Bugs"].map((seed, idx) => (
              <div key={seed} className={`w-8.5 h-8.5 sm:w-11 sm:h-11 rounded-full border-2 border-[#1e40af] bg-white shadow-lg overflow-hidden flex items-center justify-center transform hover:scale-110 transition-transform ${idx !== 0 ? "-ml-2 sm:-ml-3" : ""}`}>
                <img src={`https://api.dicebear.com/7.x/micah/svg?seed=${seed}&backgroundColor=f1f5f9`} alt={seed} className="w-full h-full object-cover" />
              </div>
            ))}
          </a>

          {/* Last Transaction / High Profit Box */}
          <div className="bg-[#10192e]/90 rounded-[28px] p-4 mb-4 backdrop-blur-xl border border-white/10 relative overflow-hidden group hover:bg-[#10192e] transition-all shadow-lg">
            <div className="flex justify-between items-center mb-2">
              <span className="text-[10px] text-white/50 font-medium">Last transaction</span>
              <Link to="/history" className="text-[10px] text-white/70 hover:text-white underline decoration-white/30 transition-all">
                View all
              </Link>
            </div>
            
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-pink-500 to-purple-500 p-0.5 shadow-lg">
                  <div className="w-full h-full bg-[#10192e] rounded-full flex items-center justify-center relative overflow-hidden">
                     <span className="text-xs font-bold text-white relative z-10">{bestTrade ? (bestTrade.side === 'BUY' ? 'B' : 'S') : 'Pro'}</span>
                     <div className="absolute inset-0 bg-white/5 backdrop-blur-sm rounded-full" />
                  </div>
                </div>
                <div>
                  <p className="text-sm font-bold text-white">{bestTrade ? bestTrade.symbol : "No trades yet"}</p>
                  <p className="text-[10px] text-white/40">{bestTrade ? new Date(bestTrade.closed_at).toLocaleDateString() : "Jan 17 • 20:12"}</p>
                </div>
              </div>
              <p className="text-lg font-bold text-white tabular-nums">{bestTrade ? fmtMoney(Number(bestTrade.profit)) : "$0.00"}</p>
            </div>
          </div>

          {/* 4 Action Buttons Row */}
          <div className="flex gap-1.5 mt-2 w-full items-center justify-between">
            <Link to="/settings" className="flex-shrink-0 w-10 h-10 sm:w-14 sm:h-14 rounded-full bg-[#10192e] hover:bg-[#16223f] active:scale-95 flex items-center justify-center text-white/80 transition-all border border-white/10 group shadow-md" aria-label="Settings">
              <Settings size={16} className="sm:w-5 sm:h-5 group-hover:rotate-90 transition-transform duration-500" />
            </Link>
            
            <Link to="/signals" className="flex-shrink-0 w-10 h-10 sm:w-14 sm:h-14 rounded-full bg-[#10192e] hover:bg-[#16223f] active:scale-95 flex items-center justify-center text-white/80 transition-all border border-white/10 group shadow-md" aria-label="Signals">
              <ArrowUpDown size={16} className="sm:w-5 sm:h-5 group-hover:scale-110 transition-transform" />
            </Link>

            <button onClick={toggleFilter} className="flex-1 h-10 sm:h-14 rounded-full bg-[#10192e] hover:bg-[#16223f] active:scale-95 flex items-center justify-center gap-1.5 text-[10px] sm:text-sm font-bold text-white/90 transition-all border border-white/10 shadow-md">
              <span>{filterMode === "all" ? "Receive" : filterMode === "profit" ? "Foyda" : "Zarar"}</span>
              {filterMode === "all" && <ArrowUpDown size={12} className="text-blue-400 sm:w-4 sm:h-4 opacity-90" />}
              {filterMode === "profit" && <TrendingUp size={12} className="text-emerald-400 sm:w-4 sm:h-4" />}
              {filterMode === "loss" && <TrendingDown size={12} className="text-rose-400 sm:w-4 sm:h-4" />}
            </button>

            <button onClick={() => setShowPrompt(true)} className="flex-1 h-10 sm:h-14 rounded-full bg-gradient-to-r from-blue-500 to-indigo-600 hover:opacity-95 active:scale-95 flex items-center justify-center gap-1 text-[10px] sm:text-sm font-bold text-white transition-all shadow-lg shadow-blue-500/20 border border-blue-400/30">
              <span>AI Send</span>
              <ArrowUpRight size={12} className="sm:w-4 sm:h-4 opacity-80" />
            </button>
          </div>
        </div>

        {/* Open Positions */}
        <div className="mt-6">
          <div className="flex items-center justify-between mb-3 ml-2">
            <h3 className="text-xs font-bold text-white/60 tracking-wider">OCHIQ POZITSIYALAR</h3>
            <span className="text-[10px] text-white/40">{filteredPositions?.length ?? 0}</span>
          </div>
          {positions.isLoading ? (
            <SkeletonRows />
          ) : filteredPositions && filteredPositions.length > 0 ? (
            <div className="space-y-2">
              {filteredPositions.map((p) => <PositionRow key={p.id} p={p} />)}
            </div>
          ) : (
            <EmptyBox text="Hozircha ochiq pozitsiya yo'q" />
          )}
        </div>

        {/* Pending Orders */}
        <div className="mt-6">
          <div className="flex items-center justify-between mb-3 ml-2">
            <h3 className="text-xs font-bold text-white/60 tracking-wider">KUTILAYOTGAN ORDERLAR</h3>
            <span className="text-[10px] text-white/40">{pending.data?.length ?? 0}</span>
          </div>
          {pending.isLoading ? (
            <SkeletonRows count={2} />
          ) : pending.data && pending.data.length > 0 ? (
            <div className="space-y-2">
              {pending.data.map((o) => <PendingRow key={o.id} o={o} />)}
            </div>
          ) : (
            <EmptyBox text="Hozircha kutilayotgan order yo'q" />
          )}
        </div>

        {/* Recent History */}
        <div className="mt-6">
          <div className="flex items-center justify-between mb-3 ml-2">
            <h3 className="text-xs font-bold text-white/60 tracking-wider">SAVDO TARIXI</h3>
            <Link to="/history" className="text-[10px] text-white/50 hover:text-white">Barchasi</Link>
          </div>
          {history.isLoading ? (
            <SkeletonRows count={2} />
          ) : history.data && history.data.length > 0 ? (
            <div className="space-y-2">
              {history.data.slice(0, 8).map((t) => <HistoryRow key={t.id} t={t} />)}
            </div>
          ) : (
            <EmptyBox text="Hozircha yopilgan savdo yo'q" />
          )}
        </div>

      </div>

      {/* AI Prompt Modal */}
      {showPrompt && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center px-4">
          <div className="bg-[#1e1a1d] border border-white/10 rounded-[28px] w-full max-w-sm p-6 shadow-2xl relative overflow-hidden">
            <div className="absolute top-[-50px] right-[-50px] w-24 h-24 rounded-full bg-blue-600/20 blur-xl pointer-events-none" />
            <h3 className="text-white font-bold mb-2">AI'ga ko'rsatma yuborish</h3>
            <p className="text-[11px] text-white/50 mb-4">Trading qarorini yaxshilash uchun nima qilish kerakligini yozing.</p>
            <textarea 
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              className="w-full h-24 bg-black/40 border border-white/10 rounded-xl p-3 text-sm text-white placeholder:text-white/30 outline-none focus:border-blue-500 transition-colors resize-none mb-4"
              placeholder="Masalan: Faqat trend bo'yicha savdo qiling, GBP juftliklariga tegma..."
            />
            <div className="flex gap-2">
              <button onClick={() => setShowPrompt(false)} disabled={isSendingPrompt} className="flex-1 py-3 rounded-xl bg-white/5 text-white/70 font-bold text-xs hover:bg-white/10 transition-colors disabled:opacity-50">Bekor qilish</button>
              <button 
                disabled={isSendingPrompt || !aiPrompt.trim()}
                onClick={async () => {
                  if (!user || !aiPrompt.trim()) return;
                  setIsSendingPrompt(true);
                  try {
                    // 24 soatdan keyingi vaqtni hisoblaymiz
                    const expiresAt = new Date();
                    expiresAt.setHours(expiresAt.getHours() + 24);
                    
                    if (isGuest) {
                      guestMock.saveSettings({
                        prompt_temporary: aiPrompt,
                        prompt_temporary_expires_at: expiresAt.toISOString()
                      });
                      setAiPrompt("");
                      setShowPrompt(false);
                      await qc.invalidateQueries({ queryKey: ["bot_settings"] });
                    } else {
                      const { error } = await supabase.from("bot_settings").upsert(
                        { 
                          user_id: user.id, 
                          prompt_temporary: aiPrompt,
                          prompt_temporary_expires_at: expiresAt.toISOString()
                        },
                        { onConflict: "user_id" }
                      );
                      
                      if (!error) {
                        setAiPrompt("");
                        setShowPrompt(false);
                        // Keshni yangilaymiz
                        await qc.invalidateQueries({ queryKey: ["bot_settings"] });
                      } else {
                        console.error("Xatolik:", error);
                      }
                    }
                  } finally {
                    setIsSendingPrompt(false);
                  }
                }} 
                className="flex-1 py-3 rounded-xl bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-bold text-xs hover:opacity-90 transition-all shadow-lg shadow-blue-500/20 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isSendingPrompt ? <span className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" /> : "Yuborish"}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export function EmptyLine({ text }: { text: string }) {
  return <p className="py-6 text-center text-xs text-white/40">{text}</p>;
}

function PositionRow({ p }: { p: Position }) {
  const isBuy = String(p.side).toUpperCase() === "BUY";
  const profit = Number(p.profit ?? 0);
  return (
    <div className="rounded-2xl bg-[#10192e]/80 backdrop-blur-md border border-white/5 p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`px-2 py-0.5 rounded-md text-[10px] font-black ${isBuy ? "bg-emerald-500/20 text-emerald-400" : "bg-rose-500/20 text-rose-400"}`}>
            {isBuy ? "BUY" : "SELL"}
          </span>
          <span className="text-sm font-bold text-white truncate">{p.symbol}</span>
          <span className="text-[10px] text-white/40 shrink-0">{fmtNum(p.volume, 2)} lot</span>
        </div>
        <span className={`text-sm font-black tabular-nums ${profit >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
          {profit >= 0 ? "+" : ""}{fmtMoney(profit)}
        </span>
      </div>
      <div className="grid grid-cols-4 gap-1.5 text-[10px]">
        <MiniField label="Open" value={fmtNum(p.open_price, 5)} />
        <MiniField label="Now" value={fmtNum(p.current_price, 5)} />
        <MiniField label="SL" value={p.stop_loss ? fmtNum(p.stop_loss, 5) : "—"} tone={p.stop_loss ? "danger" : undefined} />
        <MiniField label="TP" value={p.take_profit ? fmtNum(p.take_profit, 5) : "—"} tone={p.take_profit ? "success" : undefined} />
      </div>
    </div>
  );
}

function PendingRow({ o }: { o: PendingOrder }) {
  const isBuy = o.type.toLowerCase().startsWith("buy");
  return (
    <div className="rounded-2xl bg-[#10192e]/80 backdrop-blur-md border border-white/5 p-3">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`px-2 py-0.5 rounded-md text-[10px] font-black uppercase ${isBuy ? "bg-emerald-500/20 text-emerald-400" : "bg-rose-500/20 text-rose-400"}`}>
            {o.type.replace("_", " ")}
          </span>
          <span className="text-sm font-bold text-white truncate">{o.symbol}</span>
          <span className="text-[10px] text-white/40 shrink-0">{fmtNum(o.volume, 2)} lot</span>
        </div>
        <Clock size={14} className="text-white/40" />
      </div>
      <div className="grid grid-cols-3 gap-1.5 text-[10px]">
        <MiniField label="Price" value={fmtNum(o.price, 5)} />
        <MiniField label="SL" value={o.stop_loss ? fmtNum(o.stop_loss, 5) : "—"} tone={o.stop_loss ? "danger" : undefined} />
        <MiniField label="TP" value={o.take_profit ? fmtNum(o.take_profit, 5) : "—"} tone={o.take_profit ? "success" : undefined} />
      </div>
    </div>
  );
}

function HistoryRow({ t }: { t: TradeHistory }) {
  const isBuy = String(t.side).toUpperCase() === "BUY";
  const profit = Number(t.profit ?? 0);
  return (
    <div className="rounded-2xl bg-[#10192e]/60 backdrop-blur-md border border-white/5 p-3 flex items-center justify-between">
      <div className="flex items-center gap-2 min-w-0">
        <span className={`px-2 py-0.5 rounded-md text-[10px] font-black ${isBuy ? "bg-emerald-500/15 text-emerald-400" : "bg-rose-500/15 text-rose-400"}`}>
          {isBuy ? "BUY" : "SELL"}
        </span>
        <span className="text-sm font-bold text-white truncate">{t.symbol}</span>
        <span className="text-[10px] text-white/40 shrink-0">{timeAgo(t.closed_at)}</span>
      </div>
      <span className={`text-sm font-black tabular-nums ${profit >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
        {profit >= 0 ? "+" : ""}{fmtMoney(profit)}
      </span>
    </div>
  );
}

function MiniField({ label, value, tone }: { label: string; value: string; tone?: "success" | "danger" }) {
  const cls = tone === "success" ? "text-emerald-400" : tone === "danger" ? "text-rose-400" : "text-white/90";
  return (
    <div className="rounded-lg bg-black/30 px-2 py-1">
      <p className="text-[8px] uppercase tracking-wider text-white/40">{label}</p>
      <p className={`tabular-nums text-[11px] font-bold ${cls} truncate`}>{value}</p>
    </div>
  );
}

function EmptyBox({ text }: { text: string }) {
  return (
    <div className="rounded-2xl bg-[#10192e]/40 border border-white/5 py-6 text-center">
      <p className="text-xs text-white/40">{text}</p>
    </div>
  );
}

function SkeletonRows({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="h-16 w-full rounded-2xl bg-[#10192e]/30 border border-white/5 animate-pulse" />
      ))}
    </div>
  );
}
