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
    <div className="flex flex-col items-center h-[100dvh] w-full font-sans overflow-hidden">
      
      {/* Background Gradient to simulate the bottom green glow */}
      <div className="fixed bottom-0 left-0 right-0 h-[40vh] bg-gradient-to-t from-[#8cb369]/40 to-transparent pointer-events-none" />

      <div className="w-full max-w-md px-4 pt-4 sm:pt-6 pb-4 sm:pb-6 relative z-10 flex flex-col h-full">
        
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
        <div className="mt-6 flex-1 flex flex-col min-h-0 relative">
          <h3 className="text-xs font-bold text-white/60 mb-4 ml-2">OCHIQ POZITSIYALAR</h3>
          
          {filteredPositions && filteredPositions.length > 0 ? (
            <VerticalCarousel items={filteredPositions} />
          ) : (
            // High fidelity pulsing skeletons simulating the card structure
            [1, 2, 3, 4, 5, 6].map((i) => (
              <div 
                key={i} 
                className="h-16 w-full rounded-2xl bg-[#10192e]/30 border border-white/5 animate-pulse flex items-center px-4"
              >
                {/* Left circle skeleton */}
                <div className="w-10 h-10 rounded-xl bg-white/5 mr-3 shrink-0" />
                {/* Middle details skeleton */}
                <div className="flex-1 space-y-2">
                  <div className="h-3 w-16 bg-white/10 rounded-full" />
                  <div className="h-2 w-24 bg-white/5 rounded-full" />
                </div>
                {/* Right profit skeleton */}
                <div className="space-y-2 flex flex-col items-end">
                  <div className="h-3 w-14 bg-white/10 rounded-full" />
                  <div className="h-2 w-10 bg-white/5 rounded-full" />
                </div>
              </div>
            ))
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
