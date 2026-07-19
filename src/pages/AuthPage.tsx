import { useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { LineChart, Loader2, KeyRound, Server, User } from "lucide-react";
import { mt5LoginToEmail } from "@/hooks/useAuth";

type Mode = "signin" | "signup";

export function AuthPage() {
  const [mode, setMode] = useState<Mode>("signin");
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [server, setServer] = useState("MetaQuotes-Demo");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

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
              ai_model: "claude-3-5-sonnet-20241022",
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
    } catch (e: any) {
      setErr(e.message ?? "Xatolik yuz berdi");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-full w-full max-w-md flex-col justify-center px-6 py-10">
      <div className="mb-8 flex flex-col items-center gap-3 text-center">
        <div className="grid h-16 w-16 place-items-center rounded-3xl bg-gradient-to-br from-blue-600 to-indigo-600 shadow-2xl shadow-blue-500/40">
          <LineChart className="text-white" size={30} strokeWidth={2.4} />
        </div>
        <h1 className="text-3xl font-black tracking-tight text-white">TraderPanel AI</h1>
        <p className="max-w-xs text-xs text-white/50">
          {mode === "signup"
            ? "MT5 hisobingizni ro'yxatdan o'tkazing — faqat siz o'zingiznikini ko'rasiz."
            : "Ro'yxatdan o'tgan MT5 login va parolingiz bilan kiring."}
        </p>
      </div>

      <Card className="glass p-6 rounded-[28px] border border-white/10 relative overflow-hidden">
        <div className="absolute top-[-50px] right-[-50px] w-24 h-24 rounded-full bg-blue-500/20 blur-xl pointer-events-none" />

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-white/60 mb-2 flex items-center gap-1.5">
              <User size={12} className="text-blue-400" /> MT5 Login
            </label>
            <input
              type="text" required autoComplete="username"
              value={login} onChange={(e) => setLogin(e.target.value)}
              placeholder="Masalan: 109545213"
              className="w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-sm text-white outline-none placeholder:text-white/20 focus:border-brand/60"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-white/60 mb-2 flex items-center gap-1.5">
              <KeyRound size={12} className="text-blue-400" /> MT5 Paroli
            </label>
            <input
              type="password" required minLength={6}
              autoComplete={mode === "signup" ? "new-password" : "current-password"}
              value={password} onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-sm text-white outline-none placeholder:text-white/20 focus:border-brand/60"
            />
          </div>

          {mode === "signup" && (
            <div>
              <label className="text-xs font-semibold text-white/60 mb-2 flex items-center gap-1.5">
                <Server size={12} className="text-blue-400" /> MT5 Server
              </label>
              <input
                type="text" required
                value={server} onChange={(e) => setServer(e.target.value)}
                placeholder="Masalan: MetaQuotes-Demo"
                className="w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-sm text-white outline-none placeholder:text-white/20 focus:border-brand/60"
              />
            </div>
          )}

          {err && (
            <div className="rounded-xl bg-danger/10 border border-danger/20 px-3 py-2 text-xs text-rose-400">{err}</div>
          )}

          <Button type="submit" size="lg" className="mt-2 w-full bg-gradient-to-r from-blue-500 to-indigo-600 text-white font-bold py-3.5 rounded-xl shadow-lg" disabled={busy}>
            {busy ? <Loader2 className="animate-spin" size={18} /> : mode === "signup" ? "Ro'yxatdan o'tish" : "Kirish"}
          </Button>

          <button
            type="button"
            onClick={() => { setMode(mode === "signup" ? "signin" : "signup"); setErr(null); }}
            className="w-full text-center text-xs text-white/50 hover:text-white/80 transition-colors pt-2"
          >
            {mode === "signup" ? "Hisobingiz bormi? Kirish" : "Hisob yo'qmi? Ro'yxatdan o'ting"}
          </button>
        </form>
      </Card>

      <p className="mt-8 text-center text-[10px] text-white/30">
        Har bir foydalanuvchi faqat o'zining MT5 hisob ma'lumotlarini ko'radi. Ma'lumotlar xavfsiz saqlanadi.
      </p>
    </div>
  );
}
