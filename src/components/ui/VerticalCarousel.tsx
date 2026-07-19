import { useState, useRef, useEffect } from "react";
import { fmtMoney, fmtNum, timeAgo } from "@/lib/utils";
import type { Position } from "@/lib/types";

export function VerticalCarousel({ items }: { items: Position[] }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);

  // Allow scrolling to update the current index
  useEffect(() => {
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault(); // Prevent default vertical scrolling when hovering over this
      
      setCurrentIndex((prev) => {
        // Adjust sensitivity here
        let next = prev + (e.deltaY * 0.005);
        // Clamp to 0 .. length - 1
        return Math.max(0, Math.min(next, items.length - 1));
      });
    };

    const node = containerRef.current;
    if (node) {
      node.addEventListener("wheel", handleWheel, { passive: false });
    }
    return () => {
      if (node) {
        node.removeEventListener("wheel", handleWheel);
      }
    };
  }, [items.length]);

  // Touch handling
  const touchStartY = useRef(0);
  const touchStartIdx = useRef(0);

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartY.current = e.touches[0].clientY;
    touchStartIdx.current = currentIndex;
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    // If we want to prevent body scrolling while swiping here
    // But e.preventDefault() is not allowed in passive listeners without ref attaching.
    // So we just handle state update.
    const touchY = e.touches[0].clientY;
    const deltaY = touchStartY.current - touchY;
    
    let next = touchStartIdx.current + (deltaY * 0.015);
    setCurrentIndex(Math.max(0, Math.min(next, items.length - 1)));
  };

  if (!items || items.length === 0) return null;

  // 90px is h-[90px]
  const ITEM_HEIGHT = 100;

  return (
    <div 
      ref={containerRef}
      className="relative w-full flex-1 h-full flex items-center justify-center touch-none"
      style={{ 
        perspective: "1000px",
        maskImage: "linear-gradient(to bottom, transparent 0%, black 15%, black 85%, transparent 100%)",
        WebkitMaskImage: "linear-gradient(to bottom, transparent 0%, black 15%, black 85%, transparent 100%)"
      }}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
    >
      {items.map((p, i) => {
        const offset = i - currentIndex;
        const absOffset = Math.abs(offset);
        
        // Hide items that are too far away to improve performance
        if (absOffset > 4) return null;

        // 3 ta karta (markaziy + 1 ta tepa + 1 ta past) bir xil va katta bo'ladi.
        // Qolganlari (absOffset > 1) 3D karusel kabi orqaga ketib kichrayadi.
        const isFlat = absOffset <= 1;
        const excess = Math.max(0, absOffset - 1); // 1 dan oshgan qismi
        
        const translateY = isFlat 
          ? offset * 100 
          : Math.sign(offset) * (100 + excess * 80); // 3D bo'lganlar bir-biriga yaqinroq turadi
          
        const translateZ = -excess * 60; 
        const rotateX = -Math.sign(offset) * excess * 15; 
        const scale = Math.max(0.8, 1 - excess * 0.08); 
        
        // 3 tadan uzoqlashgan sari sekin yo'qoladi (absOffset > 3 dan keyin)
        const opacity = Math.max(0, 1 - Math.max(0, absOffset - 3) * 0.5); 
        const zIndex = 100 - Math.round(absOffset * 10);
        
        const isActive = absOffset < 0.5;

        return (
          <div 
            key={p.id} 
            className="absolute w-full px-2 cursor-pointer transition-transform duration-200 ease-out"
            style={{
              transform: `translateY(${translateY}px) translateZ(${translateZ}px) rotateX(${rotateX}deg) scale(${scale})`,
              opacity,
              zIndex,
              willChange: 'transform, opacity'
            }}
            onClick={() => {
              // Optionally snap to clicked item
              setCurrentIndex(i);
            }}
          >
            <div className={`h-[90px] w-full rounded-2xl bg-[#10192e]/80 backdrop-blur-md flex items-center px-5 transition-all duration-300 ${isActive ? 'border-2 border-brand/50 shadow-[0_0_20px_rgba(100,150,255,0.15)]' : 'border border-white/5 shadow-2xl'}`}>
              <div className={`w-12 h-12 text-lg rounded-xl flex items-center justify-center text-white font-bold mr-4 shadow-md ${p.side === 'BUY' ? 'bg-emerald-500 shadow-emerald-500/20' : 'bg-rose-500 shadow-rose-500/20'}`}>
                {p.side === 'BUY' ? 'B' : 'S'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-base font-black text-white truncate">{p.symbol}</p>
                <p className="text-xs font-medium text-white/50 truncate">{p.volume} lot at {fmtNum(p.open_price, 5)}</p>
              </div>
              <div className="text-right shrink-0">
                <p className={`text-base font-bold ${Number(p.profit) >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                  {Number(p.profit) >= 0 ? "+" : ""}{fmtMoney(Number(p.profit))}
                </p>
                <p className="text-xs font-medium text-white/40">{timeAgo(p.opened_at)}</p>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
