import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { set, get } from "idb-keyval";
import { CloudOff, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";

const SYMBOLS_TO_SYNC = ["EURUSD", "GBPUSD", "AUDUSD", "XAUUSD", "BTCUSD"];
const TIMEFRAMES_TO_SYNC = ["M15", "H1"];

export function OfflineSyncManager() {
  const [syncState, setSyncState] = useState<"idle" | "syncing" | "done" | "offline">("idle");
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    let isMounted = true;
    
    const checkOnline = () => {
       if (!navigator.onLine) {
          setSyncState("offline");
       } else {
          setSyncState("idle");
       }
    };
    
    window.addEventListener("online", checkOnline);
    window.addEventListener("offline", checkOnline);
    checkOnline();

    return () => {
       isMounted = false;
       window.removeEventListener("online", checkOnline);
       window.removeEventListener("offline", checkOnline);
    };
  }, []);

  useEffect(() => {
    if (syncState !== "idle") return;

    const performSync = async () => {
      setSyncState("syncing");
      let completed = 0;
      const totalTasks = SYMBOLS_TO_SYNC.length * TIMEFRAMES_TO_SYNC.length;

      for (const symbol of SYMBOLS_TO_SYNC) {
        for (const tf of TIMEFRAMES_TO_SYNC) {
           if (!navigator.onLine) {
              setSyncState("offline");
              return;
           }

           try {
              const cacheKey = `chartData_${symbol}_${tf}`;
              
              const [
                { data: candles },
                { data: smc },
                { data: harmonic },
                { data: wyckoff },
                { data: srVolume },
                { data: autoPattern }
              ] = await Promise.all([
                supabase.from("candles").select("*").eq("symbol", symbol).eq("timeframe", tf).order("time", { ascending: false }).limit(300),
                supabase.from("smc_zones").select("*").eq("symbol", symbol).eq("timeframe", tf).eq("status", "fresh"),
                (supabase as any).from("harmonic_patterns").select("*").eq("symbol", symbol).eq("timeframe", tf).eq("status", "fresh"),
                (supabase as any).from("wyckoff_events").select("*").eq("symbol", symbol).eq("timeframe", tf).eq("status", "fresh"),
                (supabase as any).from("sr_volume_zones").select("*").eq("symbol", symbol).eq("timeframe", tf).eq("status", "fresh"),
                (supabase as any).from("auto_patterns").select("*").eq("symbol", symbol).eq("timeframe", tf).eq("status", "fresh")
              ]);

              if (candles && candles.length > 0) {
                 const formattedCandles = [...candles].reverse().map((c: any) => ({
                    time: Math.floor(new Date(c.time).getTime() / 1000),
                    open: Number(c.open),
                    high: Number(c.high),
                    low: Number(c.low),
                    close: Number(c.close),
                    volume: c.volume ? Number(c.volume) : 0,
                  }));

                  await set(cacheKey, {
                    candles: formattedCandles,
                    smc: smc || [],
                    harmonic: harmonic || [],
                    wyckoff: wyckoff || [],
                    srVolume: srVolume || [],
                    autoPattern: autoPattern || []
                  }).catch(() => null);
              }
           } catch (e) {
              // Ignore individual sync errors
           }
           
           completed++;
           setProgress(Math.round((completed / totalTasks) * 100));
           
           // small delay to prevent rate limit
           await new Promise(r => setTimeout(r, 500));
        }
      }
      
      if (navigator.onLine) {
         setSyncState("done");
         setTimeout(() => setSyncState("idle"), 5000); // hide after 5s
      }
    };

    // Delay sync by 10 seconds to not block initial UI load
    const timer = setTimeout(() => {
       performSync();
    }, 10000);

    return () => clearTimeout(timer);
  }, [syncState]);

  if (syncState === "idle" || syncState === "done") return null;

  return (
    <div className="fixed bottom-20 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 bg-[#121829] border border-white/10 px-3 py-1.5 rounded-full shadow-2xl animate-in slide-in-from-bottom-5">
       {syncState === "offline" ? (
         <>
           <CloudOff size={14} className="text-red-400" />
           <span className="text-[10px] font-bold text-white/70">Oflayn rejim</span>
         </>
       ) : (
         <>
           <RefreshCw size={14} className="text-blue-400 animate-pulse" />
           <span className="text-[10px] font-bold text-white/70">Oflayn sinxronizatsiya: {progress}%</span>
         </>
       )}
    </div>
  );
}
