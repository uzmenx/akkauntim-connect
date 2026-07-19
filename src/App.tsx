import { Routes, Route, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { AuthPage } from "@/pages/AuthPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { PositionsPage } from "@/pages/PositionsPage";
import { SignalsPage } from "@/pages/SignalsPage";
import { HistoryPage } from "@/pages/HistoryPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { Loader2, ChevronLeft } from "lucide-react";

const titles: Record<string, string> = {
  "/": "Dashboard",
  "/positions": "Open positions",
  "/signals": "AI signals",
  "/history": "Trade history",
  "/settings": "Bot settings",
};

export default function App() {
  const { user, loading } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

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
        <header className="flex items-center gap-3 px-5 py-4 pt-[max(env(safe-area-inset-top),1rem)]">
          <button 
            onClick={() => navigate(-1)} 
            className="grid h-10 w-10 place-items-center rounded-xl bg-white/5 hover:bg-white/10 active:scale-95 transition-all text-white border border-white/10"
            aria-label="Go back"
          >
            <ChevronLeft size={20} />
          </button>
          <h1 className="text-base font-bold text-white">{title}</h1>
        </header>
      )}
      <main className="flex-1 px-4">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/positions" element={<PositionsPage />} />
          <Route path="/signals" element={<SignalsPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/auth" element={<Navigate to="/" replace />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
