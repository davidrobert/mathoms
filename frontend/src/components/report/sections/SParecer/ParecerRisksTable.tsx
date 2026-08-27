"use client";

// ADR-199 Ato 5 §5b — Tabela densa de riscos (top-5 visível + expand).
// A40.l88 (U1 · RR5-04): o expand é estado React, não `<details>`. O print CSS
// que "forçava [open]" declarava uma custom property que ninguém lê — o PDF
// escondia o summary e NÃO expandia, então saía com 5 linhas de 12 e sem aviso
// nenhum. Estado em elemento comum é o que `@media print` consegue sobrepor.

import { useState } from "react";

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

// `token` pinta ícone, `border-left` e tint — todos decorativos (o ícone é
// `aria-hidden` e a severidade também é texto), onde 3:1 basta. `textToken` é o
// RÓTULO, que precisa de 4,5:1 a 10px. Só Média divergia: `--semantic-alert`
// sobre o próprio tint dá 1,97 em light (medido por axe ao dar cobertura a
// `ParecerBody` — A40.l22). Crítica/Alta 5,84 e Baixa 5,25 já passavam, e
// mantêm `textToken = token` para a triagem por cor continuar de pé.
const SEVERIDADE_TONE: Record<
  Severidade,
  { token: string; textToken: string; Icon: typeof Info; label: string }
> = {
  Crítica: {
    token: "var(--semantic-loss)",
    textToken: "var(--semantic-loss)",
    Icon: AlertOctagon,
    label: "Crítica",
  },
  Alta: {
    token: "var(--semantic-loss)",
    textToken: "var(--semantic-loss)",
    Icon: AlertOctagon,
    label: "Alta",
  },
  Média: {
    token: "var(--semantic-alert)",
    textToken: "var(--report-alert-warning-text)",
    Icon: AlertTriangle,
    label: "Média",
  },
  Baixa: {
    token: "var(--semantic-info-financial)",
    textToken: "var(--semantic-info-financial)",
    Icon: Info,
    label: "Baixa",
  },
};

const TOP_LIMIT = 5;

/** Partição visível/colapsado — Crítica e Alta nunca colapsam. */
// `slice(TOP_LIMIT)` era cego à severidade: com 6 riscos Críticos, o 6º ia
// para trás de um `<summary>` que dizia "de baixa severidade" (A40.l7 · RV3-15).
function partitionBySeveridade(riscos: Risco[]): {
  visible: Risco[];
  extra: Risco[];
} {
  const sorted = sortBySeveridade(riscos);
  const nuncaColapsa = sorted.filter(
    (r) => SEVERIDADE_RANK[r.severidade] <= 1,
  ).length;
  const corte = Math.max(TOP_LIMIT, nuncaColapsa);
  return { visible: sorted.slice(0, corte), extra: sorted.slice(corte) };
}

/** Rótulo do disclosure, derivado da composição real do conjunto colapsado. */
function fraseSeveridadesOcultas(extra: Risco[]): string {
  const rotulos = [
    ...new Set(sortBySeveridade(extra).map((r) => r.severidade)),
  ].map((s) => s.toLowerCase());
  const lista =
    rotulos.length > 1
      ? `${rotulos.slice(0, -1).join(", ")} e ${rotulos[rotulos.length - 1]}`
      : rotulos[0];
  const plural = extra.length > 1 ? "riscos" : "risco";
  return `Ver mais ${extra.length} ${plural} de severidade ${lista}`;
}

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
  const [expandido, setExpandido] = useState(false);
  if (riscos.length === 0 && gatedCount === 0) return null;

  const { visible, extra } = partitionBySeveridade(riscos);
  const ocultosNaTela = expandido ? 0 : extra.length;

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
          total={riscos.length}
          ocultosNaTela={ocultosNaTela}
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
        <RiscosColapsados
          extra={extra}
          expandido={expandido}
          onToggle={() => setExpandido((aberto) => !aberto)}
        />
      )}
    </section>
  );
}

/** Disclosure dos riscos que a tela colapsa.
 *
 * O colapso é `hidden print:flex` — classe, nunca o atributo `hidden` nem um
 * `<details>` fechado. Os dois são `display:none !important` na folha da UA, e
 * `!important` de UA vence `!important` de autor: nenhum `@media print` os
 * revela. Medido sob `emulateMedia({media:"print"})`, que reprovou a primeira
 * tentativa desta lane (com o atributo) nos três engines.
 *
 * A linha fica montada no DOM de propósito: desmontar no colapso deixaria o
 * print sem o que revelar.
 */
function RiscosColapsados({
  extra,
  expandido,
  onToggle,
}: {
  extra: Risco[];
  expandido: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <button
        type="button"
        className="parecer-risks-toggle mt-3 cursor-pointer text-xs font-medium text-[var(--brand-accent)] hover:underline"
        aria-expanded={expandido}
        aria-controls="parecer-risks-extra"
        onClick={onToggle}
      >
        {expandido
          ? "Ocultar os riscos adicionais"
          : fraseSeveridadesOcultas(extra)}
      </button>
      <ul
        id="parecer-risks-extra"
        className={`parecer-risks-extra mt-2 flex-col gap-2 ${
          expandido ? "flex" : "hidden print:flex"
        }`}
        data-testid="parecer-risks-extra"
      >
        {extra.map((r, idx) => (
          <RiscoRow key={`extra-${r.section_id}-${idx}`} risco={r} />
        ))}
      </ul>
    </>
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
  total,
  ocultosNaTela,
  gatedCount,
  retidosCount,
}: {
  total: number;
  ocultosNaTela: number;
  gatedCount: number;
  retidosCount: number;
}) {
  return (
    <span
      className="flex flex-wrap gap-x-2 text-xs text-[var(--surface-muted-foreground)]"
      data-testid="parecer-risks-caption"
    >
      {/* "Mostrando N de" só existe enquanto a lista está partida NA TELA — o
          print revela as linhas ocultas, então o prefixo sai do PDF pela regra
          `.parecer-print-only-screen`. É a mesma afirmação medida nas duas
          superfícies, não uma legenda escolhida por crença sobre a outra. */}
      <span className="whitespace-nowrap">
        {ocultosNaTela > 0 && (
          <span className="parecer-print-only-screen">
            Mostrando {total - ocultosNaTela} de{" "}
          </span>
        )}
        {total} {total === 1 ? "risco" : "riscos"}
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
            style={{ color: tone.textToken }}
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
