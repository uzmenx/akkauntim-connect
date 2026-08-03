import { useState } from "react";
import { Activity, DollarSign, Calendar, BarChart3, ChevronDown, ChevronUp, ArrowUpRight, ArrowDownRight, ShieldCheck, Scale, Zap, CheckCircle2 } from "lucide-react";

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

interface TestResultsCardProps {
  result: TestResultProps;
  previousResult?: TestResultProps;
  isSelected?: boolean;
  onToggleSelect?: (id: string) => void;
}

export function TestResultsCard({ result, previousResult, isSelected, onToggleSelect }: TestResultsCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<"summary" | "walkforward" | "contribution">("summary");

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

  // Deltas against previous run
  let winRateDelta: number | null = null;
  let profitDelta: number | null = null;
  if (previousResult) {
    winRateDelta = result.win_rate - previousResult.win_rate;
    profitDelta = result.total_profit - previousResult.total_profit;
  }

  // Extract key phrases from reasoning string if available
  const hasWalkForward = result.reasoning?.includes("WALK-FORWARD VALIDATSIYA HISOBOTI");
  const hasContribution = result.reasoning?.includes("KOMPONENTLAR HISSA HISOBOTI");
  
  // Quick metric extracts
  const wfeMatch = result.reasoning?.match(/WFE:\s*([\d.]+)/);
  const wfeVal = wfeMatch ? parseFloat(wfeMatch[1]) : null;

  const pValMatch = result.reasoning?.match(/p-value\s*=\s*([\d.]+)/);
  const pVal = pValMatch ? parseFloat(pValMatch[1]) : null;
  const isStatSig = pVal !== null ? pVal < 0.05 : null;

  const spreadMatch = result.reasoning?.match(/Spread:\s*([\d.]+)p/);
  const spreadPips = spreadMatch ? spreadMatch[1] : null;

  return (
    <div className={`bg-[#0f172a]/90 backdrop-blur-xl border ${isSelected ? 'border-brand ring-2 ring-brand/30' : 'border-white/10'} p-4.5 rounded-2xl shadow-xl flex flex-col gap-3.5 transition-all duration-200`}>
      
      {/* Top Bar: Selection Checkbox + Type Badge + Date */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          {onToggleSelect && (
            <input 
              type="checkbox"
              checked={isSelected || false}
              onChange={() => onToggleSelect(result.id)}
              className="w-4 h-4 rounded border-white/20 bg-slate-800 text-brand focus:ring-brand/40 cursor-pointer"
              title="Solishtirish uchun tanlash"
            />
          )}
          <div className={`px-2.5 py-0.5 rounded-lg border text-[11px] font-bold ${typeColors[result.type]}`}>
            {typeLabels[result.type]}
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-white/50 text-xs font-medium">
          <Calendar className="w-3.5 h-3.5" />
          {new Date(result.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
        </div>
      </div>

      {/* Main Stats with Delta Indicators */}
      <div className="grid grid-cols-2 gap-3">
        {/* Profit Card */}
        <div className="bg-[#1e293b]/60 rounded-xl p-3 flex flex-col items-center justify-center border border-white/5 relative">
          {profitDelta !== null && (
            <div className={`absolute top-2 right-2 flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded ${
              profitDelta > 0 ? 'bg-emerald-500/20 text-emerald-400' : profitDelta < 0 ? 'bg-red-500/20 text-red-400' : 'bg-slate-700 text-white/60'
            }`}>
              {profitDelta > 0 ? <ArrowUpRight className="w-3 h-3" /> : profitDelta < 0 ? <ArrowDownRight className="w-3 h-3 text-red-400" /> : null}
              {profitDelta > 0 ? `+$${profitDelta.toFixed(0)}` : profitDelta < 0 ? `-$${Math.abs(profitDelta).toFixed(0)}` : '='}
            </div>
          )}
          
          <DollarSign className={`w-5 h-5 mb-1 ${isProfit ? 'text-emerald-400' : 'text-red-400'}`} />
          <span className={`text-lg font-black ${isProfit ? 'text-emerald-400' : 'text-red-400'}`}>
            {isProfit ? '+' : ''}{result.total_profit.toFixed(2)} USD
          </span>
          <span className="text-[10px] uppercase font-bold tracking-wider text-white/40 mt-0.5">Umumiy Foyda</span>
        </div>
        
        {/* Win Rate Card */}
        <div className="bg-[#1e293b]/60 rounded-xl p-3 flex flex-col items-center justify-center border border-white/5 relative">
          {winRateDelta !== null && (
            <div className={`absolute top-2 right-2 flex items-center text-[10px] font-bold px-1.5 py-0.5 rounded ${
              winRateDelta > 0 ? 'bg-emerald-500/20 text-emerald-400' : winRateDelta < 0 ? 'bg-red-500/20 text-red-400' : 'bg-slate-700 text-white/60'
            }`}>
              {winRateDelta > 0 ? <ArrowUpRight className="w-3 h-3" /> : winRateDelta < 0 ? <ArrowDownRight className="w-3 h-3 text-red-400" /> : null}
              {winRateDelta > 0 ? `+${winRateDelta.toFixed(1)}%` : winRateDelta < 0 ? `${winRateDelta.toFixed(1)}%` : '='}
            </div>
          )}

          <Activity className="w-5 h-5 mb-1 text-blue-400" />
          <span className="text-lg font-black text-white">
            {result.win_rate.toFixed(1)}%
          </span>
          <span className="text-[10px] uppercase font-bold tracking-wider text-white/40 mt-0.5">Win Rate</span>
        </div>
      </div>

      {/* Symbol, TF & Realism Metrics */}
      <div className="flex items-center justify-between text-xs px-1 py-1 border-t border-b border-white/5 text-white/70">
        <div className="flex items-center gap-2 font-semibold text-white">
          <BarChart3 className="w-4 h-4 text-brand" />
          <span>{result.symbol} ({result.timeframe})</span>
        </div>
        
        <div className="flex items-center gap-2 text-[11px] text-white/60">
          {spreadPips && (
            <span className="bg-white/5 px-2 py-0.5 rounded text-amber-300 font-mono" title="Dinamik Spread & Slippage active">
              Spread: {spreadPips}p
            </span>
          )}
          <span><strong className="text-white">{result.total_trades}</strong> bitim</span>
        </div>
      </div>

      {/* Advanced Badges (WFE & StatSig) */}
      {(wfeVal !== null || isStatSig !== null) && (
        <div className="flex items-center gap-2 flex-wrap">
          {wfeVal !== null && (
            <div className={`text-[10px] font-bold px-2 py-0.5 rounded-lg border flex items-center gap-1 ${
              wfeVal >= 0.7 ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : wfeVal >= 0.5 ? 'bg-amber-500/10 border-amber-500/30 text-amber-400' : 'bg-red-500/10 border-red-500/30 text-red-400'
            }`}>
              <ShieldCheck className="w-3 h-3" />
              WFE: {wfeVal} ({wfeVal >= 0.7 ? "Mukammal" : wfeVal >= 0.5 ? "Oltin O'rta" : "Overfitted"})
            </div>
          )}

          {isStatSig !== null && (
            <div className={`text-[10px] font-bold px-2 py-0.5 rounded-lg border flex items-center gap-1 ${
              isStatSig ? 'bg-purple-500/10 border-purple-500/30 text-purple-300' : 'bg-slate-800 border-white/10 text-white/60'
            }`}>
              <Zap className="w-3 h-3 text-purple-400" />
              {isStatSig ? "Statistik Ishonchli (p<0.05)" : "Tasodifiy bo'lishi mumkin"}
            </div>
          )}
        </div>
      )}

      {/* Expandable Report Accordion */}
      {result.reasoning && (
        <div className="mt-1 border border-white/10 rounded-xl overflow-hidden bg-[#1e293b]/30">
          
          <button 
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full px-3 py-2 flex items-center justify-between text-xs font-bold text-white/80 hover:text-white bg-white/5 hover:bg-white/10 transition-colors"
          >
            <span className="flex items-center gap-1.5">
              <Scale className="w-3.5 h-3.5 text-brand" />
              Tahlil Hisoboti & Metrikalar
            </span>
            {isExpanded ? <ChevronUp className="w-4 h-4 text-white/50" /> : <ChevronDown className="w-4 h-4 text-white/50" />}
          </button>

          {isExpanded && (
            <div className="p-3 space-y-2 border-t border-white/10 bg-[#0f172a]/90">
              {/* Tab Selector */}
              <div className="flex items-center gap-1 border-b border-white/10 pb-2 text-[11px]">
                <button 
                  onClick={() => setActiveTab("summary")}
                  className={`px-2.5 py-1 rounded-md font-bold transition-colors ${activeTab === 'summary' ? 'bg-brand text-black' : 'text-white/60 hover:text-white'}`}
                >
                  Xulosa
                </button>
                {hasWalkForward && (
                  <button 
                    onClick={() => setActiveTab("walkforward")}
                    className={`px-2.5 py-1 rounded-md font-bold transition-colors ${activeTab === 'walkforward' ? 'bg-brand text-black' : 'text-white/60 hover:text-white'}`}
                  >
                    Walk-Forward
                  </button>
                )}
                {hasContribution && (
                  <button 
                    onClick={() => setActiveTab("contribution")}
                    className={`px-2.5 py-1 rounded-md font-bold transition-colors ${activeTab === 'contribution' ? 'bg-brand text-black' : 'text-white/60 hover:text-white'}`}
                  >
                    Hissalar
                  </button>
                )}
              </div>

              {/* Tab Content */}
              <div className="font-mono text-[11px] text-white/80 whitespace-pre-wrap leading-relaxed max-h-52 overflow-y-auto p-2 bg-[#1e293b]/50 rounded-lg border border-white/5">
                {activeTab === "summary" && result.reasoning}
                {activeTab === "walkforward" && (
                  result.reasoning.split("WALK-FORWARD VALIDATSIYA HISOBOTI")[1] 
                    ? `WALK-FORWARD VALIDATSIYA HISOBOTI${result.reasoning.split("WALK-FORWARD VALIDATSIYA HISOBOTI")[1]}` 
                    : result.reasoning
                )}
                {activeTab === "contribution" && (
                  result.reasoning.split("KOMPONENTLAR HISSA HISOBOTI")[1]
                    ? `KOMPONENTLAR HISSA HISOBOTI${result.reasoning.split("KOMPONENTLAR HISSA HISOBOTI")[1].split("WALK-FORWARD")[0]}`
                    : result.reasoning
                )}
              </div>
            </div>
          )}

        </div>
      )}

    </div>
  );
}

