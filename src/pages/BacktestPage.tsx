import { useState } from "react";
import { FeatureCard } from "@/components/backtest/FeatureCard";
import { Play, Activity, BarChart3, Clock, DollarSign } from "lucide-react";

export function BacktestPage() {
  const [strategy, setStrategy] = useState("smc");
  const [timeframe, setTimeframe] = useState("1h");
  const [running, setRunning] = useState(false);

  const handleStart = () => {
    setRunning(true);
    // Simulate backtest running
    setTimeout(() => {
      setRunning(false);
    }, 2000);
  };

  return (
    <div className="pb-24 pt-4 space-y-6 animate-in fade-in duration-300">
      
      {/* Header Info */}
      <div className="px-2">
        <h2 className="text-2xl font-black text-white drop-shadow-md mb-2">
          Backtest
        </h2>
        <p className="text-sm text-white/60 mb-4">
          O'zingizning strategiyalaringizni tarixiy ma'lumotlarda sinab ko'ring va ularning samarasini tekshiring.
        </p>
        
        {/* The Feature Card requested by user */}
        <FeatureCard />
      </div>

      {/* Settings Panel */}
      <div className="px-2 space-y-4">
        <div className="bg-[#0f172a]/80 backdrop-blur-xl border border-white/10 p-5 rounded-2xl shadow-xl">
          <h3 className="text-lg font-bold text-white flex items-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-brand" />
            Sozlamalar
          </h3>
          
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-white/60 pl-1">Strategiya</label>
              <select 
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
                className="w-full bg-[#1e293b]/50 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-brand/50 transition-colors"
              >
                <option value="smc">Smart Money Concepts (SMC)</option>
                <option value="harmonic">Garmonik Patternlar</option>
                <option value="news">Yangiliklar Strategiyasi</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-white/60 pl-1">Vaqt Oralig'i (Timeframe)</label>
              <select 
                value={timeframe}
                onChange={(e) => setTimeframe(e.target.value)}
                className="w-full bg-[#1e293b]/50 border border-white/10 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:border-brand/50 transition-colors"
              >
                <option value="15m">15 Minut (M15)</option>
                <option value="1h">1 Soat (H1)</option>
                <option value="4h">4 Soat (H4)</option>
              </select>
            </div>
            
            <button 
              onClick={handleStart}
              disabled={running}
              className={`w-full mt-2 flex items-center justify-center gap-2 py-3.5 rounded-xl font-bold text-sm transition-all active:scale-95 ${
                running 
                  ? "bg-brand/50 text-white cursor-not-allowed" 
                  : "bg-brand text-white hover:bg-brand/90 shadow-lg shadow-brand/25 border border-white/10"
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
                  Testni Boshlash
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Results (Stub for now) */}
      <div className="px-2">
        <h3 className="text-lg font-bold text-white mb-3 pl-1 flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-green-400" />
          Natijalar
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-[#0f172a]/80 backdrop-blur-md border border-white/10 p-4 rounded-2xl flex flex-col items-center justify-center text-center">
            <DollarSign className="w-6 h-6 text-green-400 mb-2 opacity-80" />
            <span className="text-2xl font-black text-white">---</span>
            <span className="text-xs font-medium text-white/50 mt-1">Umumiy Foyda</span>
          </div>
          <div className="bg-[#0f172a]/80 backdrop-blur-md border border-white/10 p-4 rounded-2xl flex flex-col items-center justify-center text-center">
            <Activity className="w-6 h-6 text-amber-400 mb-2 opacity-80" />
            <span className="text-2xl font-black text-white">---%</span>
            <span className="text-xs font-medium text-white/50 mt-1">Win Rate</span>
          </div>
        </div>
      </div>
    </div>
  );
}
