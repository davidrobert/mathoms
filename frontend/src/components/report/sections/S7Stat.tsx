import type { ReactNode } from "react";

/** Card de estatística da S7 (label/valor/sublabel + tom por fase do plano).
 *  Extraído mecanicamente de `S7IndependenciaSection` quando a seção cruzou
 *  o teto de 500 linhas por arquivo (gate code-style-baseline). */
export function Stat({
  label,
  value,
  sublabel,
  tone = "neutral",
}: {
  label: ReactNode;
  value: ReactNode;
  sublabel?: ReactNode;
  tone?: "neutral" | "positive" | "warning";
}) {
  const toneClass =
    tone === "warning"
      ? "border-[var(--semantic-warning)]"
      : tone === "positive"
        ? "border-[var(--semantic-success)]"
        : "border-[var(--surface-border)]";
  return (
    <div
      className={`rounded-[var(--radius-card)] border ${toneClass} bg-[var(--surface-card)] p-4`}
    >
      <p className="text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
        {label}
      </p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
      {sublabel && (
        <div className="mt-1 text-xs text-[var(--surface-muted-foreground)]">
          {sublabel}
        </div>
      )}
    </div>
  );
}
