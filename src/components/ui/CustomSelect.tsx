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
  multiple?: boolean;
  maxCount?: number;
}

export function CustomSelect({ value, onChange, options, className, placeholder, multiple, maxCount }: CustomSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const selectedValues = multiple ? (value ? value.split(",").map(v => v.trim()).filter(Boolean) : []) : [value];

  let displayLabel = placeholder || "Tanlang...";
  if (!multiple) {
    const selectedOption = options.find((opt) => opt.value === value) || options[0];
    displayLabel = selectedOption?.label || displayLabel;
  } else {
    if (selectedValues.length > 0) {
      displayLabel = `${selectedValues.length} ta tanlandi`;
    }
  }

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (optionValue: string) => {
    if (!multiple) {
      onChange(optionValue);
      setIsOpen(false);
    } else {
      if (selectedValues.includes(optionValue)) {
        const newValues = selectedValues.filter(v => v !== optionValue);
        onChange(newValues.join(","));
      } else {
        if (maxCount && selectedValues.length >= maxCount) {
          return;
        }
        const newValues = [...selectedValues, optionValue];
        onChange(newValues.join(","));
      }
    }
  };

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
        <span className="truncate">{displayLabel}</span>
        <ChevronDown
          size={16}
          className={cn("text-fg-muted transition-transform duration-200", isOpen && "rotate-180 text-brand")}
        />
      </button>

      {isOpen && (
        <div className="absolute z-50 mt-2 w-full origin-top rounded-xl border border-white/10 bg-black/80 backdrop-blur-xl p-1.5 shadow-2xl animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="max-h-60 overflow-y-auto no-scrollbar space-y-1">
            {options.map((option) => {
              const isSelected = selectedValues.includes(option.value);
              const isDisabled = multiple && maxCount && !isSelected && selectedValues.length >= maxCount;
              
              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => handleSelect(option.value)}
                  disabled={isDisabled}
                  className={cn(
                    "flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-left text-sm transition-all cursor-pointer",
                    isSelected
                      ? "bg-brand/20 text-brand font-semibold"
                      : "text-fg-muted hover:bg-white/5 hover:text-fg",
                    isDisabled && "opacity-50 cursor-not-allowed hover:bg-transparent hover:text-fg-muted"
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
