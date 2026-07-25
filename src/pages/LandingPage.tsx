import { Link } from "react-router-dom";
import { ArrowRight, Sparkles, Shield, Zap, Globe, Bot, LineChart } from "lucide-react";
import logo from "@/assets/akcume-logo.png";

const features = [
  { icon: Bot, title: "AI-Powered Sync", desc: "Neural pipelines keep every connected account in perfect sync, 24/7." },
  { icon: Shield, title: "Bank-grade Security", desc: "End-to-end encryption, RLS, and zero-trust auth on every request." },
  { icon: Zap, title: "Realtime Everywhere", desc: "Sub-second updates across dashboards, mobile, and integrations." },
  { icon: Globe, title: "Global Integrations", desc: "Search Console, Analytics, MT5, Stripe — one unified hub." },
  { icon: LineChart, title: "Insight Engine", desc: "Actionable analytics distilled from your entire connector graph." },
  { icon: Sparkles, title: "Premium UX", desc: "A cinematic interface engineered to feel effortless." },
];

export function LandingPage() {
  return (
    <div className="relative min-h-[100dvh] w-full overflow-hidden text-white">
      {/* Animated glow background */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-40 left-1/2 h-[600px] w-[600px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,rgba(120,80,255,0.35),transparent_60%)] blur-3xl animate-pulse" />
        <div className="absolute top-1/3 -left-40 h-[500px] w-[500px] rounded-full bg-[radial-gradient(circle,rgba(0,220,180,0.28),transparent_60%)] blur-3xl" />
        <div className="absolute bottom-0 right-0 h-[500px] w-[500px] rounded-full bg-[radial-gradient(circle,rgba(0,140,255,0.3),transparent_60%)] blur-3xl" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:48px_48px] [mask-image:radial-gradient(ellipse_at_center,black,transparent_70%)]" />
      </div>

      {/* Nav */}
      <header className="sticky top-0 z-40 border-b border-white/5 bg-black/20 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <div className="flex items-center gap-3">
            <img src={logo} alt="Akcume AI" className="h-9 w-9 drop-shadow-[0_0_18px_rgba(120,80,255,0.6)]" />
            <span className="text-lg font-bold tracking-tight bg-gradient-to-r from-white to-white/60 bg-clip-text text-transparent">
              Akcume <span className="bg-gradient-to-r from-emerald-300 via-sky-400 to-violet-400 bg-clip-text text-transparent">AI</span>
            </span>
          </div>
          <nav className="hidden items-center gap-8 text-sm text-white/70 md:flex">
            <a href="#features" className="hover:text-white transition">Features</a>
            <a href="#connectors" className="hover:text-white transition">Connectors</a>
            <Link to="/auth" className="hover:text-white transition">Sign in</Link>
          </nav>
          <Link
            to="/auth"
            className="group relative inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-violet-500 via-sky-500 to-emerald-400 px-5 py-2 text-sm font-semibold text-white shadow-[0_0_30px_rgba(120,80,255,0.5)] transition-transform hover:scale-105"
          >
            Get Started <ArrowRight size={16} className="transition-transform group-hover:translate-x-0.5" />
          </Link>
        </div>
      </header>

      {/* Hero */}
      <section className="relative mx-auto max-w-7xl px-6 pt-20 pb-24 text-center md:pt-32 md:pb-32">
        <div className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs text-white/70 backdrop-blur-md">
          <Sparkles size={14} className="text-emerald-300" />
          Powered by state-of-the-art AI
        </div>
        <h1 className="mx-auto max-w-4xl text-5xl font-black leading-[1.05] tracking-tight md:text-7xl">
          <span className="bg-gradient-to-b from-white to-white/60 bg-clip-text text-transparent">AI-Powered</span>
          <br />
          <span className="bg-gradient-to-r from-violet-400 via-sky-400 to-emerald-300 bg-clip-text text-transparent">
            Account Connections
          </span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-white/60 md:text-xl">
          Connect every platform you rely on — from Google Search Console to Analytics, MT5, and beyond — into one intelligent control plane.
        </p>
        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Link
            to="/auth"
            className="group relative inline-flex items-center gap-2 overflow-hidden rounded-full bg-gradient-to-r from-violet-500 via-sky-500 to-emerald-400 px-8 py-4 text-base font-bold text-white shadow-[0_0_50px_rgba(120,80,255,0.6)] transition-transform hover:scale-105"
          >
            <span className="absolute inset-0 bg-white/10 opacity-0 transition-opacity group-hover:opacity-100" />
            Start Connecting <ArrowRight size={18} />
          </Link>
          <a
            href="#connectors"
            className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-8 py-4 text-base font-semibold text-white/90 backdrop-blur-md transition hover:bg-white/10"
          >
            View Connectors
          </a>
        </div>

        {/* Floating preview */}
        <div className="relative mx-auto mt-20 max-w-5xl">
          <div className="absolute -inset-4 rounded-3xl bg-gradient-to-r from-violet-500/30 via-sky-500/30 to-emerald-400/30 blur-2xl" />
          <div className="relative rounded-3xl border border-white/10 bg-white/[0.03] p-8 backdrop-blur-2xl">
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              {["Search Console", "Analytics", "MT5", "Stripe"].map((n) => (
                <div key={n} className="rounded-2xl border border-white/10 bg-gradient-to-br from-white/[0.06] to-white/[0.01] p-5 text-left transition hover:-translate-y-1 hover:border-white/20">
                  <div className="mb-3 h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_12px_rgba(52,211,153,0.9)]" />
                  <div className="text-sm font-semibold">{n}</div>
                  <div className="text-xs text-white/50">Connected</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="relative mx-auto max-w-7xl px-6 py-24">
        <div className="mb-14 text-center">
          <h2 className="text-4xl font-black tracking-tight md:text-5xl">
            <span className="bg-gradient-to-r from-white to-white/60 bg-clip-text text-transparent">Built for the </span>
            <span className="bg-gradient-to-r from-emerald-300 to-violet-400 bg-clip-text text-transparent">next era</span>
          </h2>
          <p className="mt-3 text-white/60">Everything you need to orchestrate connections at scale.</p>
        </div>
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
          {features.map((f) => (
            <div
              key={f.title}
              className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur-xl transition hover:-translate-y-1 hover:border-white/20 hover:bg-white/[0.06]"
            >
              <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-gradient-to-br from-violet-500/30 to-emerald-400/30 opacity-0 blur-2xl transition-opacity group-hover:opacity-100" />
              <div className="relative">
                <div className="mb-4 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-gradient-to-br from-violet-500/20 to-emerald-400/20 ring-1 ring-white/10">
                  <f.icon size={20} className="text-white" />
                </div>
                <h3 className="text-lg font-bold">{f.title}</h3>
                <p className="mt-2 text-sm text-white/60">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Connectors CTA */}
      <section id="connectors" className="relative mx-auto max-w-5xl px-6 py-24 text-center">
        <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-violet-500/10 via-sky-500/5 to-emerald-400/10 p-12 backdrop-blur-2xl">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(120,80,255,0.25),transparent_60%)]" />
          <div className="relative">
            <h2 className="text-4xl font-black tracking-tight md:text-5xl">
              Ready to <span className="bg-gradient-to-r from-emerald-300 to-violet-400 bg-clip-text text-transparent">connect everything?</span>
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-white/60">
              Launch your Connectors Hub and manage every integration in a single, unified dashboard.
            </p>
            <Link
              to="/auth"
              className="mt-8 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-violet-500 via-sky-500 to-emerald-400 px-8 py-4 text-base font-bold text-white shadow-[0_0_50px_rgba(120,80,255,0.6)] transition-transform hover:scale-105"
            >
              Open Dashboard <ArrowRight size={18} />
            </Link>
          </div>
        </div>
      </section>

      <footer className="border-t border-white/5 py-8 text-center text-xs text-white/40">
        © {new Date().getFullYear()} Akcume AI — All rights reserved.
      </footer>
    </div>
  );
}
