"use client";

// A40.l88 (U1 · RR5-01) — Ressalvas que o parecer emite sobre a própria análise.
// Ficam ANTES dos achados de propósito: no run medido, uma das notas declarava
// o diagnóstico patrimonial com confiança insuficiente e o produto entregava o
// diagnóstico sem ela. Ressalva que chega depois da conclusão já falhou.

import { CircleAlert } from "lucide-react";

import type { NotaMetodologica } from "@/lib/api";

interface ParecerNotasMetodologicasProps {
  notas: NotaMetodologica[];
  /** Tier free recebe `notas=0` do filtro do servidor; sem este contador o
   *  leitor free não saberia sequer que existem ressalvas. */
  gatedCount?: number;
}

export function ParecerNotasMetodologicas({
  notas,
  gatedCount = 0,
}: ParecerNotasMetodologicasProps) {
  if (notas.length === 0 && gatedCount === 0) return null;

  return (
    <section
      aria-labelledby="parecer-notas-title"
      data-testid="parecer-notas-metodologicas"
      className="rounded-md border border-[var(--surface-border)] bg-[var(--surface-muted)] px-4 py-3"
    >
      <header className="flex items-baseline justify-between gap-2">
        <h3
          id="parecer-notas-title"
          className="flex items-center gap-2 font-heading text-sm font-semibold text-[var(--surface-foreground)]"
        >
          <CircleAlert
            className="h-4 w-4 shrink-0 text-[var(--surface-muted-foreground)]"
            aria-hidden="true"
          />
          Ressalvas desta análise
        </h3>
        {gatedCount > 0 && (
          <span className="text-xs text-[var(--surface-muted-foreground)]">
            +{gatedCount} no Premium
          </span>
        )}
      </header>

      <ul className="mt-2 flex flex-col gap-2">
        {notas.map((nota, idx) => (
          <li key={`${nota.titulo}-${idx}`} data-testid="parecer-nota">
            <p className="text-xs font-semibold text-[var(--surface-foreground)]">
              {nota.titulo}
            </p>
            <p className="mt-0.5 text-xs text-[var(--surface-muted-foreground)]">
              {nota.conteudo}
            </p>
            {nota.temas_canonicos.length > 0 && (
              <p className="mt-0.5 text-[11px] text-[var(--surface-muted-foreground)]">
                {nota.temas_canonicos.join(" · ")}
              </p>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}
