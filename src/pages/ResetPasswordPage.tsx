import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { KeyRound, Loader2, Server, User, Eye, EyeOff, ArrowLeft, CheckCircle2 } from "lucide-react";
import logo from "@/assets/icon.jpg";

const inputCls =
  "w-full rounded-[12px] sm:rounded-[16px] border border-white/25 bg-black/35 px-3.5 sm:px-4 py-2.5 sm:py-3.5 text-xs sm:text-sm text-white outline-none placeholder:text-white/40 focus:border-cyan-400/80 focus:bg-black/45 focus:shadow-[0_0_25px_rgba(34,211,238,0.35),inset_0_2px_8px_rgba(0,0,0,0.4)] transition-all duration-300 shadow-[inset_0_2px_8px_rgba(0,0,0,0.3)] font-semibold";
const labelCls =
  "text-[10px] sm:text-[11px] font-black text-cyan-200 mb-1.5 sm:mb-2 flex items-center gap-2 uppercase tracking-widest";

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [login, setLogin] = useState("");
  const [server, setServer] = useState("");
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function call(payload: Record<string, unknown>) {
    const { data, error } = await supabase.functions.invoke("reset-mt5-password", { body: payload });
    if (error) {
      const ctxMsg = await (error as any)?.context?.json?.().then((j: any) => j?.error).catch(() => null);
      throw new Error(ctxMsg || error.message || "Server bilan bog'lanishda xatolik");
    }
    if ((data as any)?.error) throw new Error((data as any).error);
    return data as any;
  }

  async function handleVerify(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const data = await call({ action: "verify", mt5_login: login.trim(), mt5_server: server.trim() });
      setToken(data.token);
      setStep(2);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function handleReset(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setErr("Parollar mos kelmadi");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      await call({ action: "reset", token, password });
      localStorage.removeItem("mt5_saved_password");
      setStep(3);
      setTimeout(() => navigate("/auth"), 2500);
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-full w-full max-w-md flex-col justify-center px-4 sm:px-6 py-4 sm:py-10 relative z-10">
      <div className="fixed inset-0 pointer-events-none -z-10 overflow-hidden">
        <div
          className="absolute inset-0 bg-cover bg-center bg-no-repeat scale-105"
          style={{ backgroundImage: "url('/nature_bg.jpg')" }}
        />
        <div className="absolute top-1/4 left-[-10%] w-[320px] h-[320px] rounded-full bg-cyan-400/40 mix-blend-screen filter blur-[70px] animate-pulse" />
        <div className="absolute bottom-1/4 right-[-10%] w-[350px] h-[350px] rounded-full bg-emerald-400/35 mix-blend-screen filter blur-[85px] animate-pulse" />
        <div className="absolute inset-0 bg-black/10 backdrop-blur-[2px]" />
      </div>

      <div className="mb-4 sm:mb-8 flex flex-col items-center gap-2 sm:gap-3 text-center">
        <div className="h-14 w-14 sm:h-20 sm:w-20 overflow-hidden rounded-[18px] sm:rounded-[24px] bg-gradient-to-br from-cyan-400 via-blue-600 to-indigo-800 p-[1.5px] shadow-[0_12px_35px_rgba(34,211,238,0.4)] border border-white/20 flex items-center justify-center">
          <img src={logo} alt="Akcume AI logotipi" className="w-full h-full object-cover rounded-[16px] sm:rounded-[22px]" />
        </div>
        <h1 className="text-xl sm:text-3xl font-black tracking-tight text-white drop-shadow-[0_4px_12px_rgba(0,0,0,0.4)]">
          Parolni tiklash
        </h1>
        <p className="max-w-xs text-[10px] sm:text-[11px] font-black text-white/95 uppercase tracking-widest bg-white/20 px-3.5 py-1 sm:px-4 sm:py-1.5 rounded-full backdrop-blur-md border border-white/30">
          {step === 1 ? "MT5 login va serverni tasdiqlang" : step === 2 ? "Yangi parol qo'ying" : "Tayyor"}
        </p>
      </div>

      <Card className="bg-white/12 backdrop-blur-[45px] border-t border-l border-white/50 border-r border-b border-white/20 p-5 sm:p-8 rounded-[24px] sm:rounded-[40px] shadow-[0_45px_75px_-10px_rgba(0,0,0,0.65),inset_0_6px_28px_rgba(255,255,255,0.45)] relative overflow-hidden">
        <div className="absolute top-[-35%] left-[-25%] w-[150%] h-[75%] bg-gradient-to-b from-white/35 to-transparent rounded-[100%] pointer-events-none transform -rotate-12" />

        {step === 1 && (
          <form onSubmit={handleVerify} className="space-y-4 sm:space-y-6 relative z-10">
            <div>
              <label className={labelCls}>
                <User size={12} className="text-cyan-400" /> MT5 Login
              </label>
              <input
                type="text" required value={login} onChange={(e) => setLogin(e.target.value)}
                placeholder="Masalan: 68338156" maxLength={32} className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>
                <Server size={12} className="text-cyan-400" /> MT5 Server
              </label>
              <input
                type="text" required value={server} onChange={(e) => setServer(e.target.value)}
                placeholder="Masalan: MetaQuotes-Demo" maxLength={64} className={inputCls}
              />
            </div>
            {err && (
              <div className="rounded-xl bg-rose-500/20 border border-rose-500/40 px-3 py-2.5 text-xs text-rose-100">{err}</div>
            )}
            <Button type="submit" size="lg" disabled={busy}
              className="mt-2 w-full bg-gradient-to-r from-cyan-400/50 via-blue-500/45 to-indigo-600/40 border border-white/45 text-white font-black text-xs sm:text-sm tracking-wider uppercase py-3 sm:py-4 rounded-[12px] sm:rounded-[16px] flex items-center justify-center gap-2">
              {busy ? <Loader2 className="animate-spin" size={16} /> : "Tasdiqlash"}
            </Button>
          </form>
        )}

        {step === 2 && (
          <form onSubmit={handleReset} className="space-y-4 sm:space-y-6 relative z-10">
            <div>
              <label className={labelCls}>
                <KeyRound size={12} className="text-cyan-400" /> Yangi parol
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"} required minLength={6} autoComplete="new-password"
                  value={password} onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••" className={inputCls + " pr-12"}
                />
                <button type="button" onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Parolni yashirish" : "Parolni ko'rsatish"}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 p-1.5 text-white/60 hover:text-white/90">
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>
            <div>
              <label className={labelCls}>
                <KeyRound size={12} className="text-cyan-400" /> Parolni tasdiqlang
              </label>
              <input
                type={showPassword ? "text" : "password"} required minLength={6} autoComplete="new-password"
                value={confirm} onChange={(e) => setConfirm(e.target.value)}
                placeholder="••••••••" className={inputCls}
              />
            </div>
            {err && (
              <div className="rounded-xl bg-rose-500/20 border border-rose-500/40 px-3 py-2.5 text-xs text-rose-100">{err}</div>
            )}
            <Button type="submit" size="lg" disabled={busy}
              className="mt-2 w-full bg-gradient-to-r from-cyan-400/50 via-blue-500/45 to-indigo-600/40 border border-white/45 text-white font-black text-xs sm:text-sm tracking-wider uppercase py-3 sm:py-4 rounded-[12px] sm:rounded-[16px] flex items-center justify-center gap-2">
              {busy ? <Loader2 className="animate-spin" size={16} /> : "Parolni saqlash"}
            </Button>
          </form>
        )}

        {step === 3 && (
          <div className="relative z-10 flex flex-col items-center gap-3 py-4 text-center">
            <CheckCircle2 size={44} className="text-emerald-400" />
            <p className="text-sm font-bold text-white">Parol muvaffaqiyatli yangilandi!</p>
            <p className="text-xs text-white/70">Kirish sahifasiga qaytarilmoqda...</p>
          </div>
        )}

        <button type="button" onClick={() => navigate("/auth")}
          className="mt-5 w-full flex items-center justify-center gap-1.5 text-[11px] sm:text-xs text-cyan-200/90 hover:text-white font-bold transition-all relative z-10">
          <ArrowLeft size={13} /> Kirish sahifasiga qaytish
        </button>
      </Card>
    </div>
  );
}
