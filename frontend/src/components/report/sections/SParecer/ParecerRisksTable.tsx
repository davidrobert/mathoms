"use client";

// ADR-199 Ato 5 §5b — Tabela densa de riscos (top-5 visível + expand).
// `<details>` HTML nativo para "ver baixa severidade"; React state só para
// filtros (não usados no MVP). Print CSS força `[open]` para PDF.

import { AlertOctagon, AlertTriangle, Info } from "lucide-react";

import { ParecerAncoraChips } from "./ParecerAncoraChips";
import type { Risco, Severidade } from "@/lib/api";

const SEVERIDADE_RANK: Record<Severidade, number> = {
  Crítica: 0,
  Alta: 1,
  Média: 2,
  Baixa: 3,
};

const SEVERIDADE_TONE: Record<
  Severidade,
  { token: string; Icon: typeof Info; label: string }
> = {
  Crítica: {
    token: "var(--semantic-loss)",
    Icon: AlertOctagon,
    label: "Crítica",
  },
  Alta: { token: "var(--semantic-loss)", Icon: AlertOctagon, label: "Alta" },
  Média: {
    token: "var(--semantic-alert)",
    Icon: AlertTriangle,
    label: "Média",
  },
  Baixa: {
    token: "var(--semantic-info-financial)",
    Icon: Info,
    label: "Baixa",
  },
};

const TOP_LIMIT = 5;

interface ParecerRisksTableProps {
  riscos: Risco[];
  /** Sinaliza teaser do tier free — exibido como caption "+N no Premium". */
  gatedCount?: number;
}

function sortBySeveridade(riscos: Risco[]): Risco[] {
  return [...riscos].sort(
    (a, b) => SEVERIDADE_RANK[a.severidade] - SEVERIDADE_RANK[b.severidade],
  );
}

export function ParecerRisksTable({
  riscos,
  gatedCount = 0,
}: ParecerRisksTableProps) {
  if (riscos.length === 0 && gatedCount === 0) return null;

  const sorted = sortBySeveridade(riscos);
  const visible = sorted.slice(0, TOP_LIMIT);
  const extra = sorted.slice(TOP_LIMIT);

  return (
    <section
      className="md:col-span-2"
      aria-labelledby="parecer-risks-title"
      data-testid="parecer-risks-table"
    >
      <header className="mb-2 flex items-baseline justify-between gap-2">
        <h3
          id="parecer-risks-title"
          className="font-heading text-lg font-semibold text-[var(--surface-foreground)]"
        >
          Riscos identificados
        </h3>
        <span className="text-xs text-[var(--surface-muted-foreground)]">
          Mostrando {visible.length} de {riscos.length}
          {gatedCount > 0 && ` · +${gatedCount} no Premium`}
        </span>
      </header>

      <ul className="flex flex-col gap-2">
        {visible.map((r, idx) => (
          <RiscoRow key={`${r.section_id}-${idx}`} risco={r} />
        ))}
      </ul>

      {extra.length > 0 && (
        <details className="mt-3 parecer-details">
          <summary className="cursor-pointer text-xs font-medium text-[var(--brand-accent)] hover:underline">
            Ver mais {extra.length} risco{extra.length > 1 ? "s" : ""} de baixa severidade
          </summary>
          <ul className="mt-2 flex flex-col gap-2">
            {extra.map((r, idx) => (
              <RiscoRow key={`extra-${r.section_id}-${idx}`} risco={r} />
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}

function RiscoRow({ risco }: { risco: Risco }) {
  const tone = SEVERIDADE_TONE[risco.severidade];
  const Icon = tone.Icon;
  return (
    <li
      role="article"
      aria-label={`Risco ${tone.label}: ${risco.titulo}`}
      className="flex items-start gap-3 rounded-md border border-[var(--surface-border)] border-l-[3px] px-4 py-3"
      style={{
        borderLeftColor: tone.token,
        backgroundColor: `color-mix(in oklab, ${tone.token} 6%, transparent)`,
      }}
    >
      <Icon
        className="mt-0.5 h-4 w-4 shrink-0"
        style={{ color: tone.token }}
        aria-hidden="true"
      />
      <div className="flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <p className="text-sm font-semibold text-[var(--surface-foreground)]">
            {risco.titulo}
          </p>
          <span
            className="shrink-0 text-[10px] font-medium uppercase tracking-wide"
            style={{ color: tone.token }}
          >
            {tone.label}
          </span>
        </div>
        <p className="mt-1 text-xs text-[var(--surface-muted-foreground)]">
          {risco.descricao}
        </p>
        <p className="mt-1 text-[11px] text-[var(--surface-muted-foreground)]">
          §{risco.section_id} · {risco.tema_canonico}
          {risco.confianca && ` · confiança ${risco.confianca}`}
        </p>
        <ParecerAncoraChips ancoras={risco.ancoras} />
      </div>
    </li>
  );
}
