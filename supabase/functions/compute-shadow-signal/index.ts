import { createClient } from "npm:@supabase/supabase-js@2";
import { corsHeaders } from "npm:@supabase/supabase-js@2/cors";

const SYMBOLS = ["EURUSD", "GBPUSD", "AUDUSD"];
const TIMEFRAME = "5min";

type Candle = { open_time: string; open: number; high: number; low: number; close: number };

function sma(vals: number[], n: number) {
  if (vals.length < n) return null;
  const s = vals.slice(-n);
  return s.reduce((a, b) => a + b, 0) / n;
}

function rsi(closes: number[], n = 14) {
  if (closes.length < n + 1) return null;
  let gains = 0, losses = 0;
  for (let i = closes.length - n; i < closes.length; i++) {
    const d = closes[i] - closes[i - 1];
    if (d >= 0) gains += d; else losses -= d;
  }
  const avgG = gains / n, avgL = losses / n;
  if (avgL === 0) return 100;
  const rs = avgG / avgL;
  return 100 - 100 / (1 + rs);
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: corsHeaders });

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL")!,
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
  );

  const results: Record<string, unknown>[] = [];

  for (const symbol of SYMBOLS) {
    try {
      const { data, error } = await supabase
        .from("shadow_candles")
        .select("open_time, open, high, low, close")
        .eq("symbol", symbol)
        .eq("timeframe", TIMEFRAME)
        .order("open_time", { ascending: false })
        .limit(60);

      if (error) { results.push({ symbol, ok: false, error: error.message }); continue; }
      const candles = (data as Candle[] ?? []).slice().reverse();
      if (candles.length < 25) { results.push({ symbol, ok: false, error: "kam ma'lumot" }); continue; }

      const closes = candles.map((c) => Number(c.close));
      const last = candles[candles.length - 1];
      const price = closes[closes.length - 1];

      // --- Statistik "edge" xususiyatlari (bashorat emas, faqat og'ish o'lchovi) ---
      const sma10 = sma(closes, 10)!;
      const sma30 = sma(closes, 30) ?? sma(closes, closes.length)!;
      const trend = (sma10 - sma30) / sma30;               // trend yo'nalishi
      const r = rsi(closes) ?? 50;
      const meanRev = (50 - r) / 50;                        // o'rtachaga qaytish moyilligi

      // Momentum: oxirgi 3 shamning yopilish o'zgarishi
      const mom = (price - closes[closes.length - 4]) / closes[closes.length - 4];

      // Volatilite (ATR-ga o'xshash, normallashtirilgan)
      const ranges = candles.slice(-14).map((c) => Number(c.high) - Number(c.low));
      const atr = ranges.reduce((a, b) => a + b, 0) / ranges.length;
      const atrPct = atr / price;

      // Vaznlar: trend + momentum asosiy, mean-reversion qarshi vazn
      const score = 0.5 * (trend * 1000) + 0.3 * (mom * 1000) + 0.2 * (meanRev * 2);

      // Volatilite juda past bo'lsa signal bermaymiz (shovqin)
      const threshold = 0.35;
      let signal: "BUY" | "SELL" | "NEUTRAL" = "NEUTRAL";
      if (atrPct > 0.00015) {
        if (score > threshold) signal = "BUY";
        else if (score < -threshold) signal = "SELL";
      }

      const { error: upErr } = await supabase.from("shadow_signals").upsert({
        symbol,
        timeframe: TIMEFRAME,
        candle_time: last.open_time,
        signal,
        score: Number(score.toFixed(4)),
        features: {
          price,
          sma10,
          sma30,
          trend: Number(trend.toFixed(6)),
          rsi14: Number(r.toFixed(2)),
          momentum_3: Number(mom.toFixed(6)),
          atr14: Number(atr.toFixed(6)),
          atr_pct: Number(atrPct.toFixed(6)),
          weights: { trend: 0.5, momentum: 0.3, mean_reversion: 0.2 },
          threshold,
        },
      }, { onConflict: "symbol,timeframe,candle_time" });

      if (upErr) results.push({ symbol, ok: false, error: upErr.message });
      else results.push({ symbol, ok: true, signal, score: Number(score.toFixed(4)), candle_time: last.open_time });
    } catch (e) {
      results.push({ symbol, ok: false, error: String(e) });
    }
  }

  return new Response(JSON.stringify({ timeframe: TIMEFRAME, results }), {
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
});
