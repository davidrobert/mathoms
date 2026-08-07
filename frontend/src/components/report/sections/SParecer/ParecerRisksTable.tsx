"use client";

// ADR-199 Ato 5 §5b — Tabela densa de riscos (top-5 visível + expand).
// `<details>` HTML nativo para "ver baixa severidade"; React state só para
// filtros (não usados no MVP). Print CSS força `[open]` para PDF.

import { AlertOctagon, AlertTriangle, Info } from "lucide-react";

import { ParecerAncoraChips } from "./ParecerAncoraChips";
import { frasePecasRetidas } from "@/lib/parecerRetencaoCopy";
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
  /** A40.l22 — itens retidos na conferência, escalar do parecer inteiro.
   *  Contador ortogonal ao `gatedCount`: retido = qualidade (ação
   *  reprocessar), gated = comercial (ação comprar). Somá-los apagaria a
   *  diferença de ação. */
  retidosCount?: number;
}

function sortBySeveridade(riscos: Risco[]): Risco[] {
  return [...riscos].sort(
    (a, b) => SEVERIDADE_RANK[a.severidade] - SEVERIDADE_RANK[b.severidade],
  );
}

export function ParecerRisksTable({
  riscos,
  gatedCount = 0,
  retidosCount = 0,
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
      {/* `<md` empilha: com 3 contadores a caption não cabe ao lado do h3. */}
      <header className="mb-2 flex flex-col gap-1 md:flex-row md:items-baseline md:justify-between md:gap-2">
        <h3
          id="parecer-risks-title"
          className="font-heading text-lg font-semibold text-[var(--surface-foreground)]"
        >
          Riscos identificados
        </h3>
        <RisksCaption
          visible={visible.length}
          total={riscos.length}
          gatedCount={gatedCount}
          retidosCount={retidosCount}
        />
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

/** Caption dos 3 contadores.
 *
 * Cada contador em `<span>` próprio com `flex-wrap`, e o `·` separado e
 * `aria-hidden`: a 12px o leitor lê posicionalmente ("5, 7, 2" ⇒ 5+2=7), então
 * o substantivo de cada contador é o que separa "riscos" de "itens do parecer".
 * Quebrar no meio de "itens do parecer retidos" reintroduziria a ambiguidade.
 */
function RisksCaption({
  visible,
  total,
  gatedCount,
  retidosCount,
}: {
  visible: number;
  total: number;
  gatedCount: number;
  retidosCount: number;
}) {
  return (
    <span
      className="flex flex-wrap gap-x-2 text-xs text-[var(--surface-muted-foreground)]"
      data-testid="parecer-risks-caption"
    >
      <span className="whitespace-nowrap">
        Mostrando {visible} de {total} {total === 1 ? "risco" : "riscos"}
      </span>
      {retidosCount > 0 && (
        <>
          <span aria-hidden="true">·</span>
          <span data-testid="parecer-risks-caption-retidos">
            {frasePecasRetidas(retidosCount)}
          </span>
        </>
      )}
      {gatedCount > 0 && (
        <>
          <span aria-hidden="true">·</span>
          <span className="whitespace-nowrap">+{gatedCount} no Premium</span>
        </>
      )}
    </span>
  );
}

function RiscoRow({ risco }: { risco: Risco }) {
  const tone = SEVERIDADE_TONE[risco.severidade];
  const Icon = tone.Icon;
  // `role="article"` no `<li>` quebrava a estrutura da lista (axe `list`,
  // serious): a `<ul>` passava a ter filho que não é `listitem`. O
  // `aria-label` que ele carregava era redundante — severidade e título já
  // são texto dentro do item. Medido ao dar cobertura axe a `ParecerBody`
  // pela primeira vez (A40.l22): a seção só era escaneada no estado empty.
  return (
    <li
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
