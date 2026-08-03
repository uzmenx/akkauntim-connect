import { createClient } from "npm:@supabase/supabase-js@2";
import { corsHeaders } from "npm:@supabase/supabase-js@2/cors";

// Shadow moduli uchun kuzatiladigan juftliklar va timeframe.
// Twelve Data forex simbol formati: "EUR/USD"
const SYMBOLS = ["EUR/USD", "GBP/USD", "AUD/USD"];
const TIMEFRAME = "5min";
const OUTPUT_SIZE = 100; // har chaqiriqda oxirgi 100 sham

type TDValue = {
  datetime: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume?: string;
};

function normalizeSymbol(s: string) {
  return s.replace("/", ""); // "EUR/USD" -> "EURUSD"
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  const apiKey = Deno.env.get("TWELVE_DATA_API_KEY");
  if (!apiKey) {
    return new Response(
      JSON.stringify({ error: "TWELVE_DATA_API_KEY sozlanmagan" }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } },
    );
  }

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  );

  const results: Record<string, unknown>[] = [];

  for (const symbol of SYMBOLS) {
    try {
      const url = new URL("https://api.twelvedata.com/time_series");
      url.searchParams.set("symbol", symbol);
      url.searchParams.set("interval", TIMEFRAME);
      url.searchParams.set("outputsize", String(OUTPUT_SIZE));
      url.searchParams.set("timezone", "UTC");
      url.searchParams.set("apikey", apiKey);

      const res = await fetch(url.toString());
      const json = await res.json();

      if (json.status === "error" || !Array.isArray(json.values)) {
        results.push({ symbol, ok: false, error: json.message ?? "no data" });
        continue;
      }

      const rows = (json.values as TDValue[]).map((v) => ({
        symbol: normalizeSymbol(symbol),
        timeframe: TIMEFRAME,
        // Twelve Data UTC beradi, ISO formatga o'tkazamiz
        open_time: new Date(v.datetime.replace(" ", "T") + "Z").toISOString(),
        open: Number(v.open),
        high: Number(v.high),
        low: Number(v.low),
        close: Number(v.close),
        volume: v.volume != null ? Number(v.volume) : null,
      })).filter((r) => Number.isFinite(r.close));

      // Duplikatlarni oldini olish: symbol+timeframe+open_time bo'yicha UPSERT
      const { error } = await supabase
        .from("shadow_candles")
        .upsert(rows, { onConflict: "symbol,timeframe,open_time" });

      if (error) {
        results.push({ symbol, ok: false, error: error.message });
      } else {
        results.push({ symbol, ok: true, upserted: rows.length });
      }
    } catch (e) {
      results.push({ symbol, ok: false, error: String(e) });
    }
  }

  return new Response(JSON.stringify({ timeframe: TIMEFRAME, results }), {
    headers: { ...corsHeaders, "Content-Type": "application/json" },
    status: 200,
  });
});
