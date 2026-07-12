import { Bell, LogOut } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { supabase } from "@/integrations/supabase/client";
import type { User } from "@supabase/supabase-js";

export function AppHeader({ title, user }: { title: string; user: User | null }) {
  const initials =
    user?.email?.slice(0, 2).toUpperCase() ?? "TP";
  return (
    <header className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-5 pb-4 pt-[max(env(safe-area-inset-top),1rem)]">
      <div className="flex min-w-0 items-center gap-3">
        <div className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-gradient-to-br from-brand-strong to-brand text-sm font-black text-white shadow-lg shadow-brand-strong/40">
          {initials}
        </div>
        <div className="min-w-0">
          <p className="truncate text-xs font-medium text-fg-dim">TraderPanel</p>
          <h1 className="truncate text-lg font-bold tracking-tight">{title}</h1>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="glass" size="icon" aria-label="Notifications">
          <Bell size={18} />
        </Button>
        <Button
          variant="glass"
          size="icon"
          aria-label="Sign out"
          onClick={() => supabase.auth.signOut()}
        >
          <LogOut size={18} />
        </Button>
      </div>
    </header>
  );
}
