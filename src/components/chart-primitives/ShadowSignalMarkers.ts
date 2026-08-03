import {
  ISeriesApi,
  Time,
  SeriesMarker,
  createSeriesMarkers,
  ISeriesMarkersPluginApi,
} from "lightweight-charts";

export interface ShadowSignalRow {
  id: string;
  symbol: string;
  timeframe: string;
  candle_time: string;
  signal: string;
  score: number | string;
  features: Record<string, unknown> | null;
  was_correct?: boolean | null;
}

/**
 * Faqat vizual/kuzatuv maqsadli Shadow signal markerlari.
 * Hech qanday order/buyruq bilan bog'lanmagan, kelajakni proyeksiya qilmaydi.
 * setMarkers() bilan yangilanadi — chart qayta chizilmaydi (zoom/scroll saqlanadi).
 */
export class ShadowSignalMarkers {
  private plugin: ISeriesMarkersPluginApi<Time>;

  constructor(series: ISeriesApi<any, Time>) {
    this.plugin = createSeriesMarkers(series, []);
  }

  public update(signals: ShadowSignalRow[], candleTimes: number[]) {
    const snap = (ts: number): number => {
      if (candleTimes.length === 0) return ts;
      let best = candleTimes[0];
      let minDiff = Infinity;
      for (const t of candleTimes) {
        const d = Math.abs(t - ts);
        if (d < minDiff) {
          minDiff = d;
          best = t;
        }
      }
      return best;
    };

    const markers: SeriesMarker<Time>[] = signals
      .filter((s) => s.signal === "BUY" || s.signal === "SELL")
      .map((s) => {
        const ts = Math.floor(new Date(s.candle_time).getTime() / 1000);
        const isBuy = s.signal === "BUY";
        const evaluated = s.was_correct !== null && s.was_correct !== undefined;

        // Baholanmagan = xira, to'g'ri = to'yingan, xato = kulrang
        let color: string;
        if (!evaluated) color = isBuy ? "rgba(16,185,129,0.45)" : "rgba(244,63,94,0.45)";
        else if (s.was_correct) color = isBuy ? "#10b981" : "#f43f5e";
        else color = "rgba(148,163,184,0.9)";

        const mark = evaluated ? (s.was_correct ? " ✓" : " ✗") : "";

        return {
          time: snap(ts) as Time,
          position: isBuy ? "belowBar" : "aboveBar",
          shape: isBuy ? "arrowUp" : "arrowDown",
          color,
          text: `${s.signal}${mark}`,
          size: 1,
        } as SeriesMarker<Time>;
      })
      .sort((a, b) => Number(a.time) - Number(b.time));

    this.plugin.setMarkers(markers);
  }

  public detach() {
    this.plugin.detach();
  }
}
