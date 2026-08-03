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

    const getX = (timeVal: string | number) => {
      let ts: number;
      if (typeof timeVal === 'string') {
        ts = new Date(timeVal).getTime() / 1000;
      } else {
        ts = timeVal;
      }
      let x = timeScale.timeToCoordinate(ts as Time);
      if (x !== null) return x;

      // Extrapolate for times not exactly in the timescale (like future points or missing ones)
      // We will try to convert back and forth if possible, but the best way is usually finding closest logical.
      // Since lightweight charts can do timeScale.coordinateToLogical / logicalToCoordinate...
      // Actually we can't easily extrapolate without knowing the exact step or finding nearest point.
      // Let's just return what timeScale.timeToCoordinate gives us. If it returns null, we can try to find nearest index.
      return x;
    };

    for (const line of this.lines) {
      if (!line.points || line.points.length < 2) continue;

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
