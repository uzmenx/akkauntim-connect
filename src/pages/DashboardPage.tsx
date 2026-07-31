import { useQuery, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { guestMock } from "@/lib/guestMock";
import { fmtMoney, fmtNum, timeAgo, cn } from "@/lib/utils";
import type { BotStatus, Position, TradeHistory, PendingOrder, BotSettings } from "@/lib/types";
import {
  Play, Pause, Settings, ChevronRight, TrendingUp, TrendingDown,
  ArrowDownLeft, ArrowUpRight, Crown, LogOut, UserPlus, Clock, FlaskConical, Sparkles, Brain, Bot
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useMemo, useState, useRef, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BalanceTrendChart } from "@/components/BalanceTrendChart";
import { PaywallModal } from "@/components/PaywallModal";

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
    queryKey: ["trade_history_all", user?.id],
    queryFn: async () => {
      if (isGuest) return guestMock.getHistory();
      const { data } = await supabase
        .from("trade_history")
        .select("*")
        .order("closed_at", { ascending: false });
      return (data ?? []) as TradeHistory[];
    },
    refetchInterval: 5000,
  });

  const settings = useQuery({
    queryKey: ["bot_settings", user?.id],
    queryFn: async () => {
      if (isGuest) return guestMock.getSettings();
      const { data } = await supabase.from("bot_settings").select("*").maybeSingle();
      return data as BotSettings | null;
    },
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
  const [activeTab, setActiveTab] = useState<"positions" | "limits" | "history">("positions");
  const tabContainerRef = useRef<HTMLDivElement>(null);

  const handleTabClick = (tab: "positions" | "limits" | "history") => {
    setActiveTab(tab);
    const index = tab === "positions" ? 0 : tab === "limits" ? 1 : 2;
    if (tabContainerRef.current) {
      tabContainerRef.current.scrollTo({ left: index * tabContainerRef.current.clientWidth, behavior: "smooth" });
    }
  };

  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const el = e.currentTarget;
    const scrollRatio = el.scrollLeft / el.clientWidth;
    const index = Math.round(scrollRatio);
    if (index === 0 && activeTab !== "positions") setActiveTab("positions");
    else if (index === 1 && activeTab !== "limits") setActiveTab("limits");
    else if (index === 2 && activeTab !== "history") setActiveTab("history");
  };
  const [showPrompt, setShowPrompt] = useState(false);
  const [aiPrompt, setAiPrompt] = useState("");
  const [isSendingPrompt, setIsSendingPrompt] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [showFirstTimePaywall, setShowFirstTimePaywall] = useState(false);
  const qc = useQueryClient();
  const navigate = useNavigate();
  const profileMenuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isGuest) {
      const hasVisited = localStorage.getItem("guest_has_visited");
      const hasRedirected = sessionStorage.getItem("guest_session_redirected");
      if (hasVisited === "true") {
        if (!hasRedirected) {
          sessionStorage.setItem("guest_session_redirected", "true");
          navigate("/signals", { replace: true });
        }
      } else {
        localStorage.setItem("guest_has_visited", "true");
        sessionStorage.setItem("guest_session_redirected", "true");
        setShowFirstTimePaywall(true);
      }
    }
  }, [isGuest, navigate]);

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
    <div className="flex flex-col items-center h-full w-full font-sans overflow-hidden">
      
      {/* Background Gradient to simulate the bottom green glow */}
      <div className="fixed bottom-0 left-0 right-0 h-[40vh] bg-gradient-to-t from-[#8cb369]/30 to-transparent pointer-events-none" />

      <div className="w-full h-full mx-auto px-4 pt-[max(env(safe-area-inset-top),0.75rem)] pb-[max(env(safe-area-inset-bottom),0.5rem)] relative z-10 flex flex-col gap-2">
        
        {/* Unified Balance Trend Chart & Minimalist Stats */}
        <div className="h-[11dvh] min-h-[85px] shrink-0 w-full animate-in fade-in slide-in-from-top-4 duration-500">
           <BalanceTrendChart history={history.data || []} currentBalance={Number(equity || 0)} stats={stats} />
        </div>

        {isGuest && (
          <Link to="/pricing" className="h-[4dvh] min-h-[30px] shrink-0 w-full bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/30 rounded-2xl flex items-center justify-between px-4 animate-in fade-in slide-in-from-top-3 duration-500 backdrop-blur-md shadow-lg cursor-pointer hover:brightness-110 transition-all">
            <span className="text-[9px] font-bold text-amber-300 flex items-center gap-1.5 uppercase tracking-wider">
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping shrink-0" />
              Siz Mehmon (Demo) rejadasiz. To'liq faollashtirish
            </span>
            <ChevronRight size={12} className="text-amber-300 shrink-0" />
          </Link>
        )}

        {/* Card 22%: Main Blue Card */}
        <div className="w-full h-[25dvh] min-h-[235px] bg-gradient-to-b from-[#0052e0] to-[#00258a] rounded-[32px] p-4 shadow-2xl relative overflow-hidden border border-white/10 flex flex-col justify-between shrink-0 animate-in fade-in slide-in-from-top-2 duration-700">
          
          {/* Card Top Header */}
          <div className="flex justify-between items-center">
            <div className="relative" ref={profileMenuRef}>
              <div 
                onClick={() => setShowProfileMenu(!showProfileMenu)}
                className="flex items-center gap-2 bg-white/10 px-3 py-1.5 rounded-full backdrop-blur-md cursor-pointer hover:bg-white/20 transition-all border border-white/10"
              >
                <div className="w-5 h-5 rounded-full bg-white flex items-center justify-center overflow-hidden">
                  <img 
                    src={`https://api.dicebear.com/7.x/bottts/svg?seed=${user?.email || "Ana"}`} 
                    alt="Profile" 
                    className="w-full h-full object-cover"
                  />
                </div>
                <span className="text-white text-xs font-bold tracking-tight">
                  {settings.data?.mt5_login || "109545213"}
                </span>
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
            
            <Link to="/pricing" className="flex items-center gap-1 bg-amber-500/10 hover:bg-amber-500/20 px-3 py-1.5 rounded-full backdrop-blur-md transition-all border border-amber-500/30 cursor-pointer shadow-lg shadow-amber-500/5">
              <Crown size={12} className="text-amber-400 fill-amber-400/20" />
              <span className="text-[9px] font-extrabold text-amber-400 uppercase tracking-widest">Premium</span>
            </Link>
          </div>

          {/* Balance Area */}
          <div className="text-center flex flex-col items-center justify-center flex-1 py-0.5">
            <h1 className="text-3xl sm:text-4xl font-black text-white tracking-tight tabular-nums drop-shadow-md">
              {equity != null ? fmtMoney(Number(equity), currency) : "$89,405.18"}
            </h1>
            {isGuest && (
              <span className="mt-1.5 px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30 text-[9px] font-extrabold uppercase tracking-widest backdrop-blur-md">
                Demo Reja (Taqdimot Balansi)
              </span>
            )}
          </div>

          {/* Avatars Row */}
          <a href="https://t.me/Ai_bot_akcume" target="_blank" rel="noopener noreferrer" className="flex justify-center mb-2 cursor-pointer">
            {["Fluffy", "Cotton", "Snow", "Coco", "Bugs"].map((seed, idx) => (
              <div key={seed} className={`w-8 h-8 rounded-full border-[2px] border-[#004ade] bg-white shadow-xl overflow-hidden flex items-center justify-center transform hover:scale-110 transition-transform ${idx !== 0 ? "-ml-2" : ""}`}>
                <img src={`https://api.dicebear.com/7.x/micah/svg?seed=${seed}&backgroundColor=f1f5f9`} alt={seed} className="w-full h-full object-cover" />
              </div>
            ))}
          </a>

          {/* Action Buttons Row */}
          <div className="flex gap-1.5 min-[360px]:gap-2 w-full items-center overflow-x-auto no-scrollbar mt-auto px-1 pb-1">
            {/* Button 1: Settings */}
            <Link to="/settings" className="flex-shrink-0 w-10 h-10 min-[360px]:w-11 min-[360px]:h-11 min-[390px]:w-[50px] min-[390px]:h-[50px] rounded-xl min-[360px]:rounded-2xl bg-gradient-to-br from-slate-600 to-slate-800 shadow-[inset_0_2px_4px_rgba(255,255,255,0.2),inset_0_-2px_4px_rgba(0,0,0,0.3),0_4px_12px_rgba(71,85,105,0.5)] hover:brightness-110 active:scale-95 flex items-center justify-center text-white/90 transition-all group border border-slate-500/50" aria-label="Settings">
              <Settings size={18} className="min-[360px]:w-[20px] min-[360px]:h-[20px] group-hover:rotate-90 transition-transform duration-500" />
            </Link>
            
            {/* Button 2: Signals */}
            <Link to="/signals" className="flex-shrink-0 w-10 h-10 min-[360px]:w-11 min-[360px]:h-11 min-[390px]:w-[50px] min-[390px]:h-[50px] rounded-xl min-[360px]:rounded-2xl bg-gradient-to-br from-orange-400 to-orange-600 shadow-[inset_0_2px_4px_rgba(255,255,255,0.3),inset_0_-2px_4px_rgba(0,0,0,0.2),0_6px_16px_rgba(249,115,22,0.4)] hover:brightness-110 active:scale-95 flex items-center justify-center text-white transition-all group border border-orange-300/50" aria-label="Signals">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 80 80" className="min-[360px]:w-[22px] min-[360px]:h-[22px] group-hover:scale-110 transition-transform">
                <g fill="none" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5">
                  <path stroke="currentColor" d="M40 48v24"/>
                  <circle cx="40" cy="40" r="8" fill="currentColor" fillOpacity="0.2" stroke="currentColor"/>
                  <path stroke="currentColor" d="M17.373 62.627A32 32 0 0 1 40 8m22.627 54.627A32 32 0 0 0 40 8"/>
                  <path stroke="currentColor" d="M25.858 54.142A20 20 0 0 1 40 20m14.142 34.142A20 20 0 0 0 40 20"/>
                </g>
              </svg>
            </Link>

            {/* Button 3: Filter */}
            <button onClick={toggleFilter} className="flex-shrink-0 w-10 h-10 min-[360px]:w-11 min-[360px]:h-11 min-[390px]:w-[50px] min-[390px]:h-[50px] rounded-xl min-[360px]:rounded-2xl bg-gradient-to-br from-violet-500 to-indigo-600 shadow-[inset_0_2px_4px_rgba(255,255,255,0.3),inset_0_-2px_4px_rgba(0,0,0,0.2),0_6px_16px_rgba(139,92,246,0.4)] hover:brightness-110 active:scale-95 flex items-center justify-center transition-all group border border-violet-400/50" aria-label="Filter Mode">
              <div className="flex items-center justify-center w-6 h-6 min-[360px]:w-7 min-[360px]:h-7">
                {filterMode === "all" && (
                  <div className="relative w-full h-full group-hover:scale-110 transition-transform flex items-center justify-center">
                    <TrendingUp size={16} className="text-emerald-400 absolute top-0 left-0 min-[360px]:w-[18px] min-[360px]:h-[18px]" strokeWidth={2.5} />
                    <TrendingDown size={16} className="text-rose-400 absolute bottom-0 right-0 min-[360px]:w-[18px] min-[360px]:h-[18px]" strokeWidth={2.5} />
                  </div>
                )}
                {filterMode === "profit" && <TrendingUp size={22} className="text-emerald-400 min-[360px]:w-[24px] min-[360px]:h-[24px] group-hover:scale-110 transition-transform" strokeWidth={2.5} />}
                {filterMode === "loss" && <TrendingDown size={22} className="text-rose-400 min-[360px]:w-[24px] min-[360px]:h-[24px] group-hover:scale-110 transition-transform" strokeWidth={2.5} />}
              </div>
            </button>

            {/* Button 4: AI Send */}
            <button onClick={() => setShowPrompt(true)} className="flex-shrink-0 w-10 h-10 min-[360px]:w-11 min-[360px]:h-11 min-[390px]:w-[50px] min-[390px]:h-[50px] rounded-xl min-[360px]:rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 shadow-[inset_0_2px_4px_rgba(255,255,255,0.4),inset_0_-2px_4px_rgba(0,0,0,0.2),0_6px_16px_rgba(251,191,36,0.5)] hover:brightness-110 active:scale-95 flex items-center justify-center text-white transition-all group border border-amber-300/50" aria-label="AI Send">
              <Sparkles size={18} className="min-[360px]:w-[20px] min-[360px]:h-[20px] group-hover:scale-110 transition-transform text-white" />
            </button>

            {/* Button 5: Shadow Learning AI */}
            <Link to="/shadow-learning" className="flex-shrink-0 w-10 h-10 min-[360px]:w-11 min-[360px]:h-11 min-[390px]:w-[50px] min-[390px]:h-[50px] rounded-xl min-[360px]:rounded-2xl bg-gradient-to-br from-teal-400 to-emerald-600 shadow-[inset_0_2px_4px_rgba(255,255,255,0.4),inset_0_-2px_4px_rgba(0,0,0,0.2),0_6px_16px_rgba(20,184,166,0.5)] hover:brightness-110 active:scale-95 flex items-center justify-center text-white transition-all group border border-teal-300/50" aria-label="Shadow Learning AI">
              <Brain size={18} className="min-[360px]:w-[20px] min-[360px]:h-[20px] group-hover:scale-110 transition-transform text-white" />
            </Link>
            
            {/* Button 6: Backtest */}
            <Link to="/backtest" className="flex-shrink-0 w-10 h-10 min-[360px]:w-11 min-[360px]:h-11 min-[390px]:w-[50px] min-[390px]:h-[50px] rounded-xl min-[360px]:rounded-2xl bg-gradient-to-br from-pink-500 to-rose-600 shadow-[inset_0_2px_4px_rgba(255,255,255,0.4),inset_0_-2px_4px_rgba(0,0,0,0.2),0_6px_16px_rgba(244,63,94,0.5)] hover:brightness-110 active:scale-95 flex items-center justify-center text-white transition-all group border border-pink-400/50" aria-label="Backtest">
              <FlaskConical size={18} className="min-[360px]:w-[20px] min-[360px]:h-[20px] group-hover:scale-110 transition-transform text-white" />
            </Link>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto pb-4 space-y-2 no-scrollbar relative animate-in fade-in slide-in-from-bottom-4 duration-700">
          
          {/* Tab Selector */}
          <div className="flex bg-[#10192e]/60 border border-white/5 rounded-xl p-0.5 shrink-0 sticky top-0 backdrop-blur-md z-30 overflow-x-auto no-scrollbar">
            <button 
              onClick={() => handleTabClick("positions")}
              className={cn(
                "flex-1 min-w-[100px] py-1.5 text-[11px] min-[375px]:text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1 active:scale-95",
                activeTab === "positions" ? "bg-blue-600 text-white shadow-lg shadow-blue-600/10 border border-white/5" : "text-white/60 hover:text-white"
              )}
            >
              <span>Pozitsiya</span>
              <span className={cn("text-[9px] px-1 py-0.5 rounded-full font-bold", activeTab === "positions" ? "bg-white/20 text-white" : "bg-white/5 text-white/40")}>
                {filteredPositions?.length ?? 0}
              </span>
            </button>
            <button 
              onClick={() => handleTabClick("limits")}
              className={cn(
                "flex-1 min-w-[100px] py-1.5 text-[11px] min-[375px]:text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1 active:scale-95",
                activeTab === "limits" ? "bg-blue-600 text-white shadow-lg shadow-blue-600/10 border border-white/5" : "text-white/60 hover:text-white"
              )}
            >
              <span>Limitlar</span>
              <span className={cn("text-[9px] px-1 py-0.5 rounded-full font-bold", activeTab === "limits" ? "bg-white/20 text-white" : "bg-white/5 text-white/40")}>
                {pending.data?.length ?? 0}
              </span>
            </button>
            <button 
              onClick={() => handleTabClick("history")}
              className={cn(
                "flex-1 min-w-[100px] py-1.5 text-[11px] min-[375px]:text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1 active:scale-95",
                activeTab === "history" ? "bg-blue-600 text-white shadow-lg shadow-blue-600/10 border border-white/5" : "text-white/60 hover:text-white"
              )}
            >
              <span>Tarix</span>
            </button>
          </div>

          {/* Swipeable Tab Contents */}
          <div 
            ref={tabContainerRef}
            onScroll={handleScroll}
            className="flex overflow-x-auto snap-x snap-mandatory no-scrollbar scroll-smooth w-full h-full pb-10"
          >
            {/* Positions Tab */}
            <div className="w-full shrink-0 snap-center px-1">
              <div className="space-y-2">
                {positions.isLoading ? (
                  <SkeletonRows />
                ) : filteredPositions && filteredPositions.length > 0 ? (
                  filteredPositions.map((p) => <PositionRow key={p.id} p={p} />)
                ) : (
                  <EmptyBox text="Hozircha ochiq pozitsiya yo'q" />
                )}
              </div>
            </div>

            {/* Limits Tab */}
            <div className="w-full shrink-0 snap-center px-1">
              <div className="space-y-2">
                {pending.isLoading ? (
                  <SkeletonRows count={2} />
                ) : pending.data && pending.data.length > 0 ? (
                  pending.data.map((o) => <PendingRow key={o.id} o={o} />)
                ) : (
                  <EmptyBox text="Hozircha kutilayotgan order yo'q" />
                )}
              </div>
            </div>

            {/* History Tab */}
            <div className="w-full shrink-0 snap-center px-1">
              <div className="space-y-2">
                <div className="flex items-center justify-between px-2 mb-1">
                  <span className="text-[10px] text-white/40 font-bold">SAVDO TARIXI</span>
                  <Link to="/history" className="text-[10px] text-blue-400 hover:underline">Barchasi</Link>
                </div>
                {history.isLoading ? (
                  <SkeletonRows count={2} />
                ) : history.data && history.data.length > 0 ? (
                  history.data.slice(0, 15).map((t) => <HistoryRow key={t.id} t={t} />)
                ) : (
                  <EmptyBox text="Hozircha yopilgan savdo yo'q" />
                )}
              </div>
            </div>
          </div>
          
        </div>

      </div>

      {/* AI Prompt Modal */}
      {showPrompt && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-md flex items-center justify-center px-4">
          <div className="bg-white/[0.03] border border-white/15 rounded-[32px] w-full max-w-sm p-6 shadow-[0_32px_64px_-16px_rgba(0,0,0,0.7),inset_0_1px_2px_rgba(255,255,255,0.25)] relative overflow-hidden backdrop-blur-3xl animate-in fade-in zoom-in-95 duration-200">
            {/* Liquid glass background glow blobs */}
            <div className="absolute top-[-50px] left-[-50px] w-40 h-40 rounded-full bg-indigo-500/25 blur-3xl pointer-events-none animate-pulse" />
            <div className="absolute bottom-[-50px] right-[-50px] w-40 h-40 rounded-full bg-pink-500/20 blur-3xl pointer-events-none animate-pulse" />
            
            <h3 className="text-white font-extrabold text-lg mb-1 drop-shadow-md relative z-10">AI'ga ko'rsatma yuborish</h3>
            <p className="text-[11px] text-white/50 mb-4 relative z-10 leading-normal">Trading qarorini yaxshilash uchun nima qilish kerakligini yozing.</p>
            <textarea 
              value={aiPrompt}
              onChange={(e) => setAiPrompt(e.target.value)}
              className="w-full h-28 bg-black/45 backdrop-blur-xl border border-white/10 rounded-2xl p-3.5 text-xs text-white placeholder:text-white/20 outline-none focus:border-indigo-500/60 focus:ring-1 focus:ring-indigo-500/20 transition-all resize-none mb-4 relative z-10 shadow-[inset_0_4px_12px_rgba(0,0,0,0.5)]"
              placeholder="Masalan: Faqat trend bo'yicha savdo qiling, GBP juftliklariga tegma..."
            />
            <div className="flex gap-2.5 relative z-10">
              <button onClick={() => setShowPrompt(false)} disabled={isSendingPrompt} className="flex-1 py-3 rounded-xl bg-white/5 border border-white/5 text-white/70 font-bold text-xs hover:bg-white/10 hover:border-white/10 hover:text-white transition-all duration-300 disabled:opacity-50 active:scale-95">Bekor qilish</button>
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
                className="flex-1 py-3 rounded-xl bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 text-white font-bold text-xs hover:brightness-110 active:scale-95 transition-all shadow-lg shadow-indigo-500/25 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {isSendingPrompt ? <span className="w-4 h-4 border-2 border-white/20 border-t-white rounded-full animate-spin" /> : "Yuborish"}
              </button>
            </div>
          </div>
        </div>
      )}

      <PaywallModal isOpen={showFirstTimePaywall} onClose={() => setShowFirstTimePaywall(false)} />
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
    <div className="rounded-2xl bg-[#10192e]/80 backdrop-blur-md border border-white/5 p-3 flex flex-col gap-2">
      <div className="flex items-center justify-between">
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
      
      {/* Badges Row */}
      {(p.agreed_strategies?.length || p.ai_used) ? (
        <div className="flex items-center gap-1.5 flex-wrap">
          {p.ai_used && (
            <div className="flex items-center gap-1 bg-purple-500/20 text-purple-400 border border-purple-500/30 px-2 py-0.5 rounded-md text-[9px] font-bold tracking-wider">
              <Bot size={10} /> AI
            </div>
          )}
          {p.agreed_strategies?.map((strat) => (
            <div key={strat} className="bg-white/10 text-white/70 border border-white/5 px-2 py-0.5 rounded-md text-[9px] font-bold tracking-wider uppercase">
              {strat}
            </div>
          ))}
        </div>
      ) : null}

      <div className="grid grid-cols-4 gap-1 text-[10px] mt-1">
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
      <div className="grid grid-cols-3 gap-1 text-[10px]">
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
    <div className="rounded-2xl bg-[#10192e]/60 backdrop-blur-md border border-white/5 p-3 flex flex-col gap-2">
      <div className="flex items-center justify-between">
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
      
      {/* Badges Row */}
      {(t.agreed_strategies?.length || t.ai_used) ? (
        <div className="flex items-center gap-1.5 flex-wrap">
          {t.ai_used && (
            <div className="flex items-center gap-1 bg-purple-500/20 text-purple-400 border border-purple-500/30 px-2 py-0.5 rounded-md text-[9px] font-bold tracking-wider">
              <Bot size={10} /> AI
            </div>
          )}
          {t.agreed_strategies?.map((strat) => (
            <div key={strat} className="bg-white/10 text-white/70 border border-white/5 px-2 py-0.5 rounded-md text-[9px] font-bold tracking-wider uppercase">
              {strat}
            </div>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function MiniField({ label, value, tone }: { label: string; value: string; tone?: "success" | "danger" }) {
  const cls = tone === "success" ? "text-emerald-400" : tone === "danger" ? "text-rose-400" : "text-white/90";
  return (
    <div className="rounded-lg bg-black/35 px-1 py-1 text-center">
      <p className="text-[7.5px] uppercase tracking-wider text-white/35 font-medium leading-none mb-0.5">{label}</p>
      <p className={`tabular-nums text-[9.5px] min-[375px]:text-[10.5px] font-bold ${cls} truncate leading-tight`}>{value}</p>
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
