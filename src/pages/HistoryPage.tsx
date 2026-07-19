import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { Card } from "@/components/ui/Card";
import { fmtMoney, fmtNum, timeAgo } from "@/lib/utils";
import type { TradeHistory } from "@/lib/types";
import { Loader2 } from "lucide-react";
import { EmptyLine } from "./DashboardPage";
import { useMemo } from "react";
import { useAuth } from "@/hooks/useAuth";
import { guestMock } from "@/lib/guestMock";

export function HistoryPage() {
  const { user } = useAuth();
  const isGuest = user?.id === "guest";

  const { data, isLoading } = useQuery({
    queryKey: ["trade_history", user?.id],
    queryFn: async () => {
      if (isGuest) {
        return guestMock.getHistory();
      }
      const { data } = await supabase
        .from("trade_history")
        .select("*")
        .order("closed_at", { ascending: false })
        .limit(100);
      return (data ?? []) as TradeHistory[];
    },
  });

  const stats = useMemo(() => {
    const all = data ?? [];
    const pl = all.reduce((s, t) => s + Number(t.profit || 0), 0);
    const wins = all.filter((t) => Number(t.profit) > 0).length;
    return {
      total: all.length,
      pl,
      wr: all.length ? Math.round((wins / all.length) * 100) : 0,
    };
  }, [data]);

  return (
    <div className="space-y-3">
      <Card className="grid grid-cols-3 gap-2 p-4">
        <Stat label="Savdolar" value={String(stats.total)} />
        <Stat
          label="Umumiy P/L"
          value={fmtMoney(stats.pl)}
          tone={stats.pl >= 0 ? "success" : "danger"}
        />
        <Stat label="Win rate" value={`${stats.wr}%`} />
      </Card>

      {isLoading ? (
        <Loader2 className="mx-auto my-10 animate-spin text-brand-soft" size={22} />
      ) : !data?.length ? (
        <Card>
          <EmptyLine text="Hali yopilgan savdo yo'q." />
        </Card>
      ) : (
        <div className="space-y-2">
          {data.map((t) => {
            const profit = Number(t.profit);
            const isBuy = t.side?.toUpperCase() === "BUY";
            return (
              <Card key={t.id} className="p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex min-w-0 items-center gap-3">
                    <span
                      className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl text-[10px] font-black ${
                        isBuy ? "bg-success/20 text-success" : "bg-danger/20 text-danger"
                      }`}
                    >
                      {isBuy ? "BUY" : "SELL"}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-bold">{t.symbol}</p>
                      <p className="truncate text-[11px] text-fg-dim">
                        {fmtNum(t.open_price, 5)} → {fmtNum(t.close_price, 5)} · {timeAgo(t.closed_at)}
                      </p>
                    </div>
                  </div>
                  <p className={`tabular text-sm font-black ${profit >= 0 ? "text-success" : "text-danger"}`}>
                    {profit >= 0 ? "+" : ""}{fmtMoney(profit)}
                  </p>
                </div>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value, tone }: { label: string; value: string; tone?: "success" | "danger" }) {
  const cls = tone === "success" ? "text-success" : tone === "danger" ? "text-danger" : "text-fg";
  return (
    <div className="text-center">
      <p className="text-[10px] uppercase tracking-wider text-fg-dim">{label}</p>
      <p className={`tabular text-lg font-black ${cls}`}>{value}</p>
    </div>
  );
}
