import { NavLink } from "react-router-dom";
import { Home, Activity, Brain, History, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const items = [
  { to: "/", icon: Home, label: "Dashboard" },
  { to: "/positions", icon: Activity, label: "Positions" },
  { to: "/signals", icon: Brain, label: "Signals" },
  { to: "/history", icon: History, label: "History" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

export function BottomNav() {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 px-3 pb-[max(env(safe-area-inset-bottom),0.75rem)] pt-2"
      aria-label="Primary"
    >
      <div className="glass-strong mx-auto flex max-w-md items-center justify-between rounded-3xl px-2 py-2">
        {items.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "flex flex-1 flex-col items-center gap-0.5 rounded-2xl px-2 py-2 text-[10px] font-medium transition-colors",
                isActive ? "text-white" : "text-fg-dim hover:text-fg-muted",
              )
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={cn(
                    "grid h-8 w-8 place-items-center rounded-xl transition-all",
                    isActive
                      ? "bg-gradient-to-br from-brand to-brand-strong shadow-lg shadow-brand-strong/40"
                      : "bg-transparent",
                  )}
                >
                  <Icon size={16} strokeWidth={2.2} />
                </span>
                <span className="truncate">{label}</span>
              </>
            )}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
