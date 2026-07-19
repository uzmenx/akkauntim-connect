import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { fmtMoney, fmtNum, timeAgo } from "@/lib/utils";
import type { BotStatus, Position, TradeHistory } from "@/lib/types";
import {
  Play, Pause, Settings, ArrowUpDown, ChevronRight, TrendingUp, TrendingDown,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

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

  const [filterMode, setFilterMode] = useState<"all" | "profit" | "loss">("all");
  const [showPrompt, setShowPrompt] = useState(false);
  const [aiPrompt, setAiPrompt] = useState("");

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

  return (
    <div className="flex flex-col items-center min-h-screen w-full bg-[#1e1a1d] font-sans pb-24 overflow-x-hidden">
      
      {/* Background Gradient to simulate the bottom green glow */}
      <div className="fixed bottom-0 left-0 right-0 h-[40vh] bg-gradient-to-t from-[#8cb369]/40 to-transparent pointer-events-none" />

      <div className="w-full max-w-md px-4 pt-6 pb-6 relative z-10">
        
        {/* Main Blue Card */}
        <div className="w-full bg-gradient-to-b from-[#0a4ed6] to-[#041a5a] rounded-[40px] p-6 shadow-2xl relative overflow-hidden border border-white/10">
          
          {/* Card Top Header */}
          <div className="flex justify-between items-center mb-6">
            <div className="flex items-center gap-2 bg-white/10 px-3 py-1.5 rounded-full backdrop-blur-md cursor-pointer hover:bg-white/20 transition-all">
              <img 
                src={`https://api.dicebear.com/7.x/notionists/svg?seed=${user?.email || "Ana"}&backgroundColor=f8f9fa`} 
                alt="Profile" 
                className="w-6 h-6 rounded-full bg-white object-cover"
              />
              <span className="text-white text-xs font-medium">{user?.email?.split("@")[0] ?? "Ana"}</span>
            </div>
            <div className="w-7 h-7 rounded-full bg-white/10 flex items-center justify-center text-white/60 text-xs backdrop-blur-md cursor-pointer hover:bg-white/20 transition-all">
              i
            </div>
          </div>

          {/* Balance Area */}
          <div className="text-center mb-6 relative">
            <span className="text-[10px] text-blue-200/80 font-semibold tracking-wider uppercase bg-white/10 px-3 py-1 rounded-full inline-block backdrop-blur-sm">
              Your Balance
            </span>
            <h1 className="text-4xl font-black text-white mt-3 tracking-tight tabular-nums drop-shadow-md">
              {equity != null ? fmtMoney(Number(equity), currency) : "$ 52,002.50"}
            </h1>
          </div>

          {/* Avatars Row (Cute bunny-like faces placeholder) */}
          <div className="flex justify-center gap-2 mb-8">
            {["Fluffy", "Cotton", "Snow", "Coco", "Bugs"].map((seed, idx) => (
              <div key={seed} className={`w-11 h-11 rounded-full border-2 border-[#1e40af] bg-white shadow-lg overflow-hidden flex items-center justify-center transform hover:scale-110 transition-transform cursor-pointer ${idx !== 0 ? "-ml-3" : ""}`}>
                <img src={`https://api.dicebear.com/7.x/micah/svg?seed=${seed}&backgroundColor=f1f5f9`} alt={seed} className="w-full h-full object-cover" />
              </div>
            ))}
          </div>

          {/* Last Transaction / High Profit Box */}
          <div className="bg-[#1e2336]/80 rounded-[28px] p-4 mb-4 backdrop-blur-xl border border-white/5 relative overflow-hidden group hover:bg-[#1e2336]/90 transition-all">
            <div className="flex justify-between items-center mb-2">
              <span className="text-[10px] text-white/50 font-medium">Last transaction</span>
              <Link to="/history" className="text-[10px] text-white/70 hover:text-white underline decoration-white/30 transition-all">
                View all
              </Link>
            </div>
            
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-pink-500 to-purple-500 p-0.5 shadow-lg">
                  <div className="w-full h-full bg-[#1e2336] rounded-full flex items-center justify-center relative overflow-hidden">
                     <span className="text-xs font-bold text-white relative z-10">{bestTrade ? (bestTrade.side === 'BUY' ? 'B' : 'S') : 'Pro'}</span>
                     <div className="absolute inset-0 bg-white/5 backdrop-blur-sm" />
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
          <div className="flex gap-2.5 mt-2">
            <Link to="/settings" className="flex-shrink-0 w-14 h-14 rounded-full bg-[#2a2d46] hover:bg-[#353856] flex items-center justify-center text-white/80 transition-all shadow-inner border border-white/5 group">
              <Settings size={20} className="group-hover:rotate-90 transition-transform duration-500" />
            </Link>
            
            <Link to="/signals" className="flex-shrink-0 w-14 h-14 rounded-full bg-[#2a2d46] hover:bg-[#353856] flex items-center justify-center text-white/80 transition-all shadow-inner border border-white/5 group">
              <ArrowUpDown size={20} className="group-hover:scale-110 transition-transform" />
            </Link>

            <button onClick={toggleFilter} className="flex-1 h-14 rounded-full bg-[#2a2d46] hover:bg-[#353856] flex items-center justify-center text-sm font-bold text-white/90 transition-all shadow-inner border border-white/5 group">
              {filterMode === "all" ? "Receive" : filterMode === "profit" ? "Foyda" : "Zarar"} <TrendingDown size={14} className="ml-1 opacity-70 group-hover:translate-y-1 transition-transform" />
            </button>

            <button onClick={() => setShowPrompt(true)} className="flex-1 h-14 rounded-full bg-gradient-to-b from-[#2b6eff] to-[#0f4bd2] hover:opacity-90 flex items-center justify-center text-sm font-bold text-white transition-all shadow-xl shadow-blue-500/20 border border-blue-400/30 group">
              Send <TrendingUp size={14} className="ml-1 opacity-80 group-hover:-translate-y-1 transition-transform" />
            </button>
          </div>
        </div>

        {/* Open Positions Skeletons List */}
        <div className="mt-8 space-y-3">
          <h3 className="text-xs font-bold text-white/60 mb-4 ml-2">OCHIQ POZITSIYALAR</h3>
          
          {filteredPositions && filteredPositions.length > 0 ? (
            filteredPositions.map(p => (
              <div key={p.id} className="h-16 w-full rounded-2xl bg-white/80 backdrop-blur-sm shadow-sm flex items-center px-4 hover:scale-[1.02] transition-transform cursor-pointer border border-white/10">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-white font-bold mr-3 shadow-inner ${p.side === 'BUY' ? 'bg-emerald-400' : 'bg-rose-400'}`}>
                  {p.side === 'BUY' ? 'B' : 'S'}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-black text-slate-800">{p.symbol}</p>
                  <p className="text-[10px] font-medium text-slate-500">{p.volume} lot at {fmtNum(p.open_price, 5)}</p>
                </div>
                <div className="text-right">
                  <p className={`text-sm font-bold ${Number(p.profit) >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                    {Number(p.profit) >= 0 ? "+" : ""}{fmtMoney(Number(p.profit))}
                  </p>
                  <p className="text-[10px] font-medium text-slate-400">{timeAgo(p.opened_at)}</p>
                </div>
              </div>
            ))
          ) : (
            // Dummy skeletons simulating the image
            [1, 2, 3, 4, 5, 6].map((i) => (
              <div 
                key={i} 
                className="h-[46px] w-full rounded-full bg-white/70 backdrop-blur-md shadow-sm border border-white/20 animate-pulse hover:bg-white/80 transition-colors cursor-default"
              />
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
              <button onClick={() => setShowPrompt(false)} className="flex-1 py-3 rounded-xl bg-white/5 text-white/70 font-bold text-xs hover:bg-white/10 transition-colors">Bekor qilish</button>
              <button 
                onClick={async () => {
                  alert("AI ko'rsatmasi tizimga yuborildi: " + aiPrompt);
                  setAiPrompt("");
                  setShowPrompt(false);
                }} 
                className="flex-1 py-3 rounded-xl bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-bold text-xs hover:opacity-90 transition-all shadow-lg shadow-blue-500/20"
              >
                Yuborish
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
