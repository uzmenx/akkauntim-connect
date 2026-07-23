import { useState, useRef, useEffect } from "react";
import { ChevronDown, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface Option {
  value: string;
  label: string;
}

interface CustomSelectProps {
  value: string;
  onChange: (value: string) => void;
  options: Option[];
  className?: string;
  placeholder?: string;
}

export function CustomSelect({ value, onChange, options, className, placeholder }: CustomSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const selectedOption = options.find((opt) => opt.value === value) || options[0];

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div ref={containerRef} className={cn("relative w-full", isOpen && "z-30", className)}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex w-full items-center justify-between rounded-xl border border-white/10 bg-black/40 px-3 py-3 text-sm text-fg outline-none transition-all duration-200 cursor-pointer hover:bg-white/5 focus:border-brand/60",
          isOpen && "border-brand/60 ring-1 ring-brand/60"
        )}
      >
        <span className="truncate">{selectedOption?.label}</span>
        <ChevronDown
          size={16}
          className={cn("text-fg-muted transition-transform duration-200", isOpen && "rotate-180 text-brand")}
        />
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-2 w-full origin-top rounded-xl border border-white/10 bg-black/80 backdrop-blur-xl p-1.5 shadow-2xl animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="max-h-60 overflow-y-auto no-scrollbar space-y-1">
            {options.map((option) => {
              const isSelected = option.value === value;
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => {
                    onChange(option.value);
                    setIsOpen(false);
                  }}
                  className={cn(
                    "flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-left text-sm transition-all cursor-pointer",
                    isSelected
                      ? "bg-brand/20 text-brand font-semibold"
                      : "text-fg-muted hover:bg-white/5 hover:text-fg"
                  )}
                >
                  <span className="truncate">{option.label}</span>
                  {isSelected && <Check size={14} className="text-brand shrink-0 ml-2" />}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
