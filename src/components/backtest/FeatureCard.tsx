import { Star } from "lucide-react";

export function FeatureCard() {
  return (
    <div className="w-full bg-[#0a0a0f] border border-white/10 rounded-xl flex items-center p-4 shadow-lg">
      {/* Left side: Feature Name */}
      <div className="flex-shrink-0 w-[35%] font-bold text-white text-[15px]">
        Backtest tizimi
      </div>
      
      {/* Middle: Stars */}
      <div className="flex-shrink-0 flex items-center justify-center w-[20%] border-l border-r border-white/10 px-2">
        <div className="flex items-center gap-1.5">
          <Star className="w-4 h-4 fill-[#eab308] text-[#eab308]" />
          <Star className="w-4 h-4 fill-[#eab308] text-[#eab308]" />
          <Star className="w-4 h-4 fill-[#eab308] text-[#eab308]" />
        </div>
      </div>
      
      {/* Right side: Description */}
      <div className="flex-grow pl-4 text-[13px] text-white/70 font-medium">
        Strategiyalarni tarixiy ma'lumotlarda sinash imkoniyati
      </div>
    </div>
  );
}
