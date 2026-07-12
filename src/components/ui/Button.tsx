import * as React from "react";
import { cn } from "@/lib/utils";
import { cva, type VariantProps } from "class-variance-authority";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-2xl font-semibold transition-all active:scale-[0.97] disabled:opacity-50 disabled:pointer-events-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/60",
  {
    variants: {
      variant: {
        primary:
          "bg-gradient-to-br from-brand to-brand-strong text-white shadow-lg shadow-brand-strong/30 hover:brightness-110",
        glass:
          "glass text-fg hover:brightness-110",
        ghost: "text-fg-muted hover:text-fg hover:bg-white/5",
        danger:
          "bg-gradient-to-br from-danger to-danger text-white shadow-lg shadow-danger/30 hover:brightness-110",
        success:
          "bg-gradient-to-br from-success to-success text-white shadow-lg shadow-success/30 hover:brightness-110",
      },
      size: {
        sm: "h-9 px-3 text-sm",
        md: "h-11 px-4 text-sm",
        lg: "h-14 px-6 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />
  ),
);
Button.displayName = "Button";
