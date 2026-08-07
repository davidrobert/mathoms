"use client";

// ADR-199 Ato 5 §5b — Hero diagnóstico do parecer.
// Variant "highlight" (full width). Cita data da geração + tier badge.
// Sem cor literal — usa tokens semânticos (--surface-*, --brand-*).

import type { ParecerContentMeta } from "@/lib/api";

import { ParecerRetencaoParcialNota } from "./ParecerRetencaoNota";

interface ParecerHeroDiagnosticoProps {
  diagnostico: string;
  meta: ParecerContentMeta;
  /** A40.l22 — itens retidos na conferência (0 = parecer íntegro). */
  itensRetidos?: number;
}

function formatGeneratedAt(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  const day = String(d.getDate()).padStart(2, "0");
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const year = d.getFullYear();
  return `${day}/${month}/${year}`;
}

export function ParecerHeroDiagnostico({
  diagnostico,
  meta,
  itensRetidos = 0,
}: ParecerHeroDiagnosticoProps) {
  const isPremium = meta.tier_at_generation === "premium";
  return (
    <article
      className="md:col-span-2 rounded-[var(--radius-card)] border border-[var(--surface-border)] p-6"
      style={{
        backgroundColor:
          "color-mix(in srgb, var(--brand-accent) 4%, var(--surface-card))",
        borderLeft: "4px solid var(--brand-accent)",
      }}
      aria-labelledby="parecer-hero-title"
      data-testid="parecer-hero"
    >
      <header className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <h3
          id="parecer-hero-title"
          className="font-heading text-xl font-semibold text-[var(--surface-foreground)]"
        >
          Diagnóstico geral
        </h3>
        <div className="flex items-center gap-2 text-xs">
          <span
            className="inline-flex items-center rounded-full px-2 py-0.5 font-medium"
            style={{
              backgroundColor: isPremium
                ? "color-mix(in srgb, var(--brand-accent) 12%, transparent)"
                : "color-mix(in srgb, var(--brand-neutral) 12%, transparent)",
              color: isPremium ? "var(--brand-accent)" : "var(--surface-muted-foreground)",
            }}
            data-testid="parecer-tier-badge"
          >
            {isPremium ? "Premium" : "Amostra"}
          </span>
          <span className="text-[var(--surface-muted-foreground)]">
            Snapshot · {formatGeneratedAt(meta.generated_at)}
          </span>
        </div>
      </header>
      <ParecerRetencaoParcialNota count={itensRetidos} />
      <p
        className="font-body text-base leading-relaxed text-[var(--surface-foreground)]"
        data-testid="parecer-diagnostico-body"
      >
        {diagnostico}
      </p>
    </article>
  );
}
