import { Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { AuthPage } from "@/pages/AuthPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { PositionsPage } from "@/pages/PositionsPage";
import { SignalsPage } from "@/pages/SignalsPage";
import { HistoryPage } from "@/pages/HistoryPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { SubscriptionPage } from "@/pages/SubscriptionPage";
import { Loader2, ChevronLeft, RotateCcw, Save, Check } from "lucide-react";
import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";

const titles: Record<string, string> = {
  "/": "Dashboard",
  "/positions": "Open positions",
  "/signals": "AI signals",
  "/history": "Trade history",
  "/settings": "Bot settings",
  "/pricing": "Ta'riflar va Obuna",
};

export default function App() {
  const { user, loading } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [settingsState, setSettingsState] = useState({ busy: false, saved: false });

  useEffect(() => {
    const handler = (e: Event) => {
      const customEvent = e as CustomEvent;
      if (customEvent.detail) {
        setSettingsState(customEvent.detail);
      }
    };
    window.addEventListener("settingsState", handler);
    return () => window.removeEventListener("settingsState", handler);
  }, []);

  // Global Realtime listener — refresh every affected query key instantly
  useEffect(() => {
    if (!user || user.id === "guest") return;

    const invalidate = (keys: string[]) => {
      keys.forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
    };

    const channel = supabase
      .channel('global_realtime')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'bot_status' },
        () => invalidate(["bot_status"]))
      .on('postgres_changes', { event: '*', schema: 'public', table: 'positions' },
        () => invalidate(["positions", "positions_full"]))
      .on('postgres_changes', { event: '*', schema: 'public', table: 'ai_signals' },
        () => invalidate(["ai_signals"]))
      .on('postgres_changes', { event: '*', schema: 'public', table: 'trade_history' },
        () => invalidate(["trade_history", "history_today"]))
      .on('postgres_changes', { event: '*', schema: 'public', table: 'bot_settings' },
        () => invalidate(["bot_settings"]))
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [user, qc]);

  if (loading) {
    return (
      <div className="grid min-h-full place-items-center">
        <Loader2 className="animate-spin text-brand-soft" size={28} />
      </div>
    );
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/auth" element={<AuthPage />} />
        <Route path="*" element={<Navigate to="/auth" replace />} />
      </Routes>
    );
  }

  const title = titles[location.pathname] ?? "TraderPanel";
  const isDashboard = location.pathname === "/";

  return (
    <div className="mx-auto flex min-h-full w-full max-w-md flex-col pb-[max(env(safe-area-inset-bottom),1.5rem)]">
      {!isDashboard && (
        <header className="sticky top-0 z-40 flex items-center justify-between px-5 py-4 pt-[max(env(safe-area-inset-top),1rem)] bg-bg-deep/85 backdrop-blur-lg border-b border-white/5">
          <div className="flex items-center gap-3">
            <button 
              onClick={() => navigate(-1)} 
              className="grid h-10 w-10 place-items-center rounded-xl bg-white/5 hover:bg-white/10 active:scale-95 transition-all text-white border border-white/10"
              aria-label="Go back"
            >
              <ChevronLeft size={20} />
            </button>
            <h1 className="text-base font-bold text-white">{title}</h1>
          </div>
          {location.pathname === "/settings" && (
            <div className="flex items-center gap-2">
              <button 
                onClick={() => window.dispatchEvent(new Event('saveSettings'))}
                disabled={settingsState.busy}
                className={cn(
                  "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all active:scale-95 cursor-pointer border",
                  settingsState.saved 
                    ? "bg-green-500/10 text-green-400 border-green-500/20"
                    : "bg-brand/10 text-brand border-brand/20 hover:bg-brand/20"
                )}
              >
                {settingsState.busy ? (
                  <Loader2 className="animate-spin" size={14} />
                ) : settingsState.saved ? (
                  <Check size={14} />
                ) : (
                  <Save size={14} />
                )}
                <span>{settingsState.saved ? "Saqlandi" : "Saqlash"}</span>
              </button>

              <button 
                onClick={() => window.dispatchEvent(new Event('resetSettings'))}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-all text-xs font-bold border border-red-500/20 active:scale-95 cursor-pointer"
              >
                <RotateCcw size={14} />
                <span>Reset</span>
              </button>
            </div>
          )}
        </header>
      )}
      <main className="flex-1 px-4">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/positions" element={<PositionsPage />} />
          <Route path="/signals" element={<SignalsPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/pricing" element={<SubscriptionPage />} />
          <Route path="/auth" element={<Navigate to="/" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
