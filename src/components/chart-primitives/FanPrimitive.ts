import {
  IPrimitivePaneRenderer,
  Logical,
  SeriesAttachedParameter,
  Time
} from "lightweight-charts";
import {
  BasePrimitiveRenderer,
  BasePrimitivePaneView,
  BaseSeriesPrimitive,
  BitmapCoordinatesRenderingScope
} from "./BasePrimitive";

export interface FanData {
  last_price: number;
  direction: string;
  paths: any[];
}

export interface FanPrimitiveOptions {
  data: FanData;
  lastCandleTime: number; // unix timestamp
  stepSeconds: number;
}

class FanRenderer extends BasePrimitiveRenderer {
  private p10Points: { x: number; y: number }[] = [];
  private p90Points: { x: number; y: number }[] = [];
  private medianPoints: { x: number; y: number }[] = [];

  constructor(
    private options: FanPrimitiveOptions | null,
    private attachedParams: SeriesAttachedParameter<Time, any> | null
  ) {
    super();
    if (!options || !attachedParams) return;

    const { data, lastCandleTime, stepSeconds } = options;
    const timeScale = attachedParams.chart.timeScale();
    const series = attachedParams.series;

    if (!data.paths || data.paths.length === 0) return;
    const n_steps = data.paths[0].length;

    // Helper to get X coordinate. If timeToCoordinate returns null, try to guess via logical index offset.
    // Lightweight-charts allows mapping logical to coordinate.
    const getX = (time: number): number | null => {
      let x = timeScale.timeToCoordinate(time as Time);
      if (x !== null) return x;

      // Extrapolate for future times not in timescale
      const lastCandleLogical = timeScale.coordinateToLogical(
        timeScale.timeToCoordinate(lastCandleTime as Time) || 0
      );
      if (lastCandleLogical === null) return null;

      // Estimate width of one step. Assuming candles match stepSeconds approximately.
      // If time scale is evenly spaced, distance is proportional to logical index.
      // Since this is for visual forecasting, we'll try to calculate a logical index shift.
      const timeDiff = time - lastCandleTime;
      // We assume data has 1 candle = X seconds (usually stepSeconds matches timeframe)
      // Here we assume stepSeconds is the candle interval.
      const logicalSteps = timeDiff / stepSeconds;
      const logicalIdx = lastCandleLogical + logicalSteps;
      return timeScale.logicalToCoordinate(logicalIdx as Logical);
    };

    const initX = getX(lastCandleTime);
    const initY = series.priceToCoordinate(data.last_price);

    if (initX !== null && initY !== null) {
      this.p10Points.push({ x: initX, y: initY });
      this.p90Points.push({ x: initX, y: initY });
      this.medianPoints.push({ x: initX, y: initY });
    }

    for (let i = 0; i < n_steps; i++) {
      const step_prices = data.paths
        .map((p: any) => p[i])
        .sort((a: number, b: number) => a - b);
      const time = lastCandleTime + (i + 1) * stepSeconds;

      const x = getX(time);
      if (x === null) continue;

      const y10 = series.priceToCoordinate(step_prices[Math.floor(step_prices.length * 0.1)]);
      const y90 = series.priceToCoordinate(step_prices[Math.floor(step_prices.length * 0.9)]);
      const yMedian = series.priceToCoordinate(step_prices[Math.floor(step_prices.length * 0.5)]);

      if (y10 !== null) this.p10Points.push({ x, y: y10 });
      if (y90 !== null) this.p90Points.push({ x, y: y90 });
      if (yMedian !== null) this.medianPoints.push({ x, y: yMedian });
    }
  }

  drawBitmap(scope: BitmapCoordinatesRenderingScope): void {
    if (!this.options || this.p10Points.length === 0) return;

    const { context: ctx, horizontalPixelRatio, verticalPixelRatio } = scope;
    const { data } = this.options;

    const isBuy = data.direction === "BUY";
    const isSell = data.direction === "SELL";
    const fanColor = isBuy
      ? "rgba(16, 185, 129, 0.15)"
      : isSell
      ? "rgba(244, 63, 94, 0.15)"
      : "rgba(148, 163, 184, 0.15)";
    const lineColor = isBuy ? "#10b981" : isSell ? "#f43f5e" : "#94a3b8";

    ctx.beginPath();
    for (let i = 0; i < this.p90Points.length; i++) {
      const pt = this.p90Points[i];
      if (i === 0) ctx.moveTo(pt.x * horizontalPixelRatio, pt.y * verticalPixelRatio);
      else ctx.lineTo(pt.x * horizontalPixelRatio, pt.y * verticalPixelRatio);
    }
    for (let i = this.p10Points.length - 1; i >= 0; i--) {
      const pt = this.p10Points[i];
      ctx.lineTo(pt.x * horizontalPixelRatio, pt.y * verticalPixelRatio);
    }
    ctx.closePath();
    ctx.fillStyle = fanColor;
    ctx.fill();

    ctx.beginPath();
    for (let i = 0; i < this.medianPoints.length; i++) {
      const pt = this.medianPoints[i];
      if (i === 0) ctx.moveTo(pt.x * horizontalPixelRatio, pt.y * verticalPixelRatio);
      else ctx.lineTo(pt.x * horizontalPixelRatio, pt.y * verticalPixelRatio);
    }
    ctx.strokeStyle = lineColor;
    ctx.lineWidth = 2 * horizontalPixelRatio;
    ctx.setLineDash([5 * horizontalPixelRatio, 5 * horizontalPixelRatio]);
    ctx.stroke();
    ctx.setLineDash([]);
  }
}

class FanPaneView extends BasePrimitivePaneView {
  constructor(
    private options: FanPrimitiveOptions | null,
    private attachedParams: SeriesAttachedParameter<Time, any> | null
  ) {
    super();
  }

  renderer(): IPrimitivePaneRenderer | null {
    if (!this.options || !this.attachedParams) return null;
    return new FanRenderer(this.options, this.attachedParams);
  }
}

export class FanPrimitive extends BaseSeriesPrimitive<FanPrimitiveOptions | null> {
  paneViews() {
    return [new FanPaneView(this.data, this.attachedParams)];
  }
}
