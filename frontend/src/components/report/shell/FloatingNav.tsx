"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronRight, List, X } from "lucide-react";

export interface FloatingTocEntry {
  readonly id: string;
  readonly label: string;
}

/** ADR-117 · Fase 4 — botões flutuantes Back-to-top + Go-to-bottom + Índice mobile.
 *
 * Matching `.back-to-top` + `.go-to-bottom` EXEMPLO_DE_RELATORIO.html
 * linhas 620-628. Ambos aparecem via scroll listener (throttle por rAF).
 *
 * Botão "Índice" (3º FAB) só aparece em `<lg` (≤1023px), onde a sidebar
 * `ReportToc` está escondida e a faixa do topo pode ter overflow.
 * Drawer usa `<dialog>` nativo (Esc + backdrop click sem JS extra).
 */
export function FloatingNav({
  showAfter = 400,
  scrollTarget,
  tocEntries,
}: {
  readonly showAfter?: number;
  readonly scrollTarget?: HTMLElement | null;
  readonly tocEntries?: readonly FloatingTocEntry[];
}) {
  const [showBack, setShowBack] = useState(false);
  const [showBottom, setShowBottom] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    const mql = window.matchMedia("(max-width: 1023px)");
    const update = () => setIsMobile(mql.matches);
    update();
    mql.addEventListener("change", update);
    return () => mql.removeEventListener("change", update);
  }, []);

  useEffect(() => {
    const target = scrollTarget ?? (typeof window !== "undefined" ? window : null);
    if (!target) return;
    let frame = 0;

    const update = () => {
      const scrollTop =
        target === window
          ? window.scrollY
          : (target as HTMLElement).scrollTop;
      const scrollHeight =
        target === window
          ? document.documentElement.scrollHeight
          : (target as HTMLElement).scrollHeight;
      const clientHeight =
        target === window
          ? window.innerHeight
          : (target as HTMLElement).clientHeight;
      setShowBack(scrollTop > showAfter);
      setShowBottom(scrollTop + clientHeight < scrollHeight - showAfter);
    };

    const onScroll = () => {
      if (frame) return;
      frame = window.requestAnimationFrame(() => {
        update();
        frame = 0;
      });
    };

    update();
    target.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      target.removeEventListener("scroll", onScroll);
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, [scrollTarget, showAfter]);

  const scrollTo = (where: "top" | "bottom") => {
    const target = scrollTarget ?? null;
    const top =
      where === "top"
        ? 0
        : target
          ? target.scrollHeight
          : document.documentElement.scrollHeight;
    if (target) target.scrollTo({ top, behavior: "smooth" });
    else window.scrollTo({ top, behavior: "smooth" });
  };

  const openIndex = () => dialogRef.current?.showModal();
  const closeIndex = () => dialogRef.current?.close();

  const goToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    closeIndex();
  };

  const showIndexButton = isMobile && (tocEntries?.length ?? 0) > 0;
  const indexBottom = showBack ? (showBottom ? 132 : 78) : 24;

  return (
    <>
      <button
        type="button"
        aria-label="Voltar ao topo"
        onClick={() => scrollTo("top")}
        data-visible={showBack}
        style={{
          ...baseStyle,
          bottom: 24,
          opacity: showBack ? 1 : 0,
          pointerEvents: showBack ? "auto" : "none",
        }}
      >
        ↑
      </button>
      <button
        type="button"
        aria-label="Ir para o final"
        onClick={() => scrollTo("bottom")}
        data-visible={showBottom}
        style={{
          ...baseStyle,
          bottom: 78,
          opacity: showBottom ? 1 : 0,
          pointerEvents: showBottom ? "auto" : "none",
        }}
      >
        ↓
      </button>
      {showIndexButton && (
        <button
          type="button"
          aria-label="Abrir índice do relatório"
          onClick={openIndex}
          style={{
            ...baseStyle,
            bottom: indexBottom,
            transition: "opacity 0.3s, transform 0.2s, bottom 0.2s",
          }}
        >
          <List size={18} aria-hidden />
        </button>
      )}
      {tocEntries && tocEntries.length > 0 && (
        <dialog
          ref={dialogRef}
          aria-label="Índice do relatório"
          style={dialogStyle}
          onClick={(e) => {
            if (e.target === dialogRef.current) closeIndex();
          }}
        >
          <div style={panelStyle} onClick={(e) => e.stopPropagation()}>
            <div style={panelHeaderStyle}>
              <span style={panelTitleStyle}>Índice</span>
              <button
                type="button"
                aria-label="Fechar índice"
                onClick={closeIndex}
                style={closeButtonStyle}
              >
                <X size={18} aria-hidden />
              </button>
            </div>
            <nav aria-label="Seções do relatório" style={panelNavStyle}>
              {tocEntries.map((entry) => (
                <button
                  key={entry.id}
                  type="button"
                  onClick={() => goToSection(entry.id)}
                  style={panelLinkStyle}
                >
                  <ChevronRight size={14} aria-hidden style={{ flexShrink: 0 }} />
                  <span style={{ textAlign: "left" }}>{entry.label}</span>
                </button>
              ))}
            </nav>
          </div>
        </dialog>
      )}
    </>
  );
}

const baseStyle: React.CSSProperties = {
  position: "fixed",
  right: 24,
  width: 44,
  height: 44,
  borderRadius: "50%",
  background: "var(--brand-primary)",
  color: "#fff",
  border: 0,
  cursor: "pointer",
  fontSize: 18,
  boxShadow: "0 4px 12px rgba(0,0,0,0.2)",
  transition: "opacity 0.3s, transform 0.2s",
  zIndex: 200,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

const dialogStyle: React.CSSProperties = {
  border: 0,
  padding: 0,
  background: "transparent",
  maxWidth: "100vw",
  maxHeight: "100vh",
  width: "100vw",
  height: "100vh",
  margin: 0,
};

const panelStyle: React.CSSProperties = {
  position: "fixed",
  left: 0,
  right: 0,
  bottom: 0,
  maxHeight: "75vh",
  background: "var(--surface-card)",
  color: "var(--surface-foreground)",
  borderTopLeftRadius: 16,
  borderTopRightRadius: 16,
  borderTop: "1px solid var(--surface-border)",
  boxShadow: "0 -8px 32px rgba(0,0,0,0.25)",
  display: "flex",
  flexDirection: "column",
  overflow: "hidden",
  fontFamily: "var(--font-body)",
};

const panelHeaderStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  padding: "16px 20px",
  borderBottom: "1px solid var(--surface-border)",
};

const panelTitleStyle: React.CSSProperties = {
  fontFamily: "var(--font-display)",
  fontWeight: 600,
  fontSize: 14,
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  color: "var(--surface-muted-foreground)",
};

const closeButtonStyle: React.CSSProperties = {
  width: 32,
  height: 32,
  borderRadius: 8,
  border: 0,
  background: "var(--surface-muted)",
  color: "var(--surface-foreground)",
  cursor: "pointer",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

const panelNavStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  padding: "8px 12px 24px",
  overflowY: "auto",
  gap: 2,
};

const panelLinkStyle: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 8,
  padding: "12px 12px",
  border: 0,
  background: "transparent",
  color: "inherit",
  cursor: "pointer",
  fontFamily: "var(--font-body)",
  fontSize: 14,
  borderRadius: 8,
  textAlign: "left",
};
