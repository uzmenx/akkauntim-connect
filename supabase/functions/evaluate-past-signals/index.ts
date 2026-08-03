import { createClient } from "npm:@supabase/supabase-js@2";
import { corsHeaders } from "npm:@supabase/supabase-js@2/cors";

const N_CANDLES = 6; // 6 x 5min = 30 daqiqadan keyin natijani o'lchaymiz

function pipSize(symbol: string) {
  return symbol.endsWith("JPY") ? 0.01 : 0.0001;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  );

  // Hali baholanmagan signallar (NEUTRAL dan tashqari)
  const { data: signals, error } = await supabase
    .from("shadow_signals")
    .select("id, symbol, timeframe, candle_time, signal, shadow_outcomes(id)")
    .neq("signal", "NEUTRAL")
    .order("candle_time", { ascending: true })
    .limit(200);

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  let evaluated = 0, skipped = 0;

  for (const s of (signals ?? []) as any[]) {
    if (s.shadow_outcomes && s.shadow_outcomes.length > 0) { skipped++; continue; }

    // Signal shamidan keyingi N ta shamni olamiz (look-ahead bias yo'q: faqat o'tgan vaqt)
    const { data: after } = await supabase
      .from("shadow_candles")
      .select("open_time, close")
      .eq("symbol", s.symbol)
      .eq("timeframe", s.timeframe)
      .gt("open_time", s.candle_time)
      .order("open_time", { ascending: true })
      .limit(N_CANDLES);

    if (!after || after.length < N_CANDLES) { skipped++; continue; }

    const { data: at } = await supabase
      .from("shadow_candles")
      .select("close")
      .eq("symbol", s.symbol)
      .eq("timeframe", s.timeframe)
      .eq("open_time", s.candle_time)
      .maybeSingle();

    if (!at) { skipped++; continue; }

    const p0 = Number(at.close);
    const p1 = Number(after[after.length - 1].close);
    const diff = p1 - p0;
    const pips = diff / pipSize(s.symbol);
    const wasCorrect = s.signal === "BUY" ? diff > 0 : diff < 0;

    const { error: insErr } = await supabase.from("shadow_outcomes").upsert({
      signal_id: s.id,
      price_at_signal: p0,
      price_after_n_candles: p1,
      n_candles: N_CANDLES,
      was_correct: wasCorrect,
      pips_result: Number((s.signal === "BUY" ? pips : -pips).toFixed(2)),
      evaluated_at: new Date().toISOString(),
    }, { onConflict: "signal_id" });

    if (!insErr) evaluated++;
  }

  return new Response(JSON.stringify({ evaluated, skipped, n_candles: N_CANDLES }), {
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
});
