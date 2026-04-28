import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "1.5rem",
      screens: { "2xl": "1280px" },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        "border-strong": "hsl(var(--border-strong))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        paper: {
          DEFAULT: "hsl(var(--background))",
          warm: "hsl(var(--paper-warm))",
          tint: "hsl(var(--paper-tint))",
        },
        ink: {
          DEFAULT: "hsl(var(--foreground))",
          soft: "hsl(var(--foreground) / 0.78)",
          dim: "hsl(var(--foreground) / 0.6)",
        },
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
        },
        gold: {
          DEFAULT: "hsl(var(--gold))",
          bright: "hsl(var(--gold-bright))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
      },
      borderRadius: {
        lg: "8px",
        md: "var(--radius)",
        sm: "2px",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "system-ui"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      fontSize: {
        // Tracking ligeramente mas amplio que default para look editorial
        xs: ["0.75rem", { lineHeight: "1.1rem", letterSpacing: "0.005em" }],
        sm: ["0.8125rem", { lineHeight: "1.2rem", letterSpacing: "0" }],
        base: ["0.9375rem", { lineHeight: "1.55rem", letterSpacing: "-0.005em" }],
        lg: ["1.0625rem", { lineHeight: "1.6rem", letterSpacing: "-0.01em" }],
        xl: ["1.25rem", { lineHeight: "1.7rem", letterSpacing: "-0.012em" }],
        "2xl": ["1.5rem", { lineHeight: "1.85rem", letterSpacing: "-0.015em" }],
        "3xl": ["1.875rem", { lineHeight: "2.15rem", letterSpacing: "-0.02em" }],
        "4xl": ["2.5rem", { lineHeight: "2.75rem", letterSpacing: "-0.025em" }],
      },
      letterSpacing: {
        institutional: "0.18em",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "rise-in": {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-400px 0" },
          "100%": { backgroundPosition: "400px 0" },
        },
        "caret-blink": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0" },
        },
      },
      animation: {
        "fade-in": "fade-in 240ms cubic-bezier(0.2, 0, 0, 1) both",
        "rise-in": "rise-in 280ms cubic-bezier(0.2, 0, 0, 1) both",
        "caret-blink": "caret-blink 1.1s step-end infinite",
      },
      boxShadow: {
        card: "0 1px 0 hsl(var(--border) / 0.6)",
        composer: "0 -1px 0 hsl(var(--border)), 0 -8px 24px hsl(var(--foreground) / 0.04)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
