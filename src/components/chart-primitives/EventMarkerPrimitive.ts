import { ISeriesApi, Time, SeriesMarker, createSeriesMarkers, ISeriesMarkersPluginApi } from "lightweight-charts";

export interface EventMarkerData {
  time: string | number; // ISO string or unix timestamp (seconds)
  text: string;
  type: "buy" | "sell" | "neutral";
  color?: string;
  position?: "aboveBar" | "belowBar" | "inBar";
  shape?: "circle" | "square" | "arrowUp" | "arrowDown";
}

export class EventMarkerPrimitive {
  private plugin: ISeriesMarkersPluginApi<Time>;
  
  constructor(
    series: ISeriesApi<any, Time>,
    events: EventMarkerData[],
    seriesData: any[] // to snap to closest candle
  ) {
    const safeParseTime = (t: any): number => {
      if (!t) return 0;
      if (typeof t === 'number') return t > 2000000000 ? Math.floor(t / 1000) : t;
      if (typeof t === 'string') {
        const ms = new Date(t).getTime();
        return isNaN(ms) ? 0 : Math.floor(ms / 1000);
      }
      return 0;
    };

    const markers: SeriesMarker<Time>[] = events.map(ev => {
      const ts = safeParseTime(ev.time);
      
      // snap to closest candle
      let finalTime: Time = ts as Time;
      if (seriesData.length > 0 && ts > 0) {
        let minDiff = Infinity;
        for (const candle of seriesData) {
          const cTime = typeof candle.time === 'number' ? candle.time : safeParseTime(candle.time);
          const diff = Math.abs(cTime - ts);
          if (diff < minDiff) {
            minDiff = diff;
            finalTime = candle.time as Time;
          }
        }
      }
      
      const defaultColor = ev.type === 'buy' ? '#10b981' : ev.type === 'sell' ? '#f43f5e' : '#3b82f6';
      const defaultPosition = ev.type === 'buy' ? 'belowBar' : ev.type === 'sell' ? 'aboveBar' : 'inBar';
      const defaultShape = ev.type === 'buy' ? 'arrowUp' : ev.type === 'sell' ? 'arrowDown' : 'circle';

      return {
        time: finalTime,
        position: ev.position || defaultPosition as any,
        color: ev.color || defaultColor,
        shape: ev.shape || defaultShape as any,
        text: ev.text,
        size: 1
      };
    });

    this.plugin = createSeriesMarkers(series, markers);
  }

  public detach() {
    this.plugin.detach();
  }
}
