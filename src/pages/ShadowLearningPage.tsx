import { useState, useRef, useEffect, useMemo } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Brain, UploadCloud, BookOpen, Activity, Target, ShieldAlert, Loader2, Sparkles, CheckCircle2, Lightbulb, BarChart3, Zap } from "lucide-react";
import { cn, timeAgo } from "@/lib/utils";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Icon } from "@iconify/react";

type StrategyInsight = {
  id: string;
  insight_text: string;
  market_condition: string;
  setup_type: string;
  success_count: number;
  fail_count: number;
  created_at: string;
};

type PendingBook = {
  id: string;
  file_name: string;
  status: string;
  created_at: string;
};

type AILesson = {
  id: string;
  lesson_text: string;
  category: string;
  importance: number;
  source: string;
  success_applications: number;
  failed_applications: number;
  created_at: string;
};

type StrategyPerf = {
  id: string;
  strategy_name: string;
  wins: number;
  losses: number;
  total_profit: number;
  avg_rr: number;
  recommended_weight: number;
  updated_at: string;
};

export function ShadowLearningPage() {
  const [activeTab, setActiveTab] = useState<'overview' | 'memory'>('overview');
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const qc = useQueryClient();

  const insights = useQuery({
    queryKey: ["strategy_insights"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("strategy_insights")
        .select("*")
        .order("created_at", { ascending: false });
      if (error) {
        console.error("Error fetching insights:", error);
        return [];
      }
      return data as StrategyInsight[];
    },
    refetchInterval: 10000,
  });

  const books = useQuery({
    queryKey: ["pending_books"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("pending_books")
        .select("*")
        .order("created_at", { ascending: false })
        .limit(5);
      if (error) return [];
      return data as PendingBook[];
    },
    refetchInterval: 10000,
  });

  const isLearning = books.data?.some(book => !book.status.startsWith('done')) || false;

  // AI Memory (saboqlar)
  const lessons = useQuery({
    queryKey: ["ai_memory"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("ai_memory")
        .select("*")
        .order("importance", { ascending: false })
        .limit(10);
      if (error) return [];
      return data as AILesson[];
    },
    refetchInterval: 15000,
  });

  // Strategiya samaradorligi
  const stratPerf = useQuery({
    queryKey: ["strategy_performance"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("strategy_performance")
        .select("*")
        .order("updated_at", { ascending: false })
        .limit(7);
      if (error) return [];
      return data as StrategyPerf[];
    },
    refetchInterval: 15000,
  });

  // Trade History (o'rganish egri chizig'i uchun)
  const tradeHistory = useQuery({
    queryKey: ["trade_history_learning"],
    queryFn: async () => {
      const { data, error } = await supabase
        .from("trade_history")
        .select("ticket, symbol, profit, closed_at")
        .order("closed_at", { ascending: true });
      if (error) return [];
      return data || [];
    },
    refetchInterval: 30000,
  });

  // Learning metrics hisoblash
  const learningData = useMemo(() => {
    const trades = tradeHistory.data;
    if (!trades || trades.length < 2) return null;

    const batchSize = Math.max(5, Math.floor(trades.length / 12));
    const batches: { tradeNum: number; winRate: number }[] = [];
    
    for (let i = 0; i < trades.length; i += batchSize) {
      const batch = trades.slice(i, i + batchSize);
      const wins = batch.filter((t: any) => t.profit > 0).length;
      batches.push({
        tradeNum: i + batch.length,
        winRate: Math.round((wins / batch.length) * 100),
      });
    }

    const firstWR = batches[0]?.winRate || 0;
    const lastWR = batches[batches.length - 1]?.winRate || 0;
    const improvement = lastWR - firstWR;
    const totalWins = trades.filter((t: any) => t.profit > 0).length;
    const overallWR = Math.round((totalWins / trades.length) * 100);

    return { batches, totalTrades: trades.length, firstWR, lastWR, improvement, overallWR };
  }, [tradeHistory.data]);

  // Neural Network nodes/edges hisoblash
  const networkData = useMemo(() => {
    const insightCount = insights.data?.length || 0;
    const lessonCount = lessons.data?.length || 0;
    const knowledge = insightCount + lessonCount;

    // Layer sizes: input, hidden1, hidden2, output
    const layers = [
      Math.min(6, 3 + Math.floor(knowledge / 10)),    // Input
      Math.min(10, 3 + Math.floor(knowledge / 5)),     // Hidden 1
      Math.min(8, 2 + Math.floor(knowledge / 7)),      // Hidden 2
      3                                                 // Output (BUY/SELL/HOLD)
    ];

    const nodes: { x: number; y: number; layer: number }[] = [];
    const svgW = 320;
    const svgH = 140;
    const layerSpacing = svgW / (layers.length + 1);

    layers.forEach((count, li) => {
      const x = layerSpacing * (li + 1);
      const spacing = svgH / (count + 1);
      for (let ni = 0; ni < count; ni++) {
        nodes.push({ x, y: spacing * (ni + 1), layer: li });
      }
    });

    // Connections between adjacent layers
    const edges: { from: number; to: number; strength: number }[] = [];
    let nodeIdx = 0;
    for (let li = 0; li < layers.length - 1; li++) {
      const nextStart = nodeIdx + layers[li];
      for (let a = nodeIdx; a < nextStart; a++) {
        for (let b = nextStart; b < nextStart + layers[li + 1]; b++) {
          // Show more connections as knowledge grows
          const seed = (a * 31 + b * 17 + li * 7) % 100;
          const showProb = Math.min(1, 0.3 + knowledge * 0.03);
          if (seed / 100 < showProb) {
            edges.push({ from: a, to: b, strength: Math.min(1, 0.2 + knowledge * 0.04) });
          }
        }
      }
      nodeIdx = nextStart;
    }

    return { nodes, edges, layers, knowledge };
  }, [insights.data, lessons.data]);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadProgress(10);
    
    try {
      const fileExt = file.name.split(".").pop();
      const fileName = `${Math.random().toString(36).substring(2, 15)}_${Date.now()}.${fileExt}`;
      const filePath = `${fileName}`;

      // Upload to Storage
      const { error: uploadError } = await supabase.storage
        .from("shadow_knowledge")
        .upload(filePath, file, {
          cacheControl: "3600",
          upsert: false,
        });

      if (uploadError) throw uploadError;
      setUploadProgress(70);

      // Get public URL
      const { data: { publicUrl } } = supabase.storage
        .from("shadow_knowledge")
        .getPublicUrl(filePath);

      // Insert into pending_books
      const { error: dbError } = await supabase.from("pending_books").insert({
        file_name: file.name,
        file_url: publicUrl,
        status: "pending"
      });

      if (dbError) throw dbError;
      setUploadProgress(100);
      
      qc.invalidateQueries({ queryKey: ["pending_books"] });

    } catch (error: any) {
      console.error("Upload error:", error.message);
      alert("Yuklashda xatolik yuz berdi: " + error.message);
    } finally {
      setTimeout(() => {
        setUploading(false);
        setUploadProgress(0);
        if (fileInputRef.current) fileInputRef.current.value = "";
      }, 1000);
    }
  };

  return (
    <div className="flex flex-col min-h-full w-full font-sans bg-[#0a0f1c] pb-20 relative">
      {/* Dynamic Background */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-emerald-600/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-600/10 rounded-full blur-[120px]" />
        <div className="absolute inset-0 bg-[url('/noise.svg')] opacity-20" />
      </div>

      <div className="w-full h-full mx-auto px-3 sm:px-4 pt-4 sm:pt-6 relative z-10 flex flex-col gap-4 sm:gap-6">
        
        {/* Header Area */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className={cn(
                "w-12 h-12 rounded-[16px] flex items-center justify-center border shrink-0 transition-all duration-500",
                isLearning 
                  ? "bg-blue-500/10 border-blue-400/20 shadow-[0_0_15px_rgba(59,130,246,0.15)] animate-pulse" 
                  : "bg-emerald-500/10 border-emerald-400/20 shadow-[0_0_15px_rgba(16,185,129,0.1)]"
              )}>
                <Brain className={isLearning ? "text-blue-400" : "text-emerald-400"} size={24} />
              </div>
              <div>
                <h1 className="text-xl font-bold text-white tracking-tight">Shadow AI</h1>
                <p className={cn(
                  "text-xs font-medium flex items-center gap-1.5 transition-colors duration-500",
                  isLearning ? "text-blue-400" : "text-white/40"
                )}>
                  {isLearning ? (
                    <><Loader2 size={12} className="animate-spin" /> Tahlil qilinmoqda...</>
                  ) : (
                    <><Sparkles size={12} className="text-emerald-400/70" /> Faol o'rganish</>
                  )}
                </p>
              </div>
            </div>
            
            <button 
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="px-4 h-11 rounded-[14px] bg-gradient-to-r from-emerald-500 to-teal-400 hover:from-emerald-400 hover:to-teal-300 text-[#070b13] flex items-center justify-center gap-2 shadow-[0_0_20px_rgba(16,185,129,0.35)] hover:shadow-[0_0_30px_rgba(16,185,129,0.55)] active:scale-95 transition-all duration-300 shrink-0 border border-emerald-300/30 group"
              title="Fayl yuklash"
            >
              {uploading ? (
                <Loader2 size={20} className="animate-spin text-[#070b13]" />
              ) : (
                <>
                  <Icon icon="pixel:machine-learning" className="w-[20px] h-[20px] transition-transform group-hover:scale-110" />
                  <Icon icon="mage:file-upload-fill" className="w-[20px] h-[20px] transition-transform group-hover:scale-110" />
                </>
              )}
            </button>
          </div>
          
          <div className="flex items-center gap-1 min-[360px]:gap-1.5 bg-white/5 p-1 rounded-xl border border-white/10 overflow-x-auto no-scrollbar w-fit">
            <button 
              onClick={() => setActiveTab('overview')}
              className={cn("px-3 py-1.5 min-[360px]:px-4 min-[360px]:py-2 rounded-lg text-[11px] min-[360px]:text-xs font-bold transition-all whitespace-nowrap uppercase tracking-wider", activeTab === 'overview' ? "bg-white/10 text-white" : "text-white/40 hover:text-white/70")}
            >
              Asosiy
            </button>
            <button 
              onClick={() => setActiveTab('memory')}
              className={cn("px-3 py-1.5 min-[360px]:px-4 min-[360px]:py-2 rounded-lg text-[11px] min-[360px]:text-xs font-bold transition-all whitespace-nowrap uppercase tracking-wider", activeTab === 'memory' ? "bg-white/10 text-white" : "text-white/40 hover:text-white/70")}
            >
              Xotira
            </button>
          </div>
        </div>

        {/* === AI O'RGANISH JARAYONI VIZUALIZATSIYASI === */}
        {activeTab === 'overview' && (
        <div className="w-full bg-[#10192e]/40 backdrop-blur-xl border border-white/5 rounded-[24px] p-4 relative overflow-hidden">
          <div className="absolute top-0 left-0 w-40 h-40 bg-violet-500/10 blur-[60px] rounded-full pointer-events-none" />
          <div className="absolute bottom-0 right-0 w-32 h-32 bg-emerald-500/10 blur-[50px] rounded-full pointer-events-none" />
          
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Brain size={18} className="text-violet-400" />
              AI O'rganish Jarayoni
            </h2>
            {learningData && (
              <div className="bg-violet-500/20 px-2 py-0.5 min-[360px]:px-3 min-[360px]:py-1 rounded-full">
                <span className="text-violet-300 text-[10px] min-[360px]:text-[12px] font-black tracking-wider">
                  SAVDO #{learningData.totalTrades}
                </span>
              </div>
            )}
          </div>

          {/* Neural Network Vizualizatsiyasi */}
          <div className="relative mb-4">
            <div className="text-[9px] text-white/30 text-center font-bold uppercase tracking-[3px] mb-2">
              {networkData.knowledge === 0 ? "TARMOQ HALI BO'SH" : 
               networkData.knowledge < 5 ? "BOSHLANG'ICH TARMOQ" :
               networkData.knowledge < 15 ? "O'RGANISH DAVOM ETMOQDA" :
               networkData.knowledge < 30 ? "TARMOQ KUCHAYMOQDA" : "KUCHLI TARMOQ"}
            </div>
            <svg width="100%" viewBox="0 0 320 140" className="rounded-xl overflow-hidden">
              <defs>
                <linearGradient id="nnEdgeGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.6" />
                  <stop offset="100%" stopColor="#10b981" stopOpacity="0.6" />
                </linearGradient>
              </defs>
              {/* Edges */}
              {networkData.edges.map((edge, i) => {
                const fromN = networkData.nodes[edge.from];
                const toN = networkData.nodes[edge.to];
                if (!fromN || !toN) return null;
                return (
                  <line
                    key={`e-${i}`}
                    x1={fromN.x} y1={fromN.y}
                    x2={toN.x} y2={toN.y}
                    stroke="url(#nnEdgeGrad)"
                    strokeWidth={0.5 + edge.strength}
                    opacity={0.15 + edge.strength * 0.5}
                    className="animate-pulse"
                    style={{ animationDelay: `${(i % 7) * 0.3}s`, animationDuration: `${2 + (i % 3)}s` }}
                  />
                );
              })}
              {/* Nodes */}
              {networkData.nodes.map((node, i) => {
                const colors = ['#8b5cf6', '#6366f1', '#3b82f6', '#10b981'];
                const color = colors[node.layer] || '#8b5cf6';
                return (
                  <g key={`n-${i}`}>
                    <circle
                      cx={node.x} cy={node.y}
                      r={3.5}
                      fill={color}
                      opacity={0.9}
                      className="animate-pulse"
                      style={{ animationDelay: `${(i % 5) * 0.4}s`, animationDuration: `${2 + (i % 4)}s` }}
                    />
                    <circle cx={node.x} cy={node.y} r={6} fill={color} opacity={0.15} />
                  </g>
                );
              })}
              {/* Layer labels */}
              <text x="65" y="136" fill="white" opacity="0.25" fontSize="7" textAnchor="middle" fontWeight="bold">BOZOR</text>
              <text x="255" y="136" fill="white" opacity="0.25" fontSize="7" textAnchor="middle" fontWeight="bold">QAROR</text>
            </svg>
          </div>

          {/* Learning Curve */}
          {learningData && learningData.batches.length >= 2 && (
            <div className="mb-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] text-white/40 font-bold uppercase">Win Rate egri chizig'i</span>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-white/40">{learningData.firstWR}%</span>
                  <span className="text-[11px] text-white/30">{"\u2192"}</span>
                  <span className={cn(
                    "text-[12px] font-black",
                    learningData.improvement > 0 ? "text-emerald-400" : learningData.improvement < 0 ? "text-rose-400" : "text-white/60"
                  )}>
                    {learningData.lastWR}%
                  </span>
                </div>
              </div>
              <svg width="100%" viewBox="0 0 300 60" className="rounded-lg overflow-hidden">
                <defs>
                  <linearGradient id="curveGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#8b5cf6" />
                    <stop offset="100%" stopColor="#10b981" />
                  </linearGradient>
                </defs>
                {[0, 25, 50, 75, 100].map(v => (
                  <line key={v} x1="0" y1={60 - v * 0.55} x2="300" y2={60 - v * 0.55} stroke="white" opacity="0.05" strokeDasharray="2,4" />
                ))}
                <polyline
                  fill="none"
                  stroke="url(#curveGrad)"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  points={learningData.batches.map((b, i) => {
                    const x = (i / (learningData.batches.length - 1)) * 290 + 5;
                    const y = 55 - (b.winRate / 100) * 50;
                    return `${x},${y}`;
                  }).join(' ')}
                />
                <polygon
                  fill="url(#curveGrad)"
                  opacity="0.1"
                  points={
                    learningData.batches.map((b, i) => {
                      const x = (i / (learningData.batches.length - 1)) * 290 + 5;
                      const y = 55 - (b.winRate / 100) * 50;
                      return `${x},${y}`;
                    }).join(' ') + ' 295,58 5,58'
                  }
                />
                {learningData.batches.map((b, i) => {
                  const x = (i / (learningData.batches.length - 1)) * 290 + 5;
                  const y = 55 - (b.winRate / 100) * 50;
                  return <circle key={i} cx={x} cy={y} r="2.5" fill="#8b5cf6" opacity="0.8" />;
                })}
              </svg>
            </div>
          )}

          {/* Stats Row */}
          <div className="grid grid-cols-4 gap-1 min-[360px]:gap-2">
            <div className="bg-black/30 rounded-xl p-1.5 min-[360px]:p-2.5 text-center border border-white/5">
              <div className="text-[9px] min-[360px]:text-[10px] text-white/40 font-bold uppercase mb-1">Savdolar</div>
              <div className="text-white font-black text-sm min-[360px]:text-lg">{learningData?.totalTrades || 0}</div>
            </div>
            <div className="bg-black/30 rounded-xl p-1.5 min-[360px]:p-2.5 text-center border border-white/5">
              <div className="text-[9px] min-[360px]:text-[10px] text-white/40 font-bold uppercase mb-1">Win Rate</div>
              <div className="text-emerald-400 font-black text-sm min-[360px]:text-lg">{learningData?.overallWR || 0}%</div>
            </div>
            <div className="bg-black/30 rounded-xl p-1.5 min-[360px]:p-2.5 text-center border border-white/5">
              <div className="text-[9px] min-[360px]:text-[10px] text-white/40 font-bold uppercase mb-1">Bilimlar</div>
              <div className="text-violet-400 font-black text-sm min-[360px]:text-lg">{networkData.knowledge}</div>
            </div>
            <div className="bg-black/30 rounded-xl p-1.5 min-[360px]:p-2.5 text-center border border-white/5">
              <div className="text-[9px] min-[360px]:text-[10px] text-white/40 font-bold uppercase mb-1">O'sish</div>
              <div className={cn(
                "font-black text-sm min-[360px]:text-lg",
                (learningData?.improvement || 0) > 0 ? "text-emerald-400" : 
                (learningData?.improvement || 0) < 0 ? "text-rose-400" : "text-white/50"
              )}>
                {(learningData?.improvement || 0) > 0 ? "+" : ""}{learningData?.improvement || 0}%
              </div>
            </div>
          </div>

          {/* Learning tagline */}
          <div className="mt-3 text-center">
            <p className="text-[10px] text-violet-400/60 font-bold uppercase tracking-[4px]">
              Learning from every trade
            </p>
          </div>
        </div>
        )}

        {/* Upload Zone */}
        {activeTab === 'overview' && (
        <div className="w-full bg-[#10192e]/40 backdrop-blur-xl border border-white/5 rounded-[24px] p-4 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/10 blur-[50px] rounded-full pointer-events-none" />
          
          <h2 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
            <BookOpen size={18} className="text-emerald-400" />
            Baza qo'shish
          </h2>
          <p className="text-[13px] text-white/50 mb-5 leading-relaxed">
            Trading, psixologiya yoki matematika kitoblarini turli formatlarda (PDF, TXT, DOCX) yuklang. Bot uni o'qib, yangi qoidalarni o'zlashtiradi.
          </p>

          <input 
            type="file" 
            accept=".pdf,.txt,.docx" 
            className="hidden" 
            ref={fileInputRef}
            onChange={handleUpload}
            disabled={uploading}
          />
          
          <button 
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className={cn(
              "w-full h-24 rounded-2xl border-2 border-dashed border-white/20 flex flex-col items-center justify-center gap-2 transition-all group",
              uploading ? "bg-white/5" : "hover:bg-white/5 hover:border-emerald-400/50 cursor-pointer"
            )}
          >
            {uploading ? (
              <>
                <Loader2 size={28} className="text-emerald-400 animate-spin" />
                <span className="text-sm font-bold text-white/80">{uploadProgress}% Yuklanmoqda...</span>
              </>
            ) : (
              <>
                <div className="w-10 h-10 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400 group-hover:scale-110 transition-transform">
                  <UploadCloud size={20} />
                </div>
                <span className="text-xs font-bold text-white/60 group-hover:text-white/90">Faylni tanlang yoki shu yerga tashlang</span>
              </>
            )}
          </button>

          {/* Pending Books Status */}
          {books.data && books.data.length > 0 && (
            <div className="mt-4 space-y-2">
              <h3 className="text-[11px] font-bold text-white/40 uppercase tracking-widest mb-2">Jarayondagi fayllar</h3>
              {books.data.map((book) => {
                const isDone = book.status.startsWith('done');
                let statusText = isDone ? "O'zlashtirildi" : "O'rganilmoqda";
                let detailText = null;
                
                if (book.status.startsWith('done|')) {
                  const parts = book.status.split('|');
                  if (parts.length === 3) {
                    statusText = `✅ ${parts[1]} TA QOIDA TOPILDI`;
                    detailText = `AI jami ${parts[2]} ta qismni o'qib tahlil qildi. Topilgan foydali qoidalar pastdagi ro'yxatga qo'shildi.`;
                  }
                }

                return (
                  <div key={book.id} className="flex flex-col bg-black/40 rounded-xl p-3 border border-white/5 group transition-colors hover:bg-black/60">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 overflow-hidden">
                        {isDone ? (
                          <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
                        ) : (
                          <Loader2 size={16} className="text-blue-400 animate-spin shrink-0" />
                        )}
                        <span className="text-[13px] text-white/80 truncate font-medium">{book.file_name}</span>
                      </div>
                      <span className={cn(
                        "text-[10px] px-2 py-1 rounded-full font-bold uppercase shrink-0",
                        isDone ? "bg-emerald-500/20 text-emerald-400" : "bg-blue-500/20 text-blue-400 animate-pulse"
                      )}>
                        {statusText}
                      </span>
                    </div>
                    {detailText && (
                      <div className="mt-2.5 text-[11px] text-emerald-400/80 bg-emerald-500/5 p-2 rounded-lg border border-emerald-500/10 leading-relaxed">
                        {detailText}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
        )}

        {/* AI Insights List */}
        {activeTab === 'memory' && (
        <div className="flex flex-col gap-6">
        <div>
          <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2 px-1">
            <Activity size={20} className="text-blue-400" />
            AI Xulosalari (Fikrlari)
          </h2>
          
          <div className="space-y-4">
            {insights.isLoading ? (
              Array.from({length: 3}).map((_, i) => (
                <div key={i} className="w-full h-32 bg-[#10192e]/50 rounded-[24px] border border-white/5 animate-pulse" />
              ))
            ) : insights.data && insights.data.length > 0 ? (
              insights.data.map((insight) => (
                <div key={insight.id} className="w-full bg-[#10192e]/60 backdrop-blur-md border border-white/10 rounded-[24px] p-5 shadow-lg relative overflow-hidden group hover:bg-[#10192e]/80 transition-colors">
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-blue-500 to-emerald-500" />
                  
                  <div className="flex justify-between items-start mb-3">
                    <div className="flex items-center gap-2">
                      <span className="bg-blue-500/20 text-blue-400 text-[10px] px-2 py-1 rounded-lg font-bold uppercase tracking-wider flex items-center gap-1">
                        <Target size={12} /> {insight.setup_type}
                      </span>
                      <span className="bg-emerald-500/20 text-emerald-400 text-[10px] px-2 py-1 rounded-lg font-bold uppercase tracking-wider flex items-center gap-1">
                        <ShieldAlert size={12} /> {insight.market_condition}
                      </span>
                    </div>
                    <span className="text-[10px] text-white/40">{timeAgo(insight.created_at)}</span>
                  </div>
                  
                  <p className="text-sm text-white/90 leading-relaxed font-medium mb-4">
                    "{insight.insight_text}"
                  </p>
                  
                  <div className="flex items-center gap-4 border-t border-white/10 pt-3">
                    <div className="flex flex-col">
                      <span className="text-[10px] text-white/40 font-bold uppercase">Ish berdi (Win)</span>
                      <span className="text-emerald-400 font-black text-sm">{insight.success_count} marta</span>
                    </div>
                    <div className="w-[1px] h-6 bg-white/10" />
                    <div className="flex flex-col">
                      <span className="text-[10px] text-white/40 font-bold uppercase">Xato qildi (Loss)</span>
                      <span className="text-rose-400 font-black text-sm">{insight.fail_count} marta</span>
                    </div>
                    
                    {/* Win Rate Bar */}
                    <div className="flex-1 flex flex-col ml-2 justify-center">
                      <div className="flex justify-between text-[9px] font-bold text-white/50 mb-1">
                        <span>Win Rate</span>
                        <span>
                          {insight.success_count + insight.fail_count > 0 
                            ? Math.round((insight.success_count / (insight.success_count + insight.fail_count)) * 100) 
                            : 0}%
                        </span>
                      </div>
                      <div className="w-full h-1.5 bg-black/50 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-emerald-500 rounded-full" 
                          style={{ 
                            width: `${insight.success_count + insight.fail_count > 0 ? (insight.success_count / (insight.success_count + insight.fail_count)) * 100 : 0}%` 
                          }} 
                        />
                      </div>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="w-full bg-[#10192e]/40 border border-white/5 rounded-[24px] p-8 text-center flex flex-col items-center justify-center gap-3">
                <Brain size={32} className="text-white/20" />
                <p className="text-sm text-white/50">Hozircha AI qoidalari yo'q.<br/>Birinchi kitobingizni yuklang!</p>
              </div>
            )}
          </div>
        </div>

        {/* AI Memory (Saboqlar) */}
        <div>
          <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2 px-1">
            <Lightbulb size={20} className="text-amber-400" />
            AI Xotirasi (Saboqlar)
          </h2>

          <div className="space-y-3">
            {lessons.data && lessons.data.length > 0 ? (
              lessons.data.map((lesson) => {
                const categoryEmoji: Record<string, string> = {
                  trade_pattern: "📊", risk_management: "🛡️",
                  market_regime: "🌊", strategy_effectiveness: "⚡",
                  book_knowledge: "📚"
                };
                const total = lesson.success_applications + lesson.failed_applications;
                const winRate = total > 0 ? Math.round((lesson.success_applications / total) * 100) : null;

                return (
                  <div key={lesson.id} className="w-full bg-[#10192e]/60 backdrop-blur-md border border-white/10 rounded-2xl p-4 shadow-lg relative overflow-hidden">
                    <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-amber-500 to-orange-500" />
                    <div className="flex items-start justify-between gap-3 mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{categoryEmoji[lesson.category] || "💡"}</span>
                        <span className="bg-amber-500/20 text-amber-400 text-[10px] px-2 py-0.5 rounded-lg font-bold uppercase">
                          {lesson.category.replace('_', ' ')}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        {Array.from({ length: Math.min(lesson.importance, 5) }).map((_, i) => (
                          <div key={i} className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                        ))}
                        <span className="text-[10px] text-white/30 font-bold">{lesson.importance}/10</span>
                      </div>
                    </div>
                    <p className="text-sm text-white/85 leading-relaxed pl-1">
                      {lesson.lesson_text}
                    </p>
                    {winRate !== null && (
                      <div className="mt-2 flex items-center gap-2 text-[11px]">
                        <span className="text-white/40">Qo'llanildi: {total} marta</span>
                        <span className={winRate >= 60 ? "text-emerald-400" : winRate >= 40 ? "text-amber-400" : "text-rose-400"}>
                          {winRate}% samarali
                        </span>
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <div className="w-full bg-[#10192e]/40 border border-white/5 rounded-2xl p-6 text-center flex flex-col items-center justify-center gap-2">
                <Lightbulb size={28} className="text-white/20" />
                <p className="text-sm text-white/50">Hali saboqlar yo'q.<br/>Savdolar va kitoblardan AI o'rganib boradi.</p>
              </div>
            )}
          </div>
        </div>
        </div>
        )}

        {/* Strategiya Samaradorligi */}
        {activeTab === 'overview' && stratPerf.data && stratPerf.data.length > 0 && (
          <div className="mt-2">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2 px-1">
              <BarChart3 size={20} className="text-violet-400" />
              Strategiya Samaradorligi
            </h2>
            <div className="grid grid-cols-2 gap-3">
              {stratPerf.data.map((sp) => {
                const total = sp.wins + sp.losses;
                const wr = total > 0 ? Math.round((sp.wins / total) * 100) : 0;
                const weightColor = sp.recommended_weight >= 1.2 ? "text-emerald-400" : sp.recommended_weight <= 0.7 ? "text-rose-400" : "text-white/70";
                return (
                  <div key={sp.id} className="bg-[#10192e]/60 border border-white/10 rounded-2xl p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[12px] font-bold text-white/90 uppercase">{sp.strategy_name}</span>
                      <span className={cn("text-[11px] font-bold", weightColor)}>
                        <Zap size={10} className="inline mr-0.5" />{sp.recommended_weight.toFixed(1)}x
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-[11px] mb-1.5">
                      <span className="text-emerald-400">{sp.wins}W</span>
                      <span className="text-white/20">/</span>
                      <span className="text-rose-400">{sp.losses}L</span>
                      <span className="text-white/40">({wr}%)</span>
                    </div>
                    <div className="w-full h-1 bg-black/50 rounded-full overflow-hidden">
                      <div className="h-full bg-violet-500 rounded-full" style={{ width: `${wr}%` }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
