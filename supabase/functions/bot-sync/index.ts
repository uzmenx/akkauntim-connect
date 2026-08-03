// Python bot -> Lovable Cloud sync endpoint.
// Auth: shared secret in `x-bot-secret` header. Bot identifies itself by `mt5_login`;
// we look up the owner user_id in bot_settings and write rows on their behalf.
import { createClient } from "npm:@supabase/supabase-js@2";
import { corsHeaders } from "npm:@supabase/supabase-js@2/cors";

const supabase = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  { auth: { persistSession: false } }
);

const SHARED = Deno.env.get("BOT_SYNC_SECRET") ?? "";

type Body = {
  mt5_login: string;
  add_claude_cost?: number;
  status?: {
    is_running?: boolean;
    message?: string;
    account_equity?: number;
    account_balance?: number;
    account_currency?: string;
    available_symbols?: Record<string, string[]>;
  };
  positions?: Array<{
    ticket: number;
    symbol: string;
    side: "BUY" | "SELL";
    volume: number;
    open_price: number;
    current_price?: number | null;
    stop_loss?: number | null;
    take_profit?: number | null;
    profit: number;
    opened_at?: string;
  }>;
  pending_orders?: Array<{
    ticket: number;
    symbol: string;
    type: string;
    volume: number;
    price: number;
    stop_loss?: number | null;
    take_profit?: number | null;
  }>;
  ai_signal?: {
    symbol: string;
    signal: string;
    confidence: number;
    reasoning?: string;
    entry_price?: number;
    sl_price?: number;
    tp_price?: number;
    rr_ratio?: number;
    stop_loss_pips?: number;
    take_profit_pips?: number;
  };
  closed_trades?: Array<{
    ticket: number;
    symbol: string;
    side: string;
    volume: number;
    open_price: number;
    close_price: number;
    profit: number;
    opened_at: string;
    closed_at: string;
    agreed_strategies?: string[];
    ai_used?: boolean;
  }>;
  candles?: Array<{
    symbol: string;
    timeframe: string;
    time: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume?: number;
  }>;
  smc_zones?: Array<{
    symbol: string;
    timeframe: string;
    zone_type: 'order_block' | 'fvg';
    direction: 'demand' | 'supply';
    top: number;
    bottom: number;
    status: 'fresh' | 'mitigated' | 'invalidated';
    formed_at: string;
  }>;
  symbol?: string;
  timeframe?: string;
  strategy_overlays?: {
    smc?: Array<any>;
    harmonic?: Array<any>;
    wyckoff?: Array<any>;
    sr_volume?: Array<any>;
    auto_patterns?: Array<any>;
  };
};

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });
  if (req.method !== "POST") return json(405, { error: "method_not_allowed" });

  if (!SHARED || req.headers.get("x-bot-secret") !== SHARED) {
    return json(401, { error: "unauthorized" });
  }

  let body: Body;
  try { body = await req.json(); } catch { return json(400, { error: "invalid_json" }); }
  if (!body.mt5_login) return json(400, { error: "mt5_login_required" });

  // Look up full settings by mt5_login
  const { data: settings, error: lookupErr } = await supabase
    .from("bot_settings")
    .select("*")
    .eq("mt5_login", String(body.mt5_login))
    .maybeSingle();

  if (lookupErr) return json(500, { error: "lookup_failed", detail: lookupErr.message });
  if (!settings) return json(404, { error: "mt5_login_not_registered" });

  const user_id = settings.user_id;
  const results: Record<string, unknown> = {};

  if (body.status || body.add_claude_cost !== undefined) {
    const costToAdd = Number(body.add_claude_cost ?? 0);
    
    // Check if status row exists
    const { data: existingStatus } = await supabase
      .from("bot_status")
      .select("claude_used")
      .eq("user_id", user_id)
      .maybeSingle();

    if (existingStatus) {
      const newUsed = Number(existingStatus.claude_used ?? 0) + costToAdd;
      const updatePayload: Record<string, any> = {
        claude_used: newUsed,
        updated_at: new Date().toISOString()
      };
      if (body.status) {
        Object.assign(updatePayload, body.status);
      }
      const { error } = await supabase
        .from("bot_status")
        .update(updatePayload)
        .eq("user_id", user_id);
      results.status = error ? { error: error.message } : "ok";
    } else {
      const insertPayload = {
        user_id,
        claude_used: costToAdd,
        ...(body.status ?? {}),
        updated_at: new Date().toISOString()
      };
      const { error } = await supabase
        .from("bot_status")
        .insert(insertPayload);
      results.status = error ? { error: error.message } : "ok";
    }
  }

  if (body.positions) {
    await supabase.from("positions").delete().eq("user_id", user_id);
    if (body.positions.length) {
      const rows = body.positions.map((p) => ({ ...p, user_id }));
      const { error } = await supabase.from("positions").upsert(rows, { onConflict: "user_id,ticket" });
      results.positions = error ? { error: error.message } : `ok:${rows.length}`;
    } else {
      results.positions = "ok:0";
    }
  }

  if (body.pending_orders) {
    await supabase.from("pending_orders").delete().eq("user_id", user_id);
    if (body.pending_orders.length) {
      const rows = body.pending_orders.map((o) => ({ ...o, user_id }));
      const { error } = await supabase.from("pending_orders").upsert(rows, { onConflict: "user_id,ticket" });
      results.pending_orders = error ? { error: error.message } : `ok:${rows.length}`;
    } else {
      results.pending_orders = "ok:0";
    }
  }

  if (body.ai_signal) {
    const { error } = await supabase.from("ai_signals").insert({ user_id, ...body.ai_signal });
    results.ai_signal = error ? { error: error.message } : "ok";
  }

  if (body.closed_trades && body.closed_trades.length > 0) {
    const rows = body.closed_trades.map((t) => ({ ...t, user_id }));
    const { error } = await supabase.from("trade_history").upsert(rows, { onConflict: "user_id,ticket" });
    results.closed_trades = error ? { error: error.message } : `ok:${rows.length}`;
  }

  if (body.candles && body.candles.length > 0) {
    const rows = body.candles.map(c => ({ ...c, user_id }));
    const { error } = await supabase.from("candles").upsert(rows, { onConflict: "user_id,symbol,timeframe,time" });
    results.candles = error ? { error: error.message } : `ok:${rows.length}`;
  }

  if (body.smc_zones && body.smc_zones.length > 0) {
    const symbol = body.smc_zones[0].symbol;
    const timeframe = body.smc_zones[0].timeframe;
    await supabase.from("smc_zones").delete().eq("user_id", user_id).eq("symbol", symbol).eq("timeframe", timeframe).eq("status", "fresh");
    const rows = body.smc_zones.map(z => ({ ...z, user_id }));
    const { error } = await supabase.from("smc_zones").insert(rows);
    results.smc_zones = error ? { error: error.message } : `ok:${rows.length}`;
  }

  if (body.strategy_overlays && body.symbol && body.timeframe) {
    const symbol = body.symbol;
    const timeframe = body.timeframe;
    const overlays = body.strategy_overlays;
    
    if (overlays.smc && overlays.smc.length > 0) {
      await supabase.from("smc_zones").delete().eq("user_id", user_id).eq("symbol", symbol).eq("timeframe", timeframe).eq("status", "fresh");
      const { error } = await supabase.from("smc_zones").insert(overlays.smc.map(z => ({ ...z, user_id })));
      results.smc_zones_overlay = error ? { error: error.message } : `ok:${overlays.smc.length}`;
    }
    
    if (overlays.harmonic && overlays.harmonic.length > 0) {
      await supabase.from("harmonic_patterns").delete().eq("user_id", user_id).eq("symbol", symbol).eq("timeframe", timeframe).eq("status", "fresh");
      const { error } = await supabase.from("harmonic_patterns").insert(overlays.harmonic.map(z => ({ ...z, user_id })));
      results.harmonic_patterns = error ? { error: error.message } : `ok:${overlays.harmonic.length}`;
    }
    
    if (overlays.wyckoff && overlays.wyckoff.length > 0) {
      await supabase.from("wyckoff_events").delete().eq("user_id", user_id).eq("symbol", symbol).eq("timeframe", timeframe).eq("status", "fresh");
      const { error } = await supabase.from("wyckoff_events").insert(overlays.wyckoff.map(z => ({ ...z, user_id })));
      results.wyckoff_events = error ? { error: error.message } : `ok:${overlays.wyckoff.length}`;
    }
    
    if (overlays.sr_volume && overlays.sr_volume.length > 0) {
      await supabase.from("sr_volume_zones").delete().eq("user_id", user_id).eq("symbol", symbol).eq("timeframe", timeframe).eq("status", "fresh");
      const { error } = await supabase.from("sr_volume_zones").insert(overlays.sr_volume.map(z => ({ ...z, user_id })));
      results.sr_volume_zones = error ? { error: error.message } : `ok:${overlays.sr_volume.length}`;
    }
    
    if (overlays.auto_patterns && overlays.auto_patterns.length > 0) {
      await supabase.from("auto_patterns").delete().eq("user_id", user_id).eq("symbol", symbol).eq("timeframe", timeframe).eq("status", "fresh");
      const { error } = await supabase.from("auto_patterns").insert(overlays.auto_patterns.map(z => ({ ...z, user_id })));
      results.auto_patterns = error ? { error: error.message } : `ok:${overlays.auto_patterns.length}`;
    }
  }

  return json(200, { ok: true, user_id, results, settings });
});
