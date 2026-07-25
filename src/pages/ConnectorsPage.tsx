import { useState } from "react";
import { Check, Plus, Search, Zap } from "lucide-react";
import logo from "@/assets/akcume-logo.png";

type Connector = {
  id: string;
  name: string;
  category: string;
  desc: string;
  color: string;
  connected?: boolean;
};

const CONNECTORS: Connector[] = [
  { id: "gsc", name: "Google Search Console", category: "Analytics", desc: "Track search performance, indexing, and clicks.", color: "from-sky-500 to-blue-600", connected: true },
  { id: "ga4", name: "Google Analytics", category: "Analytics", desc: "Real-time visitor & conversion insights.", color: "from-orange-400 to-amber-500" },
  { id: "mt5", name: "MetaTrader 5", category: "Trading", desc: "Live positions, orders and account sync.", color: "from-emerald-400 to-teal-500", connected: true },
  { id: "stripe", name: "Stripe", category: "Payments", desc: "Subscriptions, invoices & payouts.", color: "from-violet-500 to-indigo-600" },
  { id: "slack", name: "Slack", category: "Comms", desc: "Push signals & alerts to channels.", color: "from-fuchsia-500 to-pink-500" },
  { id: "sheets", name: "Google Sheets", category: "Data", desc: "Two-way sync with spreadsheets.", color: "from-green-400 to-emerald-600" },
  { id: "notion", name: "Notion", category: "Workspace", desc: "Sync docs and databases seamlessly.", color: "from-neutral-300 to-neutral-500" },
  { id: "openai", name: "OpenAI", category: "AI", desc: "GPT models for smart automations.", color: "from-teal-400 to-cyan-500" },
  { id: "anthropic", name: "Anthropic", category: "AI", desc: "Claude models for reasoning tasks.", color: "from-orange-500 to-rose-500" },
];

const CATEGORIES = ["All", "Analytics", "Trading", "Payments", "AI", "Data", "Workspace", "Comms"];

export function ConnectorsPage() {
  const [query, setQuery] = useState("");
  const [cat, setCat] = useState("All");

  const filtered = CONNECTORS.filter(
    (c) =>
      (cat === "All" || c.category === cat) &&
      (c.name.toLowerCase().includes(query.toLowerCase()) || c.desc.toLowerCase().includes(query.toLowerCase()))
  );

  const connectedCount = CONNECTORS.filter((c) => c.connected).length;

  return (
    <div className="relative min-h-[100dvh] w-full overflow-hidden text-white">
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute -top-40 left-1/2 h-[500px] w-[500px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,rgba(120,80,255,0.3),transparent_60%)] blur-3xl" />
        <div className="absolute bottom-0 right-0 h-[500px] w-[500px] rounded-full bg-[radial-gradient(circle,rgba(0,220,180,0.25),transparent_60%)] blur-3xl" />
      </div>

      <div className="mx-auto max-w-7xl px-6 py-10">
        {/* Header */}
        <div className="mb-10 flex flex-col items-start justify-between gap-4 md:flex-row md:items-center">
          <div className="flex items-center gap-4">
            <img src={logo} alt="Akcume AI" className="h-11 w-11 drop-shadow-[0_0_18px_rgba(120,80,255,0.6)]" />
            <div>
              <h1 className="text-3xl font-black tracking-tight md:text-4xl">
                <span className="bg-gradient-to-r from-white to-white/60 bg-clip-text text-transparent">Connectors </span>
                <span className="bg-gradient-to-r from-emerald-300 to-violet-400 bg-clip-text text-transparent">Hub</span>
              </h1>
              <p className="text-sm text-white/60">Manage every integration in one place.</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-2 text-sm backdrop-blur-xl">
              <span className="text-white/50">Connected: </span>
              <span className="font-bold text-emerald-300">{connectedCount}</span>
              <span className="text-white/40"> / {CONNECTORS.length}</span>
            </div>
          </div>
        </div>

        {/* Search + filters */}
        <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-center">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/40" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search connectors…"
              className="w-full rounded-2xl border border-white/10 bg-white/[0.04] py-3 pl-11 pr-4 text-sm placeholder-white/40 outline-none backdrop-blur-xl transition focus:border-violet-400/60 focus:bg-white/[0.08]"
            />
          </div>
        </div>
        <div className="mb-8 flex flex-wrap gap-2">
          {CATEGORIES.map((c) => (
            <button
              key={c}
              onClick={() => setCat(c)}
              className={`rounded-full border px-4 py-1.5 text-xs font-semibold transition ${
                cat === c
                  ? "border-transparent bg-gradient-to-r from-violet-500 via-sky-500 to-emerald-400 text-white shadow-[0_0_20px_rgba(120,80,255,0.5)]"
                  : "border-white/10 bg-white/[0.03] text-white/70 hover:bg-white/[0.08]"
              }`}
            >
              {c}
            </button>
          ))}
        </div>

        {/* Grid */}
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((c) => (
            <div
              key={c.id}
              className="group relative overflow-hidden rounded-2xl border border-white/10 bg-white/[0.03] p-6 backdrop-blur-xl transition hover:-translate-y-1 hover:border-white/25 hover:bg-white/[0.06]"
            >
              <div className={`absolute -right-16 -top-16 h-40 w-40 rounded-full bg-gradient-to-br ${c.color} opacity-20 blur-2xl transition-opacity duration-500 group-hover:opacity-40`} />
              <div className="relative">
                <div className="mb-4 flex items-start justify-between">
                  <div className={`grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br ${c.color} shadow-lg`}>
                    <Zap size={20} className="text-white" />
                  </div>
                  {c.connected && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-emerald-400/30 bg-emerald-400/10 px-2.5 py-1 text-[11px] font-bold text-emerald-300">
                      <Check size={12} /> Connected
                    </span>
                  )}
                </div>
                <div className="mb-1 text-xs uppercase tracking-wide text-white/40">{c.category}</div>
                <h3 className="text-lg font-bold">{c.name}</h3>
                <p className="mt-2 text-sm text-white/60">{c.desc}</p>
                <button
                  className={`mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition ${
                    c.connected
                      ? "border border-white/10 bg-white/5 text-white/80 hover:bg-white/10"
                      : "bg-gradient-to-r from-violet-500 via-sky-500 to-emerald-400 text-white shadow-[0_0_25px_rgba(120,80,255,0.4)] hover:scale-[1.02]"
                  }`}
                >
                  {c.connected ? (
                    "Manage"
                  ) : (
                    <>
                      <Plus size={16} /> Connect
                    </>
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>

        {filtered.length === 0 && (
          <div className="mt-16 text-center text-white/50">No connectors match your search.</div>
        )}
      </div>
    </div>
  );
}
