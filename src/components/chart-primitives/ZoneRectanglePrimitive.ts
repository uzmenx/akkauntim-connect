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

    for (const zone of this.zones) {
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
        let ts: number;
        if (typeof timeVal === 'string') {
          ts = new Date(timeVal).getTime() / 1000;
        } else {
          ts = timeVal;
        }
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
