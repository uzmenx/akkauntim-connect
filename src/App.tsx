import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { BottomNav } from "@/components/BottomNav";
import { AppHeader } from "@/components/AppHeader";
import { AuthPage } from "@/pages/AuthPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { PositionsPage } from "@/pages/PositionsPage";
import { SignalsPage } from "@/pages/SignalsPage";
import { HistoryPage } from "@/pages/HistoryPage";
import { SettingsPage } from "@/pages/SettingsPage";
import { Loader2 } from "lucide-react";

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

  return (
    <div className="mx-auto flex min-h-full w-full max-w-md flex-col pb-28">
      <AppHeader title={title} user={user} />
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
      <BottomNav />
    </div>
  );
}
