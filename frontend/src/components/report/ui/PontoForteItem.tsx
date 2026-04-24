import type { ReactNode } from "react";

export interface PontoForteItemProps {
  readonly icon?: ReactNode;
  readonly titulo: string;
  readonly descricao: ReactNode;
  readonly className?: string;
}

/** ADR-117 · Fase 3 — item de ponto forte.
 *
 * Matching `.ponto-forte-item` EXEMPLO_DE_RELATORIO.html linhas 1065-1082.
 * Green-success item com border-left accent e ícone grande à esquerda.
 */
export function PontoForteItem({
  icon,
  titulo,
  descricao,
  className,
}: PontoForteItemProps) {
  return (
    <li
      className={className}
      style={{
        display: "flex",
        alignItems: "flex-start",
        gap: "var(--space-md, 12px)",
        padding: "var(--space-md, 12px) var(--space-lg, 16px)",
        background: "var(--report-surface-compare-pos)",
        borderRadius: "var(--radius-md, 6px)",
        borderLeft: "3px solid var(--brand-accent)",
        listStyle: "none",
      }}
    >
      {icon && (
        <span
          aria-hidden="true"
          style={{
            fontSize: "var(--report-font-size-xl, 22px)",
            flexShrink: 0,
            lineHeight: 1.2,
          }}
        >
          {icon}
        </span>
      )}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 2,
          minWidth: 0,
        }}
      >
        <strong
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "var(--report-font-size-md, 14px)",
            fontWeight: 600,
            color: "var(--brand-primary)",
          }}
        >
          {titulo}
        </strong>
        <span
          style={{
            fontSize: "var(--report-font-size-base, 13px)",
            color: "var(--surface-muted-foreground)",
            lineHeight: 1.4,
          }}
        >
          {descricao}
        </span>
      </div>
    </li>
  );
}

export function PontosFortesList({
  children,
  className,
}: {
  readonly children: ReactNode;
  readonly className?: string;
}) {
  return (
    <ul
      className={className}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-md, 12px)",
        padding: 0,
        margin: 0,
      }}
    >
      {children}
    </ul>
  );
}
