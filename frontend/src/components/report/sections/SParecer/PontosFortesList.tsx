"use client";

// ADR-199 Ato 5 §5b — Lista de pontos fortes (Free vê 3, Premium vê todos).
// Helper visual leve — componente irmão do `ParecerRisksTable`.

import { CircleCheck } from "lucide-react";

import type { PontoForte } from "@/lib/api";

interface PontosFortesListProps {
  pontos: PontoForte[];
  /** Teaser tier free: N>0 sinaliza UI "+N no Premium". */
  gatedCount?: number;
}

export function PontosFortesList({ pontos, gatedCount = 0 }: PontosFortesListProps) {
  if (pontos.length === 0 && gatedCount === 0) return null;

  return (
    <section
      aria-labelledby="parecer-pontos-fortes-title"
      data-testid="parecer-pontos-fortes"
    >
      <header className="mb-2 flex items-baseline justify-between gap-2">
        <h3
          id="parecer-pontos-fortes-title"
          className="font-heading text-lg font-semibold text-[var(--surface-foreground)]"
        >
          Pontos fortes
        </h3>
        {gatedCount > 0 && (
          <span className="text-xs text-[var(--surface-muted-foreground)]">
            +{gatedCount} no Premium
          </span>
        )}
      </header>
      <ul className="flex flex-col gap-2">
        {pontos.map((p, idx) => (
          <li
            key={`${p.titulo}-${idx}`}
            className="flex items-start gap-3 rounded-md border border-[var(--surface-border)] border-l-[3px] bg-[var(--surface-card)] px-4 py-3"
            style={{ borderLeftColor: "var(--semantic-gain)" }}
          >
            <CircleCheck
              className="mt-0.5 h-4 w-4 shrink-0 text-[var(--semantic-gain)]"
              aria-hidden="true"
            />
            <div className="flex-1">
              <p className="text-sm font-semibold text-[var(--surface-foreground)]">
                {p.titulo}
              </p>
              <p className="mt-1 text-xs text-[var(--surface-muted-foreground)]">
                {p.descricao}
              </p>
              {(p.tema_canonico || p.section_id) && (
                <p className="mt-1 text-[11px] text-[var(--surface-muted-foreground)]">
                  {p.section_id && <>§{p.section_id}</>}
                  {p.section_id && p.tema_canonico && <> · </>}
                  {p.tema_canonico}
                </p>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
