import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmtMoney(n: number | null | undefined, currency = "USD") {
  if (n == null || Number.isNaN(n)) return "—";
  
  const validCurrency = (currency && typeof currency === 'string' && currency.trim() !== '') ? currency : "USD";
  
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency", currency: validCurrency, maximumFractionDigits: 2,
    }).format(n);
  } catch (e) {
    return new Intl.NumberFormat("en-US", {
      style: "currency", currency: "USD", maximumFractionDigits: 2,
    }).format(n);
  }
}

export function fmtNum(n: number | null | undefined, digits = 2) {
  if (n == null || Number.isNaN(n)) return "—";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: digits }).format(n);
}

export function timeAgo(iso: string | null | undefined) {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h`;
  return `${Math.floor(h / 24)}d`;
}

export function fmtDateShort(iso: string | null | undefined) {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n: number) => n.toString().padStart(2, "0");
  return `${pad(d.getDate())}.${pad(d.getMonth() + 1)} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

