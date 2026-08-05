import { useEffect, useState, useRef } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { guestMock } from "@/lib/guestMock";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Loader2, Save, Sparkles, Settings2, Sliders, Play, Code, X, Check, ListPlus, Pencil, TriangleAlert, FlaskConical } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import type { BotSettings, BotStatus } from "@/lib/types";
import { CustomSelect } from "@/components/ui/CustomSelect";
import { BacktestPage } from "./BacktestPage";
import { EmptyLine } from "./DashboardPage";
import pubgLoader from "@/assets/pubg-loader.svg";

const MAJOR_TIMEFRAME_OPTIONS = [
  { value: "D1", label: "D1 (1 kun)" },
  { value: "H4", label: "H4 (4 soat)" },
  { value: "H1", label: "H1 (1 soat)" },
  { value: "M30", label: "M30 (30 daqiqa)" },
  { value: "M15", label: "M15 (15 daqiqa)" },
];

const MINOR_TIMEFRAME_OPTIONS = [
  { value: "H4", label: "H4 (4 soat)" },
  { value: "H1", label: "H1 (1 soat)" },
  { value: "M30", label: "M30 (30 daqiqa)" },
  { value: "M15", label: "M15 (15 daqiqa)" },
  { value: "M5", label: "M5 (5 daqiqa)" },
  { value: "M1", label: "M1 (1 daqiqa)" },
];

const AI_MODEL_OPTIONS = [
  { value: "auto", label: "Avtomatik (Smart AI Tanlash)" },
  
  // Eskilari (Direct API)
  { value: "claude-sonnet-5", label: "01. Claude Sonnet 3.5 (Direct API) - $3.00 / $15.00" },
  { value: "kimi-k3", label: "02. Kimi K3 (Direct API) - $0.06 / $0.06" },
  { value: "claude-haiku-4-5", label: "03. Claude Haiku 3.5 (Direct API) - $0.80 / $4.00" },

  // OpenRouter - Top Tier (Eng kuchli modellar)
  { value: "openrouter/openai/o1-preview", label: "04. OpenAI o1 Preview - $15.00 / $60.00" },
  { value: "openrouter/anthropic/claude-3.5-sonnet", label: "05. Claude 3.5 Sonnet - $3.00 / $15.00" },
  { value: "openrouter/openai/gpt-4o", label: "06. GPT-4o - $5.00 / $15.00" },
  { value: "openrouter/anthropic/claude-3-opus", label: "07. Claude 3 Opus - $15.00 / $75.00" },
  { value: "openrouter/google/gemini-1.5-pro", label: "08. Gemini 1.5 Pro - $3.50 / $10.50" },
  { value: "openrouter/meta-llama/llama-3.1-405b-instruct", label: "09. Llama 3.1 (405B) - $3.00 / $3.00" },
  { value: "openrouter/openai/gpt-4-turbo", label: "10. GPT-4 Turbo - $10.00 / $30.00" },
  
  // OpenRouter - High Tier (Tez va aqlli modellar)
  { value: "openrouter/mistralai/mistral-large-2407", label: "11. Mistral Large 2 - $2.00 / $6.00" },
  { value: "openrouter/x-ai/grok-2-1212", label: "12. Grok 2 - $2.00 / $10.00" },
  { value: "openrouter/cohere/command-r-plus", label: "13. Cohere Command R+ - $3.00 / $15.00" },
  { value: "openrouter/openai/o1-mini", label: "14. OpenAI o1 Mini - $3.00 / $12.00" },
  { value: "openrouter/nvidia/nemotron-4-340b-instruct", label: "15. Nemotron-4 340B - $4.00 / $4.00" },
  { value: "openrouter/nousresearch/hermes-3-llama-3.1-405b", label: "16. Hermes 3 (405B) - $3.00 / $3.00" },

  // OpenRouter - Mid Tier (Arzon va tez modellar)
  { value: "openrouter/qwen/qwen-2.5-72b-instruct", label: "17. Qwen 2.5 (72B) - $0.35 / $0.40" },
  { value: "openrouter/meta-llama/llama-3.2-90b-vision-instruct", label: "18. Llama 3.2 (90B Vision) - $0.80 / $0.80" },
  { value: "openrouter/meta-llama/llama-3.1-70b-instruct", label: "19. Llama 3.1 (70B) - $0.60 / $0.60" },
  { value: "openrouter/deepseek/deepseek-chat", label: "20. DeepSeek V3 - $0.14 / $0.28" },
  { value: "openrouter/deepseek/deepseek-coder", label: "21. DeepSeek Coder - $0.14 / $0.28" },
  { value: "openrouter/mistralai/mixtral-8x22b-instruct", label: "22. Mixtral 8x22B - $0.90 / $0.90" },
  { value: "openrouter/microsoft/wizardlm-2-8x22b", label: "23. WizardLM-2 8x22B - $0.50 / $0.50" },

  // OpenRouter - Fast & Cheap Tier (Juda arzon va tezkor)
  { value: "openrouter/anthropic/claude-3.5-haiku", label: "24. Claude 3.5 Haiku - $0.80 / $4.00" },
  { value: "openrouter/openai/gpt-4o-mini", label: "25. GPT-4o Mini - $0.15 / $0.60" },
  { value: "openrouter/qwen/qwen-2.5-coder-32b-instruct", label: "26. Qwen 2.5 Coder (32B) - $0.15 / $0.15" },
  
  // OpenRouter - Free / Almost Free Tier (Tekin yoki juda arzon)
  { value: "openrouter/google/gemini-1.5-flash", label: "27. Gemini 1.5 Flash - $0.07 / $0.30" },
  { value: "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free", label: "28. Nemotron 3 Ultra (550B) - $0.00 / $0.00" },
  { value: "openrouter/poolside/laguna-m.1:free", label: "29. Laguna M.1 (Kodlash) - $0.00 / $0.00" },
  { value: "openrouter/cohere/north-mini-code:free", label: "30. North Mini Code - $0.00 / $0.00" },
  { value: "openrouter/poolside/laguna-xs-2.1:free", label: "31. Laguna XS 2.1 - $0.00 / $0.00" },
  { value: "openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", label: "32. Nemotron Nano Omni - $0.00 / $0.00" },
];

const ASSET_CATEGORIES: Record<string, string[]> = {
  Forex: ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "EURJPY", "GBPJPY", "EURCHF", "EURAUD"],
  Crypto: ["BTCUSD", "ETHUSD", "XRPUSD", "SOLUSD", "ADAUSD", "DOGEUSD", "BNBUSD", "LTCUSD", "LINKUSD"],
  Indices: ["US30", "SPX500", "NAS100", "GER40", "UK100", "JPN225"],
  Metals: ["XAUUSD", "XAGUSD"],
  Stock: ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "NFLX", "NVDA"],
};

export function SettingsPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const isGuest = user?.id === "guest";
  
  const { data, isLoading } = useQuery({
    queryKey: ["bot_settings", user?.id],
    queryFn: async () => {
      if (isGuest) {
        return guestMock.getSettings();
      }
      const { data } = await supabase.from("bot_settings").select("*").maybeSingle();
      return data as BotSettings | null;
    },
  });

  const statusQuery = useQuery({
    queryKey: ["bot_status_settings", user?.id],
    queryFn: async () => {
      if (isGuest) {
        return guestMock.getBotStatus();
      }
      const { data } = await supabase.from("bot_status").select("*").maybeSingle();
      return data as BotStatus | null;
    },
  });

  const [form, setForm] = useState<Partial<BotSettings>>({});
  const [initialForm, setInitialForm] = useState<Partial<BotSettings> | null>(null);
  const [claudeLimit, setClaudeLimit] = useState<number>(20.0);
  const [initialClaudeLimit, setInitialClaudeLimit] = useState<number>(20.0);
  const [claudeUsed, setClaudeUsed] = useState<number>(0.0);
  const [initialClaudeUsed, setInitialClaudeUsed] = useState<number>(0.0);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  const dynamicCategories = statusQuery.data?.available_symbols && Object.keys(statusQuery.data.available_symbols).length > 0 
    ? statusQuery.data.available_symbols 
    : ASSET_CATEGORIES;

  // Symbol Modal State
  const [isSymbolModalOpen, setIsSymbolModalOpen] = useState(false);
  const [activeCategory, setActiveCategory] = useState("Forex");
  const [toastMsg, setToastMsg] = useState("");

  const toggleSymbol = (sym: string) => {
    setForm((f) => {
      const current = f.symbols || [];
      if (current.includes(sym)) {
        return { ...f, symbols: current.filter(s => s !== sym) };
      } else {
        return { ...f, symbols: [...current, sym] };
      }
    });
  };

  useEffect(() => {
    if (data) {
      setForm(data);
      setInitialForm(data);
    } else {
      const defaults = {
        symbols: ["EURUSD", "GBPUSD", "XAUUSD"],
        risk_per_trade: 0.02,
        max_daily_loss: 0.10,
        min_confidence: 50,
        max_lot_size: 5.0,
        timeframe_major: "H1",
        timeframe_minor: "M5",
        loop_interval_minutes: 5,
        realtime_enabled: false,
        loop_interval_seconds: 15,
        ai_enabled: true,
        ai_model: "kimi-k3",
        shadow_mode: true,
        prompt_identity: "Sen professional Forex treyderi va fundamental tahlilchisisan.",
        prompt_strategy: "SMC, Garmonik patternlar va Iqtisodiy yangiliklarni birlashtirib eng yaxshi nuqtadan savdoga kirish qarorini qabul qilgin.",
        prompt_output: 'JAVOBNI FAQAT quyidagi JSON formatida qaytar, boshqa hech qanday izoh yoki tushuntirish yozma. Format: {"signal": "BUY" | "SELL" | "HOLD", "confidence": 0-100, "reasoning": "...", "stop_loss_pips": 20, "take_profit_pips": 40}',
        risk_level_single_confirmation: 0.01,
        risk_level_multiple_confirmation: 0.02,
        strategy_weight_smc: 60,
        strategy_weight_pattern: 60,
        strategy_weight_news: 60
      };
      setForm(defaults);
      setInitialForm(defaults);
    }
  }, [data]);

  useEffect(() => {
    if (statusQuery.data) {
      setClaudeLimit(Number(statusQuery.data.claude_limit ?? 20.0));
      setClaudeUsed(Number(statusQuery.data.claude_used ?? 0.0));
      setInitialClaudeLimit(Number(statusQuery.data.claude_limit ?? 20.0));
      setInitialClaudeUsed(Number(statusQuery.data.claude_used ?? 0.0));
    }
  }, [statusQuery.data]);

  async function save() {
    if (!user) return;
    setBusy(true); setSaved(false);
    
    // Save Settings & status
    if (isGuest) {
      guestMock.saveSettings({
        symbols: form.symbols ?? ["EURUSD"],
        risk_per_trade: Number(form.risk_per_trade ?? 0.02),
        max_daily_loss: Number(form.max_daily_loss ?? 0.10),
        min_confidence: Number(form.min_confidence ?? 50),
        max_lot_size: Number(form.max_lot_size ?? 5.0),
        timeframe_major: form.timeframe_major ?? "H1",
        timeframe_minor: form.timeframe_minor ?? "M5",
        loop_interval_minutes: Number(form.loop_interval_minutes ?? 5),
        realtime_enabled: form.realtime_enabled ?? false,
        loop_interval_seconds: Number(form.loop_interval_seconds ?? 15),
        ai_enabled: form.ai_enabled ?? true,
        shadow_mode: form.shadow_mode ?? true,
        ai_model: form.ai_model ?? "auto",
        prompt_identity: form.prompt_identity ?? "",
        prompt_strategy: form.prompt_strategy ?? "",
        prompt_output: form.prompt_output ?? "",
        risk_level_single_confirmation: Number(form.risk_level_single_confirmation ?? 0.01),
        risk_level_multiple_confirmation: Number(form.risk_level_multiple_confirmation ?? 0.02),
        strategy_weight_smc: Number(form.strategy_weight_smc ?? 60),
        strategy_weight_pattern: Number(form.strategy_weight_pattern ?? 60),
        strategy_weight_news: Number(form.strategy_weight_news ?? 60)
      });

      guestMock.saveBotStatus({
        claude_limit: Number(claudeLimit),
        claude_used: Number(claudeUsed)
      });
    } else {
      const payload = {
        user_id: user.id,
        symbols: form.symbols ?? ["EURUSD"],
        risk_per_trade: Number(form.risk_per_trade ?? 0.02),
        max_daily_loss: Number(form.max_daily_loss ?? 0.10),
        min_confidence: Number(form.min_confidence ?? 50),
        max_lot_size: Number(form.max_lot_size ?? 5.0),
        timeframe_major: form.timeframe_major ?? "H1",
        timeframe_minor: form.timeframe_minor ?? "M5",
        loop_interval_minutes: Number(form.loop_interval_minutes ?? 5),
        realtime_enabled: form.realtime_enabled ?? false,
        loop_interval_seconds: Number(form.loop_interval_seconds ?? 15),
        ai_enabled: form.ai_enabled ?? true,
        shadow_mode: form.shadow_mode ?? true,
        ai_model: form.ai_model ?? "auto",
        prompt_identity: form.prompt_identity ?? "",
        prompt_strategy: form.prompt_strategy ?? "",
        prompt_output: form.prompt_output ?? "",
        risk_level_single_confirmation: Number(form.risk_level_single_confirmation ?? 0.01),
        risk_level_multiple_confirmation: Number(form.risk_level_multiple_confirmation ?? 0.02),
        strategy_weight_smc: Number(form.strategy_weight_smc ?? 60),
        strategy_weight_pattern: Number(form.strategy_weight_pattern ?? 60),
        strategy_weight_news: Number(form.strategy_weight_news ?? 60)
      };

      // Safe update/insert for bot_settings
      const { data: existing } = await supabase.from("bot_settings").select("id").eq("user_id", user.id).maybeSingle();
      if (existing) {
        const { error } = await supabase.from("bot_settings").update(payload).eq("id", existing.id);
        if (error) alert("Sozlamalarni saqlashda xatolik: " + error.message);
      } else {
        const { error } = await supabase.from("bot_settings").insert(payload);
        if (error) alert("Sozlamalarni saqlashda xatolik: " + error.message);
      }

      // Safe update/insert for bot_status
      const { data: existingStatus } = await supabase.from("bot_status").select("id").eq("user_id", user.id).maybeSingle();
      const statusPayload = { user_id: user.id, claude_limit: Number(claudeLimit), claude_used: Number(claudeUsed) };
      if (existingStatus) {
        await supabase.from("bot_status").update(statusPayload).eq("id", existingStatus.id);
      } else {
        await supabase.from("bot_status").insert(statusPayload);
      }
    }

    await qc.invalidateQueries({ queryKey: ["bot_settings"] });
    await qc.invalidateQueries({ queryKey: ["bot_status"] });
    await qc.invalidateQueries({ queryKey: ["bot_status_settings"] });
    
    setBusy(false); setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  const saveRef = useRef(save);
  useEffect(() => {
    saveRef.current = save;
  }, [save]);

  const hasChanges = JSON.stringify(form) !== JSON.stringify(initialForm) || claudeLimit !== initialClaudeLimit || claudeUsed !== initialClaudeUsed;

  useEffect(() => {
    window.dispatchEvent(new CustomEvent("settingsState", { detail: { busy, saved, hasChanges } }));
  }, [busy, saved, hasChanges]);

  useEffect(() => {
    const handleReset = async () => {
      if (window.confirm("Haqiqatan ham barcha sozlamalarni standart holatga qaytarmoqchimisiz?")) {
        const defaults = {
          symbols: ["AUTO"],
          risk_per_trade: 0.02,
          max_daily_loss: 0.10,
          min_confidence: 50,
          max_lot_size: 5.0,
          timeframe_major: "H1",
          timeframe_minor: "M5",
          loop_interval_minutes: 5,
          ai_enabled: true,
          shadow_mode: true,
          ai_model: "kimi-k3",
          prompt_identity: "Sen professional Forex treyderi va fundamental tahlilchisisan.",
          prompt_strategy: "SMC, Garmonik patternlar va Iqtisodiy yangiliklarni birlashtirib eng yaxshi nuqtadan savdoga kirish qarorini qabul qilgin.",
          prompt_output: 'JAVOBNI FAQAT quyidagi JSON formatida qaytar, boshqa hech qanday izoh yoki tushuntirish yozma. Format: {"signal": "BUY" | "SELL" | "HOLD", "confidence": 0-100, "reasoning": "...", "stop_loss_pips": 20, "take_profit_pips": 40}',
          risk_level_single_confirmation: 0.01,
          risk_level_multiple_confirmation: 0.02,
          strategy_weight_smc: 60,
          strategy_weight_pattern: 60,
          strategy_weight_news: 60
        };
        setForm(defaults);
        if (user) {
          setBusy(true); setSaved(false);
          if (isGuest) {
            guestMock.saveSettings(defaults);
          } else {
            await supabase.from("bot_settings").upsert(
              { user_id: user.id, ...defaults },
              { onConflict: "user_id" }
            );
          }
          await qc.invalidateQueries({ queryKey: ["bot_settings"] });
          setBusy(false); setSaved(true);
          setTimeout(() => setSaved(false), 2000);
        }
      }
    };
    
    const handleSave = () => {
      saveRef.current();
    };

    window.addEventListener('resetSettings', handleReset);
    window.addEventListener('saveSettings', handleSave);
    return () => {
      window.removeEventListener('resetSettings', handleReset);
      window.removeEventListener('saveSettings', handleSave);
    };
  }, [user, qc]);

  if (isLoading || statusQuery.isLoading) return (
    <div className="flex justify-center w-full py-10">
      <img src={pubgLoader} className="mx-auto w-32 h-32 opacity-80" alt="Yuklanmoqda..." />
    </div>
  );

  return (
    <div className="space-y-4 pb-10">
      {/* 1. Market Settings */}
      <Card className="glass relative z-10 p-5">
        <div className="flex items-center gap-2 mb-4 text-brand">
          <Settings2 size={18} />
          <h3 className="font-bold text-sm tracking-wide uppercase">Bozor va Timeframe</h3>
        </div>
        
        <div className="space-y-4">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs font-semibold text-fg-muted">Smart Scanner (Avto-qidiruv)</label>
              <button 
                type="button"
                onClick={() => {
                  const isAuto = form.symbols?.includes("AUTO");
                  setForm(f => ({ ...f, symbols: isAuto ? ["EURUSD", "GBPUSD", "XAUUSD"] : ["AUTO"] }));
                }}
                className={`relative inline-flex h-4 w-7 shrink-0 cursor-pointer items-center rounded-full transition-colors duration-300 ease-in-out ${form.symbols?.includes("AUTO") ? 'bg-brand' : 'bg-white/10'}`}
              >
                <span className={`inline-block h-2.5 w-2.5 transform rounded-full bg-white shadow-sm transition-transform duration-300 ease-in-out ${form.symbols?.includes("AUTO") ? 'translate-x-[14px]' : 'translate-x-1'}`} />
              </button>
            </div>
            
            {form.symbols?.includes("AUTO") ? (
              <div className="w-full rounded-xl border border-brand/30 bg-brand/10 px-4 py-3 text-sm text-brand-soft flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-brand animate-pulse shrink-0"></div>
                <div className="flex-1 text-xs">
                  <p className="font-semibold text-brand mb-0.5">Avtomatik qidiruv FAOL</p>
                  <p className="text-brand-soft/70 leading-relaxed">Bot MT5 dagi barcha ruxsat etilgan juftliklarni 3 tadan aylanib tahlil qilmoqda. Holatni Dashboard ekranidan jonli kuzatishingiz mumkin.</p>
                </div>
              </div>
            ) : (
              <div>
                <label className="mb-2 mt-3 block text-[10px] font-semibold text-fg-muted">Qo'lda tanlash</label>
                <div 
                  onClick={() => setIsSymbolModalOpen(true)}
                  className="w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-sm text-fg cursor-pointer hover:bg-white/5 transition-all flex items-center justify-between"
                >
                  <div className="flex-1 truncate">
                    {(form.symbols?.filter(s => s !== "AUTO").length || 0) > 0 
                      ? form.symbols?.filter(s => s !== "AUTO").join(", ") 
                      : <span className="text-fg-muted">Juftliklarni tanlang...</span>}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] bg-brand/20 text-brand px-2 py-0.5 rounded-full">
                      {form.symbols?.filter(s => s !== "AUTO").length || 0} ta
                    </span>
                    <ListPlus size={16} className="text-brand opacity-80" />
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-2 block text-xs font-semibold text-fg-muted">Major Timeframe</label>
              <CustomSelect
                value={form.timeframe_major ?? "H1"}
                onChange={(val) => setForm((f) => ({ ...f, timeframe_major: val }))}
                options={MAJOR_TIMEFRAME_OPTIONS}
              />
            </div>
            <div>
              <label className="mb-2 block text-xs font-semibold text-fg-muted">Minor Timeframe</label>
              <CustomSelect
                value={form.timeframe_minor ?? "M5"}
                onChange={(val) => setForm((f) => ({ ...f, timeframe_minor: val }))}
                options={MINOR_TIMEFRAME_OPTIONS}
              />
            </div>
            <div className="col-span-2 flex items-center justify-between py-2 border-b border-white/5">
              <div>
                <label className="block text-xs font-bold text-fg-muted uppercase tracking-wider">Real-time Rejim</label>
                <span className="text-[10px] text-white/40">Bot soniyali intervallar bilan real vaqtda ishlaydi</span>
              </div>
              <input 
                type="checkbox"
                checked={!!form.realtime_enabled}
                onChange={(e) => setForm((f) => ({ ...f, realtime_enabled: e.target.checked }))}
                className="w-4 h-4 rounded border-white/10 text-blue-600 bg-black/40 focus:ring-blue-500/20"
              />
            </div>
            
            <div className="col-span-2">
              {form.realtime_enabled ? (
                <Slider
                  label="Tahlil tezligi (Soniya)"
                  value={Number(form.loop_interval_seconds ?? 15)}
                  min={1} max={60} step={1}
                  format={(v) => `Har ${v} soniyada`}
                  onChange={(v) => setForm((f) => ({ ...f, loop_interval_seconds: v }))}
                />
              ) : (
                <Slider
                  label="Tahlil tezligi (Daqiqa)"
                  value={Number(form.loop_interval_minutes ?? 5)}
                  min={1} max={240} step={1}
                  format={(v) => `Har ${v} daqiqada`}
                  onChange={(v) => setForm((f) => ({ ...f, loop_interval_minutes: v }))}
                />
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* 1.5 DANGER SETUP */}
      <Card className="glass border-red-500/20 p-5 relative overflow-hidden">
        <div className="absolute top-0 right-0 p-2 opacity-10">
          <TriangleAlert size={100} className="text-red-500" />
        </div>
        <div className="flex items-center gap-2 mb-4 text-red-500 relative z-10">
          <FlaskConical size={18} />
          <h3 className="font-bold text-sm tracking-wide uppercase">Danger Setup (News Grid)</h3>
        </div>

        <div className="flex items-center justify-between py-3 relative z-10">
          <div className="flex-1 pr-4">
            <p className="text-sm font-semibold text-white/90">High-Frequency News Breakout</p>
            <p className="text-[11px] text-red-400/80 leading-snug mt-0.5">
              Tizim yangiliklarda tezkor Stop orderlar tarmog'ini quradi. Bu juda xavfli strategiya (40% gacha risk). 
              Ishga tushirishdan oldin ehtiyot bo'ling!
            </p>
          </div>
          <button 
            type="button"
            onClick={() => setForm(f => ({ ...f, news_breakout_grid_enabled: !f.news_breakout_grid_enabled }))}
            className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full transition-colors duration-300 ease-in-out ${form.news_breakout_grid_enabled ? 'bg-red-500' : 'bg-white/10'}`}
          >
            <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow-sm transition-transform duration-300 ease-in-out ${form.news_breakout_grid_enabled ? 'translate-x-[18px]' : 'translate-x-1'}`} />
          </button>
        </div>
      </Card>

      {/* 2. Advanced AI Configuration */}
      <Card className="glass p-5">
        <div className="flex items-center gap-2 mb-4 text-amber-500">
          <TriangleAlert size={18} />
          <h3 className="font-bold text-sm tracking-wide uppercase">AI Neyrotizim Sozlamalari</h3>
        </div>

        <div className="space-y-4">
          <div className="flex items-center justify-between py-3 border-b border-white/5">
            <div className="flex-1 pr-4">
              <p className="text-sm font-semibold text-white/90">AI Dvigateli</p>
              <p className="text-[11px] text-white/40 leading-snug mt-0.5">
                O'chirilganda bot qo'shimcha tasdiqlarsiz strategiyaga tayanadi.
              </p>
            </div>
            <button 
              type="button"
              onClick={() => setForm(f => ({ ...f, ai_enabled: !f.ai_enabled }))}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full transition-colors duration-300 ease-in-out ${form.ai_enabled !== false ? 'bg-blue-500' : 'bg-white/10'}`}
            >
              <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow-sm transition-transform duration-300 ease-in-out ${form.ai_enabled !== false ? 'translate-x-[18px]' : 'translate-x-1'}`} />
            </button>
          </div>

          <div className="flex items-center justify-between py-3 border-b border-white/5">
            <div className="flex-1 pr-4">
              <p className="text-sm font-semibold text-white/90">Shadow Mode (Soya Rejimi)</p>
              <p className="text-[11px] text-white/40 leading-snug mt-0.5">
                Yoqilgan bo'lsa, bitimlar MT5 ga (Real/Demo) bormaydi. Bot ichki xotirada savdo qilib o'rganadi.
              </p>
            </div>
            <button 
              type="button"
              onClick={() => setForm(f => ({ ...f, shadow_mode: !f.shadow_mode }))}
              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full transition-colors duration-300 ease-in-out ${form.shadow_mode !== false ? 'bg-amber-500' : 'bg-white/10'}`}
            >
              <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow-sm transition-transform duration-300 ease-in-out ${form.shadow_mode !== false ? 'translate-x-[18px]' : 'translate-x-1'}`} />
            </button>
          </div>

          <div className="py-3">
            <p className="text-xs font-semibold text-white/90 mb-2">AI Modeli (3 tagacha tanlash mumkin)</p>
            <CustomSelect
              options={AI_MODEL_OPTIONS}
              value={form.ai_model ?? "auto"}
              onChange={(v) => setForm((f) => ({ ...f, ai_model: v }))}
              placeholder="Modelni tanlang..."
              multiple={true}
              maxCount={3}
            />
          </div>

          <div className="space-y-4">
            <PromptEditor 
              label="1. Identity va Rol (Bot o'zini kim deb bilishi kerak?)" 
              value={form.prompt_identity ?? ""} 
              onChange={(v) => setForm(f => ({ ...f, prompt_identity: v }))} 
            />
            <PromptEditor 
              label="2. Strategiya va Qoidalar (SMC, Harmonic, Yangiliklar)" 
              value={form.prompt_strategy ?? ""} 
              onChange={(v) => setForm(f => ({ ...f, prompt_strategy: v }))} 
            />
            <PromptEditor 
              label="3. Natija Formati va Cheklovlar (JSON output)" 
              value={form.prompt_output ?? ""} 
              onChange={(v) => setForm(f => ({ ...f, prompt_output: v }))} 
            />
          </div>
        </div>
      </Card>

      {/* 3. Risk Management */}
      <Card className="glass p-3 rounded-xl">
        <div className="flex items-center gap-1.5 mb-2 text-amber-500">
          <TriangleAlert size={14} />
          <h3 className="font-bold text-xs tracking-wide uppercase">Riskni Boshqarish</h3>
        </div>

        <div className="space-y-2">
          <Slider
            label="Risk per Trade"
            value={Number(form.risk_per_trade ?? 0.02)}
            min={0.001} max={0.10} step={0.001}
            format={(v) => `${(v * 100).toFixed(1)}%`}
            onChange={(v) => setForm((f) => ({ ...f, risk_per_trade: v }))}
          />
          <Slider
            label="Max Lot"
            value={Number(form.max_lot_size ?? 5.0)}
            min={0.01} max={10} step={0.01}
            format={(v) => `${v.toFixed(2)} Lot`}
            onChange={(v) => setForm((f) => ({ ...f, max_lot_size: v }))}
          />
          <Slider
            label="Max Drawdown"
            value={Number(form.max_daily_loss ?? 0.10)}
            min={0.01} max={0.30} step={0.01}
            format={(v) => `${(v * 100).toFixed(0)}%`}
            onChange={(v) => setForm((f) => ({ ...f, max_daily_loss: v }))}
          />
        </div>
      </Card>




      {/* Save Button */}
      <Button size="lg" className="w-full bg-brand hover:bg-brand-strong text-white font-bold py-3.5 rounded-xl shadow-lg transition-all" onClick={save} disabled={busy}>
        {busy ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
        {saved ? "Muvaffaqiyatli saqlandi!" : "Barcha sozlamalarni saqlash"}
      </Button>

      {/* Symbol Selection Modal */}
      {isSymbolModalOpen && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="w-full max-w-md bg-[#040d21] border border-white/10 rounded-3xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh]">
            {/* Modal Header */}
            <div className="flex justify-between items-center p-5 border-b border-white/5 relative">
              <div>
                <h2 className="text-lg font-bold text-white">Juftliklarni Tanlash</h2>
                <p className="text-xs text-brand/80">Istalgancha juftlik tanlashingiz mumkin.</p>
              </div>
              <button 
                onClick={() => setIsSymbolModalOpen(false)}
                className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-all text-white/60 hover:text-white"
              >
                <X size={16} />
              </button>
            </div>

            {/* Toast Warning */}
            {toastMsg && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-xs text-center py-2 px-4 animate-in slide-in-from-top-2">
                {toastMsg}
              </div>
            )}

            {/* Category Tabs */}
            <div className="flex items-center gap-1 overflow-x-auto p-3 scrollbar-hide border-b border-white/5">
              {Object.keys(dynamicCategories).map((cat) => (
                <button
                  key={cat}
                  onClick={() => setActiveCategory(cat)}
                  className={`px-4 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
                    activeCategory === cat 
                      ? "bg-brand text-white shadow-lg shadow-brand/20" 
                      : "bg-white/5 text-fg-muted hover:bg-white/10 hover:text-white"
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>

            {/* Select/Deselect All Buttons */}
            <div className="flex justify-between items-center px-4 pt-3 pb-1">
              <button 
                onClick={() => {
                  const currentCatSymbols = dynamicCategories[activeCategory] || [];
                  setForm(f => {
                    const current = f.symbols || [];
                    const filtered = current.filter(s => !currentCatSymbols.includes(s));
                    return { ...f, symbols: [...filtered, ...currentCatSymbols] };
                  });
                }}
                className="text-xs text-brand hover:text-white transition-all font-semibold"
              >
                + Barchasini tanlash
              </button>
              <button 
                onClick={() => {
                  const currentCatSymbols = dynamicCategories[activeCategory] || [];
                  setForm(f => {
                    const current = f.symbols || [];
                    return { ...f, symbols: current.filter(s => !currentCatSymbols.includes(s)) };
                  });
                }}
                className="text-xs text-red-400 hover:text-red-300 transition-all font-semibold"
              >
                - Barchasini o'chirish
              </button>
            </div>

            {/* Symbols Grid */}
            <div className="p-4 overflow-y-auto flex-1">
              <div className="grid grid-cols-2 gap-3">
                {(dynamicCategories[activeCategory] || []).map((sym) => {
                  const isSelected = (form.symbols || []).includes(sym);
                  return (
                    <div 
                      key={sym}
                      onClick={() => toggleSymbol(sym)}
                      className={`flex items-center justify-between p-3 rounded-xl border transition-all cursor-pointer ${
                        isSelected 
                          ? "bg-brand/10 border-brand/50 shadow-[0_0_15px_rgba(37,99,235,0.15)]" 
                          : "bg-white/5 border-transparent hover:bg-white/10"
                      }`}
                    >
                      <span className={`text-sm font-bold ${isSelected ? "text-brand" : "text-white"}`}>
                        {sym}
                      </span>
                      <div className={`w-5 h-5 rounded-md border flex items-center justify-center ${
                        isSelected ? "bg-brand border-brand" : "border-white/20"
                      }`}>
                        {isSelected && <Check size={12} className="text-white" />}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-white/5 bg-black/20">
              <Button 
                onClick={() => setIsSymbolModalOpen(false)}
                className="w-full py-6 rounded-2xl bg-gradient-to-r from-[#2563eb] to-[#0434b6] hover:brightness-110 shadow-[0_0_20px_rgba(37,99,235,0.3)] text-white font-bold"
              >
                Tasdiqlash ({(form.symbols || []).length} ta)
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Slider({
  label, value, min, max, step, onChange, format, leftLabel, rightLabel
}: {
  label: string; value: number; min: number; max: number; step: number;
  onChange: (v: number) => void; format: (v: number) => string;
  leftLabel?: string; rightLabel?: string;
}) {
  return (
    <div>
      <div className="mb-1 flex items-center justify-between">
        <label className="text-[10px] font-bold text-white/40 uppercase tracking-wide">{label}</label>
        <span className="tabular rounded-full bg-white/5 px-2 py-0.5 text-[9px] font-bold text-brand">
          {format(value)}
        </span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-[color:var(--color-brand)] h-2.5 bg-white/10 rounded-lg appearance-none cursor-pointer"
      />
      {(leftLabel || rightLabel) && (
        <div className="flex justify-between text-[9px] text-fg-muted/40 mt-1 px-0.5 font-medium">
          <span>{leftLabel}</span>
          <span>{rightLabel}</span>
        </div>
      )}
    </div>
  );
}

function PromptEditor({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  const [isEditing, setIsEditing] = useState(false);
  return (
    <div className="border border-white/5 rounded-xl bg-black/20 p-4">
      <div className="flex justify-between items-center mb-3">
        <label className="text-xs font-semibold text-fg-muted uppercase tracking-wider">{label}</label>
        <button onClick={() => setIsEditing(!isEditing)} className="text-brand hover:text-white flex items-center gap-1 text-xs px-2 py-1 bg-brand/10 rounded-md transition-all">
          {isEditing ? <Check size={14}/> : <Pencil size={14}/>}
          {isEditing ? "Saqlash" : "Tahrirlash"}
        </button>
      </div>
      {isEditing ? (
        <textarea
          rows={5}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full rounded-xl border border-brand/50 bg-black/60 px-4 py-3 text-xs text-white outline-none focus:border-brand shadow-[0_0_10px_rgba(37,99,235,0.2)] font-mono transition-all"
        />
      ) : (
        <div className="text-xs text-white/70 font-mono whitespace-pre-wrap">{value}</div>
      )}
    </div>
  );
}
