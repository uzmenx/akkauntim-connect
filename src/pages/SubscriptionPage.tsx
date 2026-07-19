import { Check, Crown, Sparkles, Star, Zap, Instagram, Send } from "lucide-react";
import { useState } from "react";

export function SubscriptionPage() {
  const [showContact, setShowContact] = useState(false);

  const plans = [
    {
      name: "Low",
      price: "20",
      icon: <Star className="w-5 h-5 text-blue-400" />,
      color: "from-blue-500 to-cyan-500",
      shadow: "shadow-blue-500/20",
      description: "Boshlang'ich treyderlar va bot bilan tanishuv uchun",
      features: [
        "AI Model: Claude 3.5 Haiku",
        "Timeframe: H1, H4 (Major)",
        "Kunlik cheklangan signallar",
        "Asosiy risk menejmenti",
        "Standart tezlik"
      ],
      recommended: false
    },
    {
      name: "Pro",
      price: "69",
      icon: <Zap className="w-5 h-5 text-amber-400" />,
      color: "from-amber-500 to-orange-500",
      shadow: "shadow-amber-500/30",
      description: "Jiddiy treyderlar uchun to'liq tahlil va signallar",
      features: [
        "AI Model: Claude 3.5 Sonnet",
        "Timeframe: M5, M15, H1, H4",
        "Cheklanmagan signallar",
        "Kengaytirilgan risk menejmenti",
        "Yuqori tezlik va aniqlik"
      ],
      recommended: true
    },
    {
      name: "Pro Plus",
      price: "99",
      icon: <Crown className="w-5 h-5 text-fuchsia-400" />,
      color: "from-fuchsia-500 to-purple-600",
      shadow: "shadow-fuchsia-500/20",
      description: "Professional va agressiv savdo uslubi uchun",
      features: [
        "AI Model: Claude 3.5 Sonnet & Opus",
        "Timeframe: Barcha (M1 dan D1 gacha)",
        "VIP signallar va avtomatlashtirish",
        "Chuqurlashtirilgan Garmonik patternlar",
        "Maksimal prioritetli server tezligi"
      ],
      recommended: false
    }
  ];

  return (
    <div className="pb-10 pt-2 space-y-6">
      
      {/* Header Info */}
      <div className="text-center px-4 space-y-2">
        <h2 className="text-2xl font-black text-white drop-shadow-md">
          Ta'riflar va Obuna
        </h2>
        <p className="text-sm text-white/60 max-w-sm mx-auto">
          O'zingizning savdo uslubingizga mos keladigan Premium ta'rifni tanlang va bozorda ustunlikka ega bo'ling.
        </p>
      </div>

      {/* Pricing Cards */}
      <div className="space-y-4 px-2">
        {plans.map((plan) => (
          <div 
            key={plan.name}
            className={`relative rounded-[32px] p-6 backdrop-blur-xl border transition-all duration-300 ${
              plan.recommended 
                ? "bg-[#0d1b3e]/90 border-amber-500/50 shadow-xl " + plan.shadow
                : "bg-[#0f172a]/80 border-white/10"
            }`}
          >
            {plan.recommended && (
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-gradient-to-r from-amber-500 to-orange-500 rounded-full flex items-center gap-1 shadow-lg shadow-amber-500/30 border border-white/20">
                <Sparkles size={12} className="text-white" />
                <span className="text-[10px] font-bold text-white uppercase tracking-wider">Tavsiya Etiladi</span>
              </div>
            )}

            <div className="flex justify-between items-start mb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <div className={`p-2 rounded-xl bg-gradient-to-br ${plan.color} bg-opacity-10 bg-clip-padding backdrop-filter backdrop-blur-sm border border-white/10`}>
                    {plan.icon}
                  </div>
                  <h3 className="text-xl font-bold text-white tracking-tight">{plan.name}</h3>
                </div>
                <p className="text-[11px] text-white/50 pl-1">{plan.description}</p>
              </div>
              <div className="text-right">
                <div className="flex items-start justify-end text-white">
                  <span className="text-sm font-bold mt-1 text-white/70">$</span>
                  <span className="text-4xl font-black tabular-nums tracking-tighter">{plan.price}</span>
                </div>
                <span className="text-[10px] text-white/40 uppercase font-semibold">/oyiga</span>
              </div>
            </div>

            <div className="space-y-3 mb-6 mt-6 pl-1">
              {plan.features.map((feature, idx) => (
                <div key={idx} className="flex items-start gap-3">
                  <div className={`mt-0.5 rounded-full p-0.5 ${plan.recommended ? "bg-amber-500/20 text-amber-400" : "bg-white/10 text-white/60"}`}>
                    <Check size={12} strokeWidth={3} />
                  </div>
                  <span className="text-xs font-medium text-white/80 leading-relaxed">{feature}</span>
                </div>
              ))}
            </div>

            <button
              onClick={() => setShowContact(true)}
              className={`w-full py-3.5 rounded-2xl font-bold text-sm flex items-center justify-center gap-2 transition-all active:scale-[0.98] ${
                plan.recommended
                  ? "bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-lg " + plan.shadow + " border border-white/20 hover:opacity-90"
                  : "bg-white/5 hover:bg-white/10 text-white border border-white/10"
              }`}
            >
              Obuna Bo'lish
            </button>
          </div>
        ))}
      </div>

      {/* Contact Modal / Bottom Sheet */}
      {showContact && (
        <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center p-4 bg-black/60 backdrop-blur-sm" onClick={() => setShowContact(false)}>
          <div 
            className="w-full max-w-sm bg-[#0a1128] border border-white/10 rounded-[32px] p-6 shadow-2xl animate-in slide-in-from-bottom-10 fade-in duration-300"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="w-12 h-1.5 bg-white/10 rounded-full mx-auto mb-6 sm:hidden" />
            
            <h3 className="text-xl font-bold text-white mb-2 text-center">To'lov va Ulanish</h3>
            <p className="text-xs text-white/60 text-center mb-8">
              Obuna xarid qilish yoki hisobni to'ldirish uchun adminga murojaat qiling. Biz sizga tezda yordam beramiz!
            </p>

            <div className="space-y-3">
              <a 
                href="https://t.me/avlodona" 
                target="_blank" 
                rel="noopener noreferrer"
                className="w-full p-4 rounded-2xl bg-[#0088cc]/10 border border-[#0088cc]/30 hover:bg-[#0088cc]/20 transition-all flex items-center gap-4 group"
              >
                <div className="w-10 h-10 rounded-full bg-[#0088cc] flex items-center justify-center shadow-lg shadow-[#0088cc]/30 group-hover:scale-110 transition-transform">
                  <Send className="w-5 h-5 text-white ml-[-2px] mt-[2px]" />
                </div>
                <div className="flex-1">
                  <h4 className="text-sm font-bold text-white">Telegram orqali</h4>
                  <p className="text-xs text-[#0088cc]">@avlodona</p>
                </div>
              </a>

              <a 
                href="https://instagram.com/akcume" 
                target="_blank" 
                rel="noopener noreferrer"
                className="w-full p-4 rounded-2xl bg-gradient-to-br from-purple-500/10 to-pink-500/10 border border-pink-500/30 hover:from-purple-500/20 hover:to-pink-500/20 transition-all flex items-center gap-4 group"
              >
                <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-yellow-400 via-pink-500 to-purple-600 flex items-center justify-center shadow-lg shadow-pink-500/30 group-hover:scale-110 transition-transform">
                  <Instagram className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1">
                  <h4 className="text-sm font-bold text-white">Instagram orqali</h4>
                  <p className="text-xs text-pink-400">@akcume</p>
                </div>
              </a>
            </div>

            <button 
              onClick={() => setShowContact(false)}
              className="w-full mt-6 py-3 rounded-xl bg-white/5 hover:bg-white/10 text-white/80 text-sm font-bold transition-all"
            >
              Yopish
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
