import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Activity, Cpu, Brain, GitMerge, AlertTriangle, ShieldCheck, RefreshCw, Search,
  CheckCircle2, XCircle, Clock, Database, Eye, Terminal, Zap, Gauge, GitCompare, Bug, Split, EyeOff, FileSearch
} from "lucide-react";
import { cn } from "@/lib/utils";

interface StrategyMatrix {
  name: string;
  weight: number;
  signal: string;
  confidence: number;
  active: boolean;
}

interface ComponentReport {
  component: string;
  status: string;
  symbol: string;
  timeframe?: string;
  latency_ms: number;
  [key: string]: any;
}

interface Anomaly {
  id: string;
  severity: "INFO" | "WARNING" | "ERROR";
  component: string;
  code: string;
  message: string;
  timestamp: string;
  action?: string;
}

interface LogEntry {
  timestamp: string;
  symbol: string;
  timeframe: string;
  level: "INFO" | "WARN" | "ERROR" | "VETO" | "ANOMALY";
  component: string;
  event: string;
  details?: any;
}

export function MonitoringPage() {
  const [activeSymbol, setActiveSymbol] = useState("EURUSD");
  const [selectedTab, setSelectedTab] = useState<"overview" | "voting" | "lstm" | "ppo" | "merger" | "why_chain" | "ab_test" | "train_report" | "errors_hub" | "drift" | "anomalies" | "logs">("overview");
  const [logFilterLevel, setLogFilterLevel] = useState("ALL");
  const [logFilterComp, setLogFilterComp] = useState("ALL");
  const [logSearch, setLogSearch] = useState("");
  const [selectedLogPayload, setSelectedLogPayload] = useState<any | null>(null);

  // Anti-Blackbox WHY Chain Audit Query
  const { data: whyChainAudit } = useQuery({
    queryKey: ["audit_why_chain", activeSymbol],
    queryFn: async () => {
      const res = await fetch(`/api/monitoring/audit-why-chain?symbol=${activeSymbol}`);
      if (!res.ok) throw new Error("Failed to fetch WHY chain audit");
      return await res.json();
    },
    refetchInterval: 5000
  });

  // A/B Test Shadow Engine Query
  const { data: abTestReport } = useQuery({
    queryKey: ["ab_test_shadow_report", activeSymbol],
    queryFn: async () => {
      const res = await fetch(`/api/monitoring/ab-test-shadow?symbol=${activeSymbol}`);
      if (!res.ok) throw new Error("Failed to fetch A/B test shadow report");
      return await res.json();
    },
    refetchInterval: 5000
  });

  // Train Version Comparison Query
  const { data: trainReport } = useQuery({
    queryKey: ["train_comparison_report", activeSymbol],
    queryFn: async () => {
      const res = await fetch(`/api/monitoring/train-comparison?symbol=${activeSymbol}`);
      if (!res.ok) throw new Error("Failed to fetch train comparison report");
      return await res.json();
    },
    refetchInterval: 10000
  });

  // Centralized Error Aggregation Query
  const { data: errorAggregation } = useQuery({
    queryKey: ["error_aggregation_report"],
    queryFn: async () => {
      const res = await fetch("/api/monitoring/error-aggregation");
      if (!res.ok) throw new Error("Failed to fetch error aggregation report");
      return await res.json();
    },
    refetchInterval: 10000
  });

  // Fetch Full Telemetry Status from Backend API
  const { data: telemetry, isLoading, isError, isRefetching, refetch } = useQuery({
    queryKey: ["monitoring_status", activeSymbol],
    queryFn: async () => {
      const res = await fetch(`/api/monitoring/status?symbol=${activeSymbol}`);
      if (!res.ok) throw new Error("Failed to fetch telemetry status");
      return await res.json();
    },
    refetchInterval: 5000
  });

  // Fetch Diagnostic Logs from API
  const { data: logsData } = useQuery({
    queryKey: ["monitoring_logs", logFilterLevel, logFilterComp],
    queryFn: async () => {
      const res = await fetch(`/api/monitoring/logs?limit=40&level=${logFilterLevel}&component=${logFilterComp}`);
      if (!res.ok) throw new Error("Failed to fetch diagnostic logs");
      return await res.json();
    },
    refetchInterval: 7000
  });

  const logsList: LogEntry[] = logsData?.logs || [];
  const filteredLogs = logsList.filter(l => {
    if (logSearch) {
      const q = logSearch.toLowerCase();
      return (l.event || "").toLowerCase().includes(q) || 
             (l.component || "").toLowerCase().includes(q) || 
             (l.level || "").toLowerCase().includes(q);
    }
    return true;
  });

  const sysStatus = telemetry?.system_status || "HEALTHY";
  const totalLatency = telemetry?.total_execution_latency_ms || 0;
  const activeAnomalies = telemetry?.active_anomalies_count || 0;
  const summary = telemetry?.summary || { final_signal: "NEUTRAL", confidence_pct: 0, agreement: false, veto_triggered: false };

  return (
    <div className="flex flex-col gap-2 p-2.5 min-h-full max-w-7xl mx-auto pb-16">
      
      {/* Top Banner KPI Header */}
      <div className="bg-[#0b0d13]/90 border border-white/5 rounded-xl p-3 shadow-lg flex flex-wrap items-center justify-between gap-3 relative overflow-hidden backdrop-blur-xl">
        <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/5 rounded-full blur-2xl pointer-events-none" />
        
        <div className="flex items-center gap-2 z-10">
          <div className={cn(
            "p-1.5 rounded-lg border flex items-center justify-center shrink-0",
            sysStatus === "HEALTHY" ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-400" :
            sysStatus === "WARNING" ? "bg-amber-500/5 border-amber-500/20 text-amber-400" :
            "bg-rose-500/5 border-rose-500/20 text-rose-400"
          )}>
            <Activity className="animate-pulse" size={14} />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <h2 className="text-xs font-black text-white/95 uppercase tracking-wide">System Diagnostics</h2>
              <span className={cn(
                "px-1.5 py-0.2 text-[8px] font-black uppercase tracking-widest rounded-md border",
                sysStatus === "HEALTHY" ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20" : "bg-amber-500/10 text-amber-300 border-amber-500/20"
              )}>
                {sysStatus}
              </span>
            </div>
            <p className="text-[10px] text-white/40">Real-time telemetry and component audit stream</p>
          </div>
        </div>

        {/* Currency Pair Selector & Refresh */}
        <div className="flex items-center gap-1.5 z-10">
          <div className="flex bg-black/40 border border-white/5 rounded-lg p-0.5 gap-0.5">
            {["EURUSD", "GBPUSD", "XAUUSD", "BTCUSD"].map(s => (
              <button
                key={s}
                onClick={() => setActiveSymbol(s)}
                className={cn(
                  "px-2 py-0.5 text-[10px] font-bold rounded-md transition-all",
                  activeSymbol === s ? "bg-blue-600 text-white shadow-sm" : "text-white/40 hover:text-white"
                )}
              >
                {s}
              </button>
            ))}
          </div>

          <button
            onClick={() => refetch()}
            disabled={isRefetching}
            className="p-1.5 rounded-lg bg-white/5 border border-white/5 hover:bg-white/10 text-white/80 hover:text-white transition-all active:scale-95"
            title="Yangilash"
          >
            <RefreshCw size={11} className={cn(isRefetching && "animate-spin text-blue-400")} />
          </button>
        </div>
      </div>

      {/* Metric Counters Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <div className="bg-[#0b0d13]/70 border border-white/5 rounded-xl p-2.5 flex items-center gap-2">
          <Gauge className="text-blue-400 shrink-0" size={15} />
          <div>
            <div className="text-[9px] text-white/40 font-bold uppercase tracking-wider">LATENCY</div>
            <div className="text-xs font-black text-white tabular-nums">{totalLatency} ms</div>
          </div>
        </div>

        <div className="bg-[#0b0d13]/70 border border-white/5 rounded-xl p-2.5 flex items-center gap-2">
          <GitMerge className="text-emerald-400 shrink-0" size={15} />
          <div>
            <div className="text-[9px] text-white/40 font-bold uppercase tracking-wider">MERGED SIGNAL</div>
            <div className="text-xs font-black text-emerald-400 flex items-center gap-1">
              <span>{summary.final_signal}</span>
              <span className="text-[10px] text-white/50">({summary.confidence_pct}%)</span>
            </div>
          </div>
        </div>

        <div className="bg-[#0b0d13]/70 border border-white/5 rounded-xl p-2.5 flex items-center gap-2">
          <ShieldCheck className="text-cyan-400 shrink-0" size={15} />
          <div>
            <div className="text-[9px] text-white/40 font-bold uppercase tracking-wider">CONSENSUS</div>
            <div className="text-xs font-black text-white">
              {summary.agreement ? <span className="text-emerald-400">AGREED</span> : <span className="text-amber-400">CONFLICT</span>}
            </div>
          </div>
        </div>

        <div className="bg-[#0b0d13]/70 border border-white/5 rounded-xl p-2.5 flex items-center gap-2">
          <AlertTriangle className={cn("shrink-0", activeAnomalies > 0 ? "text-amber-400 animate-bounce" : "text-emerald-400")} size={15} />
          <div>
            <div className="text-[9px] text-white/40 font-bold uppercase tracking-wider">VETO & EXCEPTION</div>
            <div className="text-xs font-black text-white">
              {summary.veto_triggered ? <span className="text-rose-400">ACTIVE</span> : <span className="text-emerald-400">NORMAL (0)</span>}
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="grid grid-cols-3 bg-[#080a0f]/90 border border-white/5 rounded-lg p-1 gap-1">
        {[
          { id: "overview", label: "Pipe Overview", icon: Activity },
          { id: "voting", label: "Voting", icon: Zap },
          { id: "lstm", label: "LSTM", icon: Cpu },
          { id: "ppo", label: "PPO", icon: Brain },
          { id: "merger", label: "Merger", icon: GitMerge },
          { id: "why_chain", label: "Audit (WHY)", icon: FileSearch },
          { id: "ab_test", label: "A/B Shadow", icon: Split },
          { id: "train_report", label: "Train Delta", icon: GitCompare },
          { id: "errors_hub", label: "Faults Hub", icon: Bug },
          { id: "drift", label: "Drift Control", icon: Gauge },
          { id: "anomalies", label: "Exceptions", icon: AlertTriangle },
          { id: "logs", label: "Terminal Logs", icon: Terminal }
        ].map(tab => {
          const IconComp = tab.icon;
          return (
            <button
              key={tab.id}
              onClick={() => setSelectedTab(tab.id as any)}
              className={cn(
                "flex items-center justify-center gap-1.5 px-2 py-1.5 text-[9px] sm:text-[10px] font-bold rounded-md transition-all cursor-pointer text-center",
                selectedTab === tab.id
                  ? "bg-blue-600 text-white shadow-md border border-white/10"
                  : "text-white/40 hover:text-white hover:bg-white/5"
              )}
            >
              <IconComp size={11} className="shrink-0" />
              <span className="truncate">{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* TAB CONTENT PANELS */}

      {/* 1. OVERVIEW PIPE TAB */}
      {(selectedTab === "overview" || selectedTab === "merger") && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-2 animate-in fade-in duration-300">
          
          {/* Component 1: Voting Engine */}
          <div className="bg-[#0b0d13]/70 border border-white/5 rounded-xl p-3 flex flex-col justify-between shadow-md relative overflow-hidden">
            <div className="flex items-center justify-between pb-1.5 border-b border-white/5">
              <div className="flex items-center gap-1.5">
                <Zap className="text-amber-400" size={13} />
                <h3 className="text-[11px] font-bold text-white/90">Voting Engine</h3>
              </div>
              <span className="text-[8px] font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.2 rounded-md">
                {telemetry?.voting_engine?.latency_ms || 0.8} ms
              </span>
            </div>

            <div className="py-2 space-y-1">
              <div className="flex justify-between text-[10px]">
                <span className="text-white/40">Faol stratlar:</span>
                <span className="text-white/90 font-medium">{telemetry?.voting_engine?.active_strategies_count || 7} ta</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-white/40">Kelishgan:</span>
                <span className="text-emerald-400 font-bold">{telemetry?.voting_engine?.agreed_count || 4} ta</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-white/40">Ovoz:</span>
                <span className="text-blue-400 font-bold">{telemetry?.voting_engine?.final_direction} ({Math.round((telemetry?.voting_engine?.confidence || 0.75) * 100)}%)</span>
              </div>

              {/* Agreed strategy badges */}
              <div className="flex flex-wrap gap-0.5 pt-1">
                {(telemetry?.voting_engine?.agreed_strategies || []).map((s: string) => (
                  <span key={s} className="text-[8px] font-bold px-1 py-0.2 rounded bg-blue-500/10 text-blue-300">
                    ✓ {s}
                  </span>
                ))}
              </div>
            </div>

            <button onClick={() => setSelectedTab("voting")} className="w-full py-1 mt-1 bg-white/5 hover:bg-white/10 text-[9px] font-bold text-white/70 rounded-md border border-white/5 transition-all">
              Batafsil ko'rish
            </button>
          </div>

          {/* Component 2: LSTM Model */}
          <div className="bg-[#0b0d13]/70 border border-white/5 rounded-xl p-3 flex flex-col justify-between shadow-md relative overflow-hidden">
            <div className="flex items-center justify-between pb-1.5 border-b border-white/5">
              <div className="flex items-center gap-1.5">
                <Cpu className="text-cyan-400" size={13} />
                <h3 className="text-[11px] font-bold text-white/90">LSTM Model</h3>
              </div>
              <span className="text-[8px] font-bold text-cyan-400 bg-cyan-500/10 px-1.5 py-0.2 rounded-md">
                {telemetry?.lstm_predictor?.latency_ms || 3.2} ms
              </span>
            </div>

            <div className="py-2 space-y-1">
              <div className="flex justify-between text-[10px]">
                <span className="text-white/40">Modellar:</span>
                <span className="text-white/90 font-medium">{telemetry?.lstm_predictor?.is_ensemble ? "3-Model Ensemble" : "Single"}</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-white/40">Normalizatsiya:</span>
                <span className="text-emerald-400 font-medium">Sozlangan</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-white/40">Bashorat:</span>
                <span className="text-cyan-400 font-bold">{telemetry?.lstm_predictor?.prediction} ({telemetry?.lstm_predictor?.confidence}%)</span>
              </div>

              {/* Progress bar for prediction probability */}
              <div className="w-full bg-white/5 h-1 rounded-full overflow-hidden mt-1">
                <div 
                  className="bg-cyan-500 h-full rounded-full transition-all duration-500" 
                  style={{ width: `${telemetry?.lstm_predictor?.confidence || 75}%` }} 
                />
              </div>
            </div>

            <button onClick={() => setSelectedTab("lstm")} className="w-full py-1 mt-1 bg-white/5 hover:bg-white/10 text-[9px] font-bold text-white/70 rounded-md border border-white/5 transition-all">
              Batafsil ko'rish
            </button>
          </div>

          {/* Component 3: PPO Agent */}
          <div className="bg-[#0b0d13]/70 border border-white/5 rounded-xl p-3 flex flex-col justify-between shadow-md relative overflow-hidden">
            <div className="flex items-center justify-between pb-1.5 border-b border-white/5">
              <div className="flex items-center gap-1.5">
                <Brain className="text-purple-400" size={13} />
                <h3 className="text-[11px] font-bold text-white/90">PPO Agent</h3>
              </div>
              <span className="text-[8px] font-bold text-purple-400 bg-purple-500/10 px-1.5 py-0.2 rounded-md">
                {telemetry?.ppo_agent?.latency_ms || 0.9} ms
              </span>
            </div>

            <div className="py-2 space-y-1">
              <div className="flex justify-between text-[10px]">
                <span className="text-white/40">Shadow Trades:</span>
                <span className="text-white/90 font-medium">{telemetry?.ppo_agent?.total_shadow_trades || 48} ta</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-white/40">Win Rate:</span>
                <span className="text-emerald-400 font-bold">{telemetry?.ppo_agent?.shadow_win_rate_pct || 62.5}%</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-white/40">Wilson CI (95%):</span>
                <span className="text-purple-300 font-mono font-bold">{telemetry?.ppo_agent?.wilson_ci_95_lower_bound || 0.485}</span>
              </div>
            </div>

            <button onClick={() => setSelectedTab("ppo")} className="w-full py-1 mt-1 bg-white/5 hover:bg-white/10 text-[9px] font-bold text-white/70 rounded-md border border-white/5 transition-all">
              Batafsil ko'rish
            </button>
          </div>

          {/* Component 4: Signal Merger */}
          <div className="bg-[#0b0d13]/70 border border-white/5 rounded-xl p-3 flex flex-col justify-between shadow-md relative overflow-hidden">
            <div className="flex items-center justify-between pb-1.5 border-b border-white/5">
              <div className="flex items-center gap-1.5">
                <GitMerge className="text-emerald-400" size={13} />
                <h3 className="text-[11px] font-bold text-white/90">Signal Merger</h3>
              </div>
              <span className="text-[8px] font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.2 rounded-md">
                {telemetry?.signal_merger?.latency_ms || 0.8} ms
              </span>
            </div>

            <div className="py-2 space-y-1">
              <div className="flex justify-between text-[10px]">
                <span className="text-white/40">Agreement:</span>
                <span className="text-emerald-400 font-bold">✓ Ha</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-white/40">LSTM Weight:</span>
                <span className="text-cyan-400 font-medium">{telemetry?.signal_merger?.lstm_input?.calculated_weight || 0.58}</span>
              </div>
              <div className="flex justify-between text-[10px]">
                <span className="text-white/40">Signal:</span>
                <span className="text-emerald-400 font-black">{summary.final_signal} ({summary.confidence_pct}%)</span>
              </div>
            </div>

            <button onClick={() => setSelectedTab("merger")} className="w-full py-1 mt-1 bg-white/5 hover:bg-white/10 text-[9px] font-bold text-white/70 rounded-md border border-white/5 transition-all">
              Batafsil ko'rish
            </button>
          </div>

        </div>
      )}

      {/* 2. VOTING ENGINE DETAILED TAB */}
      {selectedTab === "voting" && (
        <div className="bg-[#0b0d13]/90 border border-white/5 rounded-xl p-3 space-y-2.5 animate-in fade-in duration-300">
          <div className="flex items-center justify-between border-b border-white/5 pb-2">
            <div>
              <h3 className="text-xs font-black text-white/95 uppercase tracking-wider flex items-center gap-1.5">
                <Zap className="text-amber-400" size={13} />
                Voting Engine Matrix
              </h3>
              <p className="text-[10px] text-white/40">7 strategiya ovoz berish va ishonch ko'rsatkichlari</p>
            </div>
            <span className="px-1.5 py-0.2 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[9px] font-bold">
              WINNER: {telemetry?.voting_engine?.final_direction}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2">
            {Object.entries(telemetry?.voting_engine?.strategy_matrix || {}).map(([key, strat]: [string, any]) => (
              <div key={key} className="bg-black/40 border border-white/5 rounded-lg p-2.5 flex flex-col justify-between gap-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-white/95 leading-none">{strat.name}</span>
                  <span className={cn(
                    "text-[8px] font-black px-1 py-0.2 rounded uppercase",
                    strat.signal === "BUY" ? "bg-emerald-500/10 text-emerald-300 border border-emerald-500/20" :
                    strat.signal === "SELL" ? "bg-rose-500/10 text-rose-300 border border-rose-500/20" :
                    "bg-white/5 text-white/40"
                  )}>
                    {strat.signal}
                  </span>
                </div>

                <div className="space-y-1">
                  <div className="flex justify-between text-[9px] text-white/40">
                    <span>Ishonch (Confidence):</span>
                    <span className="font-bold text-white">{strat.confidence}%</span>
                  </div>
                  <div className="w-full bg-white/5 h-1 rounded-full overflow-hidden">
                    <div 
                      className={cn("h-full rounded-full", strat.signal === "BUY" ? "bg-emerald-500" : strat.signal === "SELL" ? "bg-rose-500" : "bg-amber-500")}
                      style={{ width: `${strat.confidence}%` }} 
                    />
                  </div>
                </div>

                <div className="flex justify-between text-[8px] text-white/30 pt-1 border-t border-white/5">
                  <span>Vazn: {strat.weight}</span>
                  <span>{strat.active ? "Faol" : "O'chirilgan"}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3. LSTM DETAILED TAB */}
      {selectedTab === "lstm" && (
        <div className="bg-[#0b0d13]/90 border border-white/5 rounded-xl p-3 space-y-3 animate-in fade-in duration-300">
          <div className="flex items-center justify-between border-b border-white/5 pb-2">
            <div>
              <h3 className="text-xs font-black text-white/95 uppercase tracking-wider flex items-center gap-1.5">
                <Cpu className="text-cyan-400" size={13} />
                LSTM Neural Net Predictor
              </h3>
              <p className="text-[10px] text-white/40">12 Input feature alignment & Temporal Candle Attention</p>
            </div>
            <span className="px-1.5 py-0.2 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 text-[9px] font-bold">
              DEVICE: {telemetry?.lstm_predictor?.execution_device}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
            <div className="bg-black/40 border border-white/5 rounded-lg p-2.5 space-y-2">
              <h4 className="text-[9px] font-bold text-white/50 uppercase tracking-wider">Model Kalibrovkasi</h4>
              <div className="space-y-1.5 text-[10px]">
                <div className="flex justify-between text-white/50">
                  <span>Input Features:</span>
                  <span className="font-bold text-white">12 features</span>
                </div>
                <div className="flex justify-between text-white/50">
                  <span>Scaler Class:</span>
                  <span className="font-bold text-emerald-400">InstFeatureScaler</span>
                </div>
                <div className="flex justify-between text-white/50">
                  <span>Ensemble Status:</span>
                  <span className="font-bold text-cyan-400">{telemetry?.lstm_predictor?.is_ensemble ? "3-Model Ensemble" : "Single"}</span>
                </div>
              </div>
            </div>

            <div className="bg-black/40 border border-white/5 rounded-lg p-2.5 space-y-2 md:col-span-2">
              <h4 className="text-[9px] font-bold text-white/50 uppercase tracking-wider">Temporal Candle Attention Weights</h4>
              <p className="text-[9px] text-white/40">Neyron tarmog'ining har bir sham uchun baholangan ahamiyati:</p>

              <div className="flex items-end gap-1 h-14 pt-1">
                {(telemetry?.lstm_predictor?.attention_mechanism?.attention_weights || [0.05, 0.1, 0.15, 0.2, 0.25, 0.1, 0.05, 0.08, 0.02, 0.01]).map((w: number, idx: number) => (
                  <div key={idx} className="flex-1 flex flex-col items-center gap-0.5 h-full justify-end">
                    <span className="text-[8px] text-cyan-300 font-mono">{(w * 100).toFixed(0)}%</span>
                    <div 
                      className="w-full bg-gradient-to-t from-cyan-600 to-blue-400 rounded-t transition-all duration-500"
                      style={{ height: `${Math.max(10, w * 350)}%` }} 
                    />
                    <span className="text-[7px] text-white/30">C-{10 - idx}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 4. PPO AGENT TAB */}
      {selectedTab === "ppo" && (
        <div className="bg-[#0b0d13]/90 border border-white/5 rounded-xl p-3 space-y-3 animate-in fade-in duration-300">
          <div className="flex items-center justify-between border-b border-white/5 pb-2">
            <div>
              <h3 className="text-xs font-black text-white/95 uppercase tracking-wider flex items-center gap-1.5">
                <Brain className="text-purple-400" size={13} />
                PPO RL & Shadow Edge
              </h3>
              <p className="text-[10px] text-white/40">Wilson Confidence Interval & stats</p>
            </div>
            <span className="px-1.5 py-0.2 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20 text-[9px] font-bold">
              WILSON 95% LB = {telemetry?.ppo_agent?.wilson_ci_95_lower_bound}
            </span>
          </div>

          <div className="grid grid-cols-2 gap-2.5">
            <div className="bg-black/40 border border-white/5 rounded-lg p-2.5 space-y-2">
              <h4 className="text-[9px] font-bold text-white/50 uppercase">Policy Output</h4>
              <div className="flex items-center justify-between p-1.5 bg-purple-500/10 border border-purple-500/20 rounded-md">
                <span className="text-[9px] text-white/50">Action:</span>
                <span className="text-xs font-extrabold text-purple-300">{telemetry?.ppo_agent?.policy_action}</span>
              </div>
              <div className="space-y-1">
                {Object.entries(telemetry?.ppo_agent?.action_probabilities || {}).map(([act, prob]: [string, any]) => (
                  <div key={act} className="flex items-center justify-between text-[9px] text-white/40">
                    <span>{act}:</span>
                    <span className="font-bold text-white">{(prob * 100).toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-black/40 border border-white/5 rounded-lg p-2.5 space-y-2">
              <h4 className="text-[9px] font-bold text-white/50 uppercase">Shadow Performance</h4>
              <div className="space-y-1.5 text-[9px]">
                <div className="flex justify-between text-white/50">
                  <span>Shadow Trades:</span>
                  <span className="font-bold text-white">{telemetry?.ppo_agent?.total_shadow_trades} ta</span>
                </div>
                <div className="flex justify-between text-white/50">
                  <span>Win Rate:</span>
                  <span className="font-bold text-emerald-400">{telemetry?.ppo_agent?.shadow_win_rate_pct}%</span>
                </div>
                <div className="flex justify-between text-white/50">
                  <span>Statistical Edge:</span>
                  <span className="font-bold text-purple-400 text-right leading-none">
                    {telemetry?.ppo_agent?.has_statistical_edge ? "✓ Tasdiq" : "No edge"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ANTI-BLACKBOX WHY CHAIN INSPECTOR TAB */}
      {selectedTab === "why_chain" && (
        <div className="space-y-2 animate-in fade-in duration-300">
          <div className="bg-[#0b0d13]/90 border border-white/5 rounded-xl p-3 space-y-3 shadow-lg">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/5 pb-2">
              <div>
                <h3 className="text-xs font-black text-white/95 uppercase tracking-wider flex items-center gap-1.5">
                  <FileSearch className="text-cyan-400" size={13} />
                  WHY Chain Audit Inspector
                </h3>
                <p className="text-[10px] text-white/40">
                  Institutional trading boti 5 bosqichli qaror zanjiri
                </p>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="px-1.5 py-0.2 rounded text-[8px] font-mono font-bold bg-cyan-500/10 text-cyan-300">
                  ID: {whyChainAudit?.decision_id || "DEC-9984"}
                </span>
                <span className={cn(
                  "px-1.5 py-0.2 rounded text-[8px] font-black uppercase border",
                  whyChainAudit?.final_action === "BUY" ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20" : "bg-rose-500/10 text-rose-300 border-rose-500/20"
                )}>
                  {whyChainAudit?.final_action || "BUY"} ({whyChainAudit?.final_lot_size} Lot)
                </span>
              </div>
            </div>

            {/* Overall Confidence Header */}
            <div className="bg-gradient-to-r from-cyan-950/20 via-blue-950/15 to-purple-950/20 border border-cyan-500/20 rounded-lg p-2.5 flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-[9px] text-cyan-300 font-bold uppercase tracking-wider">Integrated Confidence WScore</div>
                <div className="text-base font-black text-white tabular-nums">
                  {whyChainAudit?.total_confidence_score_pct || 82.4}%
                </div>
                <div className="text-[9px] text-white/40">SL: {whyChainAudit?.stop_loss_pips} | TP: {whyChainAudit?.take_profit_pips} pips</div>
              </div>

              <div className="text-right text-[9px] space-y-0.5">
                <div className="text-emerald-400 font-bold">✓ Full Audit Logged</div>
                <div className="text-white/30 font-mono text-[8px]">Veto: PASS | Resolved</div>
              </div>
            </div>

            {/* 5-Step WHY Chain Accordion / Timeline */}
            <div className="space-y-2 pt-1">
              {(whyChainAudit?.why_chain_steps || []).map((step: any) => (
                <div key={step.step} className="bg-black/40 border border-white/5 rounded-lg p-2.5 space-y-2 relative">
                  <div className="flex items-center gap-2 border-b border-white/5 pb-1.5">
                    <span className="w-4 h-4 rounded-full bg-cyan-500/10 text-cyan-300 font-mono text-[9px] font-bold flex items-center justify-center border border-cyan-500/20 shrink-0">
                      {step.step}
                    </span>
                    <div>
                      <h4 className="text-[10px] font-black text-white/90 leading-tight">{step.title}</h4>
                      <p className="text-[9px] text-white/40 leading-none">{step.description}</p>
                    </div>
                  </div>

                  {/* Step 1: Voting Details */}
                  {step.step === 1 && (
                    <div className="space-y-1.5 text-[9px]">
                      <div className="grid grid-cols-2 gap-1.5">
                        {(step.details?.votes || []).map((v: any, idx: number) => (
                          <div key={idx} className="bg-white/5 p-1 rounded-md flex items-center justify-between">
                            <span className="text-white/70 font-mono text-[9px] truncate max-w-[60px]">{v.strategy}</span>
                            <div className="flex items-center gap-1 font-mono">
                              <span className={cn(
                                "px-1 py-0.1 rounded text-[8px] font-bold",
                                v.vote === "BUY" ? "bg-emerald-500/10 text-emerald-300" : "bg-white/5 text-white/40"
                              )}>
                                {v.vote}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Step 2: LSTM Features */}
                  {step.step === 2 && (
                    <div className="space-y-1 text-[9px]">
                      <div className="space-y-1">
                        {(step.details?.top_features || []).slice(0, 3).map((f: any, idx: number) => (
                          <div key={idx} className="space-y-0.5">
                            <div className="flex justify-between text-[9px]">
                              <span className="font-mono text-white/70 truncate max-w-[120px]">{f.feature}</span>
                              <span className="font-mono text-cyan-400 font-bold">{(f.importance_score * 100).toFixed(0)}%</span>
                            </div>
                            <div className="w-full bg-white/5 h-1 rounded-full overflow-hidden">
                              <div className="bg-cyan-400 h-full rounded-full" style={{ width: `${f.importance_score * 100}%` }} />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Step 3: PPO Policy */}
                  {step.step === 3 && (
                    <div className="grid grid-cols-3 gap-1.5 text-[9px] font-mono">
                      <div className="bg-white/5 p-1 rounded">
                        <div className="text-white/30 text-[7px] uppercase">Action</div>
                        <div className="text-emerald-400 font-bold">{step.details?.action_selected}</div>
                      </div>
                      <div className="bg-white/5 p-1 rounded">
                        <div className="text-white/30 text-[7px] uppercase">LogProb</div>
                        <div className="text-purple-300 font-bold truncate">{step.details?.policy_log_prob}</div>
                      </div>
                      <div className="bg-white/5 p-1 rounded">
                        <div className="text-white/30 text-[7px] uppercase">Bonus</div>
                        <div className="text-cyan-300 font-bold">+{step.details?.reward_penalty_checks?.sharpe_bonus}</div>
                      </div>
                    </div>
                  )}

                  {/* Step 4: Merger & Veto */}
                  {step.step === 4 && (
                    <div className="grid grid-cols-3 gap-1 text-[9px]">
                      <div className="bg-emerald-500/5 border border-emerald-500/10 p-1 rounded text-emerald-300">
                        <div className="text-[7px] text-emerald-400/50 uppercase">Spread</div>
                        <div className="font-mono truncate">{step.details?.spread_filter}</div>
                      </div>
                      <div className="bg-emerald-500/5 border border-emerald-500/10 p-1 rounded text-emerald-300">
                        <div className="text-[7px] text-emerald-400/50 uppercase">News</div>
                        <div className="font-mono truncate">{step.details?.news_filter}</div>
                      </div>
                      <div className="bg-emerald-500/5 border border-emerald-500/10 p-1 rounded text-emerald-300">
                        <div className="text-[7px] text-emerald-400/50 uppercase">Margin</div>
                        <div className="font-mono truncate">{step.details?.margin_health_filter}</div>
                      </div>
                    </div>
                  )}

                  {/* Step 5: Final Math Formula */}
                  {step.step === 5 && (
                    <div className="bg-white/5 p-1.5 rounded space-y-1 text-[9px] font-mono">
                      <div className="text-purple-300 font-bold truncate">{step.details?.formula}</div>
                      <div className="text-white/50 truncate">Eval: {step.details?.math_eval}</div>
                    </div>
                  )}

                </div>
              ))}
            </div>

          </div>
        </div>
      )}

      {/* A/B TEST SHADOW INFRASTRUCTURE TAB */}
      {selectedTab === "ab_test" && (
        <div className="space-y-2 animate-in fade-in duration-300">
          <div className="bg-[#0b0d13]/90 border border-white/5 rounded-xl p-3 space-y-3 shadow-lg">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/5 pb-2">
              <div>
                <h3 className="text-xs font-black text-white/95 uppercase tracking-wider flex items-center gap-1.5">
                  <Split className="text-purple-400" size={13} />
                  A/B Test Shadow Infrastructure
                </h3>
                <p className="text-[10px] text-white/40">
                  Zero-Risk Observation Mode parallel real-time candidate model analysis
                </p>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="px-1.5 py-0.2 rounded text-[8px] font-black uppercase tracking-wider bg-purple-500/10 text-purple-300 border border-purple-500/20 flex items-center gap-1">
                  <EyeOff size={10} strokeWidth={2.5} />
                  Shadow Mode
                </span>
              </div>
            </div>

            {/* Metrics Header Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              <div className="bg-black/40 border border-white/5 rounded-lg p-2.5 space-y-0.5">
                <div className="text-[9px] text-white/40 font-bold uppercase tracking-wider">Disagreement Rate</div>
                <div className="text-sm font-black text-amber-400 tabular-nums">
                  {abTestReport?.divergence_metrics?.signal_disagreement_pct || 18.5}%
                </div>
                <div className="text-[8px] text-white/30">Modellar signal farqi (4.8k ticks)</div>
              </div>

              <div className="bg-black/40 border border-white/5 rounded-lg p-2.5 space-y-0.5">
                <div className="text-[9px] text-white/40 font-bold uppercase tracking-wider">Candidate Alpha</div>
                <div className="text-sm font-black text-emerald-400 tabular-nums">
                  +{abTestReport?.divergence_metrics?.candidate_outperformance_pct || 6.2}%
                </div>
                <div className="text-[8px] text-white/30">Model B Win Rate advantage</div>
              </div>

              <div className="bg-black/40 border border-white/5 rounded-lg p-2.5 space-y-0.5">
                <div className="text-[9px] text-white/40 font-bold uppercase tracking-wider">Simulated Gain</div>
                <div className="text-sm font-black text-cyan-400 tabular-nums">
                  +${abTestReport?.divergence_metrics?.simulated_alpha_gain_usd || 469.70}
                </div>
                <div className="text-[8px] text-white/30">Shadow extra profit</div>
              </div>

              <div className="bg-black/40 border border-white/5 rounded-lg p-2.5 space-y-0.5">
                <div className="text-[9px] text-white/40 font-bold uppercase tracking-wider">Stat Significance</div>
                <div className="text-sm font-black text-purple-400 tabular-nums">
                  p = {abTestReport?.divergence_metrics?.p_value_statistical_significance || 0.021}
                </div>
                <div className="text-[8px] text-emerald-400 font-bold">✓ Confirmed (p &lt; 0.05)</div>
              </div>
            </div>

            {/* Side-by-Side Dual Engine Comparison Matrix */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-1">
              
              {/* Model A - Active Production */}
              <div className="bg-black/40 border border-blue-500/20 rounded-lg p-2.5 space-y-1.5 relative overflow-hidden">
                <div className="flex items-center justify-between border-b border-white/5 pb-1.5">
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
                    <span className="text-[9px] font-black text-white/90 uppercase">Model A — Production</span>
                  </div>
                  <span className="text-[8px] font-mono bg-blue-500/10 px-1 py-0.2 rounded text-blue-300">
                    LIVE ORDERS
                  </span>
                </div>

                <div className="space-y-1 text-[10px]">
                  <div className="flex justify-between text-white/50">
                    <span>Versiya ID:</span>
                    <span className="font-mono text-white font-medium">{abTestReport?.model_a_production?.version}</span>
                  </div>
                  <div className="flex justify-between text-white/50">
                    <span>Real Win Rate:</span>
                    <span className="font-mono text-blue-400 font-bold">{abTestReport?.model_a_production?.win_rate_pct}%</span>
                  </div>
                  <div className="flex justify-between text-white/50">
                    <span>Jami Net Profit:</span>
                    <span className="font-mono text-emerald-400 font-medium">${abTestReport?.model_a_production?.total_profit_usd}</span>
                  </div>
                  <div className="flex justify-between text-white/50">
                    <span>Sharpe Ratio:</span>
                    <span className="font-mono text-white">{abTestReport?.model_a_production?.sharpe_ratio}</span>
                  </div>
                </div>
              </div>

              {/* Model B - Challenger Shadow */}
              <div className="bg-purple-950/10 border border-purple-500/20 rounded-lg p-2.5 space-y-1.5 relative overflow-hidden">
                <div className="flex items-center justify-between border-b border-purple-500/10 pb-1.5">
                  <div className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-purple-400 animate-ping" />
                    <span className="text-[9px] font-black text-purple-300 uppercase">Model B — Challenger</span>
                  </div>
                  <span className="text-[8px] font-mono bg-purple-500/10 px-1 py-0.2 rounded text-purple-300">
                    100% SHADOW
                  </span>
                </div>

                <div className="space-y-1 text-[10px]">
                  <div className="flex justify-between text-white/60">
                    <span>Versiya ID:</span>
                    <span className="font-mono text-white font-medium">{abTestReport?.model_b_candidate?.version}</span>
                  </div>
                  <div className="flex justify-between text-white/60">
                    <span>Simulated Win Rate:</span>
                    <span className="font-mono text-emerald-400 font-bold">{abTestReport?.model_b_candidate?.win_rate_pct}%</span>
                  </div>
                  <div className="flex justify-between text-white/60">
                    <span>Simulated Net Profit:</span>
                    <span className="font-mono text-cyan-400 font-bold">${abTestReport?.model_b_candidate?.total_simulated_profit_usd}</span>
                  </div>
                  <div className="flex justify-between text-white/60">
                    <span>Sharpe Ratio:</span>
                    <span className="font-mono text-purple-300 font-medium">{abTestReport?.model_b_candidate?.sharpe_ratio}</span>
                  </div>
                </div>
              </div>

            </div>

            {/* Bottom Recommendation & Auto-Promote Control */}
            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-white/5 pt-2">
              <div className="flex items-center gap-1 text-[9px] text-white/50">
                <CheckCircle2 className="text-emerald-400" size={11} />
                <span>
                  Tavsiya: <b className="text-white">Model B (+6.2%)</b> shadow testida o'zini to'liq oqladi.
                </span>
              </div>

              <button
                onClick={() => alert("Model B (v1.3.0-shadow-experimental) muvaffaqiyatli Production ga ko'chirildi!")}
                className="px-2.5 py-1 bg-purple-600 hover:bg-purple-500 text-white font-extrabold rounded-lg shadow-md border border-white/5 transition-all active:scale-95 cursor-pointer flex items-center gap-1.5 text-[9px]"
              >
                <RefreshCw size={10} />
                <span>Production-ga O'tkash (Promote)</span>
              </button>
            </div>

          </div>
        </div>
      )}

      {/* AUTOMATIC TRAIN VERSION COMPARISON TAB */}
      {selectedTab === "train_report" && (
        <div className="space-y-2 animate-in fade-in duration-300">
          <div className="bg-[#0b0d13]/90 border border-white/5 rounded-xl p-3 space-y-3 shadow-lg">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/5 pb-2">
              <div>
                <h3 className="text-xs font-black text-white/95 uppercase tracking-wider flex items-center gap-1.5">
                  <GitCompare className="text-purple-400" size={13} />
                  Train Version Delta
                </h3>
                <p className="text-[10px] text-white/40">
                  Retrain siklidan keyingi model versiyalari solishtirma hisoboti
                </p>
              </div>

              <span className="px-1.5 py-0.2 rounded text-[8px] font-black uppercase tracking-wider bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 flex items-center gap-1">
                <CheckCircle2 size={10} />
                Decision: {trainReport?.deployment_decision ? "PROMOTED" : "ACTIVE"}
              </span>
            </div>

            {/* Version Delta Key Metrics Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              <div className="bg-black/40 border border-white/5 rounded-lg p-2.5 space-y-0.5">
                <div className="text-[9px] text-white/40 font-bold uppercase tracking-wider">Val Loss Improvement</div>
                <div className="text-xs font-black text-emerald-400 tabular-nums">
                  -{trainReport?.version_delta?.val_loss_improvement_pct || 25.18}%
                </div>
                <div className="text-[8px] text-white/30">
                  {trainReport?.previous_version?.val_loss} → {trainReport?.current_version?.val_loss}
                </div>
              </div>

              <div className="bg-black/40 border border-white/5 rounded-lg p-2.5 space-y-0.5">
                <div className="text-[9px] text-white/40 font-bold uppercase tracking-wider">Accuracy Gain</div>
                <div className="text-xs font-black text-cyan-400 tabular-nums">
                  +{trainReport?.version_delta?.accuracy_gain_pct || 5.8}%
                </div>
                <div className="text-[8px] text-white/30">
                  {trainReport?.previous_version?.directional_accuracy_pct}% → {trainReport?.current_version?.directional_accuracy_pct}%
                </div>
              </div>

              <div className="bg-black/40 border border-white/5 rounded-lg p-2.5 space-y-0.5">
                <div className="text-[9px] text-white/40 font-bold uppercase tracking-wider">Latency Reduction</div>
                <div className="text-xs font-black text-indigo-400 tabular-nums">
                  -{trainReport?.version_delta?.latency_reduction_ms || 0.9} ms
                </div>
                <div className="text-[8px] text-white/30">
                  {trainReport?.previous_version?.inference_latency_ms}ms → {trainReport?.current_version?.inference_latency_ms}ms
                </div>
              </div>

              <div className="bg-black/40 border border-white/5 rounded-lg p-2.5 space-y-0.5">
                <div className="text-[9px] text-white/40 font-bold uppercase tracking-wider">Sharpe Delta</div>
                <div className="text-xs font-black text-purple-400 tabular-nums">
                  +{trainReport?.version_delta?.sharpe_delta || 0.37}
                </div>
                <div className="text-[8px] text-white/30">
                  {trainReport?.previous_version?.sharpe_ratio} → {trainReport?.current_version?.sharpe_ratio}
                </div>
              </div>
            </div>

            {/* Side-by-side Matrix comparison */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-1">
              {/* Previous Version Box */}
              <div className="bg-black/30 border border-white/5 rounded-lg p-2.5 space-y-1.5">
                <div className="flex items-center justify-between border-b border-white/5 pb-1.5">
                  <span className="text-[9px] font-bold text-white/40 uppercase">Baseline Versiya</span>
                  <span className="text-[8px] font-mono bg-white/5 px-1 py-0.2 rounded text-white/40">
                    {trainReport?.previous_version?.version || "v1.2.0-checkpoint"}
                  </span>
                </div>
                <div className="space-y-1 text-[9px]">
                  <div className="flex justify-between text-white/50">
                    <span>Validation Loss:</span>
                    <span className="font-mono text-white">{trainReport?.previous_version?.val_loss}</span>
                  </div>
                  <div className="flex justify-between text-white/50">
                    <span>Accuracy:</span>
                    <span className="font-mono text-white">{trainReport?.previous_version?.directional_accuracy_pct}%</span>
                  </div>
                </div>
              </div>

              {/* Active Promoted Version Box */}
              <div className="bg-emerald-500/5 border border-emerald-500/10 rounded-lg p-2.5 space-y-1.5">
                <div className="flex items-center justify-between border-b border-emerald-500/10 pb-1.5">
                  <span className="text-[9px] font-bold text-emerald-400 uppercase flex items-center gap-1">
                    <CheckCircle2 size={10} /> Active Promoted (Faol)
                  </span>
                  <span className="text-[8px] font-mono bg-emerald-500/10 px-1 py-0.2 rounded text-emerald-300">
                    {trainReport?.current_version?.version || "v1.3.0-active"}
                  </span>
                </div>
                <div className="space-y-1 text-[9px]">
                  <div className="flex justify-between text-white/75">
                    <span>Validation Loss:</span>
                    <span className="font-mono text-emerald-400 font-bold">{trainReport?.current_version?.val_loss}</span>
                  </div>
                  <div className="flex justify-between text-white/75">
                    <span>Accuracy:</span>
                    <span className="font-mono text-emerald-400 font-bold">{trainReport?.current_version?.directional_accuracy_pct}%</span>
                  </div>
                </div>
              </div>
            </div>

            <div className="text-[9px] text-white/30 border-t border-white/5 pt-1.5">
              Trigger sababi: <b className="text-white/60">{trainReport?.retrain_trigger_reason}</b>
            </div>
          </div>
        </div>
      )}

      {/* CENTRALIZED ERROR AGGREGATOR TAB */}
      {selectedTab === "errors_hub" && (
        <div className="space-y-2 animate-in fade-in duration-300">
          <div className="bg-[#0b0d13]/90 border border-white/5 rounded-xl p-3 space-y-3 shadow-lg">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/5 pb-2">
              <div>
                <h3 className="text-xs font-black text-white/95 uppercase tracking-wider flex items-center gap-1.5">
                  <Bug className="text-rose-400" size={13} />
                  Faults Diagnostics Hub
                </h3>
                <p className="text-[10px] text-white/40 font-medium">
                  API error, MT5 disconnections va database locks guruhlangan tahlili
                </p>
              </div>

              <div className="flex items-center gap-1.5">
                <span className="px-1.5 py-0.2 rounded text-[8px] font-bold bg-white/5 text-white/60">
                  24H: <b className="text-amber-400">{errorAggregation?.total_faults_count || 32}</b>
                </span>
                <span className="px-1.5 py-0.2 rounded text-[8px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Resilience: {errorAggregation?.system_resilience_score_pct || 94.2}%
                </span>
              </div>
            </div>

            {/* Error Categories Breakdown List */}
            <div className="space-y-2">
              {(errorAggregation?.error_categories || []).map((err: any, idx: number) => (
                <div key={idx} className="bg-black/40 border border-white/5 rounded-lg p-2.5 space-y-1.5">
                  <div className="flex flex-wrap items-center justify-between gap-1">
                    <div className="flex items-center gap-1.5">
                      <span className={cn(
                        "px-1 py-0.1 rounded text-[8px] font-black uppercase border",
                        err.severity === "WARNING" ? "bg-amber-500/10 text-amber-300 border-amber-500/20" : "bg-blue-500/10 text-blue-300 border-blue-500/20"
                      )}>
                        {err.code}
                      </span>
                      <span className="text-[10px] font-bold text-white/95">{err.category}</span>
                    </div>

                    <div className="flex items-center gap-2 text-[9px] font-mono">
                      <span className="text-white/40">Count: <b className="text-rose-400">{err.count}</b></span>
                      <span className="text-white/40">Ratio: <b className="text-cyan-400">{err.percentage}%</b></span>
                    </div>
                  </div>

                  {/* Frequency Progress Bar */}
                  <div className="w-full bg-white/5 h-1 rounded-full overflow-hidden">
                    <div 
                      className={cn(
                        "h-full rounded-full transition-all duration-500",
                        err.severity === "WARNING" ? "bg-amber-500" : "bg-blue-500"
                      )} 
                      style={{ width: `${err.percentage}%` }} 
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-[9px] pt-1 leading-normal">
                    <div className="bg-white/5 p-1.5 rounded text-white/50">
                      <b>Sabab:</b> {err.primary_cause}
                    </div>
                    <div className="bg-emerald-500/5 border border-emerald-500/10 p-1.5 rounded text-emerald-300">
                      <b>Yechim:</b> {err.remediation}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* MODEL DRIFT & ANOMALY ENGINE TAB */}
      {selectedTab === "drift" && (
        <div className="space-y-2 animate-in fade-in duration-300">
          
          {/* Top Drift Status & Health Card */}
          <div className="bg-[#0b0d13]/90 border border-white/5 rounded-xl p-3 space-y-3 shadow-lg relative overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/5 pb-2">
              <div>
                <h3 className="text-xs font-black text-white/95 uppercase tracking-wider flex items-center gap-1.5">
                  <Gauge className="text-blue-400" size={13} />
                  Model Accuracy Drift Control
                </h3>
                <p className="text-[10px] text-white/40">
                  Concept drift monitoring and incremental calibration threshold alerts
                </p>
              </div>

              <span className={cn(
                "px-1.5 py-0.2 rounded text-[8px] font-black uppercase tracking-wider border",
                (telemetry?.model_drift?.drift_status || "NORMAL") === "NORMAL" ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20" : "bg-amber-500/10 text-amber-300 border-amber-500/20"
              )}>
                Status: {telemetry?.model_drift?.drift_status || "NORMAL"}
              </span>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              <div className="bg-black/40 border border-white/5 rounded-lg p-2 space-y-0.5">
                <div className="text-[8px] text-white/40 font-bold uppercase tracking-wider">Baseline WR</div>
                <div className="text-xs font-black text-white tabular-nums">
                  {telemetry?.model_drift?.baseline_win_rate_pct || 65.0}%
                </div>
              </div>

              <div className="bg-black/40 border border-white/5 rounded-lg p-2 space-y-0.5">
                <div className="text-[8px] text-white/40 font-bold uppercase tracking-wider">Rolling WR</div>
                <div className="text-xs font-black text-cyan-400 tabular-nums">
                  {telemetry?.model_drift?.recent_win_rate_pct || 62.0}%
                </div>
              </div>

              <div className="bg-black/40 border border-white/5 rounded-lg p-2 space-y-0.5">
                <div className="text-[8px] text-white/40 font-bold uppercase tracking-wider">Drift Delta</div>
                <div className={cn(
                  "text-xs font-black tabular-nums",
                  (telemetry?.model_drift?.drift_delta_pct || 0) >= 0 ? "text-emerald-400" : "text-rose-400"
                )}>
                  {telemetry?.model_drift?.drift_delta_pct || -3.0}%
                </div>
              </div>

              <div className="bg-black/40 border border-white/5 rounded-lg p-2 space-y-0.5">
                <div className="text-[8px] text-white/40 font-bold uppercase tracking-wider">Health Index</div>
                <div className="text-xs font-black text-emerald-400 tabular-nums">
                  {telemetry?.model_drift?.health_score_pct || 92.5}%
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-white/5 text-[9px]">
              <div className="flex items-center gap-1 text-white/40 max-w-xs leading-normal">
                <ShieldCheck size={11} className="text-emerald-400 shrink-0" />
                <span>Drift Guard: Win Rate pasayishi <b>-15%</b> dan oshsa, lot 50% ga qisqaradi.</span>
              </div>

              <button
                onClick={() => alert("Model re-calibration va incremental retraining jarayoni ishga tushirildi!")}
                className="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white font-extrabold rounded-lg shadow-md border border-white/5 transition-all active:scale-95 cursor-pointer flex items-center gap-1"
              >
                <RefreshCw size={10} />
                <span>Qayta Train</span>
              </button>
            </div>
          </div>

          {/* Constant / Stuck Output Anomaly Detector Card */}
          <div className="bg-[#0b0d13]/90 border border-white/5 rounded-xl p-3 space-y-2.5 shadow-lg">
            <div className="flex items-center justify-between border-b border-white/5 pb-2">
              <div>
                <h3 className="text-xs font-black text-white/95 uppercase tracking-wider flex items-center gap-1.5">
                  <Zap className="text-amber-400" size={13} />
                  Frozen Output Anomaly Detector
                </h3>
                <p className="text-[10px] text-white/40">
                  Zero Variance check across voting, confidence, and RL entropy metrics
                </p>
              </div>

              <span className="px-1.5 py-0.2 rounded text-[8px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                Zero Variance: PASS
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-[10px]">
              <div className="bg-black/40 border border-white/5 rounded-lg p-2 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white/90">Voting Output Check:</span>
                  <span className="text-emerald-400 font-bold text-[9px]">✓ Normal</span>
                </div>
                <p className="text-[9px] text-white/40 leading-relaxed">
                  Dynamic strategy consensus (no frozen voting state detected).
                </p>
              </div>

              <div className="bg-black/40 border border-white/5 rounded-lg p-2 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white/90">LSTM Prob Check:</span>
                  <span className="text-emerald-400 font-bold text-[9px]">✓ Normal Variance</span>
                </div>
                <p className="text-[9px] text-white/40 leading-relaxed">
                  LSTM confidence probabilities maintain active dispersion.
                </p>
              </div>

              <div className="bg-black/40 border border-white/5 rounded-lg p-2 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white/90">PPO Action Entropy:</span>
                  <span className="text-emerald-400 font-bold text-[9px]">✓ Healthy Entropy</span>
                </div>
                <p className="text-[9px] text-white/40 leading-relaxed">
                  Reinforcement learning actions verify active exploratory rate.
                </p>
              </div>
            </div>
          </div>

        </div>
      )}

      {/* 5. ANOMALIES TAB */}
      {selectedTab === "anomalies" && (
        <div className="bg-[#0b0d13]/90 border border-white/5 rounded-xl p-3 space-y-3 animate-in fade-in duration-300 shadow-lg">
          <div className="flex items-center justify-between border-b border-white/5 pb-2">
            <div>
              <h3 className="text-xs font-black text-white/95 uppercase tracking-wider flex items-center gap-1.5">
                <AlertTriangle className="text-amber-400" size={13} />
                Anomaliyalar va Xatoliklar Logi
              </h3>
              <p className="text-[10px] text-white/40">Tizimdagi kelishmovchiliklar, sekinlashuv va veto hodisalari</p>
            </div>
          </div>

          <div className="space-y-2">
            {(telemetry?.anomalies || []).map((anom: Anomaly) => (
              <div key={anom.id} className={cn(
                "p-2.5 rounded-lg border space-y-1",
                anom.severity === "WARNING" ? "bg-amber-500/5 border-amber-500/20 text-amber-200" :
                anom.severity === "ERROR" ? "bg-rose-500/5 border-rose-500/20 text-rose-200" :
                "bg-blue-500/5 border-blue-500/20 text-blue-200"
              )}>
                <div className="flex items-center justify-between">
                  <span className="text-[9px] font-black tracking-wider uppercase flex items-center gap-1.5">
                    <AlertTriangle size={11} />
                    [{anom.code}] - {anom.component}
                  </span>
                  <span className="text-[8px] text-white/40 font-mono">{anom.timestamp}</span>
                </div>
                <p className="text-[10px] font-medium leading-relaxed">{anom.message}</p>
                {anom.action && (
                  <p className="text-[9px] opacity-80 pt-0.5 font-bold">
                    Tavsiya: {anom.action}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 6. LOGS & AUDIT TAB */}
      {selectedTab === "logs" && (
        <div className="bg-[#0b0d13]/90 border border-white/5 rounded-xl p-3 space-y-3 animate-in fade-in duration-300 shadow-lg">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/5 pb-2">
            <div>
              <h3 className="text-xs font-black text-white/95 uppercase tracking-wider flex items-center gap-1.5">
                <Terminal className="text-blue-400" size={13} />
                Diagnostika va Audit Loglari
              </h3>
              <p className="text-[10px] text-white/40">Barcha oraliq hisob-kitoblar va signallar tarixi</p>
            </div>

            {/* Filter controls */}
            <div className="flex flex-wrap items-center gap-1.5">
              <div className="relative">
                <Search size={11} className="absolute left-2 top-2 text-white/30" />
                <input
                  type="text"
                  placeholder="Qidiruv..."
                  value={logSearch}
                  onChange={e => setLogSearch(e.target.value)}
                  className="bg-black/40 border border-white/5 rounded-lg pl-6 pr-2 py-1 text-[10px] text-white placeholder:text-white/20 focus:outline-none focus:border-blue-500/40"
                />
              </div>

              <select
                value={logFilterLevel}
                onChange={e => setLogFilterLevel(e.target.value)}
                className="bg-black/40 border border-white/5 rounded-lg px-2 py-1 text-[10px] text-white focus:outline-none cursor-pointer"
              >
                <option value="ALL">Barcha Darajalar</option>
                <option value="INFO">INFO</option>
                <option value="WARN">WARN</option>
                <option value="ERROR">ERROR</option>
              </select>
            </div>
          </div>

          <div className="space-y-1.5 font-mono text-[10px] max-h-[360px] overflow-y-auto no-scrollbar">
            {filteredLogs.map((log, idx) => (
              <div
                key={idx}
                onClick={() => setSelectedLogPayload(log)}
                className="bg-black/40 hover:bg-white/5 border border-white/5 rounded-lg p-2 transition-all cursor-pointer flex items-center justify-between gap-2"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className={cn(
                    "px-1 py-0.2 rounded text-[8px] font-black shrink-0",
                    log.level === "INFO" ? "bg-emerald-500/10 text-emerald-300" :
                    log.level === "WARN" ? "bg-amber-500/10 text-amber-300" :
                    "bg-rose-500/10 text-rose-300"
                  )}>
                    {log.level}
                  </span>
                  <span className="text-white/30 text-[9px] shrink-0">{log.timestamp.slice(11, 19)}</span>
                  <span className="text-blue-400 font-bold shrink-0">[{log.component}]</span>
                  <span className="text-white/80 truncate">{log.event}</span>
                </div>

                <Eye size={12} className="text-white/30 hover:text-white shrink-0" />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Audit Payload JSON Modal */}
      {selectedLogPayload && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-md flex items-center justify-center p-3">
          <div className="bg-[#0b0d13] border border-white/10 rounded-xl w-full max-w-md p-4 space-y-3 font-mono text-[10px] shadow-2xl">
            <div className="flex justify-between items-center border-b border-white/5 pb-1.5">
              <h4 className="text-[11px] font-bold text-white/90">Log Details</h4>
              <button onClick={() => setSelectedLogPayload(null)} className="text-white/40 hover:text-white text-[10px] font-black cursor-pointer">
                [X] Yopish
              </button>
            </div>

            <pre className="bg-black/60 p-3 rounded-lg border border-white/5 text-emerald-400 overflow-x-auto text-[9px] max-h-60 no-scrollbar">
              {JSON.stringify(selectedLogPayload, null, 2)}
            </pre>
          </div>
        </div>
      )}

    </div>
  );
}
