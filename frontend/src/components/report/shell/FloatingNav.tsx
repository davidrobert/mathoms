"use client";

import { useEffect, useState } from "react";

/** ADR-117 · Fase 4 — botões flutuantes Back-to-top + Go-to-bottom.
 *
 * Matching `.back-to-top` + `.go-to-bottom` EXEMPLO_DE_RELATORIO.html
 * linhas 620-628. Ambos aparecem via scroll listener (throttle por rAF).
 */
export function FloatingNav({
  showAfter = 400,
  scrollTarget,
}: {
  readonly showAfter?: number;
  readonly scrollTarget?: HTMLElement | null;
}) {
  const [showBack, setShowBack] = useState(false);
  const [showBottom, setShowBottom] = useState(false);

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
