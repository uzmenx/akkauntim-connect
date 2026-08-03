import React, { useEffect, useRef, useState } from "react";
import { createChart, ColorType, LineStyle, IChartApi, ISeriesApi, CandlestickSeries, HistogramSeries, LineSeries } from "lightweight-charts";
import { X, TrendingUp, TrendingDown, Layers, Activity, Eye, RefreshCw, BarChart2, ShieldAlert, Target, Loader2, ChevronDown, Search, ArrowLeft } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { fmtMoney, fmtNum } from "@/lib/utils";
import type { Position } from "@/lib/types";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/hooks/useAuth";
import { guestMock } from "@/lib/guestMock";

interface TradingChartModalProps {
  isOpen: boolean;
  onClose: () => void;
  symbol: string;
  position?: Position | null;
}

type Timeframe = "M1" | "M5" | "M15" | "H1" | "H4" | "D1";

const calculatePL = (entry: number, target: number, vol: number, sym: string, currentPrice: number, currentProfit: number) => {
  if (!entry || !target || !vol) return 0;
  
  const currentDiff = Math.abs(currentPrice - entry);
  const targetDiff = Math.abs(target - entry);
  
  if (currentDiff > 0.00001 && currentProfit !== 0) {
     const valuePerUnit = Math.abs(currentProfit) / currentDiff;
     return targetDiff * valuePerUnit;
  }

  let pl = targetDiff * 100000 * vol;
  if (!sym.endsWith("USD") && !sym.includes("XAU")) {
    pl = pl / currentPrice;
  } else if (sym.includes("XAU") || sym.includes("GOLD")) {
    pl = targetDiff * 100 * vol;
  }
  return pl;
};

export function TradingChartModal({ isOpen, onClose, symbol, position }: TradingChartModalProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  const [timeframe, setTimeframe] = useState<Timeframe>("M5");
  const [showSMC, setShowSMC] = useState(true);
  const [showVolume, setShowVolume] = useState(true);
  const [showFan, setShowFan] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isEmpty, setIsEmpty] = useState(false);
  const [candlesData, setCandlesData] = useState<any[]>([]);
  const [smcZonesData, setSmcZonesData] = useState<any[]>([]);

  const [activeSymbol, setActiveSymbol] = useState(symbol);
  const [activePosition, setActivePosition] = useState<Position | null | undefined>(position);
  const [showSymbolList, setShowSymbolList] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const { user } = useAuth();
  const isGuest = user?.id === "guest";

  useEffect(() => {
    if (isOpen) {
      setActiveSymbol(symbol);
      setActivePosition(position);
      setShowSymbolList(false);
      setSearchQuery("");
    }
  }, [symbol, position, isOpen]);

  const { data: statusData } = useQuery({
    queryKey: ["bot_status_symbols", user?.id],
    queryFn: async () => {
      if (isGuest) {
        return guestMock.getBotStatus();
      }
      const { data } = await supabase.from("bot_status").select("available_symbols").maybeSingle();
      return data;
    },
    enabled: isOpen,
  });

  const { data: settingsData } = useQuery({
    queryKey: ["bot_settings_pairs_modal", user?.id],
    queryFn: async () => {
      if (isGuest) {
        return guestMock.getSettings();
      }
      const { data } = await supabase.from("bot_settings").select("symbols").maybeSingle();
      return data;
    },
    enabled: isOpen,
  });

  const { data: positionsData } = useQuery({
    queryKey: ["positions_modal", user?.id],
    queryFn: async () => {
      if (isGuest) {
        return guestMock.getPositions();
      }
      const { data } = await supabase.from("positions").select("*");
      return data || [];
    },
    enabled: isOpen,
  });

  const { data: pendingOrdersData } = useQuery({
    queryKey: ["pending_orders_modal", user?.id],
    queryFn: async () => {
      if (isGuest) {
        return [];
      }
      const { data } = await supabase.from("pending_orders").select("*");
      return data || [];
    },
    enabled: isOpen,
  });

  const availableSymbolsObj = (statusData?.available_symbols as Record<string, string[]>) || {};
  const allSymbols = Object.values(availableSymbolsObj).flat();
  const filteredSymbols = allSymbols.filter(s => s.toLowerCase().includes(searchQuery.toLowerCase()));
  const loadedSymbols = (settingsData?.symbols as string[]) || [];

  const handleSymbolSelect = (sym: string) => {
    setActiveSymbol(sym);
    setActivePosition(null);
    setShowSymbolList(false);
    setSearchQuery("");
  };

  const isBuy = activePosition ? activePosition.side?.toUpperCase() === "BUY" : true;
  const openPrice = activePosition ? Number(activePosition.open_price) : 0;
  const currentPrice = activePosition ? Number(activePosition.current_price) : 0;
  const stopLoss = activePosition?.stop_loss ? Number(activePosition.stop_loss) : 0;
  const takeProfit = activePosition?.take_profit ? Number(activePosition.take_profit) : 0;
  const profit = activePosition ? Number(activePosition.profit ?? 0) : 0;
  const volume = activePosition ? Number(activePosition.volume ?? 0.1) : 0.1;

  // Predictive Fan query
  const { data: fanData, isLoading: isLoadingFan } = useQuery({
    queryKey: ["predictive_fan", activeSymbol, timeframe],
    queryFn: async () => {
      // Backend FastAPI URL: adjust port if needed
      const res = await fetch(`http://localhost:8000/api/predict/fan/${activeSymbol}?timeframe=${timeframe}`);
      if (!res.ok) throw new Error("Fan fetch error");
      return await res.json();
    },
    enabled: isOpen && showFan && !!activeSymbol,
    refetchInterval: 5000, // Real-time polling
  });

  useEffect(() => {
    if (!isOpen || !activeSymbol) return;

    let isMounted = true;
    const fetchChartData = async () => {
      setIsLoading(true);
      setError(null);
      setIsEmpty(false);
      try {
        // Fetch candles
        const { data: candles, error: candlesError } = await supabase
          .from("candles")
          .select("*")
          .eq("symbol", activeSymbol)
          .eq("timeframe", timeframe)
          .order("time", { ascending: false })
          .limit(300);

        if (candlesError) throw candlesError;

        if (!candles || candles.length === 0) {
          if (isMounted) setIsEmpty(true);
          return;
        }

        // Convert to ascending order and required format
        const formattedCandles = candles.reverse().map((c: any) => ({
          time: Math.floor(new Date(c.time).getTime() / 1000),
          open: Number(c.open),
          high: Number(c.high),
          low: Number(c.low),
          close: Number(c.close),
          volume: c.volume ? Number(c.volume) : 0,
        }));

        if (isMounted) setCandlesData(formattedCandles);

        // Fetch SMC zones if enabled
        if (showSMC) {
          const { data: zones, error: zonesError } = await supabase
            .from("smc_zones")
            .select("*")
            .eq("symbol", activeSymbol)
            .eq("timeframe", timeframe)
            .eq("status", "fresh");
            
          if (!zonesError && zones) {
            if (isMounted) setSmcZonesData(zones);
          }
        }
      } catch (err: any) {
        if (isMounted) setError(err.message || "Ma'lumotlarni yuklashda xatolik yuz berdi");
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    fetchChartData();

    return () => { isMounted = false; };
  }, [isOpen, activeSymbol, timeframe, showSMC, showFan, fanData]);

  useEffect(() => {
    if (!isOpen || !chartContainerRef.current || isEmpty || isLoading || error || candlesData.length === 0) return;

    const container = chartContainerRef.current;
    container.innerHTML = ""; // Clear existing

    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: "#090d16" },
        textColor: "#94a3b8",
        fontSize: 11,
        fontFamily: "Inter, system-ui, sans-serif",
      },
      grid: {
        vertLines: { color: "rgba(255, 255, 255, 0.04)" },
        horzLines: { color: "rgba(255, 255, 255, 0.04)" },
      },
      crosshair: {
        vertLine: { color: "#38bdf8", width: 1, style: LineStyle.Dashed },
        horzLine: { color: "#38bdf8", width: 1, style: LineStyle.Dashed },
      },
      rightPriceScale: {
        borderColor: "rgba(255, 255, 255, 0.1)",
        alignLabels: true,
      },
      timeScale: {
        borderColor: "rgba(255, 255, 255, 0.1)",
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: { mouseWheel: true, pressedMouseMove: true },
      handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
    });

    chartRef.current = chart;

    let candlestickSeries: ISeriesApi<"Candlestick">;
    const isJpy = activeSymbol.includes("JPY");
    const precision = isJpy ? 3 : 5;
    const minMove = isJpy ? 0.001 : 0.00001;

    const candleOptions = {
      upColor: "#10b981",
      downColor: "#f43f5e",
      borderVisible: false,
      wickUpColor: "#34d399",
      wickDownColor: "#fb7185",
      priceFormat: {
        type: "price" as const,
        precision: precision,
        minMove: minMove,
      },
    };

    if (typeof (chart as any).addCandlestickSeries === "function") {
      candlestickSeries = (chart as any).addCandlestickSeries(candleOptions);
    } else {
      candlestickSeries = (chart as any).addSeries(CandlestickSeries, candleOptions);
    }
    candlestickSeriesRef.current = candlestickSeries;

    candlestickSeries.setData(candlesData as any);

    // Volume Series
    if (showVolume) {
      let volumeSeries: ISeriesApi<"Histogram">;
      if (typeof (chart as any).addHistogramSeries === "function") {
        volumeSeries = (chart as any).addHistogramSeries({
          color: "#38bdf8",
          priceFormat: { type: "volume" },
          priceScaleId: "",
        });
      } else {
        volumeSeries = (chart as any).addSeries(HistogramSeries, {
          color: "#38bdf8",
          priceFormat: { type: "volume" },
          priceScaleId: "",
        });
      }
      volumeSeries.priceScale().applyOptions({
        scaleMargins: { top: 0.8, bottom: 0 },
      });

      const volumeData = candlesData.map((d) => ({
        time: d.time,
        value: d.volume,
        color: d.close >= d.open ? "rgba(16, 185, 129, 0.3)" : "rgba(244, 63, 94, 0.3)",
      }));
      volumeSeries.setData(volumeData as any);
      volumeSeriesRef.current = volumeSeries;
    }



    // Trade Overlay Lines (Entry, SL, TP)
    if (openPrice > 0) {
      candlestickSeries.createPriceLine({
        price: openPrice,
        color: "#3b82f6",
        lineWidth: 2,
        lineStyle: LineStyle.Solid,
        axisLabelVisible: true,
        title: `ENTRY (${isBuy ? "BUY" : "SELL"} ${volume}L)`,
      });
    }

    if (stopLoss > 0) {
      const slLoss = calculatePL(openPrice, stopLoss, volume, activeSymbol, currentPrice, profit);
      candlestickSeries.createPriceLine({
        price: stopLoss,
        color: "#f43f5e",
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: `SL: ${fmtNum(stopLoss, 5)} (-$${slLoss.toFixed(2)})`,
      });
    }

    if (takeProfit > 0) {
      const tpProfit = calculatePL(openPrice, takeProfit, volume, activeSymbol, currentPrice, profit);
      candlestickSeries.createPriceLine({
        price: takeProfit,
        color: "#10b981",
        lineWidth: 2,
        lineStyle: LineStyle.Dashed,
        axisLabelVisible: true,
        title: `TP: ${fmtNum(takeProfit, 5)} (+$${tpProfit.toFixed(2)})`,
      });
    }

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (container && chartRef.current) {
        chartRef.current.applyOptions({
          width: container.clientWidth,
          height: container.clientHeight,
        });
      }
    };

    const resizeObserver = new ResizeObserver(() => handleResize());
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [isOpen, candlesData, isEmpty, isLoading, error, showVolume, openPrice, stopLoss, takeProfit, isBuy, volume]);

  // Predictive Fan - alohida useEffect, chunki fanData har 5 soniyada refetch
  // bo'ladi (refetchInterval). Agar bu asosiy chart-yaratish effekti bilan bir joyda
  // bo'lganida, container.innerHTML = "" tufayli har 5 soniyada butun chart
  // (candlestick, volume, resize observer, zoom holati) qayta yaratilib, foydalanuvchi
  // zoom/scroll qilgan joyi va candle'lar "sakrab" ketardi.
  const fanSeriesRefs = useRef<{ top: ISeriesApi<"Line">; bottom: ISeriesApi<"Line">; median: ISeriesApi<"Line"> } | null>(null);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    // Har safar avval eski fan series'larini tozalaymiz
    if (fanSeriesRefs.current) {
      try {
        chart.removeSeries(fanSeriesRefs.current.top);
        chart.removeSeries(fanSeriesRefs.current.bottom);
        chart.removeSeries(fanSeriesRefs.current.median);
      } catch {
        // series allaqachon chart bilan birga o'chirilgan bo'lishi mumkin
      }
      fanSeriesRefs.current = null;
    }

    if (!showFan || !fanData || !fanData.paths || fanData.paths.length === 0 || candlesData.length === 0) {
      return;
    }

    const paths = fanData.paths; // shape: (60, 15)
    const lastCandleTime = candlesData[candlesData.length - 1].time;
    const stepSeconds = timeframe === "M1" ? 60 : timeframe === "M5" ? 300 : timeframe === "M15" ? 900 : timeframe === "H1" ? 3600 : timeframe === "H4" ? 14400 : 86400;

    const p10_line: any[] = [];
    const p90_line: any[] = [];
    const median_line: any[] = [];

    const n_steps = paths[0].length;
    p10_line.push({ time: lastCandleTime, value: fanData.last_price });
    p90_line.push({ time: lastCandleTime, value: fanData.last_price });
    median_line.push({ time: lastCandleTime, value: fanData.last_price });

    for (let i = 0; i < n_steps; i++) {
      const step_prices = paths.map((p: any) => p[i]).sort((a: number, b: number) => a - b);
      const time = lastCandleTime + (i + 1) * stepSeconds;

      p10_line.push({ time, value: step_prices[Math.floor(step_prices.length * 0.1)] });
      p90_line.push({ time, value: step_prices[Math.floor(step_prices.length * 0.9)] });
      median_line.push({ time, value: step_prices[Math.floor(step_prices.length * 0.5)] });
    }

    const fanColor = fanData.direction === "BUY" ? "rgba(16, 185, 129, 0.15)" : fanData.direction === "SELL" ? "rgba(244, 63, 94, 0.15)" : "rgba(148, 163, 184, 0.15)";
    const lineColor = fanData.direction === "BUY" ? "#10b981" : fanData.direction === "SELL" ? "#f43f5e" : "#94a3b8";

    // lightweight-charts v5'da addLineSeries() metodi olib tashlangan, faqat
    // addSeries(LineSeries, options) ishlaydi. Fayl yuqorida candlestick/histogram
    // uchun bu farq to'g'ri hisobga olingan (typeof tekshiruvi bilan), lekin fan
    // qismida v4-uslubidagi addLineSeries() chaqirilgan edi - shuning uchun fan
    // umuman chizilmasdi (yoki xato tashlardi), UI'da esa bu narsa "chart
    // buzilyapti" taassurotini kuchaytirgan bo'lishi mumkin.
    const makeLineSeries = (options: any): ISeriesApi<"Line"> => {
      if (typeof (chart as any).addLineSeries === "function") {
        return (chart as any).addLineSeries(options);
      }
      return (chart as any).addSeries(LineSeries, options);
    };

    const fanSeriesTop = makeLineSeries({ color: fanColor, lineWidth: 1, crosshairMarkerVisible: false, priceLineVisible: false, lastValueVisible: false });
    const fanSeriesBottom = makeLineSeries({ color: fanColor, lineWidth: 1, crosshairMarkerVisible: false, priceLineVisible: false, lastValueVisible: false });
    const fanSeriesMedian = makeLineSeries({ color: lineColor, lineWidth: 2, lineStyle: LineStyle.Dashed, crosshairMarkerVisible: false, priceLineVisible: false, lastValueVisible: false });

    // MUHIM: fan chiziqlari price/time scale'ni avtomatik masshtablashda hisobga
    // olinmasin. Aks holda 15 qadamlik proyeksiya x-o'qini juda uzoqqa cho'zib,
    // fitContent() chaqirilganda asosiy candlestick'lar chapga siqilib qoladi
    // ("chart oynasidan chiqib ketish" effekti aynan shundan kelib chiqadi).
    fanSeriesTop.applyOptions({ autoscaleInfoProvider: () => null });
    fanSeriesBottom.applyOptions({ autoscaleInfoProvider: () => null });
    fanSeriesMedian.applyOptions({ autoscaleInfoProvider: () => null });

    fanSeriesTop.setData(p90_line);
    fanSeriesBottom.setData(p10_line);
    fanSeriesMedian.setData(median_line);

    fanSeriesRefs.current = { top: fanSeriesTop, bottom: fanSeriesBottom, median: fanSeriesMedian };

    return () => {
      if (fanSeriesRefs.current && chartRef.current) {
        try {
          chart.removeSeries(fanSeriesRefs.current.top);
          chart.removeSeries(fanSeriesRefs.current.bottom);
          chart.removeSeries(fanSeriesRefs.current.median);
        } catch {
          // chart allaqachon unmount bo'lgan bo'lishi mumkin
        }
        fanSeriesRefs.current = null;
      }
    };
  }, [showFan, fanData, candlesData, timeframe]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-2 sm:p-4 animate-in fade-in duration-200">
      <div className="flex flex-col w-full max-w-5xl h-[95vh] bg-[#090d16] border border-white/10 rounded-2xl sm:rounded-3xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-2 py-1.5 border-b border-white/10 bg-[#0d1424]">
          <div className="flex items-center gap-1 sm:gap-2">
            <button
              onClick={onClose}
              className="p-1 text-white/70 hover:text-white hover:bg-white/10 rounded-lg transition-colors flex items-center gap-0.5 text-xs font-bold shrink-0"
              title="Ortga qaytish"
            >
              <ArrowLeft size={14} />
              <span className="hidden sm:inline">Ortga</span>
            </button>
            <div className="h-4 w-px bg-white/10 hidden sm:block mx-0.5" />
            
            <div className="flex items-center gap-1.5">
              <span className={`px-1.5 py-0.5 rounded-lg text-[10px] font-black tracking-wider uppercase ${
                isBuy ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-rose-500/20 text-rose-400 border border-rose-500/30"
              }`}>
                {isBuy ? "BUY" : "SELL"}
              </span>
              <div className="relative flex items-center">
                <button 
                  onClick={() => setShowSymbolList(!showSymbolList)}
                  className="flex items-center gap-1 px-1 py-0.5 -ml-1 rounded-lg hover:bg-white/10 transition-colors"
                >
                  <h2 className="text-sm sm:text-base font-black text-white tracking-wide">{activeSymbol}</h2>
                  <ChevronDown size={12} className={`text-white/50 transition-transform ${showSymbolList ? "rotate-180" : ""}`} />
                </button>

                {showSymbolList && (
                  <div className="absolute top-full left-0 mt-2 w-64 max-h-[60vh] flex flex-col bg-[#0d1424] border border-white/10 rounded-xl shadow-2xl z-[100]">
                    <div className="p-2 border-b border-white/5 relative shrink-0">
                      <Search size={14} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/40" />
                      <input 
                        type="text" 
                        autoFocus
                        value={searchQuery}
                        onChange={e => setSearchQuery(e.target.value)}
                        placeholder="Juftlik qidirish..." 
                        className="w-full bg-black/20 text-white text-sm rounded-lg pl-8 pr-3 py-2 outline-none border border-transparent focus:border-white/10 transition-colors"
                      />
                    </div>
                    <div className="flex-1 overflow-y-auto p-1 custom-scrollbar min-h-0">
                      {filteredSymbols.length > 0 ? (
                        filteredSymbols.map(sym => {
                          const isLoaded = loadedSymbols.includes(sym);
                          const activePos = positionsData?.find(p => p.symbol === sym);
                          const hasLimit = pendingOrdersData?.some(p => p.symbol === sym);
                          const posProfit = activePos ? Number(activePos.profit || 0) : 0;
                          
                          return (
                            <button
                              key={sym}
                              onClick={() => handleSymbolSelect(sym)}
                              className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-bold tracking-wide transition-colors ${
                                sym === activeSymbol 
                                  ? "bg-blue-500/20 text-blue-400" 
                                  : isLoaded ? "text-white hover:bg-white/10" : "text-white/30 hover:bg-white/5"
                              }`}
                            >
                              <div className="flex items-center gap-2">
                                <span>{sym}</span>
                                {!isLoaded && <span className="text-[9px] px-1.5 py-0.5 rounded bg-white/5 text-white/30 font-medium border border-white/5">No Data</span>}
                                {hasLimit && <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 font-medium border border-amber-500/20">Limit</span>}
                              </div>
                              {activePos && (
                                <div className={`text-[10px] px-2 py-0.5 rounded-md flex items-center gap-1 ${
                                  posProfit >= 0 ? "bg-emerald-500/10 text-emerald-400" : "bg-rose-500/10 text-rose-400"
                                }`}>
                                  {posProfit >= 0 ? "+" : ""}{fmtMoney(posProfit)}
                                </div>
                              )}
                            </button>
                          );
                        })
                      ) : (
                        <div className="p-4 text-center text-xs text-white/40">Topilmadi</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
              {activePosition && (
                <span className="text-[9px] text-white/50 font-semibold bg-white/5 px-1.5 py-0.5 rounded-full border border-white/10">
                  {fmtNum(volume, 2)}<span className="hidden min-[380px]:inline"> lot</span>
                </span>
              )}
            </div>

            {activePosition && (
              <div className={`flex items-center gap-0.5 px-1.5 py-0.5 rounded-md text-[9px] font-black backdrop-blur-md border ${
                profit >= 0 ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-rose-500/10 text-rose-400 border-rose-500/20"
              }`}>
                {profit >= 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                <span>{profit >= 0 ? "+" : ""}{fmtMoney(profit)}</span>
              </div>
            )}
          </div>

          <button
            onClick={onClose}
            className="p-1 text-white/60 hover:text-white bg-white/5 hover:bg-white/10 rounded-lg border border-white/10 transition-colors"
          >
            <X size={14} />
          </button>
        </div>

        {/* Trade Metrics Strip */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-1.5 bg-[#0b101c] border-b border-white/5 text-[10px] font-bold">
          <div className="flex items-center gap-1">
            <span className="text-white/40 uppercase text-[8px] tracking-wider">Open:</span>
            <span className="text-white tabular-nums">{openPrice > 0 ? fmtNum(openPrice, 5) : "—"}</span>
          </div>
          <div className="h-3 w-px bg-white/10" />
          <div className="flex items-center gap-1">
            <span className="text-white/40 uppercase text-[8px] tracking-wider">Current:</span>
            <span className="text-blue-400 tabular-nums">{currentPrice > 0 ? fmtNum(currentPrice, 5) : "—"}</span>
          </div>
          <div className="h-3 w-px bg-white/10" />
          <div className="flex items-center gap-1">
            <span className="text-rose-400/80 uppercase text-[8px] tracking-wider flex items-center gap-0.5"><ShieldAlert size={8} /> SL:</span>
            <span className="text-rose-400 tabular-nums">{stopLoss > 0 ? fmtNum(stopLoss, 5) : "Yo'q"}</span>
          </div>
          <div className="h-3 w-px bg-white/10" />
          <div className="flex items-center gap-1">
            <span className="text-emerald-400/80 uppercase text-[8px] tracking-wider flex items-center gap-0.5"><Target size={8} /> TP:</span>
            <span className="text-emerald-400 tabular-nums">{takeProfit > 0 ? fmtNum(takeProfit, 5) : "Yo'q"}</span>
          </div>
        </div>

        {/* Toolbar (Timeframes & Controls) */}
        <div className="flex flex-wrap items-center justify-between px-4 py-2 bg-[#090d16] border-b border-white/5 gap-2">
          {/* Timeframe Selector */}
          <div className="flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/5">
            {(["M1", "M5", "M15", "H1", "H4", "D1"] as Timeframe[]).map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-2.5 py-1 text-[11px] font-bold rounded-lg transition-all ${
                  timeframe === tf
                    ? "bg-blue-600 text-white shadow-lg shadow-blue-600/30"
                    : "text-white/50 hover:text-white hover:bg-white/5"
                }`}
              >
                {tf}
              </button>
            ))}
          </div>

          {/* Indicator Toggles */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowFan(!showFan)}
              className={`flex items-center gap-1 px-2.5 py-1 text-[11px] font-bold rounded-xl border transition-all ${
                showFan
                  ? "bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-lg shadow-amber-500/20"
                  : "bg-white/5 text-white/40 border-white/5 hover:text-white"
              }`}
              title="Monte Carlo Fan Simulator"
            >
              <Activity size={12} /> MC {isLoadingFan && <Loader2 size={10} className="animate-spin" />}
            </button>
            <button
              onClick={() => setShowSMC(!showSMC)}
              className={`flex items-center gap-1 px-2.5 py-1 text-[11px] font-bold rounded-xl border transition-all ${
                showSMC
                  ? "bg-purple-500/20 text-purple-300 border-purple-500/40"
                  : "bg-white/5 text-white/40 border-white/5 hover:text-white"
              }`}
            >
              <Layers size={12} /> SMC
            </button>
            <button
              onClick={() => setShowVolume(!showVolume)}
              className={`flex items-center gap-1 px-2.5 py-1 text-[11px] font-bold rounded-xl border transition-all ${
                showVolume
                  ? "bg-sky-500/20 text-sky-300 border-sky-500/40"
                  : "bg-white/5 text-white/40 border-white/5 hover:text-white"
              }`}
            >
              <BarChart2 size={12} /> Vol
            </button>
          </div>
        </div>

        {/* Main Chart Area */}
        <div className="relative flex-1 w-full bg-[#090d16] overflow-hidden flex items-center justify-center">
          {isLoading ? (
            <div className="flex flex-col items-center gap-3 text-white/50 z-20">
              <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
              <span className="text-[10px] font-bold uppercase tracking-wider">Ma'lumotlar yuklanmoqda...</span>
            </div>
          ) : error ? (
            <div className="text-rose-400 text-[11px] font-bold bg-rose-500/10 px-4 py-2 rounded-xl border border-rose-500/20 z-20 max-w-xs text-center">
              {error}
            </div>
          ) : isEmpty ? (
            <div className="text-white/50 text-[11px] font-bold flex flex-col items-center gap-3 z-20 bg-white/5 px-6 py-4 rounded-2xl border border-white/5">
              <BarChart2 className="w-10 h-10 opacity-30" />
              Hali sinxronizatsiya qilinmagan
              <span className="text-[9px] text-white/30 uppercase tracking-widest">{timeframe}</span>
            </div>
          ) : (
            <>
              <div ref={chartContainerRef} className="w-full h-full absolute inset-0 z-0" />
              
              {/* Overlay SMC Smart Money Info Badge */}
              {showSMC && smcZonesData.length > 0 && (
                <div className="absolute top-3 left-3 z-10 bg-black/80 backdrop-blur-md px-3 py-2 rounded-xl border border-purple-500/30 shadow-lg text-[10px] space-y-1.5 max-w-[200px] max-h-[160px] overflow-y-auto">
                  <div className="flex items-center gap-1.5 font-black text-purple-400 uppercase tracking-wider mb-2 sticky top-0 bg-black/80">
                    <Layers size={12} /> SMC Zones
                  </div>
                  {smcZonesData.map((zone) => (
                    <div key={zone.id} className="flex flex-col gap-0.5 border-b border-white/5 pb-1.5 last:border-0 last:pb-0">
                      <span className="text-white/60 capitalize text-[9px] font-medium">{zone.zone_type.replace('_', ' ')}</span>
                      <span className={`font-bold tabular-nums ${zone.direction === 'demand' || zone.direction === 'bullish' ? 'text-emerald-400' : 'text-rose-400'}`}>
                        {zone.direction.toUpperCase()} {fmtNum(Number(zone.top), 5)} - {fmtNum(Number(zone.bottom), 5)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer info bar */}
        <div className="px-4 py-2 bg-[#0d1424] border-t border-white/10 flex items-center justify-between text-[11px] text-white/50">
          <span>Smart Trading Chart</span>
          <span className="flex items-center gap-1">
            <Activity size={12} className="text-emerald-400 animate-pulse" /> Live Price Feed
          </span>
        </div>
      </div>
    </div>
  );
}
