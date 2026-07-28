import { Check, Crown, Sparkles, Star, Zap, Instagram, Send, ShieldCheck, HelpCircle, MessageSquareText, ChevronDown } from "lucide-react";
import { useState } from "react";

export function SubscriptionPage() {
  const [showContact, setShowContact] = useState(false);
  const [isLifetime, setIsLifetime] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const plans = [
    {
      name: "Low",
      priceMonthly: "500",
      priceLifetime: "7.499",
      icon: <Star className="w-4 h-4 md:w-5 md:h-5 text-blue-400" />,
      color: "from-blue-500 to-cyan-500",
      shadow: "shadow-blue-500/20",
      description: "Aqlli va tezkor neyron tarmoqlar bilan dastlabki professional qadamlar",
      features: [
        "AI Engine: Kimi K3 & Claude 3.5 Haiku",
        "Timeframe: H1, H4 (Trend skaneri)",
        "Kunlik 95%+ aniqlikdagi signallar",
        "Dinamik Stop-Loss risk nazorati",
        "24/7 Avtomatlashtirilgan nazorat"
      ],
      recommended: false
    },
    {
      name: "Pro",
      priceMonthly: "700",
      priceLifetime: "9.999",
      icon: <Zap className="w-4 h-4 md:w-5 md:h-5 text-amber-400" />,
      color: "from-amber-500 to-orange-500",
      shadow: "shadow-amber-500/30",
      description: "Eng yuqori darajadagi institutsional AI quvvati va cheksiz tahlillar",
      features: [
        "AI Engine: Fable 5, GPT-5 & Claude",
        "Barcha Timeframelar (M1 dan W1)",
        "Cheklanmagan VIP signallar qatori",
        "Hedge-Fond darajasidagi risk boshqaruvi",
        "Millisekundlik prioritet server tezligi",
        "Avtomatik garmonik patternlar"
      ],
      recommended: true
    }
  ];

  return (
    <div className="pb-6 pt-1 space-y-4 max-h-full overflow-y-auto no-scrollbar">
      
      {/* Header Info */}
      <div className="text-center px-4 space-y-0.5">
        <h2 className="text-xl md:text-2xl font-black text-white drop-shadow-md">
          Ta'riflar va Obuna
        </h2>
        <p className="text-[10px] md:text-sm text-white/60 max-w-sm mx-auto">
          Premium ta'rifni tanlang va bozorda ustunlikka ega bo'ling.
        </p>
      </div>

      {/* Billing Switcher */}
      <div className="flex justify-center px-4">
        <div className="bg-[#0f172a]/80 border border-white/10 rounded-full p-0.5 md:p-1 flex items-center gap-1 backdrop-blur-md shadow-lg shadow-black/40">
          <button
            onClick={() => setIsLifetime(false)}
            className={`px-3 md:px-4 py-1.5 text-[10px] md:text-xs font-bold rounded-full transition-all duration-300 ${
              !isLifetime
                ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md border border-white/10"
                : "text-white/60 hover:text-white"
            }`}
          >
            Oylik obuna
          </button>
          <button
            onClick={() => setIsLifetime(true)}
            className={`px-3 md:px-4 py-1.5 text-[10px] md:text-xs font-bold rounded-full transition-all duration-300 flex items-center gap-1 ${
              isLifetime
                ? "bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-md border border-white/10 animate-pulse"
                : "text-white/60 hover:text-white"
            }`}
          >
            <Crown size={10} className={isLifetime ? "text-white" : "text-white/60"} />
            2 Yillik (Sotib olish)
          </button>
        </div>
      </div>

      {/* Pricing Cards */}
      <div className="grid grid-cols-2 gap-2 md:gap-6 px-2 max-w-4xl mx-auto">
        {plans.map((plan) => (
          <div 
            key={plan.name}
            className={`relative rounded-2xl md:rounded-[32px] p-3 md:p-6 backdrop-blur-xl border transition-all duration-300 flex flex-col justify-between ${
              plan.recommended 
                ? "bg-[#0d1b3e]/90 border-amber-500/50 shadow-xl " + plan.shadow
                : "bg-[#0f172a]/80 border-white/10"
            }`}
          >
            {plan.recommended && (
              <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-2 py-0.5 bg-gradient-to-r from-amber-500 to-orange-500 rounded-full flex items-center gap-0.5 shadow-lg shadow-amber-500/30 border border-white/20 z-10">
                <Sparkles size={8} className="text-white" />
                <span className="text-[8px] font-bold text-white uppercase tracking-wider">Tavsiya</span>
              </div>
            )}

            <div>
              <div className="flex flex-col min-[375px]:flex-row justify-between items-start min-[375px]:items-center gap-1.5 mb-2">
                <div className="flex items-center gap-1.5">
                  <div className={`p-1.5 md:p-2 rounded-lg md:rounded-xl bg-gradient-to-br ${plan.color} bg-opacity-10 bg-clip-padding backdrop-filter backdrop-blur-sm border border-white/10`}>
                    {plan.icon}
                  </div>
                  <h3 className="text-sm md:text-xl font-bold text-white tracking-tight">{plan.name}</h3>
                </div>
                <div className="text-right flex items-baseline gap-0.5">
                  <span className="text-[10px] md:text-sm font-bold text-white/70">$</span>
                  <span className="text-lg min-[375px]:text-xl md:text-3xl font-black tabular-nums tracking-tighter text-white">
                    {isLifetime ? plan.priceLifetime : plan.priceMonthly}
                  </span>
                  <span className="text-[8px] md:text-[10px] text-white/40 uppercase font-semibold block min-[375px]:inline ml-0.5">
                    {isLifetime ? "/2y" : "/oy"}
                  </span>
                </div>
              </div>
              
              <p className="text-[9px] md:text-[11px] text-white/50 pl-0.5 min-h-[22px] md:min-h-0 line-clamp-2 mb-2">{plan.description}</p>

              {/* Alternative Price indicator (visible premium option) */}
              <div className="bg-white/[0.03] border border-white/5 rounded-xl p-1.5 md:p-3 flex flex-col justify-center text-[9px] md:text-xs my-2 gap-0.5">
                <span className="text-white/40 text-[8px] md:text-[10px]">
                  {isLifetime ? "Oylik variant:" : "2 Yillik litsenziya:"}
                </span>
                <span className="font-extrabold text-white text-[9px] md:text-xs">
                  {isLifetime 
                    ? `$${plan.priceMonthly}/oy` 
                    : `$${plan.priceLifetime}/2yil`
                  }
                </span>
              </div>

              <div className="space-y-1.5 md:space-y-3 mb-4 mt-2 pl-0.5">
                {plan.features.map((feature, idx) => (
                  <div key={idx} className="flex items-start gap-1.5 md:gap-3">
                    <div className={`mt-0.5 rounded-full p-0.5 ${plan.recommended ? "bg-amber-500/20 text-amber-400" : "bg-white/10 text-white/60"}`}>
                      <Check size={8} strokeWidth={3} className="md:w-3 md:h-3" />
                    </div>
                    <span className="text-[9px] md:text-xs font-medium text-white/80 leading-snug md:leading-relaxed">{feature}</span>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={() => setShowContact(true)}
              className={`w-full py-2 md:py-3.5 rounded-xl md:rounded-2xl font-bold text-[10px] md:text-sm flex items-center justify-center gap-1 md:gap-2 transition-all active:scale-[0.98] mt-2 ${
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

      {/* 2. Trust & Guarantee Features */}
      <div className="grid grid-cols-2 gap-2 px-2 max-w-4xl mx-auto">
        <div className="bg-[#0f172a]/40 border border-white/5 rounded-2xl p-3 flex flex-col items-center text-center space-y-1">
          <div className="p-2 rounded-full bg-emerald-500/10 text-emerald-400">
            <ShieldCheck size={18} />
          </div>
          <h4 className="text-[11px] font-bold text-white">Xavfsizlik kafolati</h4>
          <p className="text-[9px] text-white/50 leading-normal">
            Barcha API kalitlari va shaxsiy ma'lumotlar to'liq shifrlangan.
          </p>
        </div>
        <div className="bg-[#0f172a]/40 border border-white/5 rounded-2xl p-3 flex flex-col items-center text-center space-y-1">
          <div className="p-2 rounded-full bg-blue-500/10 text-blue-400">
            <Sparkles size={18} />
          </div>
          <h4 className="text-[11px] font-bold text-white">95%+ Aniqlik</h4>
          <p className="text-[9px] text-white/50 leading-normal">
            Algoritmlarimiz 24/7 davomida eng aniq nuqtalarni skanerlaydi.
          </p>
        </div>
      </div>

      {/* 3. FAQ Accordion */}
      <div className="px-2 max-w-4xl mx-auto space-y-2">
        <div className="flex items-center gap-1.5 px-2">
          <HelpCircle size={14} className="text-indigo-400" />
          <h3 className="text-xs font-extrabold uppercase tracking-wider text-white/70">FAQ / Ko'p beriladigan savollar</h3>
        </div>
        
        <div className="space-y-1.5">
          {[
            {
              q: "2 Yillik litsenziya qanday ishlaydi?",
              a: "Botni bir marta sotib olasiz va 2 yil davomida barcha yangilanishlar, VIP signallar va funksiyalardan hech qanday qo'shimcha to'lovsiz cheksiz foydalanasiz."
            },
            {
              q: "To'lov qanday qilinadi va qachon yoqiladi?",
              a: "To'lov amalga oshirilgach, adminga chekni yuborasiz. Hisobingiz 5-10 daqiqa ichida tizimda avtomatik tarzda faollashtiriladi."
            },
            {
              q: "Qaytarib berish kafolati bormi?",
              a: "Ha! Agar tizim ko'rsatilgan natijalarni bermasa, birinchi 7 kun ichida mablag'ingizni to'liq qaytarib olishingiz mumkin."
            }
          ].map((faq, idx) => {
            const isOpen = openFaq === idx;
            return (
              <div 
                key={idx}
                className="bg-[#0f172a]/60 border border-white/5 rounded-xl overflow-hidden transition-all duration-300"
              >
                <button
                  onClick={() => setOpenFaq(isOpen ? null : idx)}
                  className="w-full p-3 flex justify-between items-center text-left text-xs font-bold text-white/90 hover:text-white transition-colors"
                >
                  <span>{faq.q}</span>
                  <ChevronDown 
                    size={14} 
                    className={`text-white/40 transition-transform duration-300 ${isOpen ? "rotate-180" : ""}`} 
                  />
                </button>
                {isOpen && (
                  <div className="px-3 pb-3 text-[10px] text-white/60 leading-normal border-t border-white/[0.03] pt-2 animate-in fade-in slide-in-from-top-1 duration-200">
                    {faq.a}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* 4. Help / Contact Banner */}
      <div className="px-2 max-w-4xl mx-auto">
        <div className="relative overflow-hidden rounded-2xl border border-white/5 bg-gradient-to-br from-indigo-500/10 to-purple-600/10 p-4 text-center">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(120,80,255,0.15),transparent_60%)] pointer-events-none" />
          <div className="relative space-y-2">
            <div className="inline-flex p-2 rounded-full bg-indigo-500/20 text-indigo-400">
              <MessageSquareText size={16} />
            </div>
            <h4 className="text-xs font-bold text-white">Yordam yoki boshqa savollar bormi?</h4>
            <p className="text-[10px] text-white/50 max-w-xs mx-auto">
              Administrator bilan bog'laning va batafsil ma'lumot oling. Biz sizga tezda javob beramiz!
            </p>
            <button
              onClick={() => setShowContact(true)}
              className="px-4 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] font-bold shadow-lg shadow-indigo-600/20 border border-white/10 active:scale-95 transition-all"
            >
              Menejer bilan bog'lanish
            </button>
          </div>
        </div>
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
