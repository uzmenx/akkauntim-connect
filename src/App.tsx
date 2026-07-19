import { Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { AuthPage } from "@/pages/AuthPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { PositionsPage } from "@/pages/PositionsPage";
import { SignalsPage } from "@/pages/SignalsPage";
import { HistoryPage } from "@/pages/HistoryPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { SubscriptionPage } from "@/pages/SubscriptionPage";
import { Loader2, ChevronLeft, RotateCcw } from "lucide-react";
import { useEffect } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useQueryClient } from "@tanstack/react-query";

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

  // Global Realtime listener
  useEffect(() => {
    if (!user || user.id === "guest") return;
    
    const channel = supabase
      .channel('global_realtime')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'bot_status' }, () => qc.invalidateQueries({ queryKey: ["bot_status"] }))
      .on('postgres_changes', { event: '*', schema: 'public', table: 'positions' }, () => qc.invalidateQueries({ queryKey: ["positions"] }))
      .on('postgres_changes', { event: '*', schema: 'public', table: 'ai_signals' }, () => qc.invalidateQueries({ queryKey: ["ai_signals"] }))
      .on('postgres_changes', { event: '*', schema: 'public', table: 'trade_history' }, () => qc.invalidateQueries({ queryKey: ["trade_history"] }))
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
        <header className="flex items-center justify-between px-5 py-4 pt-[max(env(safe-area-inset-top),1rem)]">
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
            <button 
              onClick={() => window.dispatchEvent(new Event('resetSettings'))}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-all text-xs font-bold border border-red-500/20 active:scale-95"
            >
              <RotateCcw size={14} />
              <span>Reset</span>
            </button>
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
