import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Loader2, Save } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import type { BotSettings } from "@/lib/types";

export function SettingsPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["bot_settings", user?.id],
    queryFn: async () => {
      const { data } = await supabase.from("bot_settings").select("*").maybeSingle();
      return data as BotSettings | null;
    },
  });

  const [form, setForm] = useState<Partial<BotSettings>>({});
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (data) setForm(data);
    else setForm({
      symbols: ["EURUSD"], risk_per_trade: 0.02, max_daily_loss: 0.10,
      min_confidence: 50, max_lot_size: 5.0,
    });
  }, [data]);

  async function save() {
    if (!user) return;
    setBusy(true); setSaved(false);
    await supabase.from("bot_settings").upsert(
      {
        user_id: user.id,
        symbols: form.symbols ?? ["EURUSD"],
        risk_per_trade: Number(form.risk_per_trade ?? 0.02),
        max_daily_loss: Number(form.max_daily_loss ?? 0.10),
        min_confidence: Number(form.min_confidence ?? 50),
        max_lot_size: Number(form.max_lot_size ?? 5.0),
      },
      { onConflict: "user_id" },
    );
    await qc.invalidateQueries({ queryKey: ["bot_settings"] });
    setBusy(false); setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  if (isLoading) return <Loader2 className="mx-auto my-10 animate-spin text-brand-soft" size={22} />;

  const symbolsStr = (form.symbols ?? []).join(", ");

  return (
    <div className="space-y-4">
      <Card>
        <h3 className="mb-1 font-bold">Savdo juftliklari</h3>
        <p className="mb-3 text-xs text-fg-dim">Vergul bilan ajrating (masalan: EURUSD, GBPUSD)</p>
        <input
          value={symbolsStr}
          onChange={(e) =>
            setForm((f) => ({
              ...f,
              symbols: e.target.value.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean),
            }))
          }
          className="w-full rounded-2xl border border-white/10 bg-black/25 px-4 py-3 text-sm outline-none focus:border-brand/60"
        />
      </Card>

      <Card>
        <h3 className="mb-3 font-bold">Risk parametrlari</h3>
        <div className="space-y-4">
          <Slider
            label="Har bir savdo uchun risk"
            value={Number(form.risk_per_trade ?? 0.02)}
            min={0.001} max={0.1} step={0.001}
            format={(v) => `${(v * 100).toFixed(1)}%`}
            onChange={(v) => setForm((f) => ({ ...f, risk_per_trade: v }))}
          />
          <Slider
            label="Kunlik maksimal zarar"
            value={Number(form.max_daily_loss ?? 0.10)}
            min={0.01} max={0.5} step={0.01}
            format={(v) => `${(v * 100).toFixed(0)}%`}
            onChange={(v) => setForm((f) => ({ ...f, max_daily_loss: v }))}
          />
          <Slider
            label="Minimal AI ishonch"
            value={Number(form.min_confidence ?? 50)}
            min={0} max={100} step={1}
            format={(v) => `${v}%`}
            onChange={(v) => setForm((f) => ({ ...f, min_confidence: v }))}
          />
          <Slider
            label="Maksimal lot hajmi"
            value={Number(form.max_lot_size ?? 5.0)}
            min={0.01} max={20} step={0.01}
            format={(v) => `${v.toFixed(2)}`}
            onChange={(v) => setForm((f) => ({ ...f, max_lot_size: v }))}
          />
        </div>
      </Card>

      <Button size="lg" className="w-full" onClick={save} disabled={busy}>
        {busy ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
        {saved ? "Saqlandi" : "Sozlamalarni saqlash"}
      </Button>
    </div>
  );
}

function Slider({
  label, value, min, max, step, onChange, format,
}: {
  label: string; value: number; min: number; max: number; step: number;
  onChange: (v: number) => void; format: (v: number) => string;
}) {
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <label className="text-xs font-medium text-fg-muted">{label}</label>
        <span className="tabular rounded-full bg-white/10 px-2 py-0.5 text-xs font-bold">
          {format(value)}
        </span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-[color:var(--color-brand)]"
      />
    </div>
  );
}
