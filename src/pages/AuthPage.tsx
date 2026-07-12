import { useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { LineChart, Loader2 } from "lucide-react";

export function AuthPage() {
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true); setErr(null);
    try {
      const fn = mode === "signin" ? supabase.auth.signInWithPassword : supabase.auth.signUp;
      const { error } = await fn.call(supabase.auth, {
        email, password,
        options: mode === "signup" ? { emailRedirectTo: window.location.origin } : undefined,
      } as any);
      if (error) throw error;
    } catch (e: any) {
      setErr(e.message ?? "Xatolik yuz berdi");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-full w-full max-w-md flex-col justify-center px-6 py-10">
      <div className="mb-8 flex flex-col items-center gap-3 text-center">
        <div className="grid h-16 w-16 place-items-center rounded-3xl bg-gradient-to-br from-brand-strong to-brand shadow-2xl shadow-brand-strong/40">
          <LineChart className="text-white" size={30} strokeWidth={2.4} />
        </div>
        <h1 className="text-3xl font-black tracking-tight">TraderPanel</h1>
        <p className="max-w-xs text-sm text-fg-dim">
          AI-forex savdo botingizni real vaqt rejimida boshqaring va kuzating.
        </p>
      </div>

      <Card className="p-6">
        <div className="mb-5 grid grid-cols-2 gap-1 rounded-2xl bg-black/20 p-1">
          {(["signin", "signup"] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`rounded-xl px-3 py-2 text-sm font-semibold transition-all ${
                mode === m ? "bg-gradient-to-br from-brand to-brand-strong text-white shadow" : "text-fg-dim"
              }`}
            >
              {m === "signin" ? "Kirish" : "Ro'yxatdan o'tish"}
            </button>
          ))}
        </div>

        <form onSubmit={submit} className="space-y-3">
          <label className="block text-xs font-medium text-fg-dim">Email</label>
          <input
            type="email" required autoComplete="email"
            value={email} onChange={(e) => setEmail(e.target.value)}
            placeholder="siz@example.com"
            className="w-full rounded-2xl border border-white/10 bg-black/25 px-4 py-3 text-sm outline-none placeholder:text-fg-dim focus:border-brand/60"
          />
          <label className="block text-xs font-medium text-fg-dim">Parol</label>
          <input
            type="password" required minLength={6} autoComplete={mode === "signin" ? "current-password" : "new-password"}
            value={password} onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="w-full rounded-2xl border border-white/10 bg-black/25 px-4 py-3 text-sm outline-none placeholder:text-fg-dim focus:border-brand/60"
          />
          {err && (
            <div className="rounded-xl bg-danger/15 px-3 py-2 text-xs text-danger">{err}</div>
          )}
          <Button type="submit" size="lg" className="mt-2 w-full" disabled={busy}>
            {busy ? <Loader2 className="animate-spin" size={18} /> : mode === "signin" ? "Kirish" : "Ro'yxatdan o'tish"}
          </Button>
        </form>
      </Card>

      <p className="mt-6 text-center text-xs text-fg-dim">
        Ma'lumotlar Lovable Cloud'da xavfsiz saqlanadi.
      </p>
    </div>
  );
}
