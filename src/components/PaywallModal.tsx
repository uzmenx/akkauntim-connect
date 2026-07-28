import { useState } from "react";
import { Check, X, Shield, Globe, Zap, Play, Send, Instagram, Sparkles } from "lucide-react";

interface PaywallModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function PaywallModal({ isOpen, onClose }: PaywallModalProps) {
  const [showContact, setShowContact] = useState(false);
  const [isLifetime, setIsLifetime] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<string>("pro");

  if (!isOpen) return null;

  const features = [
    { icon: <Globe className="text-[#00a8ff] w-4 h-4" />, text: "60%-70% Aniqlikdagi AI Signallar" },
    { icon: <Shield className="text-[#00d2c4] w-4 h-4" />, text: "Dinamik Risk va Stop-Loss Nazorati" },
    { icon: <Play className="text-[#a8a0ff] w-4 h-4" />, text: "24/7 Avtomatlashtirilgan Monitoring" },
    { icon: <Zap className="text-[#ffb300] w-4 h-4" />, text: "Tezkor Millisekundlik Serverlar" }
  ];

  const plans = [
    {
      id: "low",
      name: "Low Plan",
      price: isLifetime ? "7.499" : "500",
      period: isLifetime ? "2yil" : "oy",
      badge: null,
      description: "Aqlli va tezkor AI tahlillari"
    },
    {
      id: "pro",
      name: "Pro Plan",
      price: isLifetime ? "9.999" : "700",
      period: isLifetime ? "2yil" : "oy",
      badge: "Tavsiya",
      description: "Institutsional darajadagi AI quvvati"
    }
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md overflow-y-auto">
      <div className="relative w-full max-w-[420px] bg-gradient-to-b from-[#0a122c] to-[#040817] border border-white/10 rounded-[32px] p-6 shadow-[0_32px_64px_-16px_rgba(0,0,0,0.8),inset_0_1px_1px_rgba(255,255,255,0.15)] backdrop-blur-3xl animate-in zoom-in-95 duration-200">
        
        {/* Glow Effects */}
        <div className="absolute top-[-40px] left-[-40px] w-48 h-48 rounded-full bg-blue-500/10 blur-3xl pointer-events-none" />
        <div className="absolute bottom-[-40px] right-[-40px] w-48 h-48 rounded-full bg-indigo-500/10 blur-3xl pointer-events-none" />

        {/* Close Button with enlarged hit target */}
        <button 
          onClick={onClose}
          className="absolute -top-3 -right-3 w-14 h-14 flex items-center justify-center rounded-full bg-[#0a122c] hover:bg-white/10 text-white/50 hover:text-white transition-all border border-white/10 active:scale-90 z-50 cursor-pointer shadow-2xl backdrop-blur-sm"
          aria-label="Close"
        >
          <X size={22} strokeWidth={2.5} />
        </button>

        {/* Header */}
        <div className="text-center mt-2 mb-4 space-y-1">
          <h2 className="text-xl md:text-2xl font-black text-white drop-shadow-md">
            Premium Imkoniyatlar!
          </h2>
          <p className="text-sm font-semibold text-white/60">
            Yuksalish AI Premium obuna tariflari
          </p>
        </div>

        {/* Features box */}
        <div className="bg-gradient-to-br from-[#0f1d3e] to-[#080d24] border border-white/5 rounded-3xl p-4 mb-4 space-y-3 shadow-[inset_0_2px_4px_rgba(0,0,0,0.4)]">
          {features.map((f, i) => (
            <div key={i} className="flex items-center gap-3">
              <div className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-white/5 border border-white/5 shadow-md">
                {f.icon}
              </div>
              <span className="text-[11px] font-bold text-white/80">{f.text}</span>
            </div>
          ))}
          <div className="text-center pt-1">
            <a 
              href="https://t.me/avlodona"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[10px] text-[#00a8ff] hover:underline font-bold"
            >
              See All Features
            </a>
          </div>
        </div>

        {/* Billing Switcher */}
        <div className="flex justify-center mb-4">
          <div className="bg-[#0b1229]/80 border border-white/10 rounded-full p-1 flex items-center gap-1 backdrop-blur-md shadow-lg shadow-black/40">
            <button
              onClick={() => setIsLifetime(false)}
              className={`px-4 py-1.5 text-[10px] font-bold rounded-full transition-all duration-300 cursor-pointer ${
                !isLifetime
                  ? "bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-md border border-white/5"
                  : "text-white/60 hover:text-white"
              }`}
            >
              Oylik obuna
            </button>
            <button
              onClick={() => setIsLifetime(true)}
              className={`px-4 py-1.5 text-[10px] font-bold rounded-full transition-all duration-300 flex items-center gap-1 cursor-pointer ${
                isLifetime
                  ? "bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-md border border-white/5 animate-pulse"
                  : "text-white/60 hover:text-white"
              }`}
            >
              2 Yillik litsenziya
            </button>
          </div>
        </div>

        {/* Tariffs List */}
        <div className="space-y-2.5">
          {plans.map((p) => {
            const isSelected = selectedPlan === p.id;
            return (
              <button
                key={p.id}
                onClick={() => setSelectedPlan(p.id)}
                className={`w-full p-4 rounded-3xl border text-left flex items-center justify-between transition-all duration-300 active:scale-[0.99] relative overflow-hidden cursor-pointer ${
                  isSelected
                    ? "bg-[#007cc0]/15 border-[#00a8ff] shadow-[0_4px_20px_rgba(0,168,255,0.15)]"
                    : "bg-[#0b1229]/60 border-white/10 hover:border-white/20"
                }`}
              >
                {/* Plan Left Side */}
                <div className="flex items-center gap-3">
                  <div className={`w-4 h-4 rounded-full border flex items-center justify-center transition-all ${
                    isSelected ? "border-[#00a8ff] bg-[#00a8ff]" : "border-white/30"
                  }`}>
                    {isSelected && <div className="w-1.5 h-1.5 rounded-full bg-[#0a122c]" />}
                  </div>
                  <div>
                    <span className={`text-xs font-black block ${isSelected ? "text-white" : "text-white/80"}`}>
                      {p.name}
                    </span>
                    <span className="text-[9px] text-white/50 block mt-0.5">{p.description}</span>
                  </div>
                </div>

                {/* Plan Right Side (Price) */}
                <div className="text-right">
                  <div className="flex items-baseline gap-0.5 justify-end">
                    <span className={`text-base font-black tabular-nums ${isSelected ? "text-[#00a8ff]" : "text-white"}`}>
                      ${p.price}
                    </span>
                    <span className="text-[9px] text-white/40 font-bold">
                      /{p.period}
                    </span>
                  </div>
                  {p.badge && (
                    <span className="inline-block mt-1 px-1.5 py-0.5 rounded-md bg-gradient-to-r from-amber-500 to-orange-500 text-white text-[7px] font-black uppercase tracking-wider">
                      {p.badge}
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>

        {/* Action Button */}
        <button
          onClick={() => setShowContact(true)}
          className="w-full mt-5 py-3.5 rounded-full bg-[#007cc0] hover:bg-[#00a8ff] text-white font-extrabold text-xs shadow-lg shadow-[#007cc0]/25 border border-white/10 active:scale-95 transition-all flex items-center justify-center gap-2 cursor-pointer"
        >
          <span>Obuna Bo'lish</span>
        </button>

        {/* Small terms */}
        <p className="text-[9px] text-white/40 text-center mt-3 leading-relaxed px-4">
          Xizmat shartlari va qoidalari amal qiladi. Savollar bo'lsa, qo'llab-quvvatlash xizmatiga murojaat qiling.
        </p>

        {/* Contacts Modal inside paywall */}
        {showContact && (
          <div 
            className="fixed inset-0 z-50 flex items-end justify-center sm:items-center p-4 bg-black/80 backdrop-blur-sm"
            onClick={() => setShowContact(false)}
          >
            <div 
              className="w-full max-w-sm bg-[#0a1128] border border-white/10 rounded-[32px] p-6 shadow-2xl animate-in slide-in-from-bottom-10 duration-300"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="w-12 h-1.5 bg-white/10 rounded-full mx-auto mb-6 sm:hidden" />
              
              <h3 className="text-xl font-bold text-white mb-2 text-center">To'lov va Ulanish</h3>
              <p className="text-xs text-white/60 text-center mb-6">
                Tanlangan tarifni faollashtirish uchun adminga murojaat qiling.
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
                className="w-full mt-6 py-3 rounded-xl bg-white/5 hover:bg-white/10 text-white/80 text-sm font-bold transition-all cursor-pointer"
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
