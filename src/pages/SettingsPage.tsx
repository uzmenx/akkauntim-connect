import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Loader2, Save, Sparkles, Settings2, Sliders, Play, Code } from "lucide-react";
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
    if (data) {
      setForm(data);
    } else {
      setForm({
        symbols: ["EURUSD", "GBPUSD", "XAUUSD"],
        risk_per_trade: 0.02,
        max_daily_loss: 0.10,
        min_confidence: 50,
        max_lot_size: 5.0,
        timeframe_major: "H1",
        timeframe_minor: "M5",
        ai_model: "claude-3-5-sonnet-20241022",
        system_prompt: "Sen professional Forex treyderi va fundamental tahlilchisisan. Texnik SMC va Garmonik patternlar hamda iqtisodiy yangiliklarni birlashtirib, optimal savdo qarorini qabul qilasan.",
        risk_level_single_confirmation: 0.01,
        risk_level_multiple_confirmation: 0.02
      });
    }
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
        timeframe_major: form.timeframe_major ?? "H1",
        timeframe_minor: form.timeframe_minor ?? "M5",
        ai_model: form.ai_model ?? "claude-3-5-sonnet-20241022",
        system_prompt: form.system_prompt ?? "",
        risk_level_single_confirmation: Number(form.risk_level_single_confirmation ?? 0.01),
        risk_level_multiple_confirmation: Number(form.risk_level_multiple_confirmation ?? 0.02)
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
    <div className="space-y-4 pb-10">
      {/* 1. Market Settings */}
      <Card className="glass relative overflow-hidden p-5">
        <div className="flex items-center gap-2 mb-4 text-brand">
          <Settings2 size={18} />
          <h3 className="font-bold text-sm tracking-wide uppercase">Bozor va Timeframe</h3>
        </div>
        
        <div className="space-y-4">
          <div>
            <label className="mb-2 block text-xs font-semibold text-fg-muted">Faol savdo juftliklari</label>
            <input
              value={symbolsStr}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  symbols: e.target.value.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean),
                }))
              }
              className="w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-sm text-fg outline-none focus:border-brand/60 transition-all"
              placeholder="EURUSD, GBPUSD, XAUUSD"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-2 block text-xs font-semibold text-fg-muted">Major Timeframe</label>
              <select
                value={form.timeframe_major ?? "H1"}
                onChange={(e) => setForm((f) => ({ ...f, timeframe_major: e.target.value }))}
                className="w-full rounded-xl border border-white/10 bg-black/40 px-3 py-3 text-sm text-fg outline-none focus:border-brand/60"
              >
                <option value="H4">H4 (4 soat)</option>
                <option value="H1">H1 (1 soat)</option>
                <option value="M30">M30 (30 daqiqa)</option>
              </select>
            </div>
            <div>
              <label className="mb-2 block text-xs font-semibold text-fg-muted">Minor Timeframe</label>
              <select
                value={form.timeframe_minor ?? "M5"}
                onChange={(e) => setForm((f) => ({ ...f, timeframe_minor: e.target.value }))}
                className="w-full rounded-xl border border-white/10 bg-black/40 px-3 py-3 text-sm text-fg outline-none focus:border-brand/60"
              >
                <option value="M15">M15 (15 daqiqa)</option>
                <option value="M5">M5 (5 daqiqa)</option>
                <option value="M1">M1 (1 daqiqa)</option>
              </select>
            </div>
          </div>
        </div>
      </Card>

      {/* 2. Advanced AI Configuration */}
      <Card className="glass p-5">
        <div className="flex items-center gap-2 mb-4 text-brand">
          <Sparkles size={18} />
          <h3 className="font-bold text-sm tracking-wide uppercase">AI Neyrotizim Sozlamalari</h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="mb-2 block text-xs font-semibold text-fg-muted">AI Model</label>
            <select
              value={form.ai_model ?? "claude-3-5-sonnet-20241022"}
              onChange={(e) => setForm((f) => ({ ...f, ai_model: e.target.value }))}
              className="w-full rounded-xl border border-white/10 bg-black/40 px-3 py-3 text-sm text-fg outline-none focus:border-brand/60"
            >
              <option value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet (Tavsiya etiladi)</option>
              <option value="claude-3-5-haiku-20241022">Claude 3.5 Haiku</option>
            </select>
          </div>

          <div>
            <label className="mb-2 block text-xs font-semibold text-fg-muted">AI Tahlil Tizimi Prompti</label>
            <textarea
              rows={4}
              value={form.system_prompt ?? ""}
              onChange={(e) => setForm((f) => ({ ...f, system_prompt: e.target.value }))}
              className="w-full rounded-xl border border-white/10 bg-black/40 px-4 py-3 text-xs text-fg outline-none focus:border-brand/60 font-mono transition-all"
            />
          </div>
        </div>
      </Card>

      {/* 3. Risk Management */}
      <Card className="glass p-5">
        <div className="flex items-center gap-2 mb-4 text-brand">
          <Sliders size={18} />
          <h3 className="font-bold text-sm tracking-wide uppercase">Riskni Boshqarish</h3>
        </div>

        <div className="space-y-4">
          <Slider
            label="Maksimal Lot Hajmi"
            value={Number(form.max_lot_size ?? 5.0)}
            min={0.01} max={10} step={0.01}
            format={(v) => `${v.toFixed(2)} lot`}
            onChange={(v) => setForm((f) => ({ ...f, max_lot_size: v }))}
          />
          <Slider
            label="Kunlik Maksimal Zarar (Max Drawdown)"
            value={Number(form.max_daily_loss ?? 0.10)}
            min={0.01} max={0.30} step={0.01}
            format={(v) => `${(v * 100).toFixed(0)}% balansdan`}
            onChange={(v) => setForm((f) => ({ ...f, max_daily_loss: v }))}
          />
          <Slider
            label="1 ta Strategiya tasdig'ida Risk (Single Confirmation)"
            value={Number(form.risk_level_single_confirmation ?? 0.01)}
            min={0.005} max={0.05} step={0.001}
            format={(v) => `${(v * 100).toFixed(1)}%`}
            onChange={(v) => setForm((f) => ({ ...f, risk_level_single_confirmation: v }))}
          />
          <Slider
            label="Ko'p strategiyali tasdiqlashda Risk (Multiple Confirmation)"
            value={Number(form.risk_level_multiple_confirmation ?? 0.02)}
            min={0.01} max={0.10} step={0.002}
            format={(v) => `${(v * 100).toFixed(1)}%`}
            onChange={(v) => setForm((f) => ({ ...f, risk_level_multiple_confirmation: v }))}
          />
        </div>
      </Card>

      {/* Save Button */}
      <Button size="lg" className="w-full bg-brand hover:bg-brand-strong text-white font-bold py-3.5 rounded-xl shadow-lg transition-all" onClick={save} disabled={busy}>
        {busy ? <Loader2 className="animate-spin" size={18} /> : <Save size={18} />}
        {saved ? "Muvaffaqiyatli saqlandi!" : "Barcha sozlamalarni saqlash"}
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
        <label className="text-xs font-semibold text-fg-muted">{label}</label>
        <span className="tabular rounded-full bg-white/10 px-2.5 py-0.5 text-[10px] font-bold text-brand">
          {format(value)}
        </span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-[color:var(--color-brand)] h-1 bg-white/10 rounded-lg appearance-none cursor-pointer"
      />
    </div>
  );
}
