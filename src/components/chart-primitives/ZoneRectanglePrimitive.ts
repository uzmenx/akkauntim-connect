import {
  SeriesAttachedParameter,
  Time
} from "lightweight-charts";
import {
  BasePrimitiveRenderer,
  BasePrimitivePaneView,
  BaseSeriesPrimitive,
  BitmapCoordinatesRenderingScope
} from "./BasePrimitive";

export interface ZoneData {
  top: number;
  bottom: number;
  start_time?: string | number;
  end_time?: string | number;
  direction: "bullish" | "bearish" | "demand" | "supply" | "support" | "resistance" | string;
  color?: string;
  borderColor?: string;
}

class ZoneRectangleRenderer extends BasePrimitiveRenderer {
  constructor(
    private zones: ZoneData[] | null,
    private attachedParams: SeriesAttachedParameter<Time, any> | null
  ) {
    super();
  }

  drawBitmap(scope: BitmapCoordinatesRenderingScope): void {
    if (!this.zones || this.zones.length === 0 || !this.attachedParams) return;

    const { context: ctx, horizontalPixelRatio, verticalPixelRatio, mediaSize } = scope;
    const timeScale = this.attachedParams.chart.timeScale();
    const series = this.attachedParams.series;

    // Viewport visible time range filtering for optimization
    const visibleRange = timeScale.getVisibleRange();
    
    const parseRangeTime = (t: any): number => {
      if (!t) return 0;
      if (typeof t === 'number') return t > 2000000000 ? Math.floor(t / 1000) : t;
      if (typeof t === 'string') return Math.floor(new Date(t).getTime() / 1000);
      if (t && typeof t === 'object') {
        if ('year' in t && 'month' in t && 'day' in t) {
          return Math.floor(new Date(`${t.year}-${t.month}-${t.day}`).getTime() / 1000);
        }
        if ('value' in t) return t.value;
      }
      return 0;
    };

    let fromSec = 0;
    let toSec = Infinity;
    let margin = 0;

    if (visibleRange) {
      fromSec = parseRangeTime(visibleRange.from);
      toSec = parseRangeTime(visibleRange.to);
      if (fromSec > 0 && toSec > 0) {
        margin = (toSec - fromSec) * 0.15; // 15% padding
      }
    }

    for (const zone of this.zones) {
      // Direct viewport time-range check before expensive coordinate calculations
      if (visibleRange && fromSec > 0 && toSec > 0) {
        const startTs = zone.start_time ? parseRangeTime(zone.start_time) : 0;
        const endTs = zone.end_time ? parseRangeTime(zone.end_time) : Infinity;

        if (endTs < (fromSec - margin) || startTs > (toSec + margin)) {
          continue;
        }
      }

      const isBullish = zone.direction === "bullish" || zone.direction === "demand" || zone.direction === "support";
      
      const fillColor = zone.color || (isBullish ? "rgba(16, 185, 129, 0.15)" : "rgba(244, 63, 94, 0.15)");
      const borderColor = zone.borderColor || (zone.color ? zone.color.replace('0.15', '0.5') : (isBullish ? "rgba(16, 185, 129, 0.5)" : "rgba(244, 63, 94, 0.5)"));

      const y1 = series.priceToCoordinate(zone.top);
      const y2 = series.priceToCoordinate(zone.bottom);
      
      if (y1 === null || y2 === null) continue;

      const topY = Math.min(y1, y2);
      const bottomY = Math.max(y1, y2);
      const height = bottomY - topY;

      // X coordinates - fallback to mediaSize.width if open-ended
      let startX = 0;
      let endX = mediaSize.width;

      const getX = (timeVal: string | number) => {
        const ts = parseRangeTime(timeVal);
        if (!ts || isNaN(ts)) return null;
        return timeScale.timeToCoordinate(ts as Time);
      };

      if (zone.start_time) {
        const x = getX(zone.start_time);
        if (x !== null) startX = x;
      }

      if (zone.end_time) {
        const x = getX(zone.end_time);
        if (x !== null) endX = x;
      }

      // Skip rendering if zone is completely off screen or invalid
      if (endX < 0 || startX > mediaSize.width || startX >= endX) continue;

      const x = startX * horizontalPixelRatio;
      const y = topY * verticalPixelRatio;
      const w = (endX - startX) * horizontalPixelRatio;
      const h = height * verticalPixelRatio;

      ctx.fillStyle = fillColor;
      ctx.fillRect(x, y, w, h);

      ctx.strokeStyle = borderColor;
      ctx.lineWidth = 1 * horizontalPixelRatio;
      ctx.strokeRect(x, y, w, h);
    }
  }
}

class ZoneRectanglePaneView extends BasePrimitivePaneView {
  constructor(
    private zones: ZoneData[] | null,
    private attachedParams: SeriesAttachedParameter<Time, any> | null
  ) {
    super();
  }

  renderer() {
    if (!this.zones || !this.attachedParams) return null;
    return new ZoneRectangleRenderer(this.zones, this.attachedParams);
  }
  
  zOrder(): "normal" | "bottom" | "top" {
    return "bottom"; // Draw behind the candles
  }
}

export class ZoneRectanglePrimitive extends BaseSeriesPrimitive<ZoneData[]> {
  paneViews() {
    return [new ZoneRectanglePaneView(this.data, this.attachedParams)];
  }
}
