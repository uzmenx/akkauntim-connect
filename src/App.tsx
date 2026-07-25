import { Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { AuthPage } from "@/pages/AuthPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { PositionsPage } from "@/pages/PositionsPage";
import { SignalsPage } from "@/pages/SignalsPage";
import { HistoryPage } from "@/pages/HistoryPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { SubscriptionPage } from "@/pages/SubscriptionPage";
import { BacktestPage } from "@/pages/BacktestPage";
import { LandingPage } from "@/pages/LandingPage";
import { ConnectorsPage } from "@/pages/ConnectorsPage";
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
  "/backtest": "Backtest Tizimi",
  "/connectors": "Connectors Hub",
};

export default function App() {
  const { user, loading } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [settingsState, setSettingsState] = useState({ busy: false, saved: false, hasChanges: false });

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
      .on('postgres_changes', { event: '*', schema: 'public', table: 'pending_orders' },
        () => invalidate(["pending_orders"]))
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
        <Route path="/" element={<LandingPage />} />
        <Route path="/auth" element={<AuthPage />} />
        <Route path="/connectors" element={<ConnectorsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    );
  }

  const title = titles[location.pathname] ?? "TraderPanel";
  const isDashboard = location.pathname === "/";

  return (
    <div className="mx-auto flex h-[100dvh] w-full flex-col overflow-hidden">
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
          {location.pathname === "/settings" && settingsState.hasChanges && (
            <div className="flex items-center gap-2">
              <button 
                onClick={() => window.dispatchEvent(new Event('saveSettings'))}
                disabled={settingsState.busy}
                className={cn(
                  "flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-xs font-bold transition-all active:scale-95 cursor-pointer shadow-lg",
                  settingsState.saved 
                    ? "bg-emerald-500 text-white shadow-emerald-500/20"
                    : "bg-blue-600 hover:bg-blue-500 text-white shadow-blue-600/20"
                )}
              >
                {settingsState.busy ? (
                  <Loader2 className="animate-spin" size={14} />
                ) : (
                  <Check size={16} strokeWidth={3} />
                )}
                <span>{settingsState.saved ? "Saqlandi" : "Saqlash"}</span>
              </button>

              <button 
                onClick={() => window.dispatchEvent(new Event('resetSettings'))}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 hover:bg-red-500/20 hover:text-red-400 text-white/60 transition-all text-xs font-bold active:scale-95 cursor-pointer"
              >
                <span>Standart</span>
              </button>
            </div>
          )}
        </header>
      )}
      <main className="flex-1 w-full overflow-y-auto no-scrollbar relative">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/positions" element={<PositionsPage />} />
          <Route path="/signals" element={<SignalsPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/pricing" element={<SubscriptionPage />} />
          <Route path="/backtest" element={<BacktestPage />} />
          <Route path="/connectors" element={<ConnectorsPage />} />
          <Route path="/auth" element={<Navigate to="/" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
