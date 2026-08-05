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

export interface PointData {
  time: string | number; // ISO string or unix timestamp (seconds)
  price: number;
}

export interface LineData {
  points: PointData[];
  color?: string;
  lineWidth?: number;
  isDashed?: boolean;
  fillColor?: string; // Optional area fill (e.g. for triangles/wedges)
}

class ConnectedLineRenderer extends BasePrimitiveRenderer {
  constructor(
    private lines: LineData[] | null,
    private attachedParams: SeriesAttachedParameter<Time, any> | null
  ) {
    super();
  }

  drawBitmap(scope: BitmapCoordinatesRenderingScope): void {
    if (!this.lines || this.lines.length === 0 || !this.attachedParams) return;

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

    const getX = (timeVal: string | number) => {
      const ts = parseRangeTime(timeVal);
      if (!ts || isNaN(ts)) return null;
      return timeScale.timeToCoordinate(ts as Time);
    };

    for (const line of this.lines) {
      if (!line.points || line.points.length < 2) continue;

      // Filter out entire line pattern if all of its points are completely outside the viewport
      if (visibleRange && fromSec > 0 && toSec > 0) {
        let allBefore = true;
        let allAfter = true;
        for (const p of line.points) {
          const pts = parseRangeTime(p.time);
          if (pts >= (fromSec - margin)) allBefore = false;
          if (pts <= (toSec + margin)) allAfter = false;
        }
        if (allBefore || allAfter) continue;
      }

      const coords: { x: number; y: number }[] = [];
      for (const p of line.points) {
        const x = getX(p.time);
        const y = series.priceToCoordinate(p.price);
        if (x !== null && y !== null) {
          coords.push({
            x: x * horizontalPixelRatio,
            y: y * verticalPixelRatio
          });
        }
      }

      if (coords.length < 2) continue;

      if (line.fillColor) {
        ctx.beginPath();
        ctx.moveTo(coords[0].x, coords[0].y);
        for (let i = 1; i < coords.length; i++) {
          ctx.lineTo(coords[i].x, coords[i].y);
        }
        ctx.closePath();
        ctx.fillStyle = line.fillColor;
        ctx.fill();
      }

      ctx.beginPath();
      ctx.moveTo(coords[0].x, coords[0].y);
      for (let i = 1; i < coords.length; i++) {
        ctx.lineTo(coords[i].x, coords[i].y);
      }
      
      ctx.strokeStyle = line.color || '#3b82f6';
      ctx.lineWidth = (line.lineWidth || 2) * horizontalPixelRatio;
      
      if (line.isDashed) {
        ctx.setLineDash([5 * horizontalPixelRatio, 5 * horizontalPixelRatio]);
      } else {
        ctx.setLineDash([]);
      }
      
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }
}

class ConnectedLinePaneView extends BasePrimitivePaneView {
  constructor(
    private lines: LineData[] | null,
    private attachedParams: SeriesAttachedParameter<Time, any> | null
  ) {
    super();
  }

  renderer() {
    if (!this.lines || !this.attachedParams) return null;
    return new ConnectedLineRenderer(this.lines, this.attachedParams);
  }
  
  zOrder(): "normal" | "bottom" | "top" {
    return "normal";
  }
}

export class ConnectedLinePrimitive extends BaseSeriesPrimitive<LineData[]> {
  paneViews() {
    return [new ConnectedLinePaneView(this.data, this.attachedParams)];
  }
}
