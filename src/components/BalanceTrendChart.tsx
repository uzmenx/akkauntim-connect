import React, { useMemo } from 'react';
import { TradeHistory } from '@/lib/types';
import { fmtMoney } from '@/lib/utils';

interface BalanceTrendChartProps {
  history: TradeHistory[];
  currentBalance: number;
}

export function BalanceTrendChart({ history, currentBalance }: BalanceTrendChartProps) {
  const { points, startBalance, endBalance, startTime, endTime, path, fillPath } = useMemo(() => {
    if (!history || history.length === 0) {
      return {
        points: [],
        startBalance: currentBalance,
        endBalance: currentBalance,
        startTime: new Date(),
        endTime: new Date(),
        path: "",
        fillPath: ""
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
    
    const minTime = startTime.getTime();
    const maxTime = endTime.getTime();
    const timeRange = Math.max(maxTime - minTime, 1);
    
    const minBalance = Math.min(...dataPoints.map(p => p.balance));
    const maxBalance = Math.max(...dataPoints.map(p => p.balance));
    
    // Add some padding to Y axis
    const yPad = (maxBalance - minBalance) * 0.1 || 10;
    const minY = minBalance - yPad;
    const maxY = maxBalance + yPad;
    const yRange = Math.max(maxY - minY, 1);

    const getX = (t: number) => ((t - minTime) / timeRange) * w;
    const getY = (b: number) => h - ((b - minY) / yRange) * h;

    const pathData = dataPoints.map((p, i) => {
      const cmd = i === 0 ? "M" : "L";
      return `${cmd} ${getX(p.time).toFixed(2)},${getY(p.balance).toFixed(2)}`;
    }).join(" ");

    const fillData = `${pathData} L ${w},${h} L 0,${h} Z`;

    return {
      points: dataPoints,
      startBalance,
      endBalance,
      startTime,
      endTime,
      path: pathData,
      fillPath: fillData
    };

  }, [history, currentBalance]);

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
    <div className="w-full h-full flex flex-col justify-center px-3 sm:px-4 bg-gradient-to-br from-[#10192e]/90 to-[#041a5a]/20 rounded-[24px] border border-white/10 relative overflow-hidden group shadow-lg">
      {/* Background SVG Grid / Glow */}
      <div className="absolute inset-0 pointer-events-none opacity-20">
         <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-3xl"></div>
      </div>
      
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
          <path 
            d={path} 
            fill="none" 
            stroke={isProfit ? "#34d399" : "#fb7185"} 
            strokeWidth="1.5" 
            strokeLinejoin="round" 
            strokeLinecap="round"
            filter="url(#glow)"
            className="transition-all duration-1000 ease-in-out"
          />
        </svg>
      </div>

      {/* Stats overlay */}
      <div className="relative z-10 flex justify-between items-end h-full py-2">
        <div className="flex flex-col text-left">
          <span className="text-[9px] text-white/50 font-medium tracking-wide uppercase">{formatShortTime(startTime)}</span>
          <span className="text-xs font-bold text-white/80 tabular-nums">{fmtMoney(startBalance)}</span>
        </div>
        <div className="flex flex-col text-right">
          <span className="text-[9px] text-white/50 font-medium tracking-wide uppercase">{formatShortTime(endTime)}</span>
          <span className={`text-sm font-black tabular-nums drop-shadow-sm ${isProfit ? 'text-emerald-400' : 'text-rose-400'}`}>
            {fmtMoney(endBalance)}
          </span>
        </div>
      </div>
    </div>
  );
}
