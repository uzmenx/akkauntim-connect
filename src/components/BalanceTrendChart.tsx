import React, { useMemo } from 'react';
import { TradeHistory } from '@/lib/types';
import { fmtMoney } from '@/lib/utils';

interface BalanceTrendChartProps {
  history: TradeHistory[];
  currentBalance: number;
}

export function BalanceTrendChart({ history, currentBalance }: BalanceTrendChartProps) {
  const { points, startBalance, endBalance, startTime, endTime, path, fillPath, segments = [] } = useMemo(() => {
    if (!history || history.length === 0) {
      return {
        points: [],
        startBalance: currentBalance,
        endBalance: currentBalance,
        startTime: new Date(),
        endTime: new Date(),
        path: "",
        fillPath: "",
        segments: []
      };
    }

    // Sort ascending by closed_at to trace history forward
    const sorted = [...history].sort((a, b) => new Date(a.closed_at).getTime() - new Date(b.closed_at).getTime());
    
    // Calculate total profit from these trades
    const totalProfit = sorted.reduce((sum, t) => sum + Number(t.profit ?? 0), 0);
    
    // Starting balance before the earliest trade in this window closed
    const startBalance = currentBalance - totalProfit;
    
    // Build points: [ { time: number, balance: number } ]
    // Point 0: The opening time of the first trade (or if invalid, slightly before its close)
    const firstTrade = sorted[0];
    const startTimeDate = firstTrade.opened_at ? new Date(firstTrade.opened_at) : new Date(new Date(firstTrade.closed_at).getTime() - 60000 * 60);
    
    const dataPoints = [];
    dataPoints.push({
      time: startTimeDate.getTime(),
      balance: startBalance
    });

    let runningBalance = startBalance;
    for (const trade of sorted) {
      runningBalance += Number(trade.profit ?? 0);
      dataPoints.push({
        time: new Date(trade.closed_at).getTime(),
        balance: runningBalance
      });
    }

    const endBalance = runningBalance; // Should equal currentBalance
    const startTime = startTimeDate;
    const endTime = new Date(sorted[sorted.length - 1].closed_at);

    // SVG coordinates mapping
    // We want to map points to 0-100% width, 0-100% height (or 0-w, 0-h viewBox)
    const w = 300;
    const h = 50;
    
    const minBalance = Math.min(...dataPoints.map(p => p.balance));
    const maxBalance = Math.max(...dataPoints.map(p => p.balance));
    
    // Add some padding to Y axis
    const yPad = (maxBalance - minBalance) * 0.15 || 10;
    const minY = minBalance - yPad;
    const maxY = maxBalance + yPad;
    const yRange = Math.max(maxY - minY, 1);

    const getX = (index: number) => (index / (dataPoints.length - 1)) * w;
    const getY = (b: number) => h - ((b - minY) / yRange) * h;

    // Build a smooth wavy bezier curve path
    let pathData = `M ${getX(0).toFixed(2)},${getY(dataPoints[0].balance).toFixed(2)}`;
    for (let i = 0; i < dataPoints.length - 1; i++) {
      const currentX = getX(i);
      const currentY = getY(dataPoints[i].balance);
      const nextX = getX(i + 1);
      const nextY = getY(dataPoints[i + 1].balance);
      
      const cp1X = currentX + (nextX - currentX) / 2;
      const cp1Y = currentY;
      const cp2X = currentX + (nextX - currentX) / 2;
      const cp2Y = nextY;
      
      pathData += ` C ${cp1X.toFixed(2)},${cp1Y.toFixed(2)} ${cp2X.toFixed(2)},${cp2Y.toFixed(2)} ${nextX.toFixed(2)},${nextY.toFixed(2)}`;
    }

    const segments = [];
    for (let i = 0; i < dataPoints.length - 1; i++) {
      const currentX = getX(i);
      const currentY = getY(dataPoints[i].balance);
      const nextX = getX(i + 1);
      const nextY = getY(dataPoints[i + 1].balance);
      
      const cp1X = currentX + (nextX - currentX) / 2;
      const cp1Y = currentY;
      const cp2X = currentX + (nextX - currentX) / 2;
      const cp2Y = nextY;
      
      const segmentPath = `M ${currentX.toFixed(2)},${currentY.toFixed(2)} C ${cp1X.toFixed(2)},${cp1Y.toFixed(2)} ${cp2X.toFixed(2)},${cp2Y.toFixed(2)} ${nextX.toFixed(2)},${nextY.toFixed(2)}`;
      const isSegmentProfit = dataPoints[i + 1].balance >= dataPoints[i].balance;
      segments.push({
        path: segmentPath,
        color: isSegmentProfit ? "#34d399" : "#fb7185"
      });
    }

    const fillData = `${pathData} L ${w},${h} L 0,${h} Z`;

    return {
      points: dataPoints,
      startBalance,
      endBalance,
      startTime,
      endTime,
      path: pathData,
      fillPath: fillData,
      segments
    };

  }, [history, currentBalance]);

  const [hoveredPoint, setHoveredPoint] = React.useState<{ time: number; balance: number } | null>(null);
  const [hoveredX, setHoveredX] = React.useState<number | null>(null);
  const [hoveredY, setHoveredY] = React.useState<number | null>(null);
  const containerRef = React.useRef<HTMLDivElement>(null);

  const handleMove = (clientX: number) => {
    if (!containerRef.current || points.length === 0) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const width = rect.width;
    const pct = Math.max(0, Math.min(1, x / width));
    const closestIdx = Math.round(pct * (points.length - 1));
    const point = points[closestIdx];
    
    if (point) {
      setHoveredPoint(point);
      const svgX = (closestIdx / (points.length - 1)) * 300;
      setHoveredX(svgX);

      const minBalance = Math.min(...points.map(p => p.balance));
      const maxBalance = Math.max(...points.map(p => p.balance));
      const yPad = (maxBalance - minBalance) * 0.15 || 10;
      const minY = minBalance - yPad;
      const maxY = maxBalance + yPad;
      const yRange = Math.max(maxY - minY, 1);
      const svgY = 50 - ((point.balance - minY) / yRange) * 50;
      setHoveredY(svgY);
    }
  };

  const onMouseMove = (e: React.MouseEvent) => {
    handleMove(e.clientX);
  };

  const onTouchMove = (e: React.TouchEvent) => {
    if (e.touches[0]) {
      handleMove(e.touches[0].clientX);
    }
  };

  const onMouseLeave = () => {
    setHoveredPoint(null);
    setHoveredX(null);
    setHoveredY(null);
  };

  if (points.length === 0) {
    return (
      <div className="w-full h-full flex flex-col justify-center px-4 bg-gradient-to-br from-[#10192e]/80 to-transparent rounded-[20px] border border-white/5 relative overflow-hidden group shadow-md shadow-black/20">
        <span className="text-[10px] text-white/40">No trades to chart</span>
      </div>
    );
  }

  const formatShortTime = (d: Date) => {
    return d.toLocaleDateString(undefined, { day: '2-digit', month: '2-digit' }) + ' ' + d.toLocaleTimeString(undefined, { hour: '2-digit', minute:'2-digit', hour12: false });
  };

  const isProfit = endBalance >= startBalance;

  return (
    <div 
      ref={containerRef}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
      onTouchStart={onTouchMove}
      onTouchMove={onTouchMove}
      onTouchEnd={onMouseLeave}
      className="w-full h-full flex flex-col justify-center px-3 sm:px-4 bg-gradient-to-br from-[#10192e]/90 to-[#041a5a]/20 rounded-[24px] border border-white/10 relative overflow-hidden group shadow-lg cursor-crosshair select-none"
    >
      {/* Background SVG Grid / Glow */}
      <div className="absolute inset-0 pointer-events-none opacity-20">
         <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-3xl"></div>
      </div>
      
      {/* Tooltip Overlay */}
      {hoveredPoint && (
        <div className="absolute top-1.5 left-1/2 -translate-x-1/2 z-20 bg-black/85 backdrop-blur-md px-2.5 py-0.5 rounded-full border border-white/10 flex items-center gap-2 pointer-events-none animate-in fade-in zoom-in-95 duration-150">
          <span className="text-[8px] text-white/50 font-bold tracking-tight">
            {formatShortTime(new Date(hoveredPoint.time))}
          </span>
          <div className="w-[1px] h-2 bg-white/20" />
          <span className={`text-[9px] font-black tabular-nums ${hoveredPoint.balance >= startBalance ? 'text-emerald-400' : 'text-rose-400'}`}>
            {fmtMoney(hoveredPoint.balance)}
          </span>
        </div>
      )}
      
      {/* The Chart */}
      <div className="absolute inset-0 pt-4 pb-2 px-0 w-full h-full pointer-events-none opacity-80 flex items-center">
        <svg viewBox="0 0 300 50" preserveAspectRatio="none" className="w-full h-full overflow-visible drop-shadow-md">
          <defs>
            <linearGradient id="trendGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={isProfit ? "#34d399" : "#fb7185"} stopOpacity="0.3"/>
              <stop offset="100%" stopColor={isProfit ? "#34d399" : "#fb7185"} stopOpacity="0.0"/>
            </linearGradient>
            <filter id="glow">
              <feGaussianBlur stdDeviation="1.5" result="coloredBlur"/>
              <feMerge>
                <feMergeNode in="coloredBlur"/>
                <feMergeNode in="SourceGraphic"/>
              </feMerge>
            </filter>
          </defs>
          <path 
            d={fillPath} 
            fill="url(#trendGradient)" 
            className="transition-all duration-1000 ease-in-out"
          />
          {segments.map((seg, idx) => (
            <path 
              key={idx}
              d={seg.path} 
              fill="none" 
              stroke={seg.color} 
              strokeWidth="1.5" 
              strokeLinejoin="round" 
              strokeLinecap="round"
              filter="url(#glow)"
            />
          ))}
          
          {/* Interactive guideline and hover dot */}
          {hoveredX !== null && (
            <>
              <line 
                x1={hoveredX} 
                y1={0} 
                x2={hoveredX} 
                y2={50} 
                stroke="rgba(255,255,255,0.2)" 
                strokeWidth="0.8" 
                strokeDasharray="2 2"
              />
              <circle 
                cx={hoveredX} 
                cy={hoveredY !== null ? hoveredY : 25} 
                r="3" 
                fill="#ffffff" 
                stroke={hoveredPoint && hoveredPoint.balance >= startBalance ? "#34d399" : "#fb7185"} 
                strokeWidth="1.5" 
                filter="url(#glow)"
              />
            </>
          )}
        </svg>
      </div>
    </div>
  );
}
