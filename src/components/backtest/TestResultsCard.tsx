import { Activity, DollarSign, Calendar, BarChart3, Clock, AlertTriangle } from "lucide-react";

export interface TestResultProps {
  id: string;
  type: "ai_bilan" | "ai_siz" | "backtest_history";
  created_at: string;
  symbol: string;
  timeframe: string;
  total_trades: number;
  win_rate: number;
  total_profit: number;
  reasoning?: string;
}

export function TestResultsCard({ result }: { result: TestResultProps }) {
  const isProfit = result.total_profit >= 0;
  
  const typeLabels = {
    ai_bilan: "AI Bilan (Live Test)",
    ai_siz: "AI Siz (Mexanik)",
    backtest_history: "Tarixiy Backtest"
  };

  const typeColors = {
    ai_bilan: "text-purple-400 bg-purple-500/10 border-purple-500/20",
    ai_siz: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    backtest_history: "text-amber-400 bg-amber-500/10 border-amber-500/20"
  };

  return (
    <div className="bg-[#0f172a]/80 backdrop-blur-xl border border-white/10 p-4 rounded-2xl shadow-xl flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className={`px-2.5 py-1 rounded-lg border text-xs font-bold ${typeColors[result.type]}`}>
          {typeLabels[result.type]}
        </div>
        <div className="flex items-center gap-1.5 text-white/50 text-xs font-medium">
          <Calendar className="w-3.5 h-3.5" />
          {new Date(result.created_at).toLocaleDateString()}
        </div>
      </div>

      {/* Main Stats */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-[#1e293b]/50 rounded-xl p-3 flex flex-col items-center justify-center border border-white/5">
          <DollarSign className={`w-5 h-5 mb-1 ${isProfit ? 'text-emerald-400' : 'text-red-400'}`} />
          <span className={`text-lg font-black ${isProfit ? 'text-emerald-400' : 'text-red-400'}`}>
            {isProfit ? '+' : ''}{result.total_profit.toFixed(2)} USD
          </span>
          <span className="text-[10px] uppercase font-bold tracking-wider text-white/40 mt-0.5">Umumiy Foyda</span>
        </div>
        
        <div className="bg-[#1e293b]/50 rounded-xl p-3 flex flex-col items-center justify-center border border-white/5">
          <Activity className="w-5 h-5 mb-1 text-blue-400" />
          <span className="text-lg font-black text-white">
            {result.win_rate.toFixed(1)}%
          </span>
          <span className="text-[10px] uppercase font-bold tracking-wider text-white/40 mt-0.5">Win Rate</span>
        </div>
      </div>

      {/* Details */}
      <div className="flex items-center justify-between text-sm px-1">
        <div className="flex items-center gap-2 text-white/80 font-medium">
          <BarChart3 className="w-4 h-4 text-brand" />
          <span>{result.symbol} ({result.timeframe})</span>
        </div>
        <div className="flex items-center gap-1.5 text-white/60 text-xs">
          <span className="font-bold text-white">{result.total_trades}</span> bitimlar
        </div>
      </div>
      
      {/* AI Reasoning if exists */}
      {result.reasoning && (
        <div className="mt-1 bg-brand/10 border border-brand/20 p-3 rounded-xl flex gap-3 items-start">
          <AlertTriangle className="w-4 h-4 text-brand shrink-0 mt-0.5" />
          <p className="text-xs text-white/80 leading-relaxed font-medium">
            {result.reasoning}
          </p>
        </div>
      )}
    </div>
  );
}
