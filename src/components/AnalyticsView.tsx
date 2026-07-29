import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { supabase } from "@/integrations/supabase/client";
import { useAuth } from "@/hooks/useAuth";
import { guestMock } from "@/lib/guestMock";
import { fmtMoney, cn } from "@/lib/utils";
import type { TradeHistory } from "@/lib/types";
import { Loader2, Activity, CalendarDays, Grid3X3, AlertTriangle, ChevronLeft, ChevronRight } from "lucide-react";

type TimeFrame = "24h" | "7d" | "30d" | "all";

export function AnalyticsView() {
  const { user } = useAuth();
  const isGuest = user?.id === "guest";
  const [timeframe, setTimeframe] = useState<TimeFrame>("30d");
  const [dateOffset, setDateOffset] = useState(0);

  const { data: history, isLoading } = useQuery({
    queryKey: ["trade_history_analytics", user?.id],
    queryFn: async () => {
      if (isGuest) return guestMock.getHistory();
      const { data } = await supabase
        .from("trade_history")
        .select("*")
        .order("closed_at", { ascending: false });
      return (data ?? []) as TradeHistory[];
    },
    refetchInterval: 15000,
  });

  const referenceDate = useMemo(() => {
    const d = new Date();
    if (timeframe === "7d") d.setDate(d.getDate() + (dateOffset * 7));
    else if (timeframe === "30d") d.setMonth(d.getMonth() + dateOffset);
    else if (timeframe === "24h") d.setDate(d.getDate() + dateOffset);
    return d;
  }, [timeframe, dateOffset]);

  const filteredData = useMemo(() => {
    if (!history) return [];
    if (timeframe === "all") return history;

    if (timeframe === "30d") {
      const year = referenceDate.getFullYear();
      const month = referenceDate.getMonth();
      const start = new Date(year, month, 1).getTime();
      const end = new Date(year, month + 1, 0, 23, 59, 59).getTime();
      return history.filter(t => {
        const time = new Date(t.closed_at).getTime();
        return time >= start && time <= end;
      });
    }

    const end = referenceDate.getTime();
    const hours = timeframe === "24h" ? 24 : 168;
    const start = end - hours * 60 * 60 * 1000;

    return history.filter(t => {
      const time = new Date(t.closed_at).getTime();
      return time >= start && time <= end;
    });
  }, [history, timeframe, referenceDate]);

  const { symbolStats, overallStats } = useMemo(() => {
    const sStats: Record<string, { trades: number; wins: number; losses: number; profit: number }> = {};
    const overall = { trades: 0, wins: 0, losses: 0, profit: 0 };

    filteredData.forEach(t => {
      const p = Number(t.profit) || 0;
      const isWin = p > 0;
      const sym = t.symbol || "Unknown";

      overall.trades++;
      if (isWin) overall.wins++; else overall.losses++;
      overall.profit += p;

      if (!sStats[sym]) sStats[sym] = { trades: 0, wins: 0, losses: 0, profit: 0 };
      sStats[sym].trades++;
      if (isWin) sStats[sym].wins++; else sStats[sym].losses++;
      sStats[sym].profit += p;
    });

    return { 
      symbolStats: Object.entries(sStats).map(([sym, st]) => ({ sym, ...st })).sort((a, b) => a.profit - b.profit),
      overallStats: overall
    };
  }, [filteredData]);

  // --- CALENDAR LOGIC (1 OY) ---
  const calendarData = useMemo(() => {
    if (timeframe !== "30d") return null;
    
    // Group by YYYY-MM-DD
    const daysData: Record<string, number> = {};
    filteredData.forEach(t => {
      const dateStr = new Date(t.closed_at).toISOString().split('T')[0];
      if (!daysData[dateStr]) daysData[dateStr] = 0;
      daysData[dateStr] += Number(t.profit) || 0;
    });

    // Create a 30-day view (or current month)
    const year = referenceDate.getFullYear();
    const month = referenceDate.getMonth();
    
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const firstDay = new Date(year, month, 1).getDay();
    const startOffset = firstDay === 0 ? 6 : firstDay - 1; // 0 for Mon, 6 for Sun
    
    const cells = [];
    for (let i = 0; i < startOffset; i++) {
      cells.push(null); // Empty cells before 1st day
    }
    for (let day = 1; day <= daysInMonth; day++) {
      const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      cells.push({
        day,
        dateStr,
        profit: daysData[dateStr] !== undefined ? daysData[dateStr] : null
      });
    }

    return { cells, monthName: referenceDate.toLocaleString('uz-UZ', { month: 'long', year: 'numeric' }) };
  }, [filteredData, timeframe, referenceDate]);

  // --- HEATMAP LOGIC (7 KUN) ---
  const heatmapData = useMemo(() => {
    if (timeframe !== "7d") return null;
    
    // 7 rows (Mon-Sun), 24 cols (0-23)
    const map = Array.from({ length: 7 }, () => Array(24).fill(null));
    
    let maxAbsProfit = 0;

    filteredData.forEach(t => {
      const d = new Date(t.closed_at);
      let dayIndex = d.getDay(); 
      dayIndex = dayIndex === 0 ? 6 : dayIndex - 1; // 0=Mon, 6=Sun
      const hour = d.getHours();
      
      const profit = Number(t.profit) || 0;
      
      if (map[dayIndex][hour] === null) {
        map[dayIndex][hour] = { profit: 0, trades: 0 };
      }
      map[dayIndex][hour].profit += profit;
      map[dayIndex][hour].trades += 1;
    });

    for (let r = 0; r < 7; r++) {
      for (let c = 0; c < 24; c++) {
        if (map[r][c]) {
          maxAbsProfit = Math.max(maxAbsProfit, Math.abs(map[r][c].profit));
        }
      }
    }

    return { map, maxAbsProfit };
  }, [filteredData, timeframe]);

  const weekDaysShort = ["Du", "Se", "Ch", "Pa", "Ju", "Sh", "Ya"];

  return (
    <div className="flex flex-col gap-4 mt-6">
      <div className="flex items-center justify-between px-1">
        <h2 className="text-lg font-bold text-white flex items-center gap-2">
          <Activity size={20} className="text-pink-500" />
          Analitika va Tahlil
        </h2>
      </div>
      
      {/* Top Filter Bar */}
      <div className="flex items-center gap-1 bg-white/5 p-1 rounded-xl border border-white/10 w-full sm:w-fit overflow-x-auto no-scrollbar">
        {(["24h", "7d", "30d", "all"] as TimeFrame[]).map(tf => (
          <button
            key={tf}
            onClick={() => { setTimeframe(tf); setDateOffset(0); }}
            className={cn(
              "px-3 py-1.5 sm:px-4 sm:py-2 rounded-lg text-[11px] sm:text-xs font-bold uppercase tracking-wider transition-all flex-1 sm:flex-none text-center whitespace-nowrap",
              timeframe === tf ? "bg-blue-600 text-white shadow-lg shadow-blue-600/20" : "text-white/40 hover:text-white/80"
            )}
          >
            {tf === "24h" ? "24 Soat" : tf === "7d" ? "7 Kun" : tf === "30d" ? "1 Oy" : "Barchasi"}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="flex justify-center py-10"><Loader2 className="animate-spin text-blue-400" size={32} /></div>
      ) : filteredData.length === 0 ? (
        <div className="bg-[#10192e]/40 border border-white/5 rounded-2xl py-8 text-center text-white/40 text-xs italic">Ushbu davr uchun savdolar yo'q.</div>
      ) : (
        <>
          {/* Calendar View for 30d */}
          {timeframe === "30d" && calendarData && (
            <div className="bg-[#10192e]/40 backdrop-blur-md rounded-2xl border border-white/5 p-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 gap-2">
                <div className="flex items-center gap-3">
                  <h2 className="text-sm font-bold text-white flex items-center gap-2">
                    <CalendarDays size={18} className="text-blue-400" />
                    <span className="capitalize">{calendarData.monthName}</span>
                  </h2>
                  <div className="flex items-center bg-white/5 rounded-lg border border-white/10">
                    <button onClick={() => setDateOffset(o => o - 1)} className="p-1 hover:bg-white/10 rounded-l-lg text-white/50 hover:text-white transition-colors"><ChevronLeft size={16} /></button>
                    <div className="w-px h-4 bg-white/10" />
                    <button onClick={() => setDateOffset(o => o + 1)} disabled={dateOffset === 0} className="p-1 hover:bg-white/10 rounded-r-lg text-white/50 hover:text-white disabled:opacity-30 transition-colors"><ChevronRight size={16} /></button>
                  </div>
                </div>
                <div className="text-xs font-black text-white bg-white/10 px-3 py-1.5 rounded-full border border-white/10 flex items-center gap-2">
                  <span className="text-white/50 font-normal">Oy natijasi:</span>
                  <span className={overallStats.profit >= 0 ? "text-emerald-400" : "text-rose-400"}>
                    {overallStats.profit >= 0 ? "+" : ""}{fmtMoney(overallStats.profit)}
                  </span>
                </div>
              </div>
              
              <div className="grid grid-cols-7 gap-1 min-[360px]:gap-1.5 mb-1.5">
                {weekDaysShort.map(day => (
                  <div key={day} className="text-center text-[10px] font-bold text-white/40 uppercase py-1 bg-white/5 rounded-md">{day}</div>
                ))}
              </div>
              
              <div className="grid grid-cols-7 gap-1 min-[360px]:gap-1.5">
                {calendarData.cells.map((cell, i) => (
                  <div 
                    key={i} 
                    className={cn(
                      "aspect-square rounded-lg sm:rounded-xl flex flex-col items-center justify-center relative transition-all border",
                      cell ? "bg-[#0c1222] border-white/5 hover:border-white/20" : "opacity-0 pointer-events-none"
                    )}
                  >
                    {cell && (
                      <>
                        <span className="text-[10px] sm:text-xs font-bold text-white/70 absolute top-1 sm:top-1.5 left-1 sm:left-2">{cell.day}</span>
                        {cell.profit !== null && (
                          <span className={cn(
                            "text-[8px] sm:text-[11px] font-black tabular-nums mt-3 sm:mt-4 text-center leading-none",
                            cell.profit >= 0 ? "text-emerald-400" : "text-rose-400"
                          )}>
                            {cell.profit >= 0 ? "+" : ""}{fmtMoney(cell.profit).replace('$', '')}
                          </span>
                        )}
                        {/* Glow effect based on profit */}
                        {cell.profit !== null && (
                          <div className={cn(
                            "absolute inset-0 rounded-lg sm:rounded-xl opacity-20 blur-[10px] pointer-events-none",
                            cell.profit >= 0 ? "bg-emerald-500" : "bg-rose-500"
                          )} />
                        )}
                      </>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Heatmap View for 7d */}
          {timeframe === "7d" && heatmapData && (
            <div className="bg-[#10192e]/40 backdrop-blur-md rounded-2xl border border-white/5 p-4 animate-in fade-in slide-in-from-bottom-2 duration-500 overflow-hidden">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 gap-2">
                <div className="flex items-center gap-3">
                  <h2 className="text-sm font-bold text-white flex items-center gap-2">
                    <Grid3X3 size={18} className="text-orange-400" />
                    Haftalik 24-Soatlik Xarita
                  </h2>
                  <div className="flex items-center bg-white/5 rounded-lg border border-white/10">
                    <button onClick={() => setDateOffset(o => o - 1)} className="p-1 hover:bg-white/10 rounded-l-lg text-white/50 hover:text-white transition-colors"><ChevronLeft size={16} /></button>
                    <div className="w-px h-4 bg-white/10" />
                    <button onClick={() => setDateOffset(o => o + 1)} disabled={dateOffset === 0} className="p-1 hover:bg-white/10 rounded-r-lg text-white/50 hover:text-white disabled:opacity-30 transition-colors"><ChevronRight size={16} /></button>
                  </div>
                </div>
                <div className="text-xs font-black text-white bg-white/10 px-3 py-1.5 rounded-full border border-white/10 flex items-center gap-2">
                  <span className="text-white/50 font-normal">Hafta natijasi:</span>
                  <span className={overallStats.profit >= 0 ? "text-emerald-400" : "text-rose-400"}>
                    {overallStats.profit >= 0 ? "+" : ""}{fmtMoney(overallStats.profit)}
                  </span>
                </div>
              </div>
              <p className="text-[10px] text-white/50 mb-4 leading-relaxed">
                Ushbu xarita oxirgi 7 kundagi har bir soatni tahlil qiladi. Qizil kataklar zarar ko'p bo'lgan soatlarni, yashil kataklar esa foydali soatlarni bildiradi. Katak qoramtir bo'lsa, u soatda savdo qilinmagan.
              </p>
              
              <div className="w-full pb-2">
                <div className="w-full">
                  {/* Hours Header */}
                  <div className="grid grid-cols-[auto_repeat(24,1fr)] gap-0.5 sm:gap-1 mb-1 items-end">
                    <div className="w-6 sm:w-8" />
                    {Array.from({length: 24}).map((_, h) => (
                      <div key={h} className="text-center text-[6px] sm:text-[8px] text-white/30 font-bold uppercase truncate">
                        <span className="hidden sm:inline">{h}</span>
                        <span className="inline sm:hidden">{h % 2 === 0 ? h : ''}</span>
                      </div>
                    ))}
                  </div>
                  
                  {/* Grid */}
                  <div className="flex flex-col gap-0.5 sm:gap-1">
                    {weekDaysShort.map((day, r) => (
                      <div key={day} className="grid grid-cols-[auto_repeat(24,1fr)] gap-0.5 sm:gap-1 items-center h-6 sm:h-8">
                        <div className="w-6 sm:w-8 text-[8px] sm:text-[9px] font-bold text-white/50">{day}</div>
                        {Array.from({length: 24}).map((_, c) => {
                          const cell = heatmapData.map[r][c];
                          let bgClass = "bg-black/30 border border-white/5";
                          
                          if (cell) {
                            const intensity = heatmapData.maxAbsProfit > 0 ? Math.abs(cell.profit) / heatmapData.maxAbsProfit : 0;
                            
                            if (cell.profit > 0) {
                              if (intensity > 0.8) bgClass = "bg-emerald-400 border border-emerald-400/50";
                              else if (intensity > 0.6) bgClass = "bg-emerald-500 border border-emerald-500/50";
                              else if (intensity > 0.4) bgClass = "bg-emerald-600 border border-emerald-600/50";
                              else if (intensity > 0.2) bgClass = "bg-emerald-700 border border-emerald-700/50";
                              else bgClass = "bg-emerald-800 border border-emerald-800/50";
                            } else if (cell.profit < 0) {
                              if (intensity > 0.8) bgClass = "bg-rose-400 border border-rose-400/50";
                              else if (intensity > 0.6) bgClass = "bg-rose-500 border border-rose-500/50";
                              else if (intensity > 0.4) bgClass = "bg-rose-600 border border-rose-600/50";
                              else if (intensity > 0.2) bgClass = "bg-rose-700 border border-rose-700/50";
                              else bgClass = "bg-rose-800 border border-rose-800/50";
                            } else {
                              bgClass = "bg-white/10 border border-white/5";
                            }
                          }

                          return (
                            <div 
                              key={`${r}-${c}`} 
                              className="flex-1 h-full relative group cursor-crosshair rounded-sm"
                            >
                              <div className={cn("w-full h-full rounded-sm transition-all", bgClass)} />
                              
                              {/* Tooltip */}
                              {cell && (
                                <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 bg-[#1a1a24] p-2 rounded-lg border border-white/10 opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-20 w-max text-center shadow-xl">
                                  <div className="text-[10px] font-bold text-white">{day}, Soat {c}:00</div>
                                  <div className="text-[9px] text-white/50">{cell.trades} ta savdo</div>
                                  <div className={cn("text-[11px] font-black mt-0.5", cell.profit >= 0 ? "text-emerald-400" : "text-rose-400")}>
                                    P/L: {fmtMoney(cell.profit)}
                                  </div>
                                </div>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Fallback to Symbol Analysis if not Calendar or Heatmap */}
          {(timeframe === "24h" || timeframe === "all") && (
            <div className="bg-[#10192e]/40 backdrop-blur-md rounded-2xl border border-white/5 p-4 animate-in fade-in slide-in-from-bottom-2 duration-500">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-4 gap-2">
                <h2 className="text-sm font-bold text-white flex items-center gap-2">
                  <Activity size={18} className="text-amber-400" />
                  Juftliklar Bo'yicha Tahlil
                </h2>
                <div className="text-xs font-black text-white bg-white/10 px-3 py-1.5 rounded-full border border-white/10 flex items-center gap-2">
                  <span className="text-white/50 font-normal">Umumiy:</span>
                  <span className={overallStats.profit >= 0 ? "text-emerald-400" : "text-rose-400"}>
                    {overallStats.profit >= 0 ? "+" : ""}{fmtMoney(overallStats.profit)}
                  </span>
                </div>
              </div>

              <div className="space-y-3 mt-4">
                {symbolStats.map(s => {
                  const wr = s.trades > 0 ? Math.round((s.wins / s.trades) * 100) : 0;
                  const isWorst = s.profit < 0;
                  return (
                    <div key={s.sym} className={cn("rounded-xl p-3 flex flex-col gap-2 border transition-all", isWorst ? "bg-rose-500/10 border-rose-500/20" : "bg-black/30 border-white/5")}>
                      <div className="flex justify-between items-center">
                        <div className="flex items-center gap-2">
                          <span className={cn("text-sm font-bold", isWorst ? "text-rose-400" : "text-white")}>{s.sym}</span>
                          {isWorst && <AlertTriangle size={12} className="text-rose-400 animate-pulse" />}
                        </div>
                        <span className={cn("text-sm font-black tabular-nums", s.profit >= 0 ? "text-emerald-400" : "text-rose-400")}>
                          {s.profit >= 0 ? "+" : ""}{fmtMoney(s.profit)}
                        </span>
                      </div>
                      <div className="flex justify-between items-end">
                        <div className="flex gap-3 text-[10px] text-white/50 font-medium">
                          <span>{s.trades} savdo</span>
                          <span className="text-rose-400/80">-{s.losses} L</span>
                        </div>
                        <div className="text-[10px] font-bold text-white/60">
                          Win Rate: <span className={wr >= 50 ? "text-emerald-400" : "text-rose-400"}>{wr}%</span>
                        </div>
                      </div>
                      <div className="w-full h-1.5 bg-black/40 rounded-full overflow-hidden flex">
                        <div className="h-full bg-emerald-500" style={{ width: `${wr}%` }} />
                        <div className="h-full bg-rose-500" style={{ width: `${100 - wr}%` }} />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
