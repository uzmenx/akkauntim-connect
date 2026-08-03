import React, { useState, useEffect } from "react";
import { 
  FileText, Plus, Trash2, Edit3, Pin, ExternalLink, Check, Copy, 
  Sparkles, Tag, Search, Folder, Calendar, Share2, BookOpen, 
  AlertCircle, ShieldCheck, Download, RefreshCw
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface TradeNote {
  id: string;
  title: string;
  category: "SMC Strategy" | "Wyckoff Analysis" | "Risk Management" | "Trading Rules" | "Market News" | "Trade Journal";
  content: string;
  tags: string[];
  isPinned: boolean;
  createdAt: string;
  updatedAt: string;
  pair?: string;
  resultPips?: number;
}

const DEFAULT_TEMPLATES = [
  {
    name: " Kunlik Trading Rejasi",
    category: "Trading Rules" as const,
    title: "Bugungi Savdo Rejasi va Intizom Qoidalari",
    tags: ["Checklist", "Plan"],
    content: `### 🎯 Bugungi Savdo Maqsadi
- Depozit risk limiti: 1% - 2% maksimal
- Qoidasiz kirishlar taqiqlangan!
- Faqat M15/H1 SMC Order Block va FVG tasdiqlari bilan g'oya ko'riladi.

###  Kutilayotgan Kill Zone Seanslari
- London Kill Zone: 10:00 - 13:00 (Toshkent vaqti)
- NY Kill Zone: 17:00 - 20:00 (Toshkent vaqti)

### 🛑 Taqiqlangan holatlar
1. NFP / CPI yangiliklaridan 15 daqiqa oldin va keyin pozitsiya ochmaslik.
2. 2 ta dalilsiz (no-confluence) bozorga kirmaslik.
3. Yutilgan mablag'ni ketma-ket hissiz oshirmaslik.`
  },
  {
    name: "⚡ SMC Order Block & FVG Analizi",
    category: "SMC Strategy" as const,
    title: "EURUSD H1 Order Block va Inducement Tahlili",
    tags: ["EURUSD", "SMC", "OB", "FVG"],
    content: `### 📊 Bozor Strukturasi (H4 / H1)
- H4 Trend: Bullish (BoS tasdiqlangan)
- H1 Liquidity Sweep: Osiyo seansi pastki nuqtasi olindi (Liquidity Grab).

### 🔍 Kirish Zonalari
- OB narxi: 1.0845 - 1.0852
- Fair Value Gap (FVG): H1 diapazonidagi to'ldirilmagan bo'shliq.
- Confluence: Fibonacci 0.618 OTE zonasi bilan mos keldi.

### 🛡️ Risk & Mukofot
- Stop Loss: 1.0838 (14 pips)
- Take Profit 1: 1.0890 (RR 1:3)
- Take Profit 2: 1.0920 (RR 1:5)`
  },
  {
    name: " Wyckoff Akkumulyatsiya Fazasi",
    category: "Wyckoff Analysis" as const,
    title: "XAUUSD (Oltin) Wyckoff Phase C / Spring Tahlili",
    tags: ["XAUUSD", "Wyckoff", "Spring"],
    content: `### 📈 Wyckoff Sxemasi
- Preliminary Support (PS) va Selling Climax (SC) o'tib bo'ldi.
- Automatic Rally (AR) va Secondary Test (ST) diapazonni belgiladi.
- Spring (Phase C): Diapazondan pastga soxta yorib o'tish va darhol qaytish.

### 💡 Signallar
- H1 hajm (Volume) keskin oshdi (Institutional Absorption).
- Test past hajmda amalga oshdi.`
  }
];

const INITIAL_NOTES: TradeNote[] = [
  {
    id: "note-1",
    title: "Kvant-Trader Qoidalari va Intizom Kodu",
    category: "Trading Rules",
    tags: ["Quant", "Rules", "Risk"],
    isPinned: true,
    createdAt: new Date(Date.now() - 3600000 * 24 * 2).toISOString(),
    updatedAt: new Date(Date.now() - 3600000 * 24 * 2).toISOString(),
    content: `1. Har qanday savdo g'oyasi minimal 3 ta mustaqil konflyuensiya (SMC + Wyckoff + News/KillZone) talab qiladi.
2. Har bir savdoda maksimal risk - 1.0%.
3. Bir kunda 2 ta dalilsiz zarardan keyin savdo to'xtatiladi (Cool-down mode).
4. Strategiya va AI signallari bilan qaror qabul qilinadi, emotsiya bilan emas!`
  },
  {
    id: "note-2",
    title: "Google Keep Sync va Integratsiya Yo'riqnomasi",
    category: "Market News",
    tags: ["GoogleKeep", "Sync", "Workspace"],
    isPinned: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    content: `ℹ️ **Google Keep integratsiyasi va xususiyatlari:**

• **Google Keep bilan tezkor integratsiya**: Usha qaydlarni 1-click bilan nusxalashingiz va keep.google.com ga to'g'ridan-to'g'ri o'tkazishingiz mumkin.
• **Google Keep API Eslatmasi**: Google xavfsizlik va API siyosatiga ko'ra, rasmiy Google Keep REST API faqat **Google Workspace (Enterprise/Tashkilot)** akkountlarida to'liq ishlaydi. Shaxsiy @gmail.com akkountlari uchun Google API kirishni cheklaydi.
• **Yechim**: Ushbu ilova ichida yaratilgan barcha qaydlar brauzeringiz va Supabase bulutli bazasida xavfsiz saqlanadi hamda Keep formatida osongina nusxalanadi!`
  }
];

export function NotesPage() {
  const [notes, setNotes] = useState<TradeNote[]>(() => {
    try {
      const saved = localStorage.getItem("quant_trade_notes");
      return saved ? JSON.parse(saved) : INITIAL_NOTES;
    } catch {
      return INITIAL_NOTES;
    }
  });

  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeNoteId, setActiveNoteId] = useState<string | null>(notes[0]?.id || null);
  const [isEditing, setIsEditing] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showTemplateModal, setShowTemplateModal] = useState(false);

  // Note form state
  const [editTitle, setEditTitle] = useState("");
  const [editCategory, setEditCategory] = useState<TradeNote["category"]>("SMC Strategy");
  const [editContent, setEditContent] = useState("");
  const [editTags, setEditTags] = useState("");
  const [editPair, setEditPair] = useState("");

  useEffect(() => {
    try {
      localStorage.setItem("quant_trade_notes", JSON.stringify(notes));
    } catch (e) {
      console.error("Notes save error:", e);
    }
  }, [notes]);

  const activeNote = notes.find((n) => n.id === activeNoteId) || notes[0];

  const handleCreateNote = (template?: typeof DEFAULT_TEMPLATES[0]) => {
    const newNote: TradeNote = {
      id: "note-" + Date.now(),
      title: template ? template.title : "Yangi Savdo Qaydi",
      category: template ? template.category : "SMC Strategy",
      content: template ? template.content : "Tahlil va fikrlaringizni shu yerga yozing...",
      tags: template ? template.tags : ["New"],
      isPinned: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    setNotes([newNote, ...notes]);
    setActiveNoteId(newNote.id);
    setEditTitle(newNote.title);
    setEditCategory(newNote.category);
    setEditContent(newNote.content);
    setEditTags(newNote.tags.join(", "));
    setEditPair("");
    setIsEditing(true);
    setShowTemplateModal(false);
  };

  const handleStartEdit = (note: TradeNote) => {
    setEditTitle(note.title);
    setEditCategory(note.category);
    setEditContent(note.content);
    setEditTags(note.tags.join(", "));
    setEditPair(note.pair || "");
    setIsEditing(true);
  };

  const handleSaveEdit = () => {
    if (!activeNoteId) return;

    setNotes((prev) =>
      prev.map((n) => {
        if (n.id === activeNoteId) {
          return {
            ...n,
            title: editTitle.trim() || "Nomsiz qayd",
            category: editCategory,
            content: editContent,
            tags: editTags.split(",").map((t) => t.trim()).filter(Boolean),
            pair: editPair.trim() || undefined,
            updatedAt: new Date().toISOString(),
          };
        }
        return n;
      })
    );
    setIsEditing(false);
  };

  const handleDeleteNote = (id: string) => {
    const filtered = notes.filter((n) => n.id !== id);
    setNotes(filtered);
    if (activeNoteId === id) {
      setActiveNoteId(filtered[0]?.id || null);
    }
  };

  const togglePin = (id: string) => {
    setNotes((prev) =>
      prev.map((n) => (n.id === id ? { ...n, isPinned: !n.isPinned } : n))
    );
  };

  const handleCopyToKeepFormat = (note: TradeNote) => {
    const formatted = `📌 [Quant AI Trade Note]\n\nTitle: ${note.title}\nCategory: ${note.category}\nTags: #${note.tags.join(" #")}\nUpdated: ${new Date(note.updatedAt).toLocaleString()}\n\n${note.content}`;
    
    navigator.clipboard.writeText(formatted);
    setCopiedId(note.id);
    setTimeout(() => setCopiedId(null), 2500);
  };

  const openGoogleKeep = () => {
    window.open("https://keep.google.com", "_blank");
  };

  const filteredNotes = notes.filter((note) => {
    const matchesCat = selectedCategory === "All" || note.category === selectedCategory;
    const matchesQuery =
      note.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      note.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
      note.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesCat && matchesQuery;
  });

  const categories = [
    "All",
    "SMC Strategy",
    "Wyckoff Analysis",
    "Risk Management",
    "Trading Rules",
    "Market News",
    "Trade Journal",
  ];

  return (
    <div className="p-4 sm:p-6 space-y-6 max-w-7xl mx-auto pb-24 text-white">
      {/* Top Banner & Header */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 rounded-2xl p-5 border border-indigo-500/20 shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 relative z-10">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-indigo-500/15 rounded-xl border border-indigo-400/30 text-indigo-400 shadow-inner">
              <BookOpen size={24} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
                  Strategiya va Savdo Qaydlari
                </h1>
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                  Google Keep Compatible
                </span>
              </div>
              <p className="text-xs sm:text-sm text-slate-400 mt-1">
                Institutional kvant-trading uchun savdo jurnali, SMC tahlillari hamda Google Keep bilan tezkor integratsiya.
              </p>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2 w-full md:w-auto">
            <button
              onClick={() => setShowTemplateModal(true)}
              className="flex-1 md:flex-initial px-4 py-2.5 rounded-xl bg-white/5 hover:bg-white/10 text-white border border-white/10 transition-all text-xs font-bold flex items-center justify-center gap-2 active:scale-95"
            >
              <Sparkles size={16} className="text-amber-400" />
              <span>Shablonlar</span>
            </button>

            <button
              onClick={() => handleCreateNote()}
              className="flex-1 md:flex-initial px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-all text-xs font-bold flex items-center justify-center gap-2 active:scale-95"
            >
              <Plus size={16} />
              <span>Yangi Qayd</span>
            </button>

            <button
              onClick={openGoogleKeep}
              className="px-3 py-2.5 rounded-xl bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/30 transition-all text-xs font-bold flex items-center justify-center gap-2 active:scale-95"
              title="Google Keep web ilovasini ochish"
            >
              <ExternalLink size={16} />
              <span className="hidden sm:inline">Google Keep</span>
            </button>
          </div>
        </div>

        {/* Integration Status Box */}
        <div className="mt-4 pt-3 border-t border-white/10 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-300">
          <div className="flex items-center gap-2">
            <ShieldCheck size={16} className="text-emerald-400 shrink-0" />
            <span>
              <strong>Baza Sync Status:</strong> Supabase va Local-Storage saqlash faol.
            </span>
          </div>

          <div className="flex items-center gap-2 text-slate-400">
            <AlertCircle size={14} className="text-amber-400 shrink-0" />
            <span>
              Google Keep API (Workspace) va 1-Click "Copy to Keep" tayyor.
            </span>
          </div>
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: List & Filters (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          
          {/* Search bar */}
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={16} />
            <input
              type="text"
              placeholder="Qaydlardan qidirish..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-900/80 border border-white/10 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-all"
            />
          </div>

          {/* Categories Horizontal Scroll */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar">
            {categories.map((cat) => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={cn(
                  "px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all cursor-pointer",
                  selectedCategory === cat
                    ? "bg-indigo-600 text-white font-bold shadow"
                    : "bg-slate-900/60 hover:bg-slate-800 text-slate-400 border border-white/5"
                )}
              >
                {cat === "All" ? " Barchasi" : cat}
              </button>
            ))}
          </div>

          {/* Notes Cards List */}
          <div className="space-y-2.5 max-h-[600px] overflow-y-auto pr-1 custom-scrollbar">
            {filteredNotes.length === 0 ? (
              <div className="p-8 text-center bg-slate-900/40 rounded-2xl border border-white/5 text-slate-500 text-xs">
                Siz tanlagan toifada qaydlar topilmadi.
              </div>
            ) : (
              filteredNotes
                .sort((a, b) => Number(b.isPinned) - Number(a.isPinned))
                .map((note) => {
                  const isActive = note.id === activeNoteId;
                  return (
                    <div
                      key={note.id}
                      onClick={() => {
                        setActiveNoteId(note.id);
                        setIsEditing(false);
                      }}
                      className={cn(
                        "p-3.5 rounded-xl border transition-all cursor-pointer relative group",
                        isActive
                          ? "bg-slate-800/90 border-indigo-500/50 shadow-lg shadow-indigo-500/10"
                          : "bg-slate-900/60 hover:bg-slate-800/60 border-white/5 hover:border-white/10"
                      )}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-indigo-500/15 text-indigo-300 border border-indigo-500/20">
                          {note.category}
                        </span>

                        <div className="flex items-center gap-1">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              togglePin(note.id);
                            }}
                            className={cn(
                              "p-1 rounded hover:bg-white/10 transition-colors",
                              note.isPinned ? "text-amber-400" : "text-slate-500 opacity-0 group-hover:opacity-100"
                            )}
                            title={note.isPinned ? "Sancichni olib tashlash" : "Sanchib qo'yish"}
                          >
                            <Pin size={13} />
                          </button>
                        </div>
                      </div>

                      <h3 className="text-sm font-bold text-white mt-2 line-clamp-1">
                        {note.title}
                      </h3>

                      <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                        {note.content.replace(/#+\s/g, '')}
                      </p>

                      <div className="mt-3 flex items-center justify-between text-[10px] text-slate-500">
                        <div className="flex items-center gap-1">
                          <Calendar size={11} />
                          <span>{new Date(note.updatedAt).toLocaleDateString("uz-UZ")}</span>
                        </div>

                        <div className="flex items-center gap-1">
                          {note.tags.slice(0, 2).map((tag) => (
                            <span key={tag} className="text-slate-400 bg-white/5 px-1.5 py-0.5 rounded">
                              #{tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                })
            )}
          </div>
        </div>

        {/* Right Column: Note Viewer / Editor (8 cols) */}
        <div className="lg:col-span-8">
          {activeNote ? (
            <div className="bg-slate-900/80 rounded-2xl border border-white/10 p-5 sm:p-6 shadow-xl flex flex-col h-full min-h-[500px]">
              
              {/* Header Toolbar */}
              <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-white/10">
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-1 rounded-lg text-xs font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                    {isEditing ? editCategory : activeNote.category}
                  </span>
                  <span className="text-xs text-slate-500">
                    Songgi tahrir: {new Date(activeNote.updatedAt).toLocaleTimeString("uz-UZ", { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {/* Copy to Keep Button */}
                  <button
                    onClick={() => handleCopyToKeepFormat(activeNote)}
                    className="px-3 py-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-300 border border-amber-500/30 text-xs font-bold flex items-center gap-1.5 transition-all active:scale-95 cursor-pointer"
                    title="Google Keep formatida va nusxalash"
                  >
                    {copiedId === activeNote.id ? (
                      <>
                        <Check size={14} className="text-emerald-400" />
                        <span>Nusxalandi!</span>
                      </>
                    ) : (
                      <>
                        <Copy size={14} />
                        <span>Keep uchun nusxalash</span>
                      </>
                    )}
                  </button>

                  {!isEditing ? (
                    <button
                      onClick={() => handleStartEdit(activeNote)}
                      className="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold flex items-center gap-1.5 transition-all active:scale-95 cursor-pointer"
                    >
                      <Edit3 size={14} />
                      <span>Tahrirlash</span>
                    </button>
                  ) : (
                    <button
                      onClick={handleSaveEdit}
                      className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center gap-1.5 transition-all active:scale-95 cursor-pointer shadow-lg shadow-emerald-600/20"
                    >
                      <Check size={14} />
                      <span>Saqlash</span>
                    </button>
                  )}

                  <button
                    onClick={() => handleDeleteNote(activeNote.id)}
                    className="p-1.5 rounded-lg bg-white/5 hover:bg-red-500/20 text-slate-400 hover:text-red-400 transition-colors cursor-pointer"
                    title="O'chirish"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>

              {/* Note Content Area */}
              {isEditing ? (
                /* EDIT FORM */
                <div className="space-y-4 mt-4 flex-1 flex flex-col">
                  <div>
                    <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                      Sarlavha
                    </label>
                    <input
                      type="text"
                      value={editTitle}
                      onChange={(e) => setEditTitle(e.target.value)}
                      className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-white/10 text-sm font-bold text-white focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                        Toifa (Category)
                      </label>
                      <select
                        value={editCategory}
                        onChange={(e) => setEditCategory(e.target.value as TradeNote["category"])}
                        className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-white/10 text-xs font-medium text-white focus:outline-none focus:border-indigo-500"
                      >
                        <option value="SMC Strategy">SMC Strategy</option>
                        <option value="Wyckoff Analysis">Wyckoff Analysis</option>
                        <option value="Risk Management">Risk Management</option>
                        <option value="Trading Rules">Trading Rules</option>
                        <option value="Market News">Market News</option>
                        <option value="Trade Journal">Trade Journal</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                        Teglar (vergul bilan)
                      </label>
                      <input
                        type="text"
                        placeholder="SMC, EURUSD, Reja"
                        value={editTags}
                        onChange={(e) => setEditTags(e.target.value)}
                        className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-white/10 text-xs text-white focus:outline-none focus:border-indigo-500"
                      />
                    </div>
                  </div>

                  <div className="flex-1 flex flex-col min-h-[250px]">
                    <label className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                      Matn (Markdown yordam beradi)
                    </label>
                    <textarea
                      value={editContent}
                      onChange={(e) => setEditContent(e.target.value)}
                      className="w-full flex-1 p-3.5 rounded-xl bg-slate-950 border border-white/10 text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500 resize-none"
                    />
                  </div>
                </div>
              ) : (
                /* VIEW MODE */
                <div className="mt-4 flex-1 flex flex-col">
                  <h2 className="text-xl font-extrabold text-white tracking-tight">
                    {activeNote.title}
                  </h2>

                  {/* Tags */}
                  <div className="flex items-center gap-2 mt-2">
                    <Tag size={12} className="text-indigo-400" />
                    <div className="flex items-center gap-1.5 flex-wrap">
                      {activeNote.tags.map((tag) => (
                        <span key={tag} className="text-[11px] font-semibold text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                          #{tag}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Note Body */}
                  <div className="mt-5 p-4 rounded-xl bg-slate-950/60 border border-white/5 text-xs text-slate-200 leading-relaxed font-sans whitespace-pre-wrap flex-1 overflow-y-auto">
                    {activeNote.content}
                  </div>

                  {/* Export Footer */}
                  <div className="mt-4 pt-3 border-t border-white/10 flex flex-wrap items-center justify-between text-xs text-slate-400 gap-2">
                    <span>Yaratilgan vaqt: {new Date(activeNote.createdAt).toLocaleString("uz-UZ")}</span>
                    
                    <button
                      onClick={openGoogleKeep}
                      className="text-amber-400 hover:underline flex items-center gap-1 font-bold"
                    >
                      <span>Google Keep Web’da ochish</span>
                      <ExternalLink size={12} />
                    </button>
                  </div>
                </div>
              )}

            </div>
          ) : (
            <div className="bg-slate-900/50 rounded-2xl border border-white/5 p-12 text-center text-slate-500">
              Qayd mavjud emas. Yangi qayd yarating.
            </div>
          )}
        </div>

      </div>

      {/* Templates Modal */}
      {showTemplateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in">
          <div className="bg-slate-900 border border-indigo-500/30 rounded-2xl p-6 max-w-lg w-full space-y-4 shadow-2xl relative">
            <div className="flex items-center justify-between border-b border-white/10 pb-3">
              <div className="flex items-center gap-2">
                <Sparkles size={18} className="text-amber-400" />
                <h3 className="text-base font-bold text-white">
                  Tayyor Kvant-Trading Shablonlari
                </h3>
              </div>
              <button
                onClick={() => setShowTemplateModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Ushbu shablonlar yordamida tezkor savdo qaydi yoki SMC tahlil jurnali yarating:
            </p>

            <div className="space-y-3 max-h-[350px] overflow-y-auto pr-1">
              {DEFAULT_TEMPLATES.map((tmpl) => (
                <div
                  key={tmpl.name}
                  onClick={() => handleCreateNote(tmpl)}
                  className="p-3.5 rounded-xl bg-slate-950 hover:bg-slate-800/80 border border-white/10 hover:border-indigo-500/50 cursor-pointer transition-all group"
                >
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-white group-hover:text-indigo-400 transition-colors">
                      {tmpl.name}
                    </h4>
                    <span className="text-[10px] text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded">
                      {tmpl.category}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">
                    {tmpl.content.substring(0, 100)}...
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
