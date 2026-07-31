import React, { useEffect, useRef, useState } from 'react';
import { createChart, IChartApi, ISeriesApi, LineStyle, CandlestickSeries } from 'lightweight-charts';
import { supabase } from '@/integrations/supabase/client';
import { CandlestickChart } from 'lucide-react';

interface CandleData {
  time: string | number;
  open: number;
  high: number;
  low: number;
  close: number;
}

interface SmcZone {
  id: string;
  zone_type: 'order_block' | 'fvg';
  direction: 'demand' | 'supply';
  top: number;
  bottom: number;
  status: string;
}

interface Position {
  id: string;
  symbol: string;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
}

export function ChartPage() {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  const [symbol, setSymbol] = useState('EURUSD');
  const [timeframe, setTimeframe] = useState('H1');
  const [loading, setLoading] = useState(true);
  
  const [candles, setCandles] = useState<CandleData[]>([]);
  const [zones, setZones] = useState<SmcZone[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);

  // Fetch initial data
  const fetchData = async () => {
    setLoading(true);
    try {
      // 1. Fetch candles
      const { data: candlesData, error: candlesError } = await supabase
        .from('candles')
        .select('*')
        .eq('symbol', symbol)
        .eq('timeframe', timeframe)
        .order('time', { ascending: true })
        .limit(300);
      
      if (candlesError && candlesError.code !== '42P01') console.error(candlesError);

      const formattedCandles = (candlesData || []).map(c => ({
        time: Math.floor(new Date(c.time).getTime() / 1000),
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }));
      setCandles(formattedCandles);

      // 2. Fetch SMC Zones
      const { data: zonesData, error: zonesError } = await supabase
        .from('smc_zones')
        .select('*')
        .eq('symbol', symbol)
        .eq('timeframe', timeframe)
        .eq('status', 'fresh');
      
      if (zonesError && zonesError.code !== '42P01') console.error(zonesError);
      setZones(zonesData || []);

      // 3. Fetch Positions
      const { data: posData, error: posError } = await supabase
        .from('positions')
        .select('*')
        .eq('symbol', symbol);
      
      if (!posError && posData) {
        setPositions(posData);
      }
    } catch (error) {
      console.error('Error fetching chart data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, timeframe]);

  // Handle Realtime Subscriptions
  useEffect(() => {
    const channel = supabase.channel('chart_realtime')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'candles' }, () => {
        fetchData();
      })
      .on('postgres_changes', { event: '*', schema: 'public', table: 'smc_zones' }, () => {
        fetchData();
      })
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, timeframe]);

  // Chart setup
  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Initialize Chart
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: 'transparent' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: 'rgba(42, 46, 57, 0.2)' },
        horzLines: { color: 'rgba(42, 46, 57, 0.2)' },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
      width: chartContainerRef.current.clientWidth,
      height: 500,
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  // Update Data and Drawings
  useEffect(() => {
    if (!seriesRef.current || !chartRef.current) return;

    if (candles.length > 0) {
      seriesRef.current.setData(candles);
    }

    zones.forEach(zone => {
      const color = zone.direction === 'demand' ? '#34d399' : '#fb7185';
      const label = zone.zone_type === 'fvg' ? 'FVG' : 'OB';
      
      seriesRef.current?.createPriceLine({
        price: zone.top,
        color: color,
        lineWidth: 1,
        lineStyle: LineStyle.Solid,
        axisLabelVisible: true,
        title: `${label} Top`,
      });

      seriesRef.current?.createPriceLine({
        price: zone.bottom,
        color: color,
        lineWidth: 1,
        lineStyle: LineStyle.Solid,
        axisLabelVisible: true,
        title: `${label} Bottom`,
      });
    });

    positions.forEach(pos => {
      if (pos.entry_price) {
        seriesRef.current?.createPriceLine({
          price: pos.entry_price,
          color: '#3b82f6', // blue
          lineWidth: 2,
          lineStyle: LineStyle.Solid,
          axisLabelVisible: true,
          title: 'Entry',
        });
      }
      if (pos.stop_loss) {
        seriesRef.current?.createPriceLine({
          price: pos.stop_loss,
          color: '#ef4444', // red
          lineWidth: 2,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: 'SL',
        });
      }
      if (pos.take_profit) {
        seriesRef.current?.createPriceLine({
          price: pos.take_profit,
          color: '#10b981', // green
          lineWidth: 2,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title: 'TP',
        });
      }
    });

  }, [candles, zones, positions]);

  return (
    <div className="min-h-screen bg-[#0f172a] text-white p-4 font-sans">
      <div className="max-w-6xl mx-auto backdrop-blur-xl bg-[#0f172a]/80 border border-white/10 rounded-2xl overflow-hidden shadow-2xl">
        
        {/* Header / Controls */}
        <div className="p-4 border-b border-white/10 flex flex-wrap gap-4 items-center justify-between bg-black/20">
          <div className="flex items-center gap-2 text-xl font-bold">
            <CandlestickChart className="w-6 h-6 text-blue-400" />
            <span>Narx Grafigi</span>
          </div>
          
          <div className="flex items-center gap-4">
            <select 
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="bg-black/40 border border-white/10 rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-500 text-sm font-medium"
            >
              <option value="EURUSD">EURUSD</option>
              <option value="GBPUSD">GBPUSD</option>
              <option value="XAUUSD">XAUUSD</option>
              <option value="BTCUSDT">BTCUSDT</option>
            </select>

            <div className="flex bg-black/40 rounded-lg p-1 border border-white/10">
              {['M15', 'H1', 'H4'].map(tf => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-3 py-1 rounded-md text-xs font-bold transition-colors ${
                    timeframe === tf ? 'bg-blue-500 text-white shadow' : 'text-gray-400 hover:text-white'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Chart Area */}
        <div className="relative w-full" style={{ height: '500px' }}>
          {loading && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-[#0f172a]/50 backdrop-blur-sm">
              <div className="animate-pulse text-blue-400 font-medium bg-black/50 px-4 py-2 rounded-xl">Ma'lumotlar yuklanmoqda...</div>
            </div>
          )}
          
          {!loading && candles.length === 0 && (
            <div className="absolute inset-0 z-10 flex items-center justify-center">
              <div className="text-gray-500 bg-black/50 px-6 py-4 rounded-xl border border-white/5 shadow-xl text-sm font-medium backdrop-blur-md">
                Hali candle sinxronizatsiya qilinmagan. (Bo'sh holat)
              </div>
            </div>
          )}

          <div ref={chartContainerRef} className="w-full h-full" />
        </div>
      </div>
    </div>
  );
}

// Force Vite HMR update
