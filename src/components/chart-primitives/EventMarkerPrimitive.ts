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
    const markers: SeriesMarker<Time>[] = events.map(ev => {
      let ts: number;
      if (typeof ev.time === 'string') {
        ts = new Date(ev.time).getTime() / 1000;
      } else {
        ts = ev.time;
      }
      
      // snap to closest candle
      let closestTime: Time | null = null;
      if (seriesData.length > 0) {
        let minDiff = Infinity;
        for (const candle of seriesData) {
          const cTime = (typeof candle.time === 'object') 
             ? new Date(candle.time.year + '-' + candle.time.month + '-' + candle.time.day).getTime()/1000 
             : typeof candle.time === 'string' 
                ? new Date(candle.time).getTime() / 1000 
                : Number(candle.time);
          const diff = Math.abs(cTime - ts);
          if (diff < minDiff) {
            minDiff = diff;
            closestTime = candle.time as Time;
          }
        }
      }
      
      let finalTime = closestTime !== null ? closestTime : (ts as Time);
      
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
