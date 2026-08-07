import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { Card } from "@/components/ui/Card";
import { fmtMoney, fmtNum, timeAgo, fmtDateShort } from "@/lib/utils";
import type { TradeHistory } from "@/lib/types";
import { Loader2, Bot, Search, Calendar, X } from "lucide-react";
import pubgLoader from "@/assets/pubg-loader.svg";
import { EmptyLine } from "./DashboardPage";
import { useMemo, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { guestMock } from "@/lib/guestMock";
import { TradingChartModal } from "@/components/TradingChartModal";

export function HistoryPage() {
  const { user } = useAuth();
  const isGuest = user?.id === "guest";

  // Filter states
  const [searchSymbol, setSearchSymbol] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [selectedTrade, setSelectedTrade] = useState<TradeHistory | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["trade_history", user?.id],
    queryFn: async () => {
      if (isGuest) {
        return guestMock.getHistory();
      }
      const { data } = await supabase
        .from("trade_history")
        .select("*")
        .order("closed_at", { ascending: false });
      return (data ?? []) as TradeHistory[];
    },
  });

  const filteredData = useMemo(() => {
    const all = data ?? [];
    return all.filter((t) => {
      if (searchSymbol && !t.symbol.toLowerCase().includes(searchSymbol.toLowerCase())) {
        return false;
      }
      if (startDate) {
        const start = new Date(startDate);
        if (new Date(t.closed_at) < start) return false;
      }
      if (endDate) {
        const end = new Date(endDate);
        end.setHours(23, 59, 59, 999);
        if (new Date(t.closed_at) > end) return false;
      }
      return true;
    });
  }, [data, searchSymbol, startDate, endDate]);

  const stats = useMemo(() => {
    const all = filteredData;
    const pl = all.reduce((s, t) => s + Number(t.profit || 0), 0);
    const wins = all.filter((t) => Number(t.profit) > 0).length;
    return {
      total: all.length,
      pl,
      wr: all.length ? Math.round((wins / all.length) * 100) : 0,
    };
  }, [filteredData]);

  return (
    <div className="space-y-3">
      {/* Filters Bar */}
      <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-3 flex flex-wrap items-center gap-3 shadow-[inset_0_1px_1px_rgba(255,255,255,0.05)] backdrop-blur-md">
        {/* Symbol Search */}
        <div className="relative flex-1 min-w-[150px]">
          <Search size={14} className="absolute left-3 top-2.5 text-white/30" />
          <input
            type="text"
            placeholder="Simvol orqali qidirish..."
            value={searchSymbol}
            onChange={(e) => setSearchSymbol(e.target.value)}
            className="w-full bg-black/20 border border-white/5 rounded-xl pl-9 pr-3 py-1.5 text-xs text-white placeholder:text-white/20 focus:outline-none focus:border-blue-500/40 transition-colors"
          />
        </div>

        {/* Start Date */}
        <div className="relative flex-1 min-w-[150px]">
          <span className="absolute left-3 top-2 text-[10px] text-white/30 pointer-events-none uppercase font-bold">Dan:</span>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            className="w-full bg-black/20 border border-white/5 rounded-xl pl-12 pr-3 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500/40 transition-colors cursor-pointer scheme-dark"
          />
        </div>

        {/* End Date */}
        <div className="relative flex-1 min-w-[150px]">
          <span className="absolute left-3 top-2 text-[10px] text-white/30 pointer-events-none uppercase font-bold">Gacha:</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            className="w-full bg-black/20 border border-white/5 rounded-xl pl-16 pr-3 py-1.5 text-xs text-white focus:outline-none focus:border-blue-500/40 transition-colors cursor-pointer scheme-dark"
          />
        </div>

        {/* Clear Filters */}
        {(searchSymbol || startDate || endDate) && (
          <button
            onClick={() => {
              setSearchSymbol("");
              setStartDate("");
              setEndDate("");
            }}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-bold text-white/60 hover:text-white bg-white/5 hover:bg-white/10 rounded-xl border border-white/5 transition-all cursor-pointer"
          >
            <X size={12} />
            Tozalash
          </button>
        )}
      </div>

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
        <div className="flex justify-center w-full py-10">
          <img src={pubgLoader} className="mx-auto w-32 h-32 opacity-80" alt="Yuklanmoqda..." />
        </div>
      ) : !filteredData.length ? (
        <Card>
          <EmptyLine text="Mos keluvchi yopilgan savdolar topilmadi." />
        </Card>
      ) : (
        <div className="space-y-2">
          {filteredData.map((t) => {
            const profit = Number(t.profit);
            const isBuy = t.side?.toUpperCase() === "BUY";
            return (
              <Card 
                key={t.id} 
                className="p-3 flex flex-col gap-2 cursor-pointer hover:bg-white/[0.04] transition-colors border border-transparent hover:border-white/10"
                onClick={() => setSelectedTrade(t)}
              >
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
                        {fmtNum(t.volume, 2)} lot &bull; {fmtNum(t.open_price, 5)} → {fmtNum(t.close_price, 5)} &bull; {fmtDateShort(t.closed_at)}
                      </p>
                    </div>
                  </div>
                  <p className={`tabular text-sm font-black ${profit >= 0 ? "text-success" : "text-danger"}`}>
                    {profit >= 0 ? "+" : ""}{fmtMoney(profit)}
                  </p>
                </div>
                {/* Badges Row */}
                {(t.agreed_strategies?.length || t.ai_used) ? (
                  <div className="flex items-center gap-1.5 flex-wrap mt-1">
                    {t.ai_used && (
                      <div className="flex items-center gap-1 bg-purple-500/20 text-purple-400 border border-purple-500/30 px-2 py-0.5 rounded-md text-[9px] font-bold tracking-wider">
                        <Bot size={10} /> AI
                      </div>
                    )}
                    {t.agreed_strategies?.map((strat) => (
                      <div key={strat} className="bg-white/10 text-white/70 border border-white/5 px-2 py-0.5 rounded-md text-[9px] font-bold tracking-wider uppercase">
                        {strat}
                      </div>
                    ))}
                  </div>
                ) : null}
              </Card>
            );
          })}
        </div>
      )}

      {selectedTrade && (
        <TradingChartModal
          isOpen={!!selectedTrade}
          onClose={() => setSelectedTrade(null)}
          symbol={selectedTrade.symbol}
          historyTrade={selectedTrade}
        />
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
