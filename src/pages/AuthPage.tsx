import { useState, useEffect } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Bot, Loader2, KeyRound, Server, User, UserCheck, Eye, EyeOff } from "lucide-react";
import { mt5LoginToEmail, useAuth } from "@/hooks/useAuth";
import logo from "@/assets/icon.jpg";

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
      let msg = e.message ?? "Xatolik yuz berdi";
      if (msg.includes("Invalid login credentials")) {
        msg = "Logingiz yoki parolingiz noto'g'ri. Agar yangi bo'lsangiz, avval 'Ro'yxatdan o'tish' qismini tanlang!";
      } else if (msg.includes("Email not confirmed")) {
        msg = "Tizimga kirish uchun Email tasdiqlanishi kerak (Supabase Dashboard'dan Email Confirmations ni o'chiring).";
      } else if (msg.includes("already registered")) {
        msg = "Bu login allaqachon band. Iltimos, boshqasini tanlang yoki Tizimga kiring.";
      }
      setErr(msg);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-full w-full max-w-md flex-col justify-center px-4 sm:px-6 py-4 sm:py-10 relative z-10">
      {/* Nature background with glowing liquid blobs for realistic 3D refraction */}
      <div className="fixed inset-0 pointer-events-none -z-10 overflow-hidden">
        <div 
          className="absolute inset-0 bg-cover bg-center bg-no-repeat scale-105"
          style={{ backgroundImage: "url('/nature_bg.jpg')" }}
        />
        {/* Fluid liquid glowing blobs refracting through the glass */}
        <div className="absolute top-1/4 left-[-10%] w-[320px] h-[320px] rounded-full bg-cyan-400/40 mix-blend-screen filter blur-[70px] animate-pulse duration-[8000ms]" />
        <div className="absolute bottom-1/4 right-[-10%] w-[350px] h-[350px] rounded-full bg-emerald-400/35 mix-blend-screen filter blur-[85px] animate-pulse duration-[10000ms]" />
        <div className="absolute top-1/3 right-1/4 w-[280px] h-[280px] rounded-full bg-blue-500/30 mix-blend-screen filter blur-[60px] animate-pulse duration-[6000ms]" />
        <div className="absolute inset-0 bg-black/10 backdrop-blur-[2px]" />
      </div>

      <div className="mb-4 sm:mb-8 flex flex-col items-center gap-2 sm:gap-3 text-center">
        <div className="h-14 w-14 sm:h-20 sm:w-20 overflow-hidden rounded-[18px] sm:rounded-[24px] bg-gradient-to-br from-cyan-400 via-blue-600 to-indigo-800 p-[1.5px] shadow-[0_12px_35px_rgba(34,211,238,0.4),inset_0_2px_10px_rgba(255,255,255,0.4)] border border-white/20 flex items-center justify-center">
          <img src={logo} alt="Logo" className="w-full h-full object-cover rounded-[16px] sm:rounded-[22px]" />
        </div>
        <h1 className="text-xl sm:text-3xl font-black tracking-tight text-white bg-clip-text text-transparent bg-gradient-to-r from-white via-cyan-100 to-blue-200 drop-shadow-[0_4px_12px_rgba(0,0,0,0.4)]">
          Akcume Trading AI
        </h1>
        <p className="max-w-xs text-[10px] sm:text-[11px] font-black text-white/95 uppercase tracking-widest shadow-lg bg-white/20 px-3.5 py-1 sm:px-4 sm:py-1.5 rounded-full backdrop-blur-md border border-white/30">
          {mode === "signup"
            ? "MT5 hisobingizni ro'yxatdan o'tkazing"
            : "Ro'yxatdan o'tgan MT5 hisobi orqali kiring"}
        </p>
      </div>

      <Card className="bg-white/12 backdrop-blur-[45px] backdrop-saturate-[200%] border-t border-l border-white/50 border-r border-b border-white/20 p-5 sm:p-8 rounded-[24px] sm:rounded-[40px] shadow-[0_45px_75px_-10px_rgba(0,0,0,0.65),inset_0_6px_28px_rgba(255,255,255,0.45),inset_0_-6px_28px_rgba(0,0,0,0.2)] relative overflow-hidden transition-all duration-500">
        {/* High-definition 3D liquid highlights & glares */}
        <div className="absolute top-[-35%] left-[-25%] w-[150%] h-[75%] bg-gradient-to-b from-white/35 to-transparent rounded-[100%] pointer-events-none transform -rotate-12 blur-[0.5px]" />
        {/* Diagonal persistent liquid sheen glow */}
        <div className="absolute -inset-[100%] bg-gradient-to-tr from-transparent via-white/8 to-transparent transform rotate-45 pointer-events-none" />
        <div className="absolute bottom-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-white/40 to-transparent pointer-events-none" />
        <div className="absolute top-0 bottom-0 left-0 w-[1.5px] bg-gradient-to-b from-white/35 via-transparent to-transparent pointer-events-none" />

        <form onSubmit={handleSubmit} className="space-y-4 sm:space-y-6 relative z-10">
          <div>
            <label className="text-[10px] sm:text-[11px] font-black text-cyan-200 mb-1.5 sm:mb-2 flex items-center gap-2 uppercase tracking-widest drop-shadow-[0_2px_4px_rgba(0,0,0,0.2)]">
              <User size={12} className="text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.6)]" /> MT5 Login
            </label>
            <input
              type="text" required autoComplete="username"
              value={login} onChange={(e) => setLogin(e.target.value)}
              placeholder="Masalan: 109545213"
              className="w-full rounded-[12px] sm:rounded-[16px] border border-white/25 bg-black/35 px-3.5 sm:px-4 py-2.5 sm:py-3.5 text-xs sm:text-sm text-white outline-none placeholder:text-white/40 focus:border-cyan-400/80 focus:bg-black/45 focus:shadow-[0_0_25px_rgba(34,211,238,0.35),inset_0_2px_8px_rgba(0,0,0,0.4)] transition-all duration-300 shadow-[inset_0_2px_8px_rgba(0,0,0,0.3)] font-semibold"
            />
          </div>

          <div>
            <label className="text-[10px] sm:text-[11px] font-black text-cyan-200 mb-1.5 sm:mb-2 flex items-center gap-2 uppercase tracking-widest drop-shadow-[0_2px_4px_rgba(0,0,0,0.2)]">
              <KeyRound size={12} className="text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.6)]" /> MT5 Paroli
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"} required minLength={6}
                autoComplete={mode === "signup" ? "new-password" : "current-password"}
                value={password} onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-[12px] sm:rounded-[16px] border border-white/25 bg-black/35 px-3.5 sm:px-4 py-2.5 sm:py-3.5 pr-12 text-xs sm:text-sm text-white outline-none placeholder:text-white/40 focus:border-cyan-400/80 focus:bg-black/45 focus:shadow-[0_0_25px_rgba(34,211,238,0.35),inset_0_2px_8px_rgba(0,0,0,0.4)] transition-all duration-300 shadow-[inset_0_2px_8px_rgba(0,0,0,0.3)] font-semibold"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 p-1.5 text-white/60 hover:text-white/90 transition-colors"
                aria-label={showPassword ? "Parolni yashirish" : "Parolni ko'rsatish"}
              >
                {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          {mode === "signup" && (
            <div>
              <label className="text-[10px] sm:text-[11px] font-black text-cyan-200 mb-1.5 sm:mb-2 flex items-center gap-2 uppercase tracking-widest drop-shadow-[0_2px_4px_rgba(0,0,0,0.2)]">
                <Server size={12} className="text-cyan-400 drop-shadow-[0_0_8px_rgba(34,211,238,0.6)]" /> MT5 Server
              </label>
              <input
                type="text" required
                value={server} onChange={(e) => setServer(e.target.value)}
                placeholder="Masalan: MetaQuotes-Demo"
                className="w-full rounded-[12px] sm:rounded-[16px] border border-white/25 bg-black/35 px-3.5 sm:px-4 py-2.5 sm:py-3.5 text-xs sm:text-sm text-white outline-none placeholder:text-white/40 focus:border-cyan-400/80 focus:bg-black/45 focus:shadow-[0_0_25px_rgba(34,211,238,0.35),inset_0_2px_8px_rgba(0,0,0,0.4)] transition-all duration-300 shadow-[inset_0_2px_8px_rgba(0,0,0,0.3)] font-semibold"
              />
            </div>
          )}

          <div className="flex items-center gap-2.5 pt-0.5">
            <input
              type="checkbox"
              id="rememberMe"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              className="w-4 h-4 rounded-[5px] bg-black/40 border border-white/30 text-cyan-400 focus:ring-cyan-400 focus:ring-offset-0 cursor-pointer transition-all"
            />
            <label htmlFor="rememberMe" className="text-xs sm:text-sm font-semibold text-white cursor-pointer select-none">
              Meni eslab qol
            </label>
          </div>

          {err && (
            <div className="rounded-xl sm:rounded-2xl bg-rose-500/20 border border-rose-500/40 px-3 sm:px-4 py-2.5 sm:py-3 text-xs text-rose-100 shadow-[0_4px_20px_rgba(244,63,94,0.25)] animate-fade-in">{err}</div>
          )}

          <Button 
            type="submit" 
            size="lg" 
            className="mt-2 sm:mt-4 w-full bg-gradient-to-r from-cyan-400/50 via-blue-500/45 to-indigo-600/40 border border-white/45 hover:from-cyan-400/60 hover:via-blue-500/55 hover:to-indigo-600/50 text-white font-black text-xs sm:text-sm tracking-wider uppercase py-3 sm:py-4 rounded-[12px] sm:rounded-[16px] shadow-[0_15px_30px_rgba(6,182,212,0.25),inset_0_2px_10px_rgba(255,255,255,0.6)] hover:shadow-[0_20px_35px_rgba(6,182,212,0.35),inset_0_3px_14px_rgba(255,255,255,0.7)] hover:scale-[1.02] active:scale-98 transition-all duration-300 backdrop-blur-md cursor-pointer flex items-center justify-center gap-2" 
            disabled={busy}
          >
            {busy ? <Loader2 className="animate-spin" size={16} /> : mode === "signup" ? "Ro'yxatdan o'tish" : "Tizimga kirish"}
          </Button>

          <button
            type="button"
            onClick={() => loginAsGuest()}
            className="w-full flex items-center justify-center gap-2.5 bg-white/10 border border-white/20 hover:bg-white/15 hover:border-white/30 active:scale-[0.98] text-white font-bold py-2.5 sm:py-3.5 rounded-[12px] sm:rounded-[16px] text-xs sm:text-sm transition-all duration-300 shadow-[0_4px_15px_rgba(0,0,0,0.1),inset_0_1px_3px_rgba(255,255,255,0.2)] cursor-pointer"
          >
            <UserCheck size={15} className="text-cyan-300 drop-shadow-[0_0_8px_rgba(34,211,238,0.6)]" />
            <span>Mehmon bo'lib kirish</span>
          </button>

          <button
            type="button"
            onClick={() => { setMode(mode === "signup" ? "signin" : "signup"); setErr(null); }}
            className="w-full text-center text-[11px] sm:text-xs text-cyan-200/90 hover:text-white font-bold transition-all pt-1 sm:pt-3 underline underline-offset-4 cursor-pointer"
          >
            {mode === "signup" ? "Hisobingiz bormi? Kirish" : "Hisob yo'qmi? Ro'yxatdan o'ting"}
          </button>
        </form>
      </Card>

      <p className="mt-4 sm:mt-8 text-center text-[9px] sm:text-[10px] text-white/40 leading-relaxed font-medium">
        Har bir foydalanuvchi faqat o'zining MT5 hisob ma'lumotlarini ko'radi.
        <br />Ma'lumotlar xavfsiz saqlanadi.
      </p>
    </div>
  );
}
