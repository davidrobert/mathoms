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

/** [[ADR-418]] §D3 — nomeia o que a meta financia e o que foi descontado dela.
 *  Sem isso o card publica "Meta IF" sem dizer de que base o gap e o progresso saíram,
 *  e sem dizer qual renda mensal aquele patrimônio sustenta (A40.l91 §Escopo 3). */
export function MetaIfSublabel({
  alvoMensal,
  rendaForaMensal,
  formatCurrency,
}: {
  alvoMensal?: number;
  rendaForaMensal?: number;
  formatCurrency: (v: number) => string;
}) {
  if (typeof alvoMensal !== "number") return null;
  return (
    <>
      <span className="block">
        financia {formatCurrency(alvoMensal)}/mês — a renda-alvo declarada
      </span>
      {typeof rendaForaMensal === "number" && rendaForaMensal > 0 && (
        <span className="block">
          já descontados {formatCurrency(rendaForaMensal)}/mês de bens fora
          desta carteira
        </span>
      )}
    </>
  );
}
