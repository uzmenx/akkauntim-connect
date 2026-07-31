import { useState, useEffect } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Bot, Loader2, KeyRound, Server, User, UserCheck, Eye, EyeOff } from "lucide-react";
import { mt5LoginToEmail, useAuth } from "@/hooks/useAuth";

type Mode = "signin" | "signup";

export function AuthPage() {
  const { loginAsGuest } = useAuth();
  const [mode, setMode] = useState<Mode>("signin");
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [server, setServer] = useState("MetaQuotes-Demo");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [rememberMe, setRememberMe] = useState(false);

  useEffect(() => {
    const savedLogin = localStorage.getItem("mt5_saved_login");
    const savedPass = localStorage.getItem("mt5_saved_password");
    if (savedLogin && savedPass) {
      setLogin(savedLogin);
      setPassword(savedPass);
      setRememberMe(true);
    }
  }, []);


  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    const email = mt5LoginToEmail(login);

    try {
      if (mode === "signup") {
        const { data, error } = await supabase.auth.signUp({
          email,
          password,
          options: { emailRedirectTo: window.location.origin, data: { mt5_login: login.trim(), mt5_server: server.trim() } },
        });
        if (error) throw error;

        // Save settings (bot_settings has RLS by user_id)
        if (data.user) {
          const { error: upErr } = await supabase.from("bot_settings").upsert(
            {
              user_id: data.user.id,
              mt5_login: login.trim(),
              mt5_password: password,
              mt5_server: server.trim(),
              symbols: ["EURUSD", "GBPUSD", "XAUUSD"],
              risk_per_trade: 0.02,
              max_daily_loss: 0.10,
              min_confidence: 50,
              max_lot_size: 5.0,
              timeframe_major: "H1",
              timeframe_minor: "M5",
              ai_model: "auto",
              system_prompt: "Sen professional Forex treyderi va fundamental tahlilchisisan.",
              risk_level_single_confirmation: 0.01,
              risk_level_multiple_confirmation: 0.02,
            },
            { onConflict: "user_id" }
          );
          if (upErr) console.warn("bot_settings save:", upErr.message);
        }
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      }
      
      if (rememberMe) {
        localStorage.setItem("mt5_saved_login", login.trim());
        localStorage.setItem("mt5_saved_password", password);
      } else {
        localStorage.removeItem("mt5_saved_login");
        localStorage.removeItem("mt5_saved_password");
      }
    } catch (e: any) {
      setErr(e.message ?? "Xatolik yuz berdi");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-full w-full max-w-md flex-col justify-center px-6 py-10 relative z-10">
      {/* 3D Open Sea background */}
      <div className="fixed inset-0 pointer-events-auto z-0">
        <iframe src="/ocean.html?v=2" className="absolute inset-0 w-full h-full border-0 pointer-events-auto" title="Open Sea Background" />
      </div>

      <div className="mb-8 flex flex-col items-center gap-3 text-center relative z-10">
        <div className="h-16 w-16 overflow-hidden rounded-[20px] bg-gradient-to-br from-blue-500 to-indigo-700 shadow-[0_0_25px_rgba(59,130,246,0.3)] border border-white/20 flex items-center justify-center">
          <img src="/logo.jpg" alt="Logo" className="w-full h-full object-cover" />
        </div>
        <h1 className="text-2xl font-extrabold tracking-tight text-white bg-clip-text text-transparent bg-gradient-to-r from-white via-blue-100 to-blue-300">Akcume Trading AI</h1>
        <p className="max-w-xs text-[11px] font-black text-white/90 uppercase tracking-wider shadow-sm bg-black/20 px-3 py-1 rounded-full backdrop-blur-md border border-white/10">
          {mode === "signup"
            ? "MT5 hisobingizni ro'yxatdan o'tkazing"
            : "Ro'yxatdan o'tgan MT5 hisobi orqali kiring"}
        </p>
      </div>

      <Card className="bg-gradient-to-br from-white/10 to-transparent backdrop-blur-[32px] backdrop-saturate-[150%] border-t border-l border-white/30 border-r border-b border-white/5 p-8 rounded-[42px] shadow-[0_30px_60px_rgba(0,0,0,0.3),inset_1px_1px_15px_rgba(255,255,255,0.2),inset_-1px_-1px_15px_rgba(0,0,0,0.1)] relative z-10 overflow-hidden">
        {/* Crisp curved reflection (glare) at the top for 3D liquid glass effect */}
        <div className="absolute top-[-25%] left-[-20%] w-[140%] h-[60%] bg-gradient-to-b from-white/30 to-transparent rounded-[100%] pointer-events-none transform -rotate-12 blur-[1px]" />

        <form onSubmit={handleSubmit} className="space-y-5 relative z-10">
          <div>
            <label className="text-xs font-black text-white/90 mb-2 flex items-center gap-1.5 uppercase tracking-wider">
              <User size={12} className="text-white/90" /> MT5 Login
            </label>
            <input
              type="text" required autoComplete="username"
              value={login} onChange={(e) => setLogin(e.target.value)}
              placeholder="Masalan: 109545213"
              className="w-full rounded-[16px] border-t border-l border-white/20 border-r border-b border-white/5 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-white/30 focus:border-white/40 focus:bg-white/10 focus:shadow-[0_0_20px_rgba(255,255,255,0.1),inset_0_2px_5px_rgba(0,0,0,0.1)] transition-all duration-300"
            />
          </div>

          <div>
            <label className="text-xs font-black text-white/90 mb-2 flex items-center gap-1.5 uppercase tracking-wider">
              <KeyRound size={12} className="text-white/90" /> MT5 Paroli
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"} required minLength={6}
                autoComplete={mode === "signup" ? "new-password" : "current-password"}
                value={password} onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-[16px] border-t border-l border-white/20 border-r border-b border-white/5 bg-white/5 px-4 py-3 pr-12 text-sm text-white outline-none placeholder:text-white/30 focus:border-white/40 focus:bg-white/10 focus:shadow-[0_0_20px_rgba(255,255,255,0.1),inset_0_2px_5px_rgba(0,0,0,0.1)] transition-all duration-300"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-white/50 hover:text-white/90 transition-colors"
                aria-label={showPassword ? "Parolni yashirish" : "Parolni ko'rsatish"}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {mode === "signup" && (
            <div>
              <label className="text-xs font-black text-white/90 mb-2 flex items-center gap-1.5 uppercase tracking-wider">
                <Server size={12} className="text-white/90" /> MT5 Server
              </label>
              <input
                type="text" required
                value={server} onChange={(e) => setServer(e.target.value)}
                placeholder="Masalan: MetaQuotes-Demo"
                className="w-full rounded-[16px] border-t border-l border-white/20 border-r border-b border-white/5 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-white/30 focus:border-white/40 focus:bg-white/10 focus:shadow-[0_0_20px_rgba(255,255,255,0.1),inset_0_2px_5px_rgba(0,0,0,0.1)] transition-all duration-300"
              />
            </div>
          )}

          <div className="flex items-center gap-2 pt-1 pb-1">
            <input
              type="checkbox"
              id="rememberMe"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="w-4 h-4 rounded bg-white/10 border-white/20 text-blue-500 focus:ring-blue-500 focus:ring-offset-0 cursor-pointer"
            />
            <label htmlFor="rememberMe" className="text-sm font-medium text-white/90 cursor-pointer select-none">
              Meni eslab qol
            </label>
          </div>

          {err && (
            <div className="rounded-xl bg-red-500/10 border-t border-l border-red-500/30 border-r border-b border-red-500/10 px-3 py-2.5 text-xs text-rose-200">{err}</div>
          )}

          <Button type="submit" size="lg" className="mt-4 w-full bg-gradient-to-br from-white/25 to-white/5 border-t border-l border-white/40 border-r border-b border-white/10 hover:bg-white/20 text-white font-bold py-4 rounded-[16px] shadow-[0_10px_20px_rgba(0,0,0,0.2),inset_1px_1px_5px_rgba(255,255,255,0.5)] hover:shadow-[0_15px_25px_rgba(0,0,0,0.3),inset_1px_1px_8px_rgba(255,255,255,0.6)] hover:scale-[1.02] active:scale-95 transition-all duration-300 backdrop-blur-md" disabled={busy}>
            {busy ? <Loader2 className="animate-spin" size={18} /> : mode === "signup" ? "Ro'yxatdan o'tish" : "Tizimga kirish"}
          </Button>

          <button
            type="button"
            onClick={() => loginAsGuest()}
            className="w-full flex items-center justify-center gap-2 bg-black/20 border-t border-l border-white/10 border-r border-b border-black/20 hover:bg-black/30 hover:border-white/20 active:scale-[0.98] text-white/90 font-semibold py-3.5 rounded-[16px] transition-all duration-300 shadow-inner mt-2"
          >
            <UserCheck size={16} className="text-blue-400" />
            <span>Mehmon bo'lib kirish</span>
          </button>

          <button
            type="button"
            onClick={() => { setMode(mode === "signup" ? "signin" : "signup"); setErr(null); }}
            className="w-full text-center text-xs text-[#0d2f25] hover:text-[#16423c] font-black transition-all pt-2 underline underline-offset-4"
          >
            {mode === "signup" ? "Hisobingiz bormi? Kirish" : "Hisob yo'qmi? Ro'yxatdan o'ting"}
          </button>
        </form>
      </Card>

      <p className="mt-8 text-center text-[10px] text-white/30 leading-relaxed relative z-10">
        Har bir foydalanuvchi faqat o'zining MT5 hisob ma'lumotlarini ko'radi.
        <br />Ma'lumotlar xavfsiz saqlanadi.
      </p>
    </div>
  );
}
