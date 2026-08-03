import { X, ArrowUpRight, ArrowDownRight, Minus, TrendingUp, CheckCircle2, AlertTriangle, ShieldCheck, Scale } from "lucide-react";
import { TestResultProps } from "./TestResultsCard";

interface BacktestCompareModalProps {
  testA: TestResultProps;
  testB: TestResultProps;
  onClose: () => void;
}

export function BacktestCompareModal({ testA, testB, onClose }: BacktestCompareModalProps) {
  // Determine baseline (older) vs candidate (newer)
  const dateA = new Date(testA.created_at).getTime();
  const dateB = new Date(testB.created_at).getTime();
  const baseline = dateA <= dateB ? testA : testB;
  const candidate = dateA <= dateB ? testB : testA;

  const winRateDiff = candidate.win_rate - baseline.win_rate;
  const profitDiff = candidate.total_profit - baseline.total_profit;
  const tradesDiff = candidate.total_trades - baseline.total_trades;

  const isImproved = profitDiff > 0 || (profitDiff === 0 && winRateDiff > 0);
  const isDegraded = profitDiff < 0 || (profitDiff === 0 && winRateDiff < 0);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-200">
      <div className="bg-[#0f172a] border border-white/15 w-full max-w-3xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-[#1e293b]/50">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Backtest Natijalarini Solishtirish</h3>
              <p className="text-xs text-white/50">Eski versiya (Baseline) va Yangi versiya (Candidate) taqqoslanishi</p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/60 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-6 overflow-y-auto space-y-6">
          
          {/* Comparison Status Verdict Banner */}
          <div className={`p-4 rounded-xl border flex items-center gap-3.5 ${
            isImproved 
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' 
              : isDegraded 
                ? 'bg-red-500/10 border-red-500/30 text-red-400' 
                : 'bg-slate-800 border-white/10 text-white/70'
          }`}>
            {isImproved && <CheckCircle2 className="w-6 h-6 shrink-0 text-emerald-400" />}
            {isDegraded && <AlertTriangle className="w-6 h-6 shrink-0 text-red-400" />}
            {!isImproved && !isDegraded && <Minus className="w-6 h-6 shrink-0 text-white/50" />}
            
            <div>
              <h4 className="text-sm font-bold">
                {isImproved ? "Yaxshilanish aniqlandi (Ijobiy o'zgarish ▲)" : isDegraded ? "Samaradorlik pasaydi (Salbiy o'zgarish ▼)" : "Natijalar teng (O'zgarishsiz =)"}
              </h4>
              <p className="text-xs opacity-80 mt-0.5">
                Yangi test natijasida foyda <strong>{profitDiff >= 0 ? `+$${profitDiff.toFixed(2)}` : `-$${Math.abs(profitDiff).toFixed(2)}`}</strong> va Win Rate <strong>{winRateDiff >= 0 ? `+${winRateDiff.toFixed(1)}%` : `${winRateDiff.toFixed(1)}%`}</strong> farq qildi.
              </p>
            </div>
          </div>

          {/* Grid Side by Side Comparison */}
          <div className="grid grid-cols-2 gap-4">
            
            {/* Baseline Test Card */}
            <div className="bg-[#1e293b]/40 border border-white/10 rounded-xl p-4 space-y-3">
              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <span className="text-xs font-bold text-white/50 uppercase tracking-wider">A (Oldingi Test)</span>
                <span className="text-[10px] text-white/40">{new Date(baseline.created_at).toLocaleString()}</span>
              </div>
              
              <div className="space-y-2">
                <div>
                  <span className="text-[10px] text-white/40 uppercase font-bold">Juftlik & TF</span>
                  <p className="text-sm font-bold text-white">{baseline.symbol} ({baseline.timeframe})</p>
                </div>

                <div>
                  <span className="text-[10px] text-white/40 uppercase font-bold">Jami Foyda</span>
                  <p className={`text-base font-black ${baseline.total_profit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {baseline.total_profit >= 0 ? '+' : ''}{baseline.total_profit.toFixed(2)} USD
                  </p>
                </div>

                <div>
                  <span className="text-[10px] text-white/40 uppercase font-bold">Win Rate</span>
                  <p className="text-sm font-bold text-white">{baseline.win_rate.toFixed(1)}%</p>
                </div>

                <div>
                  <span className="text-[10px] text-white/40 uppercase font-bold">Bitimlar Soni</span>
                  <p className="text-sm font-medium text-white/80">{baseline.total_trades} ta</p>
                </div>

                <div>
                  <span className="text-[10px] text-white/40 uppercase font-bold">Rejim</span>
                  <p className="text-xs font-semibold text-amber-400 capitalize">{baseline.type.replace('_', ' ')}</p>
                </div>
              </div>
            </div>

            {/* Candidate Test Card */}
            <div className="bg-[#1e293b]/70 border border-brand/30 rounded-xl p-4 space-y-3 relative shadow-lg shadow-brand/5">
              <div className="flex items-center justify-between border-b border-white/10 pb-2">
                <span className="text-xs font-bold text-brand uppercase tracking-wider">B (Yangi Test)</span>
                <span className="text-[10px] text-white/40">{new Date(candidate.created_at).toLocaleString()}</span>
              </div>

              <div className="space-y-2">
                <div>
                  <span className="text-[10px] text-white/40 uppercase font-bold">Juftlik & TF</span>
                  <p className="text-sm font-bold text-white">{candidate.symbol} ({candidate.timeframe})</p>
                </div>

                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-white/40 uppercase font-bold">Jami Foyda</span>
                    <span className={`text-[11px] font-bold flex items-center gap-0.5 ${profitDiff >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {profitDiff >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                      {profitDiff >= 0 ? `+$${profitDiff.toFixed(2)}` : `-$${Math.abs(profitDiff).toFixed(2)}`}
                    </span>
                  </div>
                  <p className={`text-base font-black ${candidate.total_profit >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {candidate.total_profit >= 0 ? '+' : ''}{candidate.total_profit.toFixed(2)} USD
                  </p>
                </div>

                <div>
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-white/40 uppercase font-bold">Win Rate</span>
                    <span className={`text-[11px] font-bold flex items-center gap-0.5 ${winRateDiff >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                      {winRateDiff >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                      {winRateDiff >= 0 ? `+${winRateDiff.toFixed(1)}%` : `${winRateDiff.toFixed(1)}%`}
                    </span>
                  </div>
                  <p className="text-sm font-bold text-white">{candidate.win_rate.toFixed(1)}%</p>
                </div>

                <div>
                  <span className="text-[10px] text-white/40 uppercase font-bold">Bitimlar Soni</span>
                  <p className="text-sm font-medium text-white/80">{candidate.total_trades} ta ({tradesDiff >= 0 ? `+${tradesDiff}` : tradesDiff})</p>
                </div>

                <div>
                  <span className="text-[10px] text-white/40 uppercase font-bold">Rejim</span>
                  <p className="text-xs font-semibold text-brand capitalize">{candidate.type.replace('_', ' ')}</p>
                </div>
              </div>
            </div>

          </div>

          {/* Reasoning & Statistical Deep Dive */}
          {candidate.reasoning && (
            <div className="bg-[#1e293b]/30 border border-white/10 rounded-xl p-4 space-y-2">
              <h5 className="text-xs font-bold text-white flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-purple-400" />
                Yangi Testning Walk-Forward & Statistik Tahlil Hisoboti:
              </h5>
              <div className="bg-[#0f172a] p-3 rounded-lg border border-white/5 font-mono text-[11px] text-white/80 whitespace-pre-wrap max-h-60 overflow-y-auto leading-relaxed">
                {candidate.reasoning}
              </div>
            </div>
          )}

        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-white/10 bg-[#1e293b]/30 flex justify-end">
          <button 
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-white/10 hover:bg-white/20 text-white font-bold text-xs transition-colors"
          >
            Yopish
          </button>
        </div>

      </div>
    </div>
  );
}
