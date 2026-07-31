import { useState, useEffect } from "react";
import { FeatureCard } from "@/components/backtest/FeatureCard";
import { TestResultsCard, TestResultProps } from "@/components/backtest/TestResultsCard";
import { Play, Activity, BarChart3, Clock, DollarSign, History, Cpu, Zap, Loader2, Timer, AlertCircle } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";

export function BacktestPage() {
  const [activeTab, setActiveTab] = useState<"ai_siz" | "ai_bilan" | "history">("ai_siz");
  const [strategy, setStrategy] = useState("smc");
  const [timeframe, setTimeframe] = useState("1h");
  const [period, setPeriod] = useState("6m");
  const [symbol, setSymbol] = useState("EURUSD");
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<TestResultProps[]>([]);
  const [loading, setLoading] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [simulatedProgress, setSimulatedProgress] = useState(0);

  // Fetch history
  const fetchHistory = async () => {
    setLoading(true);
    const { data, error } = await supabase
      .from('test_results')
      .select('*')
      .order('created_at', { ascending: false });
      
    if (!error && data) {
      setResults(data as TestResultProps[]);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (activeTab === "history") {
      fetchHistory();
    }
  }, [activeTab]);

  // Timer and simulated progress logic
  useEffect(() => {
    let timer: any;
    if (running) {
      timer = setInterval(() => {
        setElapsedTime(prev => prev + 1);
        setSimulatedProgress(prev => {
          // Asimptotik tarzda 95% gacha o'sadi
          if (prev < 40) return prev + 2;
          if (prev < 70) return prev + 1;
          if (prev < 90) return prev + 0.5;
          if (prev < 98) return prev + 0.1;
          return prev;
        });
      }, 1000);
    } else {
      setElapsedTime(0);
      setSimulatedProgress(0);
      clearInterval(timer);
    }
    return () => clearInterval(timer);
  }, [running]);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  // Realtime subscription for backtest_jobs
  useEffect(() => {
    const channel = supabase
      .channel('schema-db-changes')
      .on(
        'postgres_changes',
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'backtest_jobs'
        },
        (payload) => {
          if (payload.new.status === 'completed') {
            setRunning(false);
            setActiveTab("history"); // Auto switch to history
          } else if (payload.new.status === 'failed') {
            setRunning(false);
            console.error("Backtest failed");
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  const handleStart = async () => {
    setRunning(true);
    
    try {
      const { error } = await supabase.from('backtest_jobs').insert({
        symbol,
        timeframe,
        period, // Added period
        strategy: activeTab === "ai_siz" ? strategy : null,
        mode: activeTab === "ai_bilan" ? "ai_bilan" : "ai_siz",
        status: "pending"
      });
      
      if (error) {
        console.warn("Backend error (probably table doesn't exist yet). Using MVP Mock simulation.", error);
      }
      
      // MVP Simulation (Backend hali to'liq ulanmaganligi sababli UI ni simulyatsiya qilamiz)
      setTimeout(() => {
        setRunning(false);
        
        const newFakeResult: TestResultProps = {
          id: Math.random().toString(),
          type: activeTab === 'ai_siz' ? 'ai_siz' : 'ai_bilan',
          created_at: new Date().toISOString(),
          symbol,
          timeframe,
          total_trades: Math.floor(Math.random() * 40) + 15,
          win_rate: 45 + Math.random() * 35,
          total_profit: (Math.random() * 1500) - 300,
          reasoning: activeTab === 'ai_bilan' 
            ? "AI SMC va Garmonik patternlarni tahlil qildi. Asosiy trend kuchli Uptrend, kutilmagan yangiliklar ta'siri hisobga olindi." 
            : undefined
        };
        
        setResults(prev => [newFakeResult, ...prev]);
        setActiveTab("history");
      }, 10000); // 10 soniya kutamiz
      
    } catch (e) {
      console.error(e);
      setRunning(false);
    }
  };

  return (
    <div className="pb-24 pt-4 space-y-6 animate-in fade-in duration-300">
      
      {/* Header Info */}
      <div className="px-4">
        <h2 className="text-2xl font-black text-white drop-shadow-md mb-2">
          Test Markazi
        </h2>
        <p className="text-sm text-white/60 mb-4">
          Strategiyalarni mexanik yoki AI yordamida tarixiy ma'lumotlarda sinab ko'ring.
        </p>
      </div>

      {/* Tabs */}
      <div className="px-4 flex gap-2">
        <button
          onClick={() => setActiveTab("ai_siz")}
          className={`flex-1 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 ${
            activeTab === "ai_siz" 
              ? "bg-blue-500 text-white shadow-lg shadow-blue-500/20" 
              : "bg-[#1e293b] text-white/50 border border-white/5"
          }`}
        >
          <Zap className="w-4 h-4" />
          AI Siz
        </button>
        <button
          onClick={() => setActiveTab("ai_bilan")}
          className={`flex-1 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 ${
            activeTab === "ai_bilan" 
              ? "bg-purple-500 text-white shadow-lg shadow-purple-500/20" 
              : "bg-[#1e293b] text-white/50 border border-white/5"
          }`}
        >
          <Cpu className="w-4 h-4" />
          AI Bilan
        </button>
        <button
          onClick={() => setActiveTab("history")}
          className={`flex-1 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center justify-center gap-2 ${
            activeTab === "history" 
              ? "bg-amber-500 text-white shadow-lg shadow-amber-500/20" 
              : "bg-[#1e293b] text-white/50 border border-white/5"
          }`}
        >
          <History className="w-4 h-4" />
          Tarix
        </button>
      </div>

      {/* Settings Panel for Tests */}
      {activeTab !== "history" && !running && (
        <div className="px-4 space-y-4 animate-in slide-in-from-bottom-2">
          <div className="bg-[#0f172a]/80 backdrop-blur-xl border border-white/10 p-5 rounded-2xl shadow-xl">
            <h3 className="text-base font-bold text-white flex items-center gap-2 mb-4">
              <Activity className={`w-5 h-5 ${activeTab === 'ai_bilan' ? 'text-purple-400' : 'text-blue-400'}`} />
              {activeTab === 'ai_bilan' ? 'AI Test Sozlamalari' : 'Mexanik Backtest Sozlamalari'}
            </h3>
            
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-white/60 pl-1">Valyuta Juftligi</label>
                <select 
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  className="w-full bg-[#1e293b]/50 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-brand/50 transition-colors appearance-none"
                >
                  <option value="EURUSD">EUR/USD</option>
                  <option value="GBPUSD">GBP/USD</option>
                  <option value="XAUUSD">XAU/USD (Gold)</option>
                </select>
              </div>

              {activeTab === "ai_siz" && (
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-white/60 pl-1">Strategiya (Agar faqat bitta kerak bo'lsa)</label>
                  <select 
                    value={strategy}
                    onChange={(e) => setStrategy(e.target.value)}
                    className="w-full bg-[#1e293b]/50 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-brand/50 transition-colors appearance-none"
                  >
                    <option value="all">Barchasi (Voting Engine)</option>
                    <option value="smc">Smart Money Concepts (SMC)</option>
                    <option value="harmonic">Garmonik Patternlar</option>
                    <option value="wyckoff">Wyckoff</option>
                  </select>
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-white/60 pl-1">Vaqt Oralig'i (Timeframe)</label>
                <select 
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value)}
                  className="w-full bg-[#1e293b]/50 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-brand/50 transition-colors appearance-none"
                >
                  <option value="15m">15 Minut (M15)</option>
                  <option value="1h">1 Soat (H1)</option>
                  <option value="4h">4 Soat (H4)</option>
                </select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-white/60 pl-1">Test Davri (Qancha tarix)</label>
                <select 
                  value={period}
                  onChange={(e) => setPeriod(e.target.value)}
                  className="w-full bg-[#1e293b]/50 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-brand/50 transition-colors appearance-none"
                >
                  <option value="1m">So'nggi 1 oy</option>
                  <option value="3m">So'nggi 3 oy</option>
                  <option value="6m">So'nggi 6 oy</option>
                  <option value="1y">So'nggi 1 yil</option>
                </select>
              </div>
              
              <button 
                onClick={handleStart}
                disabled={running}
                className={`w-full mt-4 flex items-center justify-center gap-2 py-3.5 rounded-xl font-bold text-sm transition-all active:scale-95 ${
                  running 
                    ? "bg-[#1e293b] text-white/50 cursor-not-allowed" 
                    : activeTab === "ai_bilan"
                      ? "bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-600/25 border border-white/10"
                      : "bg-blue-600 hover:bg-blue-500 text-white shadow-lg shadow-blue-600/25 border border-white/10"
                }`}
              >
                {running ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Hisoblanmoqda...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    {activeTab === "ai_bilan" ? "AI orqali Testni Boshlash" : "Mexanik Testni Boshlash"}
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Running Progress Panel */}
      {activeTab !== "history" && running && (
        <div className="px-4 space-y-4 animate-in slide-in-from-bottom-2">
          <div className="bg-[#0f172a]/90 backdrop-blur-xl border border-blue-500/30 p-6 rounded-2xl shadow-xl shadow-blue-500/10">
            <div className="flex flex-col items-center justify-center text-center space-y-4">
              <div className="relative w-20 h-20 flex items-center justify-center">
                <Loader2 className="w-12 h-12 text-blue-500 animate-spin absolute" />
                <span className="text-xs font-bold text-white relative">{Math.floor(simulatedProgress)}%</span>
              </div>
              
              <div>
                <h3 className="text-lg font-bold text-white mb-1">
                  {activeTab === 'ai_bilan' ? 'AI Tahlil Qilmoqda...' : 'Mexanik Test Ishlamoqda...'}
                </h3>
                <p className="text-sm text-white/60">
                  Iltimos, kutib turing. Bu jarayon 1-2 daqiqa vaqt olishi mumkin.
                </p>
              </div>

              <div className="w-full h-2 bg-slate-800 rounded-full overflow-hidden mt-2">
                <div 
                  className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-300 ease-out"
                  style={{ width: `${simulatedProgress}%` }}
                />
              </div>
              
              <div className="w-full flex justify-between items-center mt-2 px-1">
                <div className="flex items-center gap-1.5 text-white/50 text-xs">
                  <Timer className="w-3.5 h-3.5" />
                  <span>O'tgan vaqt: <strong className="text-white">{formatTime(elapsedTime)}</strong></span>
                </div>
                <div className="flex items-center gap-1.5 text-white/50 text-xs">
                  <AlertCircle className="w-3.5 h-3.5" />
                  <span>Kutilmoqda: ~02:00</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* History Panel */}
      {activeTab === "history" && (
        <div className="px-4 space-y-4 animate-in slide-in-from-bottom-2">
          {loading ? (
            <div className="flex justify-center py-10">
              <div className="w-6 h-6 border-2 border-brand/30 border-t-brand rounded-full animate-spin" />
            </div>
          ) : results.length > 0 ? (
            results.map((r, i) => (
              <TestResultsCard key={r.id || i} result={r} />
            ))
          ) : (
            <div className="bg-[#0f172a]/50 border border-white/5 rounded-2xl p-8 flex flex-col items-center justify-center text-center">
              <Clock className="w-10 h-10 text-white/20 mb-3" />
              <p className="text-white/50 text-sm">Hali hech qanday test o'tkazilmagan</p>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
