import React, { useEffect, useRef, useState } from "react";
import { get, set } from "idb-keyval";
import { createChart, ColorType, LineStyle, IChartApi, ISeriesApi, CandlestickSeries, HistogramSeries, LineSeries } from "lightweight-charts";
import { X, TrendingUp, TrendingDown, Layers, Activity, Eye, RefreshCw, BarChart2, ShieldAlert, Target, Loader2, ChevronDown, Search, ArrowLeft } from "lucide-react";
import pubgLoader from "@/assets/pubg-loader.svg";
import { useQuery } from "@tanstack/react-query";
import { fmtMoney, fmtNum } from "@/lib/utils";
import type { Position } from "@/lib/types";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/hooks/useAuth";
import { ZoneRectanglePrimitive, ZoneData } from "./chart-primitives/ZoneRectanglePrimitive";
import { ConnectedLinePrimitive, LineData } from "./chart-primitives/ConnectedLinePrimitive";
import { EventMarkerPrimitive, EventMarkerData } from "./chart-primitives/EventMarkerPrimitive";

import { guestMock } from "@/lib/guestMock";

interface TradingChartModalProps {
  isOpen: boolean;
  onClose: () => void;
  symbol: string;
  position?: Position | null;
}

type Timeframe = "M1" | "M5" | "M15" | "H1" | "H4" | "D1";

const parseTimeToSec = (t: any) => {
  if (!t) return 0;
  if (typeof t === "number") {
    return t > 2000000000 ? Math.floor(t / 1000) : t;
  }
  return Math.floor(new Date(t).getTime() / 1000);
};

const getAlpha = (confidence: number | undefined, maxAlpha: number, minAlpha: number) => {
  if (confidence === undefined || confidence === null) return maxAlpha;
  const ratio = Math.max(0, Math.min(100, confidence)) / 100;
  return minAlpha + ratio * (maxAlpha - minAlpha);
};

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
  const zonePrimitiveRef = useRef<ZoneRectanglePrimitive | null>(null);
  const linePrimitiveRef = useRef<ConnectedLinePrimitive | null>(null);
  const eventMarkerRef = useRef<EventMarkerPrimitive | null>(null);

  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  const [timeframe, setTimeframe] = useState<Timeframe>("M5");
  const [showSMC, setShowSMC] = useState(true);
  const [showVolume, setShowVolume] = useState(true);
  const [showFan, setShowFan] = useState(false);
  const [showHarmonic, setShowHarmonic] = useState(false);
  const [showWyckoff, setShowWyckoff] = useState(false);
  const [showSRVolume, setShowSRVolume] = useState(false);
  const [showAutoPattern, setShowAutoPattern] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isEmpty, setIsEmpty] = useState(false);
  const [candlesData, setCandlesData] = useState<any[]>([]);
  const [smcZonesData, setSmcZonesData] = useState<any[]>([]);
  const [harmonicData, setHarmonicData] = useState<any[]>([]);
  const [wyckoffData, setWyckoffData] = useState<any[]>([]);
  const [srVolumeData, setSrVolumeData] = useState<any[]>([]);
  const [autoPatternData, setAutoPatternData] = useState<any[]>([]);

  const [activeSymbol, setActiveSymbol] = useState(symbol);
  const [activePosition, setActivePosition] = useState<Position | null | undefined>(position);
  const [showSymbolList, setShowSymbolList] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [hoveredTooltip, setHoveredTooltip] = useState<{
    x: number;
    y: number;
    strategy: string;
    signalType: string;
    confidence: number | null;
    reasoning?: string;
    color: string;
    priceRange?: string;
  } | null>(null);

  const lastVisibleRangeRef = useRef<any>(null);
  const candlesDataRef = useRef<any[]>([]);
  const isFetchingMoreRef = useRef(false);
  const hasMoreHistoryRef = useRef(true);
  const [isFetchingMore, setIsFetchingMore] = useState(false);
  const [hasMoreHistory, setHasMoreHistory] = useState(true);

  // Sync ref with state
  useEffect(() => {
    candlesDataRef.current = candlesData;
  }, [candlesData]);

  // Reset pagination state when symbol or timeframe changes
  useEffect(() => {
    hasMoreHistoryRef.current = true;
    setHasMoreHistory(true);
    lastVisibleRangeRef.current = null;
  }, [activeSymbol, timeframe]);

  const loadMoreCandles = async () => {
    if (isFetchingMoreRef.current || !hasMoreHistoryRef.current || candlesDataRef.current.length === 0) return;
    isFetchingMoreRef.current = true;
    setIsFetchingMore(true);

    try {
      const oldestCandle = candlesDataRef.current[0];
      const oldestTimeISO = new Date(oldestCandle.time * 1000).toISOString();

      const { data: olderCandles, error: fetchErr } = await supabase
        .from("candles")
        .select("*")
        .eq("symbol", activeSymbol)
        .eq("timeframe", timeframe)
        .lt("time", oldestTimeISO)
        .order("time", { ascending: false })
        .limit(500);

      if (fetchErr) throw fetchErr;

      if (!olderCandles || olderCandles.length === 0) {
        hasMoreHistoryRef.current = false;
        setHasMoreHistory(false);
        return;
      }

      const formattedOlder = olderCandles.reverse().map((c: any) => ({
        time: Math.floor(new Date(c.time).getTime() / 1000),
        open: Number(c.open),
        high: Number(c.high),
        low: Number(c.low),
        close: Number(c.close),
        volume: c.volume ? Number(c.volume) : 0,
      }));

      // Prepend older candles to the state
      setCandlesData(prev => [...formattedOlder, ...prev]);
    } catch (err) {
      console.error("Failed to load older candles:", err);
    } finally {
      isFetchingMoreRef.current = false;
      setIsFetchingMore(false);
    }
  };

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
  const filteredSymbols = allSymbols.filter(s => (s || "").toLowerCase().includes((searchQuery || "").toLowerCase()));
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

      const cacheKey = `chartData_${activeSymbol}_${timeframe}`;
      
      try {
        // 1. Avval IndexedDB keshdan o'qiymiz (oflayn tezkor yuklanish)
        const cached = await get(cacheKey).catch(() => null);
        if (cached && isMounted) {
          if (cached.candles?.length > 0) {
            const formattedCachedCandles = cached.candles.map((c: any) => ({
              ...c,
              time: typeof c.time === 'number' ? c.time : Math.floor(new Date(c.time).getTime() / 1000)
            }));
            setCandlesData(formattedCachedCandles);
          }
          // MUHIM: Toggle holatidan qat'iy nazar BARCHA strategiya datalarini state ga yozamiz.
          // Aks holda foydalanuvchi SMC tugmasini bosganda data bo'sh bo'ladi.
          if (cached.smc) setSmcZonesData(cached.smc);
          if (cached.harmonic) setHarmonicData(cached.harmonic);
          if (cached.wyckoff) setWyckoffData(cached.wyckoff);
          if (cached.srVolume) setSrVolumeData(cached.srVolume);
          if (cached.autoPattern) setAutoPatternData(cached.autoPattern);
          
          if (cached.candles?.length > 0) {
             setIsLoading(false);
          }
        }
        
        // 2. Supabase'dan yangi kandel va BARCHA strategiya ma'lumotlarini tortamiz
        const [
          { data: candles, error: candlesError },
          { data: zones },
          { data: harmonics },
          { data: wyckoffs },
          { data: sr },
          { data: ap }
        ] = await Promise.all([
          supabase.from("candles").select("*").eq("symbol", activeSymbol).eq("timeframe", timeframe).order("time", { ascending: false }).limit(1000),
          supabase.from("smc_zones").select("*").eq("symbol", activeSymbol).eq("timeframe", timeframe).eq("status", "fresh"),
          (supabase as any).from("harmonic_patterns").select("*").eq("symbol", activeSymbol).eq("timeframe", timeframe).eq("status", "fresh"),
          (supabase as any).from("wyckoff_events").select("*").eq("symbol", activeSymbol).eq("timeframe", timeframe).eq("status", "fresh"),
          (supabase as any).from("sr_volume_zones").select("*").eq("symbol", activeSymbol).eq("timeframe", timeframe).eq("status", "fresh"),
          (supabase as any).from("auto_patterns").select("*").eq("symbol", activeSymbol).eq("timeframe", timeframe).eq("status", "fresh")
        ]);

        if (candlesError) throw candlesError;

        if (!candles || candles.length === 0) {
          if (isMounted && !cached?.candles?.length) setIsEmpty(true);
          return;
        }

        const formattedCandles = candles.reverse().map((c: any) => ({
          time: Math.floor(new Date(c.time).getTime() / 1000),
          open: Number(c.open),
          high: Number(c.high),
          low: Number(c.low),
          close: Number(c.close),
          volume: c.volume ? Number(c.volume) : 0,
        }));

        if (isMounted) {
          setCandlesData(formattedCandles);
          setSmcZonesData(zones && zones.length > 0 ? zones : (cached?.smc || []));
          setHarmonicData(harmonics && harmonics.length > 0 ? harmonics : (cached?.harmonic || []));
          setWyckoffData(wyckoffs && wyckoffs.length > 0 ? wyckoffs : (cached?.wyckoff || []));
          setSrVolumeData(sr && sr.length > 0 ? sr : (cached?.srVolume || []));
          setAutoPatternData(ap && ap.length > 0 ? ap : (cached?.autoPattern || []));
        }
        
        // Keshga saqlash
        await set(cacheKey, {
          candles: formattedCandles,
          smc: zones && zones.length > 0 ? zones : (cached?.smc || []),
          harmonic: harmonics && harmonics.length > 0 ? harmonics : (cached?.harmonic || []),
          wyckoff: wyckoffs && wyckoffs.length > 0 ? wyckoffs : (cached?.wyckoff || []),
          srVolume: sr && sr.length > 0 ? sr : (cached?.srVolume || []),
          autoPattern: ap && ap.length > 0 ? ap : (cached?.autoPattern || [])
        }).catch(() => null);

      } catch (err: any) {
        console.warn("Supabase fetch failed, trying local fallback:", err);
        try {
           // Oflayn/Fallback: Python bot saqlagan lokal JSON fayldan o'qish
           const res = await fetch(`/data/chart_${activeSymbol}_${timeframe}.json`);
           if (res.ok) {
              const localData = await res.json();
              if (localData.candles && isMounted) {
                 const formattedLocalCandles = localData.candles.map((c: any) => ({
                   ...c,
                   time: parseTimeToSec(c.time),
                   open: Number(c.open),
                   high: Number(c.high),
                   low: Number(c.low),
                   close: Number(c.close),
                   volume: c.volume ? Number(c.volume) : 0,
                 }));
                 setCandlesData(formattedLocalCandles);
                 setSmcZonesData(localData.strategy_overlays?.smc || []);
                 setHarmonicData(localData.strategy_overlays?.harmonic || []);
                 setWyckoffData(localData.strategy_overlays?.wyckoff || []);
                 setSrVolumeData(localData.strategy_overlays?.sr_volume || []);
                 setAutoPatternData(localData.strategy_overlays?.auto_patterns || []);
                 
                 await set(cacheKey, {
                    candles: formattedLocalCandles,
                    smc: localData.strategy_overlays?.smc || [],
                    harmonic: localData.strategy_overlays?.harmonic || [],
                    wyckoff: localData.strategy_overlays?.wyckoff || [],
                    srVolume: localData.strategy_overlays?.sr_volume || [],
                    autoPattern: localData.strategy_overlays?.auto_patterns || []
                 }).catch(() => null);
                 return;
              }
           }
        } catch (localErr) {
           console.warn("Local fallback failed:", localErr);
        }
        
        const cached = await get(cacheKey).catch(() => null);
        if (!cached?.candles?.length && isMounted) {
           setError(err.message || "Ma'lumotlarni yuklashda xatolik yuz berdi");
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    fetchChartData();

    return () => { isMounted = false; };
  }, [isOpen, activeSymbol, timeframe]);

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

    // Restore visible time range if exists to prevent scroll reset
    if (lastVisibleRangeRef.current) {
      try {
        chart.timeScale().setVisibleRange(lastVisibleRangeRef.current);
      } catch (e) {}
    }

    // Subscribe to visible range changes to save position
    chart.timeScale().subscribeVisibleTimeRangeChange((range) => {
      if (range) {
        lastVisibleRangeRef.current = range;
      }
    });

    // Subscribe to logical range changes to lazy load older candles when scrolled to the left
    chart.timeScale().subscribeVisibleLogicalRangeChange((logicalRange) => {
      if (!logicalRange) return;
      if (logicalRange.from < 10) {
        loadMoreCandles();
      }
    });

    let candlestickSeries: ISeriesApi<"Candlestick">;
    let precision = 5;
    let minMove = 0.00001;
    
    // Asset-Agnostic Y-Scale
    if (candlesData.length > 0) {
       const avgPrice = candlesData[0].close;
       if (avgPrice > 5000) { precision = 2; minMove = 0.01; } // BTC, US30, NAS100
       else if (avgPrice > 1000) { precision = 2; minMove = 0.01; } // XAU, ETH
       else if (avgPrice > 50) { precision = 3; minMove = 0.001; } // JPY pairs, WTI
       else if (avgPrice > 2) { precision = 4; minMove = 0.0001; } // Some altcoins
       else if (avgPrice < 0.01) { precision = 7; minMove = 0.0000001; } // SHIB, PEPE
       else { precision = 5; minMove = 0.00001; } // Major forex EURUSD, GBPUSD
    }

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
        try {
          chartRef.current.remove();
        } catch (e) {}
        chartRef.current = null;
      }
      candlestickSeriesRef.current = null;
      fanSeriesRefs.current = null;
      zonePrimitiveRef.current = null;
      eventMarkerRef.current = null;
      linePrimitiveRef.current = null;
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


  // Combined Zones - drawn as an official Series Primitive
  useEffect(() => {
    const series = candlestickSeriesRef.current;
    if (!series) return;

    if (zonePrimitiveRef.current) {
      try {
        series.detachPrimitive(zonePrimitiveRef.current);
      } catch {}
      zonePrimitiveRef.current = null;
    }

    const aggregatedZones: ZoneData[] = [];

    // Add SMC Zones (Purple)
    if (showSMC && smcZonesData && smcZonesData.length > 0) {
      smcZonesData.forEach(z => {
        aggregatedZones.push({
          top: z.top,
          bottom: z.bottom,
          start_time: z.formed_at || z.time,
          direction: z.direction,
          color: `rgba(168, 85, 247, ${getAlpha(z.confidence, 0.25, 0.05)})`,
          borderColor: `rgba(168, 85, 247, ${getAlpha(z.confidence, 0.8, 0.2)})`
        });
      });
    }

    // Add SR Volume Zones (Green for Support, Red for Resistance)
    if (showSRVolume && srVolumeData && srVolumeData.length > 0) {
      srVolumeData.forEach(z => {
        const price = z.price || (z.top_price && z.bottom_price ? (Number(z.top_price) + Number(z.bottom_price)) / 2 : 0);
        const margin = Number(price) * 0.001; // 0.1% margin for thickness
        const isSupport = (z.zone_type || z.type || '').toLowerCase().includes('support') || (z.zone_type || z.type || '').toLowerCase().includes('demand');
        aggregatedZones.push({
          top: z.top_price ? Number(z.top_price) : (Number(price) + margin),
          bottom: z.bottom_price ? Number(z.bottom_price) : (Number(price) - margin),
          start_time: z.formed_at || z.time,
          direction: isSupport ? 'support' : 'resistance',
          color: isSupport ? `rgba(16, 185, 129, ${getAlpha(z.confidence, 0.25, 0.05)})` : `rgba(244, 63, 94, ${getAlpha(z.confidence, 0.25, 0.05)})`,
          borderColor: isSupport ? `rgba(16, 185, 129, ${getAlpha(z.confidence, 0.8, 0.2)})` : `rgba(244, 63, 94, ${getAlpha(z.confidence, 0.8, 0.2)})`
        });
      });
    }

    if (aggregatedZones.length > 0) {
      const primitive = new ZoneRectanglePrimitive(aggregatedZones);
      series.attachPrimitive(primitive);
      zonePrimitiveRef.current = primitive;
    }

    return () => {
      if (zonePrimitiveRef.current && candlestickSeriesRef.current) {
        try {
          candlestickSeriesRef.current.detachPrimitive(zonePrimitiveRef.current);
        } catch {}
      }
    };
  }, [showSMC, showSRVolume, smcZonesData, srVolumeData, candlesData]);

  // Wyckoff Events - Event Markers (Blue)
  useEffect(() => {
    const series = candlestickSeriesRef.current;
    if (!series) return;

    if (eventMarkerRef.current) {
      try {
        eventMarkerRef.current.detach();
      } catch {}
      eventMarkerRef.current = null;
    }

    if (showWyckoff && wyckoffData && wyckoffData.length > 0 && candlesData.length > 0) {
      const events: EventMarkerData[] = wyckoffData.map(w => {
        const rawTime = w.formed_at || w.time || w.event_time;
        const evTimeSec = parseTimeToSec(rawTime);
        let snapTime = evTimeSec;
        
        // Volume kabi bar_index orqali bog'lash
        const bIdx = w.event_bar_index ?? w.bar_index;
        if (bIdx !== undefined && bIdx !== null && bIdx >= 0 && bIdx < candlesData.length) {
            snapTime = candlesData[bIdx].time;
        } else if (candlesData.length > 0) {
           const closest = candlesData.reduce((prev, curr) => Math.abs(curr.time - evTimeSec) < Math.abs(prev.time - evTimeSec) ? curr : prev);
           if (Math.abs(closest.time - evTimeSec) < 86400 * 2) {
               snapTime = closest.time;
           }
        }
        return {
        time: snapTime,
        text: w.phase || w.event_type || 'Event',
        type: 'neutral', // use neutral so we can customize color
        color: `rgba(59, 130, 246, ${getAlpha(w.confidence, 1, 0.3)})`,
        };
      });

      eventMarkerRef.current = new EventMarkerPrimitive(series, events, candlesData);
    }

    return () => {
      if (eventMarkerRef.current) {
        try {
          eventMarkerRef.current.detach();
        } catch {}
        eventMarkerRef.current = null;
      }
    };
  }, [showWyckoff, wyckoffData, candlesData]);

  // Connected Lines - Harmonic (Gold) & Auto Patterns (Orange)
  useEffect(() => {
    const series = candlestickSeriesRef.current;
    if (!series) return;

    if (linePrimitiveRef.current) {
      try {
        series.detachPrimitive(linePrimitiveRef.current);
      } catch {}
      linePrimitiveRef.current = null;
    }

    const aggregatedLines: LineData[] = [];

    // Check if auto patterns have lines data in their JSON (Orange)
    if (showAutoPattern && autoPatternData && autoPatternData.length > 0) {
      autoPatternData.forEach(a => {
        let pts: any[] = [];
        if (a.pivots && Array.isArray(a.pivots) && a.pivots.length > 0) {
           // Map pivots directly
           const snap = (t: number) => {
              if (candlesData.length === 0) return t;
              return candlesData.reduce((prev, curr) => Math.abs(curr.time - t) < Math.abs(prev.time - t) ? curr : prev).time;
           };
           pts = a.pivots.map((p: any) => ({
              time: snap(parseTimeToSec(p.time || p.date)),
              price: Number(p.price || p.val)
           }));
        } else if (a.pattern_points) {
           // For simple cases where points are given in a dict
           const snap = (t: number) => {
              if (candlesData.length === 0) return t;
              return candlesData.reduce((prev, curr) => Math.abs(curr.time - t) < Math.abs(prev.time - t) ? curr : prev).time;
           };
           const keys = Object.keys(a.pattern_points).sort(); // Sort keys like A, B, C or 0, 1, 2
           pts = keys.map(k => {
               const p = a.pattern_points[k];
               return {
                  time: snap(parseTimeToSec(p.time || p.date)),
                  price: Number(p.price || p.val)
               };
           }).filter(p => !isNaN(p.price));
        }

        if (pts.length > 1) {
           aggregatedLines.push({
             points: pts,
             color: `rgba(249, 115, 22, ${getAlpha(a.confidence, 1, 0.4)})`,
             lineWidth: 2
           });
        }
      });
    }

    // Check if harmonic patterns have points/lines (Gold/Yellow)
    if (showHarmonic && harmonicData && harmonicData.length > 0) {
      harmonicData.forEach(h => {
        let pts: any[] = [];
        if (h.points && Array.isArray(h.points)) {
            pts = h.points;
        } else if (h.x_time && h.x_price) {
            // Reconstruct points array from x, a, b, c, d columns
            const tX = parseTimeToSec(h.x_time);
            const tA = parseTimeToSec(h.a_time);
            const tB = parseTimeToSec(h.b_time);
            const tC = parseTimeToSec(h.c_time);
            const tD = parseTimeToSec(h.d_time);
            
            // Map to closest candle time for snapping or use exact bar_index
            const snap = (t: number, bIdx?: number) => {
               if (bIdx !== undefined && bIdx !== null && bIdx >= 0 && bIdx < candlesData.length) {
                   return candlesData[bIdx].time;
               }
               if (candlesData.length === 0) return t;
               return candlesData.reduce((prev, curr) => Math.abs(curr.time - t) < Math.abs(prev.time - t) ? curr : prev).time;
            };
            
            pts = [
                { time: snap(tX, h.x_bar_index), price: Number(h.x_price) },
                { time: snap(tA, h.a_bar_index), price: Number(h.a_price) },
                { time: snap(tB, h.b_bar_index), price: Number(h.b_price) },
                { time: snap(tC, h.c_bar_index), price: Number(h.c_price) },
                { time: snap(tD, h.d_bar_index), price: Number(h.d_price) }
            ];
        }
        
        if (pts.length > 0) {
          aggregatedLines.push({
             points: pts,
             color: `rgba(234, 179, 8, ${getAlpha(h.confidence, 1, 0.5)})`,
             lineWidth: 2,
             fillColor: `rgba(234, 179, 8, ${getAlpha(h.confidence, 0.2, 0.1)})`
          });
        }
      });
    }

    if (aggregatedLines.length > 0) {
      const primitive = new ConnectedLinePrimitive(aggregatedLines);
      series.attachPrimitive(primitive);
      linePrimitiveRef.current = primitive;
    }

    return () => {
      if (linePrimitiveRef.current && candlestickSeriesRef.current) {
        try {
          candlestickSeriesRef.current.detachPrimitive(linePrimitiveRef.current);
        } catch {}
      }
    };
  }, [showAutoPattern, showHarmonic, autoPatternData, harmonicData, candlesData]);


  // Dynamic detailed tooltip matching crosshair hover on indicators
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    const handleCrosshairMove = (param: any) => {
      if (
        !param.point ||
        !param.time ||
        param.point.x < 0 ||
        param.point.y < 0
      ) {
        setHoveredTooltip(null);
        return;
      }

      const series = candlestickSeriesRef.current;
      if (!series) return;
      const hoveredPrice = series.coordinateToPrice(param.point.y);
      if (!hoveredPrice) return;

      const hoverTimeSec = typeof param.time === "number" 
        ? param.time 
        : (param.time as any).value || new Date(param.time).getTime() / 1000;

      const matchedIndicators: any[] = [];

      // 1. SMC Zones
      if (showSMC && smcZonesData && smcZonesData.length > 0) {
        smcZonesData.forEach(z => {
          const zTimeSec = parseTimeToSec(z.formed_at || z.time);
          const isPriceInside = hoveredPrice >= Number(z.bottom) && hoveredPrice <= Number(z.top);
          if (isPriceInside && hoverTimeSec >= zTimeSec - 3600) {
            matchedIndicators.push({
              strategy: "Smart Money Concepts (SMC)",
              signalType: `${z.zone_type.replace("_", " ").toUpperCase()} (${z.direction.toUpperCase()})`,
              confidence: z.confidence || null,
              reasoning: z.reasoning || z.description || "Smart Money demand/supply imbalance detected.",
              color: "border-purple-500/50 text-purple-400 bg-purple-950/90",
              priceRange: `${fmtNum(z.bottom, 5)} - ${fmtNum(z.top, 5)}`,
              dist: Math.abs(hoveredPrice - (Number(z.bottom) + Number(z.top)) / 2)
            });
          }
        });
      }

      // 2. SR Volume Zones
      if (showSRVolume && srVolumeData && srVolumeData.length > 0) {
        srVolumeData.forEach(z => {
          const zTimeSec = parseTimeToSec(z.formed_at || z.time);
          const zPrice = Number(z.price);
          const margin = zPrice * 0.005; // 0.5% tolerance
          const isPriceClose = Math.abs(hoveredPrice - zPrice) <= margin;
          if (isPriceClose && hoverTimeSec >= zTimeSec - 3600) {
            const isSupport = (z.type || "").toLowerCase().includes("support") || (z.type || "").toLowerCase().includes("demand");
            matchedIndicators.push({
              strategy: "Support & Resistance (Volume)",
              signalType: z.type.toUpperCase(),
              confidence: z.confidence || null,
              reasoning: z.reasoning || z.description || "Volume-profile based key psychological levels.",
              color: isSupport 
                ? "border-emerald-500/50 text-emerald-400 bg-emerald-950/90" 
                : "border-rose-500/50 text-rose-400 bg-rose-950/90",
              priceRange: `@ ${fmtNum(zPrice, 5)}`,
              dist: Math.abs(hoveredPrice - zPrice)
            });
          }
        });
      }

      // 3. Wyckoff Events
      if (showWyckoff && wyckoffData && wyckoffData.length > 0) {
        wyckoffData.forEach(w => {
          const wTimeSec = parseTimeToSec(w.formed_at || w.time);
          const stepSeconds = timeframe === "M1" ? 60 : timeframe === "M5" ? 300 : timeframe === "M15" ? 900 : timeframe === "H1" ? 3600 : timeframe === "H4" ? 14400 : 86400;
          if (Math.abs(hoverTimeSec - wTimeSec) <= stepSeconds * 2.5) {
            matchedIndicators.push({
              strategy: "Wyckoff Market Cycles",
              signalType: `${w.phase} - ${w.signal}`,
              confidence: w.confidence || null,
              reasoning: w.reasoning || w.description || "Accumulation/Distribution phase structural transition event.",
              color: "border-blue-500/50 text-blue-400 bg-blue-950/90",
              priceRange: `Time: ${new Date(wTimeSec * 1000).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`,
              dist: Math.abs(hoverTimeSec - wTimeSec) / stepSeconds
            });
          }
        });
      }

      // 4. Auto Patterns
      if (showAutoPattern && autoPatternData && autoPatternData.length > 0) {
        autoPatternData.forEach(a => {
          const aTimeSec = parseTimeToSec(a.formed_at || a.time);
          const stepSeconds = timeframe === "M1" ? 60 : timeframe === "M5" ? 300 : timeframe === "M15" ? 900 : timeframe === "H1" ? 3600 : timeframe === "H4" ? 14400 : 86400;
          if (Math.abs(hoverTimeSec - aTimeSec) <= stepSeconds * 2.5) {
            matchedIndicators.push({
              strategy: "Auto Pattern Finder",
              signalType: `${a.pattern_type.toUpperCase()} (${a.signal})`,
              confidence: a.confidence || null,
              reasoning: a.reasoning || a.description || "Chart geometry pattern recognition logic triggered.",
              color: "border-orange-500/50 text-orange-400 bg-orange-950/90",
              dist: Math.abs(hoverTimeSec - aTimeSec) / stepSeconds
            });
          }
        });
      }

      // 5. Harmonic Patterns
      if (showHarmonic && harmonicData && harmonicData.length > 0) {
        harmonicData.forEach(h => {
          const hTimeSec = parseTimeToSec(h.formed_at || h.time);
          const stepSeconds = timeframe === "M1" ? 60 : timeframe === "M5" ? 300 : timeframe === "M15" ? 900 : timeframe === "H1" ? 3600 : timeframe === "H4" ? 14400 : 86400;
          if (Math.abs(hoverTimeSec - hTimeSec) <= stepSeconds * 2.5) {
            matchedIndicators.push({
              strategy: "Harmonic Patterns",
              signalType: `${h.pattern_type.toUpperCase()} (${h.signal})`,
              confidence: h.confidence || null,
              reasoning: h.reasoning || h.description || "Fibonacci ratio coordinate convergence completed.",
              color: "border-yellow-500/50 text-yellow-400 bg-yellow-950/90",
              dist: Math.abs(hoverTimeSec - hTimeSec) / stepSeconds
            });
          }
        });
      }

      if (matchedIndicators.length > 0) {
        matchedIndicators.sort((a, b) => a.dist - b.dist);
        const bestMatch = matchedIndicators[0];
        setHoveredTooltip({
          x: param.point.x + 15,
          y: param.point.y + 15,
          strategy: bestMatch.strategy,
          signalType: bestMatch.signalType,
          confidence: bestMatch.confidence,
          reasoning: bestMatch.reasoning,
          color: bestMatch.color,
          priceRange: bestMatch.priceRange
        });
      } else {
        setHoveredTooltip(null);
      }
    };

    chart.subscribeCrosshairMove(handleCrosshairMove);
    return () => {
      try { chart.unsubscribeCrosshairMove(handleCrosshairMove); } catch(e) {}
    };
  }, [showSMC, showSRVolume, showWyckoff, showAutoPattern, showHarmonic, smcZonesData, srVolumeData, wyckoffData, autoPatternData, harmonicData, candlesData, timeframe]);


  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-2 pt-[max(env(safe-area-inset-top),0.5rem)] pb-[max(env(safe-area-inset-bottom),0.5rem)] sm:p-4 animate-in fade-in duration-200">
      <div className="flex flex-col w-full max-w-5xl h-full max-h-[calc(100dvh-env(safe-area-inset-top)-env(safe-area-inset-bottom)-16px)] sm:h-[90vh] bg-[#090d16] border border-white/10 rounded-2xl sm:rounded-3xl shadow-2xl overflow-hidden">
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


        </div>

        {/* Main Chart Area */}
        <div className="relative flex-1 w-full bg-[#090d16] overflow-hidden flex items-center justify-center">
          {isLoading ? (
            <div className="flex flex-col items-center gap-3 text-white/50 z-20">
              <img src={pubgLoader} className="w-32 h-32 opacity-80" alt="Yuklanmoqda..." />
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

              {/* Floating Detailed Tooltip */}
              {hoveredTooltip && (
                <div 
                  className={`absolute z-30 pointer-events-none rounded-xl border p-2.5 shadow-2xl text-[10px] space-y-1.5 min-w-[180px] max-w-[240px] backdrop-blur-md transition-all duration-75 ${hoveredTooltip.color}`}
                  style={{ left: `${hoveredTooltip.x}px`, top: `${hoveredTooltip.y}px` }}
                >
                  <div className="font-extrabold text-[11px] uppercase tracking-wider text-white">
                    {hoveredTooltip.strategy}
                  </div>
                  <div className="flex items-center justify-between gap-2 border-t border-white/10 pt-1">
                    <span className="text-white/60">Signal:</span>
                    <span className="font-extrabold">{hoveredTooltip.signalType}</span>
                  </div>
                  {hoveredTooltip.priceRange && (
                    <div className="flex items-center justify-between gap-2 text-[9px]">
                      <span className="text-white/40">Range/Price:</span>
                      <span className="font-medium text-white/80 tabular-nums">{hoveredTooltip.priceRange}</span>
                    </div>
                  )}
                  {hoveredTooltip.confidence !== null && (
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-white/60">Confidence:</span>
                      <span className="font-extrabold flex items-center gap-1.5">
                        <span className="text-emerald-400">{hoveredTooltip.confidence}%</span>
                        <div className="w-12 h-1.5 bg-white/10 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-emerald-400" 
                            style={{ width: `${hoveredTooltip.confidence}%` }}
                          />
                        </div>
                      </span>
                    </div>
                  )}
                  {hoveredTooltip.reasoning && (
                    <div className="text-[9px] text-white/70 italic leading-relaxed pt-1 border-t border-white/5 font-sans">
                      "{hoveredTooltip.reasoning}"
                    </div>
                  )}
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
