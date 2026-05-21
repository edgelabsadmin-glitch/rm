import type { Config } from "tailwindcss";

/*
 * SPEC-034 — Tailwind theme generated from Tier-0 §2 + Appendix A.
 * Semantic utilities (bg-brand, text-ink-secondary, shadow-xl-brand, …) resolve
 * to the CSS custom properties declared in src/styles/tokens.css — one source of
 * truth (dual-plumbing per pre-034 audit disposition D1). Opacity variants of the
 * brand color are NAMED tokens (brand-muted/ghost/soft/edge/glow), not Tailwind
 * `/opacity` modifiers, matching how the design language defines them.
 */
const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "var(--color-brand-primary)",
          hover: "var(--color-brand-primary-hover)",
          deep: "var(--color-brand-primary-deep)",
          muted: "var(--color-brand-primary-muted)",
          ghost: "var(--color-brand-primary-ghost)",
          soft: "var(--color-brand-primary-soft)",
          edge: "var(--color-brand-primary-edge)",
          glow: "var(--color-brand-primary-glow)",
        },
        surface: {
          page: "var(--color-surface-page)",
          chrome: "var(--color-surface-chrome)",
          card: "var(--color-surface-card)",
          sidebar: "var(--color-surface-sidebar)",
          "sidebar-soft": "var(--color-surface-sidebar-soft)",
          "tinted-row": "var(--color-surface-tinted-row)",
          track: "var(--color-surface-track)",
          "glass-light": "var(--color-surface-glass-light)",
          "glass-border": "var(--color-surface-glass-border)",
        },
        ink: {
          primary: "var(--color-text-primary)",
          secondary: "var(--color-text-secondary)",
          muted: "var(--color-text-muted)",
          "on-brand": "var(--color-text-on-brand)",
          "on-brand-soft": "var(--color-text-on-brand-soft)",
          "on-brand-faint": "var(--color-text-on-brand-faint)",
          "on-brand-strip": "var(--color-text-on-brand-strip)",
          quote: "var(--color-text-quote)",
        },
        line: {
          subtle: "var(--color-border-subtle)",
          strong: "var(--color-border-strong)",
          brand: "var(--color-border-brand)",
        },
        risk: {
          "high-bg": "var(--color-risk-high-bg)",
          "high-fg": "var(--color-risk-high-fg)",
          "high-border": "var(--color-risk-high-border)",
          "medium-bg": "var(--color-risk-medium-bg)",
          "medium-fg": "var(--color-risk-medium-fg)",
          "medium-border": "var(--color-risk-medium-border)",
          "low-bg": "var(--color-risk-low-bg)",
          "low-fg": "var(--color-risk-low-fg)",
          "low-border": "var(--color-risk-low-border)",
        },
      },
      fontFamily: {
        sans: ["Inter Variable", "Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "SF Mono", "Menlo", "Monaco", "monospace"],
      },
      fontSize: {
        // Tier-0 §3 "Eyebrow-tiny" (the "HEALTH" label inside the conic ring).
        "2xs": ["0.625rem", { lineHeight: "1" }],
      },
      borderRadius: {
        "2.5xl": "1.25rem",
        "4xl": "2rem", // hero card + outer shell (rounded-[2rem])
      },
      boxShadow: {
        // The Edge-Purple tinted shadow — RESTRICTED to hero card + brand-mark tile (§6).
        "xl-brand":
          "0 20px 25px -5px rgba(107, 70, 193, 0.20), 0 8px 10px -6px rgba(107, 70, 193, 0.10)",
        "2xl-shell": "0 25px 50px -12px rgba(226, 232, 240, 0.70)",
      },
      transitionTimingFunction: {
        ease: "cubic-bezier(0.16, 1, 0.3, 1)",
        "ease-in-pulse": "cubic-bezier(0.4, 0, 1, 1)",
      },
      transitionDuration: {
        fast: "200ms",
        base: "250ms",
        slow: "400ms",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
