import {
  ISeriesPrimitive,
  IPrimitivePaneView,
  IPrimitivePaneRenderer,
  SeriesAttachedParameter,
  Time
} from "lightweight-charts";

export interface BitmapCoordinatesRenderingScope {
  context: CanvasRenderingContext2D;
  mediaSize: { width: number; height: number };
  bitmapSize: { width: number; height: number };
  horizontalPixelRatio: number;
  verticalPixelRatio: number;
}

export abstract class BasePrimitiveRenderer implements IPrimitivePaneRenderer {
  draw(target: any): void {
    target.useBitmapCoordinateSpace((scope: BitmapCoordinatesRenderingScope) => {
      this.drawBitmap(scope);
    });
  }

  abstract drawBitmap(scope: BitmapCoordinatesRenderingScope): void;
}

export abstract class BasePrimitivePaneView implements IPrimitivePaneView {
  zOrder(): "normal" | "bottom" | "top" {
    return "normal";
  }

  abstract renderer(): IPrimitivePaneRenderer | null;
}

export abstract class BaseSeriesPrimitive<TData> implements ISeriesPrimitive<Time> {
  protected attachedParams: SeriesAttachedParameter<Time, any> | null = null;
  protected data: TData;

  constructor(data: TData) {
    this.data = data;
  }

  attached(param: SeriesAttachedParameter<Time, any>): void {
    this.attachedParams = param;
  }

  detached(): void {
    this.attachedParams = null;
  }

  updateData(data: TData): void {
    this.data = data;
    this.requestUpdate();
  }

  protected requestUpdate(): void {
    if (this.attachedParams && this.attachedParams.requestUpdate) {
      this.attachedParams.requestUpdate();
    }
  }

  updateAllViews(): void {}

  abstract paneViews(): readonly IPrimitivePaneView[];
}
