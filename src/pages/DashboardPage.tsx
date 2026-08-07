import { useQuery, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { guestMock } from "@/lib/guestMock";
import { fmtMoney, fmtNum, timeAgo, cn, fmtDateShort } from "@/lib/utils";
import type { BotStatus, Position, TradeHistory, PendingOrder, BotSettings } from "@/lib/types";
import { Icon } from "@iconify/react";
import {
  Play, Pause, Settings, ChevronRight, TrendingUp, TrendingDown,
  ArrowDownLeft, ArrowUpRight, Crown, LogOut, UserPlus, Clock, FlaskConical, Sparkles, Brain, Bot, CandlestickChart, Globe, BookOpen, FileText, Activity, Search, X
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useMemo, useState, useRef, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BalanceTrendChart } from "@/components/BalanceTrendChart";
import { PaywallModal } from "@/components/PaywallModal";
import { TradingChartModal } from "@/components/TradingChartModal";

const polarToCartesian = (centerX: number, centerY: number, radius: number, angleInDegrees: number) => {
  const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180.0;
  return {
    x: centerX + radius * Math.cos(angleInRadians),
    y: centerY + radius * Math.sin(angleInRadians)
  };
};

const describeArc = (x: number, y: number, radius: number, startAngle: number, endAngle: number) => {
  const start = polarToCartesian(x, y, radius, startAngle);
  const end = polarToCartesian(x, y, radius, endAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
  return [
    "M", start.x, start.y, 
    "A", radius, radius, 0, largeArcFlag, 1, end.x, end.y
  ].join(" ");
};

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

  const [activeChart, setActiveChart] = useState<{ symbol: string; position?: Position | null; historyTrade?: TradeHistory | null } | null>(null);



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

  const strategyWeights = useMemo(() => ({
    smc: settings.data?.strategy_weight_smc ?? 60,
    pattern: settings.data?.strategy_weight_pattern ?? 60,
    news: settings.data?.strategy_weight_news ?? 60,
    wyckoff: settings.data?.strategy_weight_wyckoff ?? 50,
    sr_volume: settings.data?.strategy_weight_sr_volume ?? 50,
    auto_pattern: settings.data?.strategy_weight_auto_pattern ?? 50
  }), [settings.data]);

  const sentiment = useMemo(() => status.data?.market_sentiment ?? 50, [status.data]);

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
    const aiEnabled = !!settings.data?.ai_enabled;
    
    let nextRunning = false;
    let nextAiEnabled = false;

    if (!running) {
      nextRunning = true;
      nextAiEnabled = false;
    } else if (running && !aiEnabled) {
      nextRunning = true;
      nextAiEnabled = true;
    } else {
      nextRunning = false;
      nextAiEnabled = false;
    }

    if (isGuest) {
      guestMock.saveBotStatus({ is_running: nextRunning, message: nextRunning ? "Panel started" : "Panel paused" });
      guestMock.saveSettings({ ai_enabled: nextAiEnabled });
    } else {
      await Promise.all([
        supabase.from("bot_status").upsert(
          { user_id: user!.id, is_running: nextRunning, message: nextRunning ? "Panel started" : "Panel paused" },
          { onConflict: "user_id" }
        ),
        supabase.from("bot_settings").upsert(
          { user_id: user!.id, ai_enabled: nextAiEnabled },
          { onConflict: "user_id" }
        )
      ]);
    }
    status.refetch();
    settings.refetch();
  }

  const [limitsSearch, setLimitsSearch] = useState("");
  const [limitsAssetType, setLimitsAssetType] = useState<"all" | "forex" | "metals" | "indices" | "crypto">("all");

  const filteredPending = useMemo(() => {
    const all = pending.data ?? [];
    return all.filter((o) => {
      if (limitsSearch && !o.symbol.toLowerCase().includes(limitsSearch.toLowerCase())) {
        return false;
      }
      if (limitsAssetType !== "all") {
        const sym = (o.symbol || "").toUpperCase();
        let type: "forex" | "metals" | "indices" | "crypto" = "forex";
        if (sym.includes("XAU") || sym.includes("XAG") || sym.includes("XPT") || sym.includes("XPD") || sym.includes("GOLD") || sym.includes("SILVER")) {
          type = "metals";
        } else if (sym.includes("BTC") || sym.includes("ETH") || sym.includes("SOL") || sym.includes("XRP") || sym.includes("ADA") || sym.includes("DOGE") || sym.includes("DOT") || sym.includes("LTC")) {
          type = "crypto";
        } else if (sym.includes("DE40") || sym.includes("US30") || sym.includes("USTEC") || sym.includes("SPX") || sym.includes("HK50") || sym.includes("UK100") || sym.includes("NAS100") || sym.includes("US500") || sym.includes("GER30") || sym.includes("EU50")) {
          type = "indices";
        }
        if (type !== limitsAssetType) return false;
      }
      return true;
    });
  }, [pending.data, limitsSearch, limitsAssetType]);

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
  const aiEnabled = !!settings.data?.ai_enabled;
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

        {/* Card 22%: Main Neumorphic Card */}
        <div className="w-full h-[17dvh] min-h-[145px] min-[340px]:min-h-[155px] bg-[#11131a] rounded-[24px] min-[340px]:rounded-[28px] p-1.5 min-[340px]:p-2 shadow-[inset_0_1px_2px_rgba(255,255,255,0.05),0_10px_40px_rgba(0,0,0,0.6)] border border-white/5 relative overflow-hidden flex shrink-0 animate-in fade-in slide-in-from-top-2 duration-700">
          
          {/* Subtle Ambient Glow */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 bg-blue-500/10 rounded-full blur-[50px] pointer-events-none" />

          {/* Left Column: AI Yordam & Sozlama */}
          <div className="flex flex-col justify-around items-center h-full z-10 py-0 shrink-0 gap-0.5 pr-0.5 border-r border-white/5 w-[50px] min-[360px]:w-[58px]">
            {/* Button 4: AI Send */}
            <button onClick={() => setShowPrompt(true)} className="flex flex-col items-center group transition-all" aria-label="AI Send">
              <div className="w-9 h-9 min-[360px]:w-10 min-[360px]:h-10 rounded-lg bg-[#1a1d29] shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_3px_8px_rgba(0,0,0,0.3)] border border-white/5 flex items-center justify-center group-hover:bg-[#1e2230] group-active:scale-95 transition-all relative overflow-hidden">
                <div className="absolute inset-0 bg-amber-500/10 opacity-0 group-hover:opacity-100 transition-opacity" />
                <Icon icon="game-icons:bully-minion" width="18" height="18" className="text-amber-400 group-hover:scale-110 transition-transform" />
              </div>
              <span className="text-[7px] min-[360px]:text-[8px] font-bold text-white/50 group-hover:text-white/80 transition-colors mt-0.5">AI Yordam</span>
            </button>

            {/* Button 1: Settings */}
            <Link to="/settings" className="flex flex-col items-center group transition-all" aria-label="Settings">
              <div className="w-9 h-9 min-[360px]:w-10 min-[360px]:h-10 rounded-lg bg-[#1a1d29] shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_3px_8px_rgba(0,0,0,0.3)] border border-white/5 flex items-center justify-center group-hover:bg-[#1e2230] group-active:scale-95 transition-all relative overflow-hidden">
                <div className="absolute inset-0 bg-slate-400/10 opacity-0 group-hover:opacity-100 transition-opacity" />
                <Icon icon="eos-icons:atom-electron" width="18" height="18" className="text-rose-400 group-hover:text-rose-300 group-hover:scale-110 transition-transform duration-500 animate-spin-slow" />
              </div>
              <span className="text-[7px] min-[360px]:text-[8px] font-bold text-white/50 group-hover:text-white/80 transition-colors mt-0.5">Sozlama</span>
            </Link>
          </div>

          {/* Center Column: Header, Balance */}
          <div className="flex-1 flex flex-col justify-between h-full px-1.5 min-[340px]:px-2 z-10 min-w-0">
            {/* Card Top Header */}
            <div className="flex items-center justify-between w-full gap-1 px-0.5">
              
              {/* 1. Akkaunt */}
              <div className="relative min-w-0" ref={profileMenuRef}>
                <div 
                  onClick={() => setShowProfileMenu(!showProfileMenu)}
                  className="flex items-center gap-1 bg-[#1a1d29] px-1.5 py-0.5 rounded-full shadow-[inset_0_2px_4px_rgba(0,0,0,0.2),0_1px_2px_rgba(255,255,255,0.05)] border border-[#2a2f42] cursor-pointer hover:bg-[#1e2230] transition-all min-w-0"
                >
                  <div className="w-3 h-3 min-[340px]:w-3.5 min-[340px]:h-3.5 rounded-full bg-white flex items-center justify-center overflow-hidden shrink-0">
                    <img 
                      src={`https://api.dicebear.com/7.x/bottts/svg?seed=${user?.email || "Ana"}`} 
                      alt="Profile" 
                      className="w-full h-full object-cover"
                    />
                  </div>
                  <span className="text-white/90 text-[8px] min-[340px]:text-[9px] font-bold tracking-tight truncate">
                    {settings.data?.mt5_login || "109545213"}
                  </span>
                </div>
                
                {showProfileMenu && (
                  <div className="absolute top-full left-0 mt-1 w-32 bg-[#1a1d29] border border-[#2a2f42] rounded-xl shadow-xl overflow-hidden z-50 animate-in fade-in slide-in-from-top-2 duration-200">
                    <div className="p-1 space-y-0.5">
                      <button 
                        onClick={async () => {
                          setShowProfileMenu(false);
                          await logout();
                          navigate("/auth");
                        }}
                        className="w-full flex items-center gap-1.5 px-2 py-1.5 text-[9px] font-medium text-white/80 hover:text-white hover:bg-white/5 rounded-lg transition-colors"
                      >
                        <UserPlus size={11} className="text-blue-400 shrink-0" />
                        <span>Qo'shish</span>
                      </button>
                      <button 
                        onClick={async () => {
                          setShowProfileMenu(false);
                          await logout();
                          navigate("/auth");
                        }}
                        className="w-full flex items-center gap-1.5 px-2 py-1.5 text-[9px] font-medium text-rose-400/80 hover:text-rose-400 hover:bg-rose-500/10 rounded-lg transition-colors"
                      >
                        <LogOut size={11} className="shrink-0" />
                        <span>Chiqish</span>
                      </button>
                    </div>
                  </div>
                )}
              </div>



              <Link 
                to="/monitoring" 
                className="w-5.5 h-5.5 min-[340px]:w-6.5 min-[340px]:h-6.5 rounded-full bg-[#1a1d29] shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_4px_10px_rgba(0,0,0,0.3)] border border-white/5 flex items-center justify-center text-emerald-400 hover:text-emerald-300 transition-colors cursor-pointer active:scale-95 shrink-0 relative"
                title="System Monitoring & Diagnostika"
              >
                <Icon icon="twemoji:heart-suit" width="12" height="12" className="animate-heartbeat" />
                <span className="absolute -top-0.5 -right-0.5 w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
              </Link>

              {/* 3. Web */}
              <a 
                href="https://akkauntim-connect.vercel.app/" 
                target="_blank" 
                rel="noopener noreferrer"
                className="w-5.5 h-5.5 min-[340px]:w-6.5 min-[340px]:h-6.5 rounded-full bg-[#1a1d29] shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_4px_10px_rgba(0,0,0,0.3)] border border-white/5 flex items-center justify-center text-blue-400 hover:text-blue-300 transition-colors cursor-pointer active:scale-95 shrink-0"
                title="Vebsaytni ochish"
              >
                <Globe size={10} />
              </a>

              {/* 3. Telegram */}
              <a 
                href="https://t.me/akcume_signal" 
                target="_blank" 
                rel="noopener noreferrer"
                className="w-5.5 h-5.5 min-[340px]:w-6.5 min-[340px]:h-6.5 rounded-full bg-[#1a1d29] shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_4px_10px_rgba(0,0,0,0.3)] border border-white/5 flex items-center justify-center text-[#229ED9] hover:text-[#28a8e9] transition-colors cursor-pointer active:scale-95 shrink-0"
                title="Telegram kanali"
              >
                <svg viewBox="0 0 24 24" width="10" height="10" fill="currentColor">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1 .22-1.6 1.5-1.55 2.76-2.97 2.84-3.37.01-.09-.01-.13-.06-.15-.05-.02-.12-.01-.17.01-.08.02-1.28.82-3.61 2.39-.34.23-.65.35-.93.34-.3-.01-.89-.17-1.32-.31-.53-.17-.95-.26-.91-.56.02-.15.22-.3.6-.45 2.34-1.02 3.9-1.69 4.67-2.01 2.21-.92 2.67-1.08 2.97-1.08.07 0 .21.02.3.1.08.07.1.16.11.23.01.06.02.19.01.29z"/>
                </svg>
              </a>

              {/* 4. Tarif */}
              <Link 
                to="/pricing" 
                className="w-5.5 h-5.5 min-[340px]:w-6.5 min-[340px]:h-6.5 rounded-full bg-[#1a1d29] shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_4px_10px_rgba(0,0,0,0.3)] border border-white/5 flex items-center justify-center text-amber-400 hover:text-amber-300 transition-colors cursor-pointer active:scale-95 shrink-0"
                title="Tariflar / Premium"
              >
                <Icon icon="noto:crown" width="12" height="12" />
              </Link>

            </div>

            {/* Balance Dial Container with Legends */}
            <div className="flex-1 flex items-center justify-between w-full select-none gap-1 px-1">
              
              {/* Left Legend: SMC, PAT, NWS */}
              <div className="flex flex-col gap-1 items-start text-[7px] font-extrabold text-white/50 leading-none shrink-0 pl-0.5">
                <div className="flex items-center gap-1">
                  <span className="w-1 h-1 rounded-full bg-[#06b6d4] shrink-0 animate-pulse" />
                  <span>SMC</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="w-1 h-1 rounded-full bg-[#3b82f6] shrink-0" />
                  <span>PAT</span>
                </div>
                <div className="flex items-center gap-1">
                  <span className="w-1 h-1 rounded-full bg-[#a855f7] shrink-0" />
                  <span>NWS</span>
                </div>
              </div>

              <div 
                onClick={toggleBot}
                className="relative w-[95px] h-[95px] min-[340px]:w-[108px] min-[340px]:h-[108px] min-[375px]:w-[122px] min-[375px]:h-[122px] flex items-center justify-center rounded-full cursor-pointer active:scale-95 transition-all duration-300 group shrink-0"
              >
                
                {/* Hover Play/Pause Overlay */}
                <div className="absolute inset-0 rounded-full bg-black/50 opacity-0 group-hover:opacity-100 backdrop-blur-[2px] transition-all duration-300 flex flex-col items-center justify-center z-20 shadow-[inset_0_0_20px_rgba(255,255,255,0.05)] border border-white/5">
                  {running ? (
                     <div className="text-white text-[9px] font-black tracking-widest flex flex-col items-center drop-shadow-md">
                        <span className="w-6 h-6 rounded-full bg-rose-500/80 mb-1 flex items-center justify-center shadow-[0_0_15px_rgba(244,63,94,0.6)] backdrop-blur-md">
                           <span className="w-2.5 h-2.5 bg-white rounded-[1px]"></span>
                        </span>
                        BOTNI TO'XTATISH
                     </div>
                  ) : (
                     <div className="text-white text-[9px] font-black tracking-widest flex flex-col items-center drop-shadow-md">
                        <span className="w-6 h-6 rounded-full bg-emerald-500/80 mb-1 flex items-center justify-center shadow-[0_0_15px_rgba(16,185,129,0.6)] pl-0.5 backdrop-blur-md">
                           <svg width="12" height="12" viewBox="0 0 24 24" fill="white"><path d="M5 3l14 9-14 9V3z"/></svg>
                        </span>
                        BOTNI ISHGA TUSHIRISH
                     </div>
                  )}
                </div>

                {/* SVG circular track, glowing progress rings, sentiment, and AI weights */}
                <svg viewBox="0 0 120 120" className="absolute inset-0 w-full h-full overflow-visible pointer-events-none">
                  <defs>
                    <linearGradient id="botActiveGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#10b981" />
                      <stop offset="100%" stopColor="#06b6d4" />
                    </linearGradient>
                    <linearGradient id="sentimentGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#f43f5e" />     {/* Strong Sell */}
                      <stop offset="50%" stopColor="#eab308" />    {/* Neutral */}
                      <stop offset="100%" stopColor="#10b981" />   {/* Strong Buy */}
                    </linearGradient>
                    <filter id="glowEffect" x="-20%" y="-20%" width="140%" height="140%">
                      <feGaussianBlur stdDeviation="1.5" result="blur" />
                      <feMerge>
                        <feMergeNode in="blur" />
                        <feMergeNode in="SourceGraphic" />
                      </feMerge>
                    </filter>
                  </defs>
                  
                  {/* Outer Rings & HUD elements */}
                  
                  {/* 1. Multi-Strategy AI Weights Ring (Radius 50) */}
                  {/* SMC (0-50 deg) */}
                  <path d={describeArc(60, 60, 50, 0, 50)} stroke="rgba(255,255,255,0.03)" strokeWidth="2.2" fill="none" strokeLinecap="round" />
                  <path d={describeArc(60, 60, 50, 0, (strategyWeights.smc / 100) * 50)} stroke="#06b6d4" strokeWidth="2.2" fill="none" strokeLinecap="round" filter="url(#glowEffect)" />

                  {/* Pattern (60-110 deg) */}
                  <path d={describeArc(60, 60, 50, 60, 110)} stroke="rgba(255,255,255,0.03)" strokeWidth="2.2" fill="none" strokeLinecap="round" />
                  <path d={describeArc(60, 60, 50, 60, 60 + (strategyWeights.pattern / 100) * 50)} stroke="#3b82f6" strokeWidth="2.2" fill="none" strokeLinecap="round" filter="url(#glowEffect)" />

                  {/* News (120-170 deg) */}
                  <path d={describeArc(60, 60, 50, 120, 170)} stroke="rgba(255,255,255,0.03)" strokeWidth="2.2" fill="none" strokeLinecap="round" />
                  <path d={describeArc(60, 60, 50, 120, 120 + (strategyWeights.news / 100) * 50)} stroke="#a855f7" strokeWidth="2.2" fill="none" strokeLinecap="round" filter="url(#glowEffect)" />

                  {/* Wyckoff (180-230 deg) */}
                  <path d={describeArc(60, 60, 50, 180, 230)} stroke="rgba(255,255,255,0.03)" strokeWidth="2.2" fill="none" strokeLinecap="round" />
                  <path d={describeArc(60, 60, 50, 180, 180 + (strategyWeights.wyckoff / 100) * 50)} stroke="#ec4899" strokeWidth="2.2" fill="none" strokeLinecap="round" filter="url(#glowEffect)" />

                  {/* SR Volume (240-290 deg) */}
                  <path d={describeArc(60, 60, 50, 240, 290)} stroke="rgba(255,255,255,0.03)" strokeWidth="2.2" fill="none" strokeLinecap="round" />
                  <path d={describeArc(60, 60, 50, 240, 240 + (strategyWeights.sr_volume / 100) * 50)} stroke="#f59e0b" strokeWidth="2.2" fill="none" strokeLinecap="round" filter="url(#glowEffect)" />

                  {/* Auto Pattern (300-350 deg) */}
                  <path d={describeArc(60, 60, 50, 300, 350)} stroke="rgba(255,255,255,0.03)" strokeWidth="2.2" fill="none" strokeLinecap="round" />
                  <path d={describeArc(60, 60, 50, 300, 300 + (strategyWeights.auto_pattern / 100) * 50)} stroke="#10b981" strokeWidth="2.2" fill="none" strokeLinecap="round" filter="url(#glowEffect)" />


                  {/* 2. NLP Market Sentiment Ring (Radius 44) */}
                  {/* Sweep from 210 deg (bottom-left) to 150 deg (bottom-right) or standard 60-300 deg */}
                  <path d={describeArc(60, 60, 43, 60, 300)} stroke="rgba(255,255,255,0.04)" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeDasharray="2.5 1.5" />
                  <path d={describeArc(60, 60, 43, 60, 60 + (sentiment / 100) * 240)} stroke="url(#sentimentGrad)" strokeWidth="2" fill="none" strokeLinecap="round" filter="url(#glowEffect)" />


                  {/* 3. Bot Control Ring (Radius 36) */}
                  <circle cx="60" cy="60" r="36" stroke="rgba(255,255,255,0.02)" strokeWidth="2" fill="none" />
                  <circle 
                    cx="60" cy="60" r="36" 
                    stroke={running ? "url(#botActiveGrad)" : "#f43f5e"} 
                    strokeWidth="2.5" 
                    fill="none" 
                    strokeDasharray="226.2"
                    strokeDashoffset={running ? "40" : "160"}
                    strokeLinecap="round"
                    filter="url(#glowEffect)"
                    className="transition-all duration-1000 ease-out origin-center -rotate-90"
                  />


                  {/* 4. Center 3D Dial Core (Radius 31) */}
                  <circle 
                    cx="60" cy="60" r="31" 
                    className="fill-gradient from-[#1b1e2c] to-[#0a0b12] stroke-white/5" 
                    style={{ fill: "#0c0e17", filter: "drop-shadow(0 4px 8px rgba(0,0,0,0.8))" }}
                  />
                </svg>

                {/* Inner Balance & Status Info */}
                <div className="text-center z-10 flex flex-col items-center justify-center p-0.5 select-none pointer-events-none gap-0">
                  {/* Market Sentiment Mini Badge */}
                  <div className="flex items-center justify-center gap-0.5">
                    {sentiment > 55 ? (
                      <TrendingUp size={9} className="text-emerald-400 shrink-0" strokeWidth={2.5} />
                    ) : sentiment < 45 ? (
                      <TrendingDown size={9} className="text-rose-400 shrink-0" strokeWidth={2.5} />
                    ) : (
                      <Sparkles size={8} className="text-amber-400 shrink-0 animate-pulse" />
                    )}
                    <span className={cn(
                      "text-[8px] font-black leading-none tracking-tight",
                      sentiment > 55 ? "text-emerald-400" : sentiment < 45 ? "text-rose-400" : "text-amber-400"
                    )}>
                      {sentiment}%
                    </span>
                  </div>
                  
                  {/* Balance Value */}
                  <h1 className="text-[14px] min-[340px]:text-[16px] min-[375px]:text-[18px] font-black text-transparent bg-clip-text bg-gradient-to-b from-white to-white/80 tracking-tight tabular-nums drop-shadow-md leading-none py-0.5">
                    {equity != null ? (
                      new Intl.NumberFormat("en-US", {
                        style: "currency",
                        currency: currency || "USD",
                        maximumFractionDigits: 0,
                      }).format(Math.round(Number(equity)))
                    ) : "$89,405"}
                  </h1>

                  {/* Status Badge */}
                  <div className="flex items-center justify-center">
                    {!running ? (
                      <span className="text-rose-400 flex items-center gap-0.5 font-black text-[7px] tracking-wider uppercase">
                        <span className="w-1 h-1 rounded-full bg-rose-400" />
                        STOP
                      </span>
                    ) : aiEnabled ? (
                      <span className="text-cyan-400 flex items-center gap-0.5 font-black text-[7px] tracking-wider uppercase animate-pulse">
                        <Bot size={8} className="text-cyan-400" />
                        AI FAOL
                      </span>
                    ) : (
                      <span className="text-emerald-400 flex items-center gap-0.5 font-black text-[7px] tracking-wider uppercase">
                        <span className="w-1 h-1 rounded-full bg-emerald-400 animate-ping" />
                        FAOL
                      </span>
                    )}
                  </div>
                </div>

              </div>

              {/* Right Legend: WYC, SRV, AUT */}
              <div className="flex flex-col gap-1 items-end text-[7px] font-extrabold text-white/50 leading-none shrink-0 pr-0.5">
                <div className="flex items-center gap-1">
                  <span>WYC</span>
                  <span className="w-1 h-1 rounded-full bg-[#ec4899] shrink-0" />
                </div>
                <div className="flex items-center gap-1">
                  <span>SRV</span>
                  <span className="w-1 h-1 rounded-full bg-[#f59e0b] shrink-0" />
                </div>
                <div className="flex items-center gap-1">
                  <span>AUT</span>
                  <span className="w-1 h-1 rounded-full bg-[#10b981] shrink-0" />
                </div>
              </div>

            </div>
          </div>

          {/* Right Column: Signallar & O'rganish */}
          <div className="flex flex-col justify-around items-center h-full z-10 py-0 shrink-0 gap-0.5 pl-0.5 border-l border-white/5 w-[50px] min-[360px]:w-[58px]">
            {/* Button 2: Signals */}
            <Link to="/signals" className="flex flex-col items-center group transition-all" aria-label="Signals">
              <div className="w-9 h-9 min-[360px]:w-10 min-[360px]:h-10 rounded-lg bg-[#1a1d29] shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_3px_8px_rgba(0,0,0,0.3)] border border-white/5 flex items-center justify-center group-hover:bg-[#1e2230] group-active:scale-95 transition-all relative overflow-hidden">
                <div className="absolute inset-0 bg-orange-500/10 opacity-0 group-hover:opacity-100 transition-opacity" />
                <Icon icon="streamline-stickies-color:dangerous-chemical-lab-duo" width="18" height="18" className="text-orange-400 group-hover:scale-110 transition-transform" />
              </div>
              <span className="text-[7px] min-[360px]:text-[8px] font-bold text-white/50 group-hover:text-white/80 transition-colors mt-0.5">Signallar</span>
            </Link>

            {/* Button 5: Shadow Learning AI */}
            <Link to="/shadow-learning" className="flex flex-col items-center group transition-all" aria-label="Shadow Learning AI">
              <div className="w-9 h-9 min-[360px]:w-10 min-[360px]:h-10 rounded-lg bg-[#1a1d29] shadow-[inset_0_1px_1px_rgba(255,255,255,0.05),0_3px_8px_rgba(0,0,0,0.3)] border border-white/5 flex items-center justify-center group-hover:bg-[#1e2230] group-active:scale-95 transition-all relative overflow-hidden">
                <div className="absolute inset-0 bg-emerald-500/10 opacity-0 group-hover:opacity-100 transition-opacity" />
                <Icon icon="game-icons:black-hand-shield" width="18" height="18" className="text-emerald-400 group-hover:scale-110 transition-transform" />
              </div>
              <span className="text-[7px] min-[360px]:text-[8px] font-bold text-white/50 group-hover:text-white/80 transition-colors mt-0.5">O'rganish</span>
            </Link>
          </div>

        </div>
 
 
        <div className="flex-1 overflow-y-auto pb-4 space-y-2 no-scrollbar relative animate-in fade-in slide-in-from-bottom-4 duration-700">
          
          {/* Tab Selector */}
          <div className="flex bg-[#10192e]/60 border border-white/5 rounded-xl p-0.5 shrink-0 sticky top-0 backdrop-blur-md z-30 overflow-x-auto no-scrollbar items-center gap-0.5 w-full">
            <button 
              onClick={() => handleTabClick("positions")}
              className={cn(
                "flex-1 min-w-[70px] py-1.5 text-[10px] min-[350px]:text-[11px] min-[375px]:text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1 active:scale-95",
                activeTab === "positions" ? "bg-blue-600 text-white shadow-lg shadow-blue-600/10 border border-white/5" : "text-white/60 hover:text-white"
              )}
            >
              <span>Pozitsiya</span>
              <span className={cn("text-[8px] px-1 py-0.5 rounded-full font-bold", activeTab === "positions" ? "bg-white/20 text-white" : "bg-white/5 text-white/40")}>
                {filteredPositions?.length ?? 0}
              </span>
            </button>
            <button 
              onClick={() => handleTabClick("limits")}
              className={cn(
                "flex-1 min-w-[70px] py-1.5 text-[10px] min-[350px]:text-[11px] min-[375px]:text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1 active:scale-95",
                activeTab === "limits" ? "bg-blue-600 text-white shadow-lg shadow-blue-600/10 border border-white/5" : "text-white/60 hover:text-white"
              )}
            >
              <span>Limitlar</span>
              <span className={cn("text-[8px] px-1 py-0.5 rounded-full font-bold", activeTab === "limits" ? "bg-white/20 text-white" : "bg-white/5 text-white/40")}>
                {pending.data?.length ?? 0}
              </span>
            </button>
            <button 
              onClick={() => handleTabClick("history")}
              className={cn(
                "flex-1 min-w-[70px] py-1.5 text-[10px] min-[350px]:text-[11px] min-[375px]:text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1 active:scale-95",
                activeTab === "history" ? "bg-blue-600 text-white shadow-lg shadow-blue-600/10 border border-white/5" : "text-white/60 hover:text-white"
              )}
            >
              <span>Tarix</span>
            </button>
            
            {/* Small Filter Button */}
            <button 
              onClick={toggleFilter}
              className={cn(
                "px-2 py-1.5 rounded-lg transition-all flex items-center justify-center gap-1 active:scale-95 border mr-0.5",
                filterMode !== "all" 
                  ? "bg-purple-600/20 text-purple-400 border-purple-500/30" 
                  : "text-white/40 hover:text-white/60 border-transparent bg-white/5"
              )}
              title="Filtrlash"
            >
              {filterMode === "all" && (
                <div className="relative w-3.5 h-3.5 flex items-center justify-center">
                  <TrendingUp size={10} className="text-emerald-400 absolute top-0 left-0" strokeWidth={2.5} />
                  <TrendingDown size={10} className="text-rose-400 absolute bottom-0 right-0" strokeWidth={2.5} />
                </div>
              )}
              {filterMode === "profit" && <TrendingUp size={12} className="text-emerald-400" strokeWidth={2.5} />}
              {filterMode === "loss" && <TrendingDown size={12} className="text-rose-400" strokeWidth={2.5} />}
            </button>
          </div>

          {/* Active Tab Content */}
          <div className="w-full h-full pb-10 px-1 animate-in fade-in duration-300">
            {activeTab === "positions" && (
              <div className="space-y-2">
                {positions.isLoading ? (
                  <SkeletonRows />
                ) : filteredPositions && filteredPositions.length > 0 ? (
                  filteredPositions.map((p) => (
                    <PositionRow
                      key={p.id}
                      p={p}
                      onClick={() => setActiveChart({ symbol: p.symbol, position: p })}
                    />
                  ))
                ) : (
                  <EmptyBox text="Hozircha ochiq pozitsiya yo'q" />
                )}
              </div>
            )}

            {activeTab === "limits" && (
              <div className="space-y-2">
                {/* Search & Category Filter Bar */}
                <div className="bg-[#10192e]/40 border border-white/5 rounded-xl p-2 space-y-2 mb-2">
                  <div className="relative">
                    <Search size={12} className="absolute left-2.5 top-2 text-white/30" />
                    <input
                      type="text"
                      placeholder="Simvol orqali qidirish..."
                      value={limitsSearch}
                      onChange={(e) => setLimitsSearch(e.target.value)}
                      className="w-full bg-black/30 border border-white/5 rounded-lg pl-8 pr-2 py-1 text-[11px] text-white placeholder:text-white/20 focus:outline-none focus:border-blue-500/40"
                    />
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {(["all", "forex", "metals", "indices", "crypto"] as const).map((type) => (
                      <button
                        key={type}
                        onClick={() => setLimitsAssetType(type)}
                        className={cn(
                          "px-2 py-0.5 rounded text-[10px] font-bold border transition-all cursor-pointer capitalize",
                          limitsAssetType === type
                            ? "bg-blue-600/20 text-blue-400 border-blue-500/30"
                            : "bg-transparent text-white/40 border-white/5 hover:text-white/60"
                        )}
                      >
                        {type === "all" ? "Barchasi" : type}
                      </button>
                    ))}
                  </div>
                </div>

                {pending.isLoading ? (
                  <SkeletonRows count={2} />
                ) : filteredPending && filteredPending.length > 0 ? (
                  filteredPending.map((o) => (
                    <PendingRow
                      key={o.id}
                      o={o}
                      onClick={() => setActiveChart({ symbol: o.symbol })}
                      onCancel={async () => {
                        if (isGuest) {
                          // mock cancel in guest mode
                          qc.invalidateQueries({ queryKey: ["pending_orders"] });
                        } else {
                          try {
                            if (o.ticket) {
                              await fetch(`/api/orders/pending/${o.ticket}`, { method: "DELETE" });
                            }
                            await supabase.from("pending_orders").delete().eq("id", o.id);
                            qc.invalidateQueries({ queryKey: ["pending_orders"] });
                          } catch (e) {
                            console.error("Bekor qilishda xatolik:", e);
                          }
                        }
                      }}
                    />
                  ))
                ) : (
                  <EmptyBox text="Mos keluvchi limit order yo'q" />
                )}
              </div>
            )}

            {activeTab === "history" && (
              <div className="space-y-2">
                <div className="flex items-center justify-between px-2 mb-1">
                  <span className="text-[10px] text-white/40 font-bold">SAVDO TARIXI</span>
                  <Link to="/history" className="text-[10px] text-blue-400 hover:underline">Barchasi</Link>
                </div>
                {history.isLoading ? (
                  <SkeletonRows count={2} />
                ) : history.data && history.data.length > 0 ? (
                  history.data.slice(0, 15).map((t) => (
                    <HistoryRow
                      key={t.id}
                      t={t}
                      onClick={() => setActiveChart({ symbol: t.symbol, historyTrade: t })}
                    />
                  ))
                ) : (
                  <EmptyBox text="Hozircha yopilgan savdo yo'q" />
                )}
              </div>
            )}
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
      <TradingChartModal 
        isOpen={!!activeChart} 
        onClose={() => setActiveChart(null)} 
        symbol={activeChart?.symbol ?? ""} 
        position={activeChart?.position} 
        historyTrade={activeChart?.historyTrade}
      />
    </div>
  );
}

export function EmptyLine({ text }: { text: string }) {
  return <p className="py-6 text-center text-xs text-white/40">{text}</p>;
}

function PositionRow({ p, onClick }: { p: Position; onClick?: () => void }) {
  const isBuy = String(p.side).toUpperCase() === "BUY";
  const profit = Number(p.profit ?? 0);
  return (
    <div
      onClick={onClick}
      className="rounded-xl bg-[#10192e] border border-white/5 p-2 flex flex-col gap-1.5 cursor-pointer hover:border-blue-500/40 hover:bg-[#121c34] transition-all group"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className={`px-1.5 py-0.5 rounded text-[8.5px] font-black ${isBuy ? "bg-emerald-500/20 text-emerald-400" : "bg-rose-500/20 text-rose-400"}`}>
            {isBuy ? (
              <span className="inline-flex items-center gap-1">
                BUY
                <Icon icon="game-icons:bull-horns" width="12" height="12" className="text-emerald-400" />
              </span>
            ) : (
              <span className="inline-flex items-center gap-1">
                SELL
                <Icon icon="game-icons:bear-head" width="12" height="12" className="text-rose-400" />
              </span>
            )}
          </span>
          <span className="text-xs font-bold text-white truncate group-hover:text-blue-400 transition-colors flex items-center gap-1">
            {p.symbol}
            <CandlestickChart size={10} className="opacity-0 group-hover:opacity-100 transition-opacity text-blue-400" />
          </span>
          <span className="text-[8.5px] text-white/40 shrink-0">{fmtNum(p.volume, 2)} lot &bull; {fmtDateShort(p.opened_at)}</span>
        </div>
        <span className={`inline-flex items-center gap-1 text-xs font-black tabular-nums ${profit >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
          <Icon icon={profit >= 0 ? "mdi:rocket-launch" : "game-icons:evil-hand"} width="14" height="14" className={profit >= 0 ? "text-emerald-400" : "text-rose-400"} />
          {fmtMoney(Math.abs(profit)).replace(/^[^0-9]+/, "")}
        </span>
      </div>
      
      {/* Badges Row */}
      {(p.agreed_strategies?.length || p.ai_used) ? (
        <div className="flex items-center gap-1 flex-wrap">
          {p.ai_used && (
            <div className="flex items-center gap-0.5 bg-purple-500/20 text-purple-400 border border-purple-500/30 px-1.5 py-0 rounded text-[8px] font-bold tracking-wider">
              <Bot size={8} /> AI
            </div>
          )}
          {p.agreed_strategies?.map((strat) => (
            <div key={strat} className="bg-white/10 text-white/70 border border-white/5 px-1.5 py-0 rounded text-[8px] font-bold tracking-wider uppercase">
              {strat}
            </div>
          ))}
        </div>
      ) : null}

      <div className="grid grid-cols-4 gap-1 text-[9px] mt-0.5">
        <MiniField label="Open" value={fmtNum(p.open_price, 5)} />
        <MiniField label="Now" value={fmtNum(p.current_price, 5)} />
        <MiniField label="SL" value={p.stop_loss ? fmtNum(p.stop_loss, 5) : "—"} tone={p.stop_loss ? "danger" : undefined} />
        <MiniField label="TP" value={p.take_profit ? fmtNum(p.take_profit, 5) : "—"} tone={p.take_profit ? "success" : undefined} />
      </div>
    </div>
  );
}

function PendingRow({ o, onClick, onCancel }: { o: PendingOrder; onClick?: () => void; onCancel?: () => void }) {
  const isBuy = (o.type || "").toLowerCase().startsWith("buy");
  return (
    <div
      onClick={onClick}
      className="rounded-xl bg-[#10192e] border border-white/5 p-2 flex flex-col gap-1.5 cursor-pointer hover:border-blue-500/40 hover:bg-[#121c34] transition-all group"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className={`px-1.5 py-0.5 rounded text-[8.5px] font-black uppercase ${isBuy ? "bg-emerald-500/20 text-emerald-400" : "bg-rose-500/20 text-rose-400"}`}>
            {o.type.replace("_", " ")}
          </span>
          <span className="text-xs font-bold text-white truncate group-hover:text-blue-400 transition-colors flex items-center gap-1">
            {o.symbol}
            <CandlestickChart size={10} className="opacity-0 group-hover:opacity-100 transition-opacity text-blue-400" />
          </span>
          <span className="text-[8.5px] text-white/40 shrink-0">{fmtNum(o.volume, 2)} lot &bull; {fmtDateShort(o.created_at)}</span>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {onCancel && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onCancel();
              }}
              className="p-1 rounded hover:bg-rose-500/10 text-white/40 hover:text-rose-400 transition-all cursor-pointer"
              title="Bekor qilish"
            >
              <X size={11} />
            </button>
          )}
          <Clock size={12} className="text-white/40" />
        </div>
      </div>
      <div className="grid grid-cols-3 gap-1 text-[9px]">
        <MiniField label="Price" value={fmtNum(o.price, 5)} />
        <MiniField label="SL" value={o.stop_loss ? fmtNum(o.stop_loss, 5) : "—"} tone={o.stop_loss ? "danger" : undefined} />
        <MiniField label="TP" value={o.take_profit ? fmtNum(o.take_profit, 5) : "—"} tone={o.take_profit ? "success" : undefined} />
      </div>
    </div>
  );
}

function HistoryRow({ t, onClick }: { t: TradeHistory; onClick?: () => void }) {
  const isBuy = String(t.side).toUpperCase() === "BUY";
  const profit = Number(t.profit ?? 0);
  return (
    <div
      onClick={onClick}
      className="rounded-xl bg-[#10192e] border border-white/5 p-2 flex flex-col gap-1.5 cursor-pointer hover:border-blue-500/40 hover:bg-[#121c34] transition-all group"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 min-w-0">
          <span className={`px-1.5 py-0.5 rounded text-[8.5px] font-black ${isBuy ? "bg-emerald-500/15 text-emerald-400" : "bg-rose-500/15 text-rose-400"}`}>
            {isBuy ? "BUY" : "SELL"}
          </span>
          <span className="text-xs font-bold text-white truncate group-hover:text-blue-400 transition-colors flex items-center gap-1">
            {t.symbol}
            <CandlestickChart size={10} className="opacity-0 group-hover:opacity-100 transition-opacity text-blue-400" />
          </span>
          <span className="text-[8.5px] text-white/40 shrink-0">{fmtNum(t.volume, 2)} lot &bull; {fmtDateShort(t.closed_at)}</span>
        </div>
        <span className={`inline-flex items-center gap-1 text-xs font-black tabular-nums ${profit >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
          <Icon icon={profit >= 0 ? "mdi:rocket-launch" : "game-icons:evil-hand"} width="14" height="14" className={profit >= 0 ? "text-emerald-400" : "text-rose-400"} />
          {fmtMoney(Math.abs(profit)).replace(/^[^0-9]+/, "")}
        </span>
      </div>
      
      {/* Badges Row */}
      {(t.agreed_strategies?.length || t.ai_used) ? (
        <div className="flex items-center gap-1 flex-wrap">
          {t.ai_used && (
            <div className="flex items-center gap-0.5 bg-purple-500/20 text-purple-400 border border-purple-500/30 px-1.5 py-0 rounded text-[8px] font-bold tracking-wider">
              <Bot size={8} /> AI
            </div>
          )}
          {t.agreed_strategies?.map((strat) => (
            <div key={strat} className="bg-white/10 text-white/70 border border-white/5 px-1.5 py-0 rounded text-[8px] font-bold tracking-wider uppercase">
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
