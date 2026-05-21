/*
 * shadcn/ui Button — substrate primitive (pre-034 audit D6). Generated-equivalent
 * of `npx shadcn@latest add button`, then RE-TOKENED to Tier-0 (§8.4/8.5/8.6):
 * solid Edge Purple primary, purple-edged outline, ghost. No default shadcn look
 * (§12 #1). When network returns, `shadcn init` will recognize this file in place.
 */
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full text-sm font-medium transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-edge disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-brand text-ink-on-brand hover:bg-brand-hover",
        outline: "border border-brand-edge bg-transparent text-brand hover:bg-brand-ghost",
        ghost: "bg-transparent text-brand hover:bg-brand-ghost",
      },
      size: {
        default: "px-4 py-2",
        sm: "px-3 py-1.5 text-xs",
        lg: "px-5 py-2.5",
      },
    },
    defaultVariants: { variant: "primary", size: "default" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
