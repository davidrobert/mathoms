"use client";

// A7.2a · ADR-136 — Plano de Ação (Decisões editoriais).
// Renderização **read-only** das decisões em vigor. O relatório é um
// snapshot (ADR-149); ações editoriais (criar/editar/marcar como executada)
// vivem em /acao (ADR-152). Por isso a seção apenas lista decisões e
// expõe um link "Gerenciar Plano de Ação" para o módulo editorial.

import Link from "next/link";
import { ArrowRight } from "lucide-react";

import { ReportSection } from "../../ReportSection";
import { MonetaryValue } from "../../MonetaryValue";
import { useDecisions } from "@/hooks/useDecisions";
import type { Decision, DecisionStatus } from "@/lib/api";

// ADR-076 · design tokens — substitui Tailwind literal por mix dos tokens
// semânticos (color-mix gera fundo "soft" com 15% do token, texto sólido).
// O tint dá a cor do fundo; o TEXTO usa o par `-on-tint` do mesmo token, porque
// a cor base sobre o próprio tint de 15% reprova AA em 4 dos 5 status (Pendente
// dava 1,86:1 em light, Superseded 3,81:1 light e 4,40:1 dark). `brand-info` é
// o único que passa na base. Gate: dev/check_tint_contrast.py.
// Mapeamento (fundo → texto):
//   Pendente   → --semantic-alert            (laranja, aguardando ação)
//   Decidido   → --brand-info                (azul-teal, informativo)
//   Executado  → --semantic-gain             (verde, sucesso)
//   Descartado → --surface-muted-foreground  (slate, neutro)
//   Superseded → --brand-secondary           (azul desaturado, "histórico")
const STATUS_BADGE_CLASS: Record<DecisionStatus, string> = {
  Pendente:
    "bg-[color-mix(in_srgb,var(--semantic-alert)_15%,transparent)] text-[var(--semantic-alert-on-tint)]",
  Decidido:
    "bg-[color-mix(in_srgb,var(--brand-info)_15%,transparent)] text-[var(--brand-info)]",
  Executado:
    "bg-[color-mix(in_srgb,var(--semantic-gain)_15%,transparent)] text-[var(--semantic-gain-on-tint)]",
  Descartado:
    "bg-[color-mix(in_srgb,var(--surface-muted-foreground)_15%,transparent)] text-[var(--surface-muted-foreground-on-tint)]",
  Superseded:
    "bg-[color-mix(in_srgb,var(--brand-secondary)_15%,transparent)] text-[var(--brand-secondary-on-tint)]",
};

interface PlanoDeAcaoSectionProps {
  workspaceId: string | undefined;
}

/** F9 · A7.2a · ADR-136 — Tabela read-only do Plano de Ação. */
export function PlanoDeAcaoSection({ workspaceId }: PlanoDeAcaoSectionProps) {
  const { decisions, loading, error } = useDecisions(workspaceId);

  return (
    <ReportSection id="plano_de_acao" title="Plano de Ação">
      <div className="md:col-span-2 flex flex-col gap-4">
        <ManageInAcaoLink />
        {error ? (
          // Erro de fetch: copy explícita pra não confundir com "vazio"
          // (lição do review do financial-planner — Cerbasi: cliente
          // não pode confundir "plano em dia" com "falha de carga").
          <p className="text-sm text-[var(--semantic-danger)]">
            Não foi possível carregar — atualize a página.
          </p>
        ) : loading ? (
          <p className="text-sm text-[var(--surface-muted-foreground)]">Carregando…</p>
        ) : (
          <DecisionTable rows={decisions} />
        )}
      </div>
    </ReportSection>
  );
}

/** Link discreto para o módulo editorial (/acao). No PDF degrada para
 *  texto simples — aceitável: o relatório é leitura por design. */
function ManageInAcaoLink() {
  return (
    <div className="flex justify-end">
      <Link
        href="/acao"
        className="inline-flex items-center gap-1 text-xs font-medium text-foreground hover:underline"
      >
        Gerenciar Plano de Ação
        <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
      </Link>
    </div>
  );
}

interface DecisionTableProps {
  rows: Decision[];
}

function DecisionTable({ rows }: DecisionTableProps) {
  if (rows.length === 0) {
    return (
      // Empty state pedagógico (Cerbasi): aponta para o próximo passo do
      // ciclo em vez de só relatar ausência ("Nenhuma decisão registrada").
      <p className="text-sm text-[var(--surface-muted-foreground)]">
        Nenhuma decisão pendente neste ciclo. Revise no próximo fechamento.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase text-[var(--surface-muted-foreground)]">
            <th scope="col" className="py-2 pr-4">Code</th>
            <th scope="col" className="py-2 pr-4">Título</th>
            <th scope="col" className="py-2 pr-4">Valor</th>
            <th scope="col" className="py-2 pr-4">Status</th>
            <th scope="col" className="py-2 pr-4">Supersede</th>
            <th scope="col" className="py-2 pr-4">Decidida</th>
            <th scope="col" className="py-2 pr-4">Executada</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((d) => (
            <DecisionRow key={d.id} decision={d} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface DecisionRowProps {
  decision: Decision;
}

function DecisionRow({ decision }: DecisionRowProps) {
  const amount = decision.amount_brl !== null ? Number(decision.amount_brl) : null;
  return (
    <tr className="border-t border-[var(--surface-border)]">
      <td className="py-2 pr-4 font-mono text-xs">{decision.code}</td>
      <td className="py-2 pr-4">{decision.title}</td>
      <td className="py-2 pr-4">
        <MonetaryValue value={amount} hideSymbol={false} />
      </td>
      <td className="py-2 pr-4">
        <StatusBadge status={decision.status} />
      </td>
      <td className="py-2 pr-4 text-xs text-[var(--surface-muted-foreground)]">
        {decision.supersedes_id ? "supersedes" : "—"}
      </td>
      <td className="py-2 pr-4 text-xs">{decision.decided_at ?? "—"}</td>
      <td className="py-2 pr-4 text-xs">{decision.executed_at ?? "—"}</td>
    </tr>
  );
}

interface StatusBadgeProps {
  status: DecisionStatus;
}

function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span
      className={[
        "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
        STATUS_BADGE_CLASS[status],
      ].join(" ")}
    >
      {status}
    </span>
  );
}
