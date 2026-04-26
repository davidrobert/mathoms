"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useTheme } from "next-themes";

import {
  useReportFontScale,
  type ReportFontScale,
} from "@/components/report/useReportFontScale";

/** ADR-121 — popover de aparência (tamanho do texto + tema) na top-nav
 * do relatório. Reading-time prefs ficam inline na superfície de leitura
 * (padrão Medium/NYT/Apple Books); não migram para `/settings`. */
type ThemeValue = "light" | "dark";

const FONT_SIZES: ReadonlyArray<{ scale: ReportFontScale; label: string; px: number }> = [
  { scale: "compact", label: "Compacto", px: 12 },
  { scale: "normal", label: "Normal", px: 14 },
  { scale: "comfortable", label: "Confortável", px: 16 },
];

const PILL_ACTIVE_BG = "rgba(255,255,255,0.12)";
const PILL_ACTIVE_BORDER = "rgba(255,255,255,0.25)";
const PILL_IDLE_BORDER = "rgba(255,255,255,0.15)";
const PILL_IDLE_COLOR = "rgba(255,255,255,0.5)";

export function AppearanceMenu({ className }: { className?: string }) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);

  const { scale, setScale } = useReportFontScale();
  const { resolvedTheme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    setMounted(true);
  }, []);
  const currentTheme: ThemeValue =
    mounted && resolvedTheme === "dark" ? "dark" : "light";

  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        close();
        triggerRef.current?.focus();
      }
    };
    const onClick = (e: MouseEvent) => {
      const target = e.target as Node | null;
      if (!target) return;
      if (panelRef.current?.contains(target)) return;
      if (triggerRef.current?.contains(target)) return;
      close();
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [open, close]);

  return (
    <div className={className} style={{ position: "relative", display: "inline-block" }}>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="Aparência"
        aria-haspopup="dialog"
        aria-expanded={open}
        data-active={open}
        data-appearance-trigger
        style={{
          fontFamily: "var(--font-display)",
          fontSize: 13,
          fontWeight: 600,
          letterSpacing: "-0.01em",
          padding: "5px 12px",
          border: `1px solid ${open ? PILL_ACTIVE_BORDER : PILL_IDLE_BORDER}`,
          borderRadius: "var(--radius-md, 6px)",
          background: open ? PILL_ACTIVE_BG : "transparent",
          color: open ? "var(--brand-primary-foreground)" : PILL_IDLE_COLOR,
          cursor: "pointer",
          transition: "all 0.2s",
          minWidth: 36,
        }}
      >
        Aa
      </button>

      {open && (
        <div
          ref={panelRef}
          role="dialog"
          aria-label="Aparência"
          data-appearance-panel
          style={{
            position: "absolute",
            top: "calc(100% + 8px)",
            right: 0,
            zIndex: 50,
            minWidth: 248,
            padding: 14,
            background: "var(--brand-primary)",
            border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: "var(--radius-md, 8px)",
            boxShadow: "0 8px 24px rgba(0,0,0,0.32)",
            display: "flex",
            flexDirection: "column",
            gap: 12,
          }}
        >
          <SectionLabel>Tamanho do texto</SectionLabel>
          <div role="group" aria-label="Tamanho do texto" style={{ display: "inline-flex", gap: 2 }}>
            {FONT_SIZES.map(({ scale: s, label, px }) => {
              const active = s === scale;
              return (
                <button
                  key={s}
                  type="button"
                  title={label}
                  aria-label={label}
                  onClick={() => {
                    setScale(s);
                    close();
                  }}
                  aria-pressed={active}
                  data-active={active}
                  data-font-scale-value={s}
                  style={{
                    flex: 1,
                    fontFamily: "var(--font-display)",
                    fontSize: px,
                    fontWeight: 600,
                    lineHeight: 1,
                    padding: "8px 10px",
                    border: `1px solid ${active ? PILL_ACTIVE_BORDER : PILL_IDLE_BORDER}`,
                    borderRadius: "var(--radius-md, 6px)",
                    background: active ? PILL_ACTIVE_BG : "transparent",
                    color: active ? "var(--brand-primary-foreground)" : PILL_IDLE_COLOR,
                    cursor: "pointer",
                    transition: "all 0.2s",
                  }}
                >
                  Aa
                </button>
              );
            })}
          </div>

          <SectionLabel>Tema</SectionLabel>
          <div
            role="group"
            aria-label="Tema do relatório"
            data-report-theme-toggle
            style={{ display: "inline-flex", gap: 2 }}
          >
            {(["light", "dark"] satisfies ThemeValue[]).map((value) => {
              const active = currentTheme === value;
              return (
                <button
                  key={value}
                  type="button"
                  onClick={() => {
                    setTheme(value);
                    close();
                  }}
                  aria-pressed={active}
                  data-active={active}
                  data-theme-value={value}
                  style={{
                    flex: 1,
                    fontFamily: "var(--font-body)",
                    fontSize: 11,
                    fontWeight: 600,
                    padding: "6px 12px",
                    border: `1px solid ${active ? PILL_ACTIVE_BORDER : PILL_IDLE_BORDER}`,
                    borderRadius: "var(--radius-md, 6px)",
                    background: active ? PILL_ACTIVE_BG : "transparent",
                    color: active ? "var(--brand-primary-foreground)" : PILL_IDLE_COLOR,
                    cursor: "pointer",
                    transition: "all 0.2s",
                  }}
                >
                  {value === "light" ? "Light" : "Dark"}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <span
      style={{
        fontFamily: "var(--font-body)",
        fontSize: 10,
        fontWeight: 600,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        color: "rgba(255,255,255,0.55)",
      }}
    >
      {children}
    </span>
  );
}
