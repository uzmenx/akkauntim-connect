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
  status?: {
    is_running?: boolean;
    message?: string;
    account_equity?: number;
    account_balance?: number;
    account_currency?: string;
  };
  positions?: Array<{
    id: number;
    symbol: string;
    side: "BUY" | "SELL";
    volume: number;
    open_price: number;
    profit: number;
    opened_at?: string;
  }>;
  ai_signal?: {
    symbol: string;
    signal: string;
    confidence: number;
    reasoning?: string;
    stop_loss_pips?: number;
    take_profit_pips?: number;
  };
  closed_trade?: {
    id: number;
    symbol: string;
    side: string;
    volume: number;
    open_price: number;
    close_price: number;
    profit: number;
    opened_at?: string;
    closed_at?: string;
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

  // Look up user_id by mt5_login
  const { data: settings, error: lookupErr } = await supabase
    .from("bot_settings")
    .select("user_id")
    .eq("mt5_login", String(body.mt5_login))
    .maybeSingle();

  if (lookupErr) return json(500, { error: "lookup_failed", detail: lookupErr.message });
  if (!settings) return json(404, { error: "mt5_login_not_registered" });

  const user_id = settings.user_id;
  const results: Record<string, unknown> = {};

  if (body.status) {
    const { error } = await supabase.from("bot_status").upsert(
      { user_id, ...body.status, updated_at: new Date().toISOString() },
      { onConflict: "user_id" }
    );
    results.status = error ? { error: error.message } : "ok";
  }

  if (body.positions) {
    await supabase.from("positions").delete().eq("user_id", user_id);
    if (body.positions.length) {
      const rows = body.positions.map((p) => ({ ...p, user_id }));
      const { error } = await supabase.from("positions").upsert(rows);
      results.positions = error ? { error: error.message } : `ok:${rows.length}`;
    } else {
      results.positions = "ok:0";
    }
  }

  if (body.ai_signal) {
    const { error } = await supabase.from("ai_signals").insert({ user_id, ...body.ai_signal });
    results.ai_signal = error ? { error: error.message } : "ok";
  }

  if (body.closed_trade) {
    const { error } = await supabase.from("trade_history").insert({ user_id, ...body.closed_trade });
    results.closed_trade = error ? { error: error.message } : "ok";
  }

  return json(200, { ok: true, user_id, results });
});
