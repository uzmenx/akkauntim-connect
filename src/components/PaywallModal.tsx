import { useState } from "react";
import { Check, X, Shield, Globe, Zap, Play, Send, Instagram, Sparkles, Star, Crown } from "lucide-react";

interface PaywallModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function PaywallModal({ isOpen, onClose }: PaywallModalProps) {
  const [showContact, setShowContact] = useState(false);
  const [isLifetime, setIsLifetime] = useState(false);

  if (!isOpen) return null;

  const plans = [
    {
      name: "Low",
      priceMonthly: "500",
      priceLifetime: "7.499",
      icon: <Star className="w-3.5 h-3.5 text-blue-400" />,
      color: "from-blue-500 to-cyan-500",
      shadow: "shadow-blue-500/10",
      description: "Aqlli va tezkor neyron tarmoqlar bilan dastlabki professional qadamlar",
      features: [
        "AI Engine: Kimi K3 & Claude 3.5",
        "Timeframe: H1, H4",
        "Kunlik 95%+ aniqlik",
        "Dinamik Stop-Loss",
        "24/7 Avtomatlashtirilgan"
      ],
      recommended: false
    },
    {
      name: "Pro",
      priceMonthly: "700",
      priceLifetime: "9.999",
      icon: <Zap className="w-3.5 h-3.5 text-amber-400" />,
      color: "from-amber-500 to-orange-500",
      shadow: "shadow-amber-500/20",
      description: "Eng yuqori darajadagi institutsional AI quvvati va cheksiz tahlillar",
      features: [
        "AI Engine: Fable 5 & GPT-5",
        "Barcha Timeframelar (M1-W1)",
        "Cheklanmagan VIP signallar",
        "Hedge-Fond risk nazorati",
        "Millisekundlik prioritet"
      ],
      recommended: true
    }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-2 bg-black/85 backdrop-blur-md">
      <div className="relative w-full max-w-[395px] my-auto bg-[#070c1e] border border-white/10 rounded-[28px] p-4 shadow-[0_32px_64px_-16px_rgba(0,0,0,0.8)] backdrop-blur-3xl animate-in zoom-in-95 duration-200">
        
        {/* Close Button */}
        <button 
          onClick={onClose}
          className="absolute top-3 right-3 w-8 h-8 flex items-center justify-center rounded-full bg-[#0a122c]/80 hover:bg-white/10 text-white/50 hover:text-white transition-all border border-white/10 active:scale-90 z-50 cursor-pointer shadow-2xl"
          aria-label="Close"
        >
          <X size={15} strokeWidth={2.5} />
        </button>

        {/* Header */}
        <div className="text-center mt-1 mb-3 space-y-0.5">
          <h2 className="text-lg font-black text-white tracking-tight">
            Ta'riflar va Obuna
          </h2>
          <p className="text-[10px] text-white/60 max-w-[280px] mx-auto leading-tight">
            Premium ta'rifni tanlang va bozorda ustunlikka ega bo'ling.
          </p>
        </div>

        {/* Switcher */}
        <div className="flex justify-center mb-3">
          <div className="bg-[#0b1229]/80 border border-white/10 rounded-full p-0.5 flex items-center gap-0.5 shadow-lg shadow-black/40">
            <button
              onClick={() => setIsLifetime(false)}
              className={`px-3 py-1 text-[8.5px] font-bold rounded-full transition-all duration-300 cursor-pointer ${
                !isLifetime
                  ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md border border-white/5"
                  : "text-white/60 hover:text-white"
              }`}
            >
              Oylik obuna
            </button>
            <button
              onClick={() => setIsLifetime(true)}
              className={`px-3 py-1 text-[8.5px] font-bold rounded-full transition-all duration-300 flex items-center gap-1 cursor-pointer ${
                isLifetime
                  ? "bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-md border border-white/5"
                  : "text-white/60 hover:text-white"
              }`}
            >
              <Crown size={9} />
              2 Yillik (Sotib olish)
            </button>
          </div>
        </div>

        {/* 2-Column Cards Grid */}
        <div className="grid grid-cols-2 gap-2">
          {plans.map((plan) => (
            <div 
              key={plan.name}
              className={`relative rounded-2xl p-3 border transition-all duration-300 flex flex-col justify-between ${
                plan.recommended 
                  ? "bg-[#0d1b3e]/90 border-amber-500/50 shadow-xl " + plan.shadow
                  : "bg-[#0f172a]/80 border-white/10"
              }`}
            >
              {plan.recommended && (
                <div className="absolute -top-2 left-1/2 -translate-x-1/2 px-1.5 py-0.5 bg-gradient-to-r from-amber-500 to-orange-500 rounded-full flex items-center gap-0.5 border border-white/20 z-10 scale-90">
                  <Sparkles size={7} className="text-white" />
                  <span className="text-[6px] font-bold text-white uppercase tracking-wider">Tavsiya</span>
                </div>
              )}

              <div>
                <div className="flex justify-between items-center gap-1 mb-1.5">
                  <div className="flex items-center gap-1">
                    <div className={`p-1 rounded-lg bg-gradient-to-br ${plan.color} bg-opacity-10 border border-white/10 shrink-0`}>
                      {plan.icon}
                    </div>
                    <h3 className="text-[11px] font-bold text-white tracking-tight">{plan.name}</h3>
                  </div>
                  <div className="text-right flex items-baseline gap-0.5">
                    <span className="text-[8px] font-bold text-white/70">$</span>
                    <span className="text-sm font-black tabular-nums tracking-tighter text-white">
                      {isLifetime ? plan.priceLifetime : plan.priceMonthly}
                    </span>
                    <span className="text-[7px] text-white/40 uppercase font-semibold ml-0.5">
                      {isLifetime ? "/2y" : "/oy"}
                    </span>
                  </div>
                </div>
                
                <p className="text-[8px] text-white/50 leading-tight mb-2 min-h-[22px] line-clamp-2">{plan.description}</p>

                {/* Subprice block */}
                <div className="bg-white/[0.02] border border-white/5 rounded-lg p-1 flex flex-col justify-center text-[8px] mb-2">
                  <span className="text-white/40 text-[7px]">
                    {isLifetime ? "Oylik:" : "2 Yillik litsenziya:"}
                  </span>
                  <span className="font-extrabold text-white text-[8px]">
                    {isLifetime ? `$${plan.priceMonthly}/oy` : `$${plan.priceLifetime}/2yil`}
                  </span>
                </div>

                {/* Features List */}
                <div className="space-y-1 mb-3">
                  {plan.features.map((feature, idx) => (
                    <div key={idx} className="flex items-start gap-1">
                      <div className={`mt-0.5 rounded-full p-0.5 ${plan.recommended ? "bg-amber-500/25 text-amber-400" : "bg-white/10 text-white/60"}`}>
                        <Check size={6} strokeWidth={4} />
                      </div>
                      <span className="text-[8.5px] font-medium text-white/80 leading-normal truncate block max-w-[130px]">{feature}</span>
                    </div>
                  ))}
                </div>
              </div>

              <button
                onClick={() => setShowContact(true)}
                className={`w-full py-1.5 rounded-lg font-extrabold text-[9px] flex items-center justify-center gap-1 transition-all active:scale-[0.98] mt-auto cursor-pointer ${
                  plan.recommended
                    ? "bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-md border border-white/10"
                    : "bg-white/5 hover:bg-white/10 text-white border border-white/10"
                }`}
              >
                Obuna Bo'lish
              </button>
            </div>
          ))}
        </div>

        {/* Contacts Modal Inside Paywall */}
        {showContact && (
          <div 
            className="fixed inset-0 z-50 flex items-end justify-center sm:items-center p-3 bg-black/80 backdrop-blur-sm"
            onClick={() => setShowContact(false)}
          >
            <div 
              className="w-full max-w-[320px] bg-[#0a1128] border border-white/10 rounded-[24px] p-4 shadow-2xl animate-in slide-in-from-bottom-10 duration-200"
              onClick={(e) => e.stopPropagation()}
            >
              <h3 className="text-base font-bold text-white mb-1.5 text-center">To'lov va Ulanish</h3>
              <p className="text-[10px] text-white/60 text-center mb-4">
                Tanlangan tarifni faollashtirish uchun adminga murojaat qiling.
              </p>

              <div className="space-y-2">
                <a 
                  href="https://t.me/avlodona" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="w-full p-3 rounded-xl bg-[#0088cc]/10 border border-[#0088cc]/30 hover:bg-[#0088cc]/20 transition-all flex items-center gap-3 group"
                >
                  <div className="w-8 h-8 rounded-full bg-[#0088cc] flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
                    <Send className="w-4 h-4 text-white ml-[-1px] mt-[1px]" />
                  </div>
                  <div className="flex-1">
                    <h4 className="text-xs font-bold text-white">Telegram orqali</h4>
                    <p className="text-[10px] text-[#0088cc]">@avlodona</p>
                  </div>
                </a>

                <a 
                  href="https://instagram.com/akcume" 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="w-full p-3 rounded-xl bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-pink-500/30 hover:from-purple-500/20 hover:to-pink-500/20 transition-all flex items-center gap-3 group"
                >
                  <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-yellow-400 via-pink-500 to-purple-600 flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
                    <Instagram className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1">
                    <h4 className="text-xs font-bold text-white">Instagram orqali</h4>
                    <p className="text-[10px] text-pink-400">@akcume</p>
                  </div>
                </a>
              </div>

              <button 
                onClick={() => setShowContact(false)}
                className="w-full mt-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-white/80 text-xs font-bold transition-all cursor-pointer"
              >
                Orqaga
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
