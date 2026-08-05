import { useState, useEffect } from "react";
import { FeatureCard } from "@/components/backtest/FeatureCard";
import { TestResultsCard, TestResultProps } from "@/components/backtest/TestResultsCard";
import { BacktestCompareModal } from "@/components/backtest/BacktestCompareModal";
import { Play, Activity, BarChart3, Clock, DollarSign, History, Cpu, Zap, Loader2, Timer, AlertCircle, Scale, ShieldCheck } from "lucide-react";
import pubgLoader from "@/assets/pubg-loader.svg";
import { supabase } from "@/integrations/supabase/client";

export function BacktestPage({ isEmbedded = false }: { isEmbedded?: boolean }) {
  const [activeTab, setActiveTab] = useState<"ai_siz" | "ai_bilan" | "history">("ai_siz");
  const [strategy, setStrategy] = useState("smc");
  const [timeframe, setTimeframe] = useState("1h");
  const [period, setPeriod] = useState("6m");
  const [symbol, setSymbol] = useState("EURUSD");
  const [spreadPips, setSpreadPips] = useState("1.5");
  const [slippagePips, setSlippagePips] = useState("0.8");
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<TestResultProps[]>([]);
  const [loading, setLoading] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(0);
  const [simulatedProgress, setSimulatedProgress] = useState(0);

  // Compare selection state
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
  const [isCompareModalOpen, setIsCompareModalOpen] = useState(false);

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
        period,
        strategy: activeTab === "ai_siz" ? strategy : null,
        mode: activeTab === "ai_bilan" ? "ai_bilan" : "ai_siz",
        spread_pips: parseFloat(spreadPips) || 1.5,
        slippage_pips: parseFloat(slippagePips) || 0.8,
        status: "pending"
      } as any);
      
      if (error) {
        console.error("Vazifa qo'shishda xatolik:", error);
        setRunning(false);
      }
      
    } catch (e) {
      console.error(e);
      setRunning(false);
    }
  };

  const handleToggleSelectForCompare = (id: string) => {
    setSelectedForCompare(prev => {
      if (prev.includes(id)) {
        return prev.filter(x => x !== id);
      }
      if (prev.length >= 2) {
        // Keep max 2
        return [prev[1], id];
      }
      return [...prev, id];
    });
  };

  const selectedTestA = results.find(r => r.id === selectedForCompare[0]);
  const selectedTestB = results.find(r => r.id === selectedForCompare[1]);

  return (
    <div className={`${isEmbedded ? "space-y-2.5" : "pb-12 pt-2 space-y-4"} animate-in fade-in duration-300`}>
      
      {/* Header Info */}
      {!isEmbedded && (
        <div className="px-3">
          <h2 className="text-sm font-black text-white drop-shadow-md mb-1">
            Institutional Test Markazi
          </h2>
          <p className="text-[10px] text-white/50 mb-2">
            Mexanik va AI voting engine tarixiy sinovlari, Walk-Forward validatsiya va Statistik Z-Test tahlili.
          </p>
        </div>
      )}

      {/* Tabs */}
      <div className={`${isEmbedded ? "" : "px-3"} flex gap-1`}>
        <button
          onClick={() => setActiveTab("ai_siz")}
          className={`flex-1 py-1.5 rounded-lg text-[10px] font-bold transition-all flex items-center justify-center gap-1.5 ${
            activeTab === "ai_siz" 
              ? "bg-blue-500 text-white shadow-md shadow-blue-500/20" 
              : "bg-[#1e293b] text-white/50 border border-white/5"
          }`}
        >
          <Zap className="w-3.5 h-3.5" />
          AI Siz
        </button>
        <button
          onClick={() => setActiveTab("ai_bilan")}
          className={`flex-1 py-1.5 rounded-lg text-[10px] font-bold transition-all flex items-center justify-center gap-1.5 ${
            activeTab === "ai_bilan" 
              ? "bg-purple-500 text-white shadow-md shadow-purple-500/20" 
              : "bg-[#1e293b] text-white/50 border border-white/5"
          }`}
        >
          <Cpu className="w-3.5 h-3.5" />
          AI Bilan
        </button>
        <button
          onClick={() => setActiveTab("history")}
          className={`flex-1 py-1.5 rounded-lg text-[10px] font-bold transition-all flex items-center justify-center gap-1.5 ${
            activeTab === "history" 
              ? "bg-amber-500 text-white shadow-md shadow-amber-500/20" 
              : "bg-[#1e293b] text-white/50 border border-white/5"
          }`}
        >
          <History className="w-3.5 h-3.5" />
          Tarix & Jurnal
        </button>
      </div>

      {/* Settings Panel for Tests */}
      {activeTab !== "history" && !running && (
        <div className={isEmbedded ? "space-y-3 animate-in slide-in-from-bottom-2" : "px-3 space-y-3 animate-in slide-in-from-bottom-2"}>
          <div className="bg-[#0f172a]/80 backdrop-blur-xl border border-white/15 p-3.5 rounded-xl shadow-xl space-y-3">
            <h3 className="text-xs font-bold text-white flex items-center gap-1.5">
              <Activity className={`w-4 h-4 ${activeTab === 'ai_bilan' ? 'text-purple-400' : 'text-blue-400'}`} />
              {activeTab === 'ai_bilan' ? 'AI Test Sozlamalari' : 'Mexanik Backtest Sozlamalari'}
            </h3>
            
            <div className="grid grid-cols-2 gap-2.5">
              <div className="space-y-0.5">
                <label className="text-[9px] font-bold text-white/40 uppercase pl-0.5">Valyuta Juftligi</label>
                <select 
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  className="w-full bg-[#1e293b]/50 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-brand/50 transition-colors appearance-none"
                >
                  <option value="EURUSD">EUR/USD</option>
                  <option value="GBPUSD">GBP/USD</option>
                  <option value="XAUUSD">XAU/USD (Gold)</option>
                </select>
              </div>

              <div className="space-y-0.5">
                <label className="text-[9px] font-bold text-white/40 uppercase pl-0.5">Vaqt Oralig'i (TF)</label>
                <select 
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value)}
                  className="w-full bg-[#1e293b]/50 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-brand/50 transition-colors appearance-none"
                >
                  <option value="15m">15 Minut (M15)</option>
                  <option value="1h">1 Soat (H1)</option>
                  <option value="4h">4 Soat (H4)</option>
                </select>
              </div>
            </div>

            {activeTab === "ai_siz" && (
              <div className="space-y-0.5">
                <label className="text-[9px] font-bold text-white/40 uppercase pl-0.5">Strategiya Rejimi</label>
                <select 
                  value={strategy}
                  onChange={(e) => setStrategy(e.target.value)}
                  className="w-full bg-[#1e293b]/50 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-brand/50 transition-colors appearance-none"
                >
                  <option value="voting">Barchasi (Voting Engine - SMC, Wyckoff, Harmonic)</option>
                  <option value="smc">Smart Money Concepts (SMC)</option>
                  <option value="harmonic">Garmonik Patternlar</option>
                  <option value="wyckoff">Wyckoff</option>
                </select>
              </div>
            )}

            <div className="space-y-0.5">
              <label className="text-[9px] font-bold text-white/40 uppercase pl-0.5">Test Davri</label>
              <select 
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                className="w-full bg-[#1e293b]/50 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-brand/50 transition-colors appearance-none"
              >
                <option value="1m">So'nggi 1 oy</option>
                <option value="3m">So'nggi 3 oy</option>
                <option value="6m">So'nggi 6 oy</option>
                <option value="1y">So'nggi 1 yil</option>
              </select>
            </div>

            {/* Realism Parameters: Spread & Slippage */}
            <div className="p-2.5 bg-[#1e293b]/30 rounded-lg border border-white/5 space-y-2">
              <span className="text-[10px] font-bold text-amber-400 uppercase tracking-wider flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5" />
                Realist Soddalashtirish (Bozor Shovqini & Narx Sirpanishi)
              </span>

              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-0.5">
                  <label className="text-[9px] text-white/50">Base Spread (Pips)</label>
                  <input 
                    type="number"
                    step="0.1"
                    value={spreadPips}
                    onChange={(e) => setSpreadPips(e.target.value)}
                    className="w-full bg-[#0f172a] border border-white/10 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-amber-400 font-mono"
                  />
                </div>
                
                <div className="space-y-0.5">
                  <label className="text-[9px] text-white/50">Base Slippage (Pips)</label>
                  <input 
                    type="number"
                    step="0.1"
                    value={slippagePips}
                    onChange={(e) => setSlippagePips(e.target.value)}
                    className="w-full bg-[#0f172a] border border-white/10 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-amber-400 font-mono"
                  />
                </div>
              </div>
            </div>

            <button 
              onClick={handleStart}
              disabled={running}
              className={`w-full flex items-center justify-center gap-1.5 py-2.5 rounded-lg font-bold text-xs transition-all active:scale-95 ${
                running 
                  ? "bg-[#1e293b] text-white/50 cursor-not-allowed" 
                  : activeTab === "ai_bilan"
                    ? "bg-purple-600 hover:bg-purple-500 text-white shadow-md shadow-purple-600/25 border border-white/10"
                    : "bg-blue-600 hover:bg-blue-500 text-white shadow-md shadow-blue-600/25 border border-white/10"
              }`}
            >
              {running ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Hisoblanmoqda...
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-white" />
                  {activeTab === "ai_bilan" ? "AI orqali Testni Boshlash" : "Mexanik Testni Boshlash"}
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Running Progress Panel */}
      {activeTab !== "history" && running && (
        <div className={isEmbedded ? "space-y-4 animate-in slide-in-from-bottom-2" : "px-4 space-y-4 animate-in slide-in-from-bottom-2"}>
          <div className="bg-[#0f172a]/90 backdrop-blur-xl border border-blue-500/30 p-6 rounded-2xl shadow-xl shadow-blue-500/10">
            <div className="flex flex-col items-center justify-center text-center space-y-4">
              <div className="relative w-20 h-20 flex items-center justify-center">
                <img src={pubgLoader} className="w-20 h-20 absolute opacity-80" alt="Loader" />
                <span className="text-xs font-bold text-white relative">{Math.floor(simulatedProgress)}%</span>
              </div>
              
              <div>
                <h3 className="text-lg font-bold text-white mb-1">
                  {activeTab === 'ai_bilan' ? 'AI Tahlil Qilmoqda...' : 'Mexanik Test Ishlamoqda...'}
                </h3>
                <p className="text-sm text-white/60">
                  Walk-Forward & Statistik Z-Test tahlillari bajarilmoqda. 1-2 daqiqa kuting.
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

      {/* History & Compare Journal Panel */}
      {activeTab === "history" && (
        <div className={isEmbedded ? "space-y-4 animate-in slide-in-from-bottom-2" : "px-4 space-y-4 animate-in slide-in-from-bottom-2"}>
          
          {/* Compare Toolbar */}
          <div className="flex items-center justify-between bg-[#0f172a]/80 border border-white/10 p-3 rounded-xl">
            <div className="flex items-center gap-2">
              <Scale className="w-4 h-4 text-amber-400" />
              <span className="text-xs font-bold text-white">Backtest Solishtirish Jurnali</span>
            </div>

            {selectedForCompare.length === 2 && (
              <button
                onClick={() => setIsCompareModalOpen(true)}
                className="px-3 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 font-black text-xs shadow-lg shadow-amber-500/20 flex items-center gap-1.5 transition-all animate-pulse"
              >
                <Scale className="w-3.5 h-3.5" />
                2 ta testni solishtirish
              </button>
            )}

            {selectedForCompare.length < 2 && (
              <span className="text-[11px] text-white/40">
                {selectedForCompare.length === 1 ? "1 ta tanlandi. Yana 1 tasini tanlang" : "Solishtirish uchun 2 ta testni tanlang (checkbox)"}
              </span>
            )}
          </div>

          {loading ? (
            <div className="flex justify-center py-10">
              <div className="w-6 h-6 border-2 border-brand/30 border-t-brand rounded-full animate-spin" />
            </div>
          ) : results.length > 0 ? (
            results.map((r, i) => (
              <TestResultsCard 
                key={r.id || i} 
                result={r} 
                previousResult={results[i + 1]}
                isSelected={selectedForCompare.includes(r.id)}
                onToggleSelect={handleToggleSelectForCompare}
              />
            ))
          ) : (
            <div className="bg-[#0f172a]/50 border border-white/5 rounded-2xl p-8 flex flex-col items-center justify-center text-center">
              <Clock className="w-10 h-10 text-white/20 mb-3" />
              <p className="text-white/50 text-sm">Hali hech qanday test o'tkazilmagan</p>
            </div>
          )}
        </div>
      )}

      {/* Side by side comparison modal */}
      {isCompareModalOpen && selectedTestA && selectedTestB && (
        <BacktestCompareModal 
          testA={selectedTestA}
          testB={selectedTestB}
          onClose={() => setIsCompareModalOpen(false)}
        />
      )}

    </div>
  );
}

