"use client";

// ADR-199 Ato 5 §5b — Lista de movimentos por horizonte.
// 3 horizontes: execução (4 sem) · tático (3-12 mes) · estratégico (12+ mes).

import type { Sugestao } from "@/lib/api";

import { ParecerMovimentoCard } from "./ParecerMovimentoCard";

export type Horizonte = "execucao" | "tatico" | "estrategico";

const HORIZONTE_TITULO: Record<Horizonte, string> = {
  execucao: "Execução (4 semanas)",
  tatico: "Tático (3–12 meses)",
  estrategico: "Estratégico (12+ meses)",
};

const HORIZONTE_HELP: Record<Horizonte, string> = {
  execucao:
    "Movimentos urgentes — calendário próximo. Confirmar nesta janela.",
  tatico:
    "Ajustes do plano — revisão trimestral. Programa-se nos próximos meses.",
  estrategico:
    "Movimentos de longo prazo — revisão anual ou na próxima virada de ciclo.",
};

interface ParecerHorizonteListProps {
  horizon: Horizonte;
  sugestoes: Sugestao[];
  workspaceId: string;
  /** Teaser do tier free: N>0 sinaliza UI "destrave no Premium". */
  gatedCount?: number;
  /** Callback após mutação no aggregate Suggestion. */
  onMutate?: () => void | Promise<void>;
}

export function ParecerHorizonteList({
  horizon,
  sugestoes,
  workspaceId,
  gatedCount = 0,
  onMutate,
}: ParecerHorizonteListProps) {
  if (sugestoes.length === 0 && gatedCount === 0) {
    return null;
  }

  return (
    <section
      className="md:col-span-2"
      aria-labelledby={`horizonte-${horizon}-title`}
      data-testid={`parecer-horizonte-${horizon}`}
    >
      <header className="mb-2">
        <h3
          id={`horizonte-${horizon}-title`}
          className="font-heading text-lg font-semibold text-[var(--surface-foreground)]"
        >
          {HORIZONTE_TITULO[horizon]}
        </h3>
        <p className="text-xs text-[var(--surface-muted-foreground)]">
          {HORIZONTE_HELP[horizon]}
        </p>
      </header>

      {sugestoes.length === 0 && gatedCount > 0 ? (
        <FreeTeaserCard horizon={horizon} count={gatedCount} />
      ) : (
        <ul className="flex flex-col gap-3">
          {sugestoes.map((s) => (
            <li key={s.suggestion_dedup_key}>
              <ParecerMovimentoCard
                sugestao={s}
                workspaceId={workspaceId}
                onMutate={onMutate}
              />
            </li>
          ))}
        </ul>
      )}

      {sugestoes.length > 0 && gatedCount > 0 && (
        <p className="mt-2 text-xs text-[var(--surface-muted-foreground)]">
          +{gatedCount} movimento{gatedCount > 1 ? "s" : ""} no Premium
        </p>
      )}
    </section>
  );
}

function FreeTeaserCard({
  horizon,
  count,
}: {
  horizon: Horizonte;
  count: number;
}) {
  return (
    <div
      className="rounded-[var(--radius-card)] border border-dashed border-[var(--brand-accent)] p-4 text-center"
      style={{
        backgroundColor:
          "color-mix(in srgb, var(--brand-accent) 4%, var(--surface-card))",
      }}
      data-testid={`parecer-horizonte-teaser-${horizon}`}
    >
      <p className="font-heading text-sm font-semibold text-[var(--brand-accent)]">
        {count} movimento{count > 1 ? "s" : ""} no Premium
      </p>
      <p className="mt-1 text-xs text-[var(--surface-muted-foreground)]">
        Destrave o plano completo para receber recomendações priorizadas neste
        horizonte.
      </p>
    </div>
  );
}
