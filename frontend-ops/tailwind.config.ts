import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: "var(--font-display)",
        body: "var(--font-body)",
        mono: "var(--font-mono)",
      },
      colors: {
        brand: {
          primary: "var(--brand-primary)",
          "primary-fg": "var(--brand-primary-foreground)",
          accent: "var(--brand-accent)",
          "accent-fg": "var(--brand-accent-foreground)",
          neutral: "var(--brand-neutral)",
          danger: "var(--brand-danger)",
          "danger-fg": "var(--brand-danger-foreground)",
          warning: "var(--brand-warning)",
          "warning-fg": "var(--brand-warning-foreground)",
          info: "var(--brand-info)",
        },
        surface: {
          bg: "var(--surface-background)",
          fg: "var(--surface-foreground)",
          card: "var(--surface-card)",
          muted: "var(--surface-muted)",
          "muted-fg": "var(--surface-muted-foreground)",
          border: "var(--surface-border)",
          input: "var(--surface-input)",
          ring: "var(--surface-ring)",
        },
        semantic: {
          gain: "var(--semantic-gain)",
          loss: "var(--semantic-loss)",
          alert: "var(--semantic-alert)",
          info: "var(--semantic-info-financial)",
        },
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
        card: "var(--radius-card)",
        pill: "var(--radius-pill)",
      },
    },
  },
  plugins: [],
};

export default config;
