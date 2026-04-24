import type { ReactNode } from "react";

/** ADR-117 · Fase 3 — divider entre seções com ícone circular opcional.
 *
 * Matching `.section-divider` EXEMPLO_DE_RELATORIO.html linhas 472-509.
 * Render: linha-gradient à esquerda — ícone — linha-gradient à direita.
 */
export function SectionDivider({
  icon,
  ariaLabel,
  className,
}: {
  readonly icon?: ReactNode;
  readonly ariaLabel?: string;
  readonly className?: string;
}) {
  return (
    <div
      role="separator"
      aria-label={ariaLabel}
      className={className}
      style={{
        margin: "56px 0",
        display: "flex",
        alignItems: "center",
        gap: 16,
      }}
    >
      <span
        style={{
          flex: 1,
          height: 1,
          background:
            "linear-gradient(90deg, transparent, var(--surface-border) 20%, var(--surface-border) 80%, transparent)",
        }}
        aria-hidden="true"
      />
      {icon && (
        <span
          aria-hidden="true"
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 36,
            height: 36,
            borderRadius: 10,
            background:
              "linear-gradient(135deg, rgba(46,134,171,0.08), rgba(45,198,83,0.08))",
            border: "1px solid var(--surface-border)",
            color: "var(--brand-info)",
            fontSize: 14,
            flexShrink: 0,
          }}
        >
          {icon}
        </span>
      )}
      <span
        style={{
          flex: 1,
          height: 1,
          background:
            "linear-gradient(90deg, transparent, var(--surface-border) 20%, var(--surface-border) 80%, transparent)",
        }}
        aria-hidden="true"
      />
    </div>
  );
}
