"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { ChevronRight } from "lucide-react";
import { useReportMode } from "@/components/report/ReportModeProvider";
import { useMountedSectionIds } from "@/components/report/hooks/useMountedSectionIds";
import {
  keepInView,
  mostVisibleId,
  SPY_ROOT_MARGIN,
  SPY_THRESHOLD,
  trackRatios,
} from "@/components/report/hooks/scrollSpy";

export interface NavLink {
  readonly id: string;
  readonly label: string;
  readonly num?: string;
  readonly isAppendix?: boolean;
}

export interface NavGroup {
  readonly label?: string;
  readonly links: readonly NavLink[];
}

export type NavDensity = "default" | "compact";

/** Acima desse total de links no modo ativo, faixa entra em modo compacto:
 * apenas o `link.num` aparece; o label só expande no item ativo (scroll-spy).
 * Estratégico tem 16 alvos (com plano_de_acao) → compacta; USA (4) fica normal.
 * ADR-151 (Direção E): Modo Tático removido.
 */
const COMPACT_THRESHOLD = 8;

export interface ReportTopNavProps {
  /** Slot esquerdo — breadcrumb ou brand. Sem fallback. */
  readonly brand?: ReactNode;
  /** Slot direito — ações do relatório (modo, TOC, print, PDF, fonte, tema). */
  readonly actions?: ReactNode;
  readonly groupsByMode: {
    readonly estrategico: readonly NavGroup[];
  };
  /** Container do scroll observado para active link. Default: window. */
  readonly scrollRoot?: HTMLElement | null;
  readonly className?: string;
}

/** ADR-117 · Fase 4 — sticky top-nav do relatório premium.
 *
 * Matching `.nav-sticky` EXEMPLO_DE_RELATORIO.html linhas 178-204 +
 * 1315-1359 (3 grupos por modo). IntersectionObserver atualiza
 * `[data-active]` no link da seção visível.
 */
export function ReportTopNav({
  brand,
  actions,
  groupsByMode,
  scrollRoot,
  className,
}: ReportTopNavProps) {
  const { mode } = useReportMode();
  const [activeId, setActiveId] = useState<string | null>(null);
  const groups = groupsByMode[mode];
  const totalLinks = groups.reduce((acc, g) => acc + g.links.length, 0);
  const density: NavDensity = totalLinks > COMPACT_THRESHOLD ? "compact" : "default";

  const railRef = useRef<HTMLDivElement>(null);
  const manualUntil = useRef(0);
  const [edges, setEdges] = useState({ left: false, right: false });

  const syncEdges = useCallback(() => {
    const el = railRef.current;
    if (!el) return;
    const left = el.scrollLeft > 1;
    const right = el.scrollLeft + el.clientWidth < el.scrollWidth - 1;
    setEdges((prev) =>
      prev.left === left && prev.right === right ? prev : { left, right },
    );
  }, []);

  const linkIds = useMemo(
    () => groups.flatMap((g) => g.links.map((l) => l.id)),
    [groups],
  );
  // Depende dos ids JÁ MONTADOS, não dos declarados: a faixa monta antes do
  // fetch resolver, e com `groups` na dep o efeito registrava zero elementos
  // e nunca mais rodava — nenhum chip ficava `data-active` (A40.l104).
  const mountedIds = useMountedSectionIds(linkIds);

  useEffect(() => {
    const elements = mountedIds
      .map((id) => document.getElementById(id))
      .filter((el): el is HTMLElement => el !== null);
    if (elements.length === 0) return;

    const ratios = new Map<string, number>();
    const observer = new IntersectionObserver(
      (entries) => {
        trackRatios(entries, ratios);
        const top = mostVisibleId(ratios);
        if (top) setActiveId(top);
      },
      { root: scrollRoot ?? null, rootMargin: SPY_ROOT_MARGIN, threshold: SPY_THRESHOLD },
    );
    for (const el of elements) observer.observe(el);
    return () => observer.disconnect();
  }, [mountedIds, scrollRoot]);

  // Sem isto o chip ativo é justamente o que fica fora de campo: no compacto
  // só ele expande o rótulo, e a faixa nunca rolava sozinha (A40.l104).
  // `instant` porque é movimento passivo em faixa sticky; `nearest` para não
  // arrastar a página. Suprimido após gesto do usuário, para não brigar com ele.
  useEffect(() => {
    const rail = railRef.current;
    if (!activeId || !rail) return;
    if (performance.now() < manualUntil.current) return;
    const chip = rail.querySelector<HTMLElement>(`[data-nav-id="${activeId}"]`);
    if (chip) keepInView(rail, chip, "x");
  }, [activeId]);

  useEffect(() => {
    const el = railRef.current;
    if (!el) return;
    syncEdges();
    const observer = new ResizeObserver(syncEdges);
    observer.observe(el);
    return () => observer.disconnect();
  }, [syncEdges, mountedIds, density]);

  return (
    <nav
      className={className}
      aria-label="Navegação do relatório"
      data-report-topnav
      data-density={density}
      style={{
        position: "sticky",
        top: 0,
        zIndex: 30,
        minHeight: "var(--report-topnav-h, 52px)",
        boxSizing: "border-box",
        background: "var(--report-gradient-nav-sticky)",
        borderBottom: "1px solid rgba(255,255,255,0.08)",
        boxShadow: "0 2px 12px rgba(0,0,0,0.15)",
        display: "flex",
        alignItems: "center",
        padding: "0 20px",
      }}
    >
      {brand && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "10px 16px 10px 0",
            borderRight: "1px solid rgba(255,255,255,0.1)",
            marginRight: 8,
            whiteSpace: "nowrap",
            color: "#fff",
          }}
        >
          {brand}
        </div>
      )}
      {/* `hidden md:flex`: abaixo de md a caixa útil é 0–26px, e os 20 chips
          ficavam focáveis dentro dela — foco sem pixel algum (2.4.7). Ali quem
          serve o índice é o FAB do `FloatingNav`. A máscara declara que a
          faixa é parcial; sem ela o auto-scroll lê como corte, não janela. */}
      <div
        ref={railRef}
        data-report-nav-rail
        className="hidden min-w-0 flex-1 items-center overflow-x-auto md:flex"
        onScroll={syncEdges}
        onWheel={() => {
          manualUntil.current = performance.now() + 800;
        }}
        onPointerDown={() => {
          manualUntil.current = performance.now() + 800;
        }}
        style={{
          scrollbarWidth: "none",
          maskImage: edgeMask(edges),
          WebkitMaskImage: edgeMask(edges),
        }}
      >
        {groups.map((group, i) => (
          <div
            key={`${mode}-${i}`}
            style={{ display: "flex", alignItems: "center", gap: 2 }}
          >
            {i > 0 && (
              <span
                aria-hidden="true"
                style={{
                  width: 1,
                  height: 20,
                  background: "rgba(255,255,255,0.15)",
                  margin: "0 4px",
                  flexShrink: 0,
                }}
              />
            )}
            {group.label && (
              <span
                style={{
                  fontSize: 9,
                  textTransform: "uppercase",
                  letterSpacing: "0.8px",
                  color: "rgba(255,255,255,0.3)",
                  padding: "0 6px",
                  whiteSpace: "nowrap",
                  fontWeight: 600,
                }}
              >
                {group.label}
              </span>
            )}
            {group.links.map((link) => (
              <NavLinkItem
                key={link.id}
                link={link}
                active={link.id === activeId}
                density={density}
              />
            ))}
          </div>
        ))}
      </div>
      {actions && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginLeft: 12,
            flexShrink: 0,
            paddingLeft: 12,
            borderLeft: "1px solid rgba(255,255,255,0.1)",
          }}
        >
          {actions}
        </div>
      )}
    </nav>
  );
}

const FADE_PX = 24;

/** `undefined` quando não há transbordo — máscara constante custa camada.
 *
 * `black`/`transparent` aqui não são cor: a máscara consome só o canal alfa,
 * então não há token de design a aplicar (ADR-076 é sobre cor renderizada). */
function edgeMask(edges: { left: boolean; right: boolean }): string | undefined {
  if (!edges.left && !edges.right) return undefined;
  const start = edges.left ? FADE_PX : 0;
  const end = edges.right ? FADE_PX : 0;
  return `linear-gradient(to right, transparent 0, black ${start}px, black calc(100% - ${end}px), transparent 100%)`;
}

const NAV_BADGE = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  width: 16,
  height: 16,
  borderRadius: "var(--radius-sm, 4px)",
  background: "rgba(255,255,255,0.15)",
  fontSize: 10,
  fontWeight: 700,
  flexShrink: 0,
} as const;

function NavLinkItem({
  link,
  active,
  density,
}: {
  link: NavLink;
  active: boolean;
  density: NavDensity;
}) {
  const labelHidden = density === "compact" && !active;
  return (
    <a
      href={`#${link.id}`}
      data-nav-id={link.id}
      data-active={active}
      data-density={density}
      aria-current={active ? "location" : undefined}
      aria-label={labelHidden ? link.label : undefined}
      title={labelHidden ? link.label : undefined}
      style={{
        display: "flex",
        alignItems: "center",
        gap: labelHidden ? 0 : 4,
        padding: labelHidden ? "10px 6px" : "10px 10px",
        color: active
          ? "#fff"
          : link.isAppendix
            ? "rgba(255,255,255,0.4)"
            : "rgba(255,255,255,0.7)",
        textDecoration: "none",
        fontSize: 12,
        fontWeight: 500,
        whiteSpace: "nowrap",
        borderRadius: "var(--radius-sm, 4px)",
        background: active ? "rgba(255,255,255,0.12)" : "transparent",
        transition: "all 0.2s",
        fontFamily: "var(--font-body)",
      }}
    >
      {/* Chip sem `num` (seção shell-level: V0, perfil) renderizava 12px em
          branco no modo compacto — o label colapsa e não havia badge para
          sobrar (A40.l104). Glifo neutro espelha `ReportToc`, que já resolve
          o mesmo caso com ChevronRight. */}
      <span aria-hidden style={NAV_BADGE}>
        {link.num ?? <ChevronRight size={10} strokeWidth={3} />}
      </span>
      <span
        style={{
          maxWidth: labelHidden ? 0 : 200,
          opacity: labelHidden ? 0 : 1,
          overflow: "hidden",
          transition: "max-width 0.2s, opacity 0.2s",
        }}
      >
        {link.label}
      </span>
    </a>
  );
}
