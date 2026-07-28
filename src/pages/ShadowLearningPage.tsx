import { useState, useRef, useEffect } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Brain, UploadCloud, BookOpen, Activity, Target, ShieldAlert, Loader2, Sparkles, CheckCircle2 } from "lucide-react";
import { cn, timeAgo } from "@/lib/utils";
import { useQuery, useQueryClient } from "@tanstack/react-query";

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

export function ShadowLearningPage() {
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
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20" />
      </div>

      <div className="w-full h-full mx-auto px-4 pt-6 relative z-10 flex flex-col gap-6">
        
        {/* Header Area */}
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500 to-emerald-700 shadow-lg shadow-emerald-500/20 flex items-center justify-center border border-emerald-400/30 shrink-0">
            <Brain className="text-white" size={28} />
          </div>
          <div>
            <h1 className="text-2xl font-black text-white tracking-tight">Shadow Learning</h1>
            <p className="text-emerald-400/80 text-sm font-medium flex items-center gap-1.5">
              <Sparkles size={14} /> AI doimiy ravishda o'rganmoqda
            </p>
          </div>
        </div>

        {/* Upload Zone */}
        <div className="w-full bg-[#10192e]/80 backdrop-blur-xl border border-white/10 rounded-[28px] p-5 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/10 blur-[50px] rounded-full pointer-events-none" />
          
          <h2 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
            <BookOpen size={18} className="text-emerald-400" />
            Baza qo'shish
          </h2>
          <p className="text-[13px] text-white/50 mb-5 leading-relaxed">
            Trading, psixologiya yoki matematika kitoblarini PDF formatida yuklang. Bot uni o'qib, yangi qoidalarni o'zlashtiradi.
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
              {books.data.map((book) => (
                <div key={book.id} className="flex items-center justify-between bg-black/40 rounded-xl p-2.5 border border-white/5">
                  <div className="flex items-center gap-3 overflow-hidden">
                    {book.status === 'done' ? (
                      <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
                    ) : (
                      <Loader2 size={16} className="text-blue-400 animate-spin shrink-0" />
                    )}
                    <span className="text-[13px] text-white/80 truncate font-medium">{book.file_name}</span>
                  </div>
                  <span className={cn(
                    "text-[10px] px-2 py-1 rounded-full font-bold uppercase shrink-0",
                    book.status === 'done' ? "bg-emerald-500/20 text-emerald-400" : "bg-blue-500/20 text-blue-400"
                  )}>
                    {book.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* AI Insights List */}
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

      </div>
    </div>
  );
}
