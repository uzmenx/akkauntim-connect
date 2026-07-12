import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { Card } from "@/components/ui/Card";
import { fmtMoney, fmtNum, timeAgo } from "@/lib/utils";
import type { Position } from "@/lib/types";
import { Loader2 } from "lucide-react";
import { EmptyLine } from "./DashboardPage";

export function PositionsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["positions_full"],
    queryFn: async () => {
      const { data } = await supabase.from("positions").select("*").order("opened_at", { ascending: false });
      return (data ?? []) as Position[];
    },
    refetchInterval: 4000,
  });

  if (isLoading) {
    return <Loader2 className="mx-auto my-10 animate-spin text-brand-soft" size={22} />;
  }

  if (!data?.length) {
    return (
      <Card>
        <EmptyLine text="Ochiq pozitsiya yo'q. Bot yangi imkoniyat topganda bu yerda ko'rinadi." />
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {data.map((p) => {
        const isBuy = p.side?.toUpperCase() === "BUY";
        const profit = Number(p.profit ?? 0);
        return (
          <Card key={p.id} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex min-w-0 items-center gap-3">
                <span
                  className={`grid h-10 w-10 shrink-0 place-items-center rounded-2xl text-xs font-black ${
                    isBuy ? "bg-success/20 text-success" : "bg-danger/20 text-danger"
                  }`}
                >
                  {isBuy ? "BUY" : "SELL"}
                </span>
                <div className="min-w-0">
                  <p className="truncate text-base font-bold">{p.symbol}</p>
                  <p className="truncate text-[11px] text-fg-dim">
                    Ticket #{p.ticket} · {timeAgo(p.opened_at)} oldin
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className={`tabular text-lg font-black ${profit >= 0 ? "text-success" : "text-danger"}`}>
                  {profit >= 0 ? "+" : ""}{fmtMoney(profit)}
                </p>
                <p className="text-[11px] text-fg-dim">{fmtNum(p.volume, 2)} lot</p>
              </div>
            </div>
            <div className="mt-3 grid grid-cols-4 gap-2 text-[11px]">
              <Field label="Open" value={fmtNum(p.open_price, 5)} />
              <Field label="Now" value={fmtNum(p.current_price, 5)} />
              <Field label="SL" value={fmtNum(p.stop_loss, 5)} tone="danger" />
              <Field label="TP" value={fmtNum(p.take_profit, 5)} tone="success" />
            </div>
          </Card>
        );
      })}
    </div>
  );
}

function Field({ label, value, tone }: { label: string; value: string; tone?: "success" | "danger" }) {
  const cls = tone === "success" ? "text-success" : tone === "danger" ? "text-danger" : "text-fg";
  return (
    <div className="rounded-xl bg-black/20 px-2 py-1.5">
      <p className="text-[9px] uppercase tracking-wider text-fg-dim">{label}</p>
      <p className={`tabular text-xs font-bold ${cls}`}>{value}</p>
    </div>
  );
}
