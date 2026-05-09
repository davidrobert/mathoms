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

const STATUS_BADGE_CLASS: Record<DecisionStatus, string> = {
  Pendente: "bg-amber-100 text-amber-900 dark:bg-amber-900/30 dark:text-amber-200",
  Decidido: "bg-sky-100 text-sky-900 dark:bg-sky-900/30 dark:text-sky-200",
  Executado: "bg-emerald-100 text-emerald-900 dark:bg-emerald-900/30 dark:text-emerald-200",
  Descartado: "bg-zinc-200 text-zinc-700 dark:bg-zinc-700/50 dark:text-zinc-200",
  Superseded: "bg-violet-100 text-violet-900 dark:bg-violet-900/30 dark:text-violet-200",
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
        {error && (
          <p className="text-sm text-[var(--semantic-danger)]">{error}</p>
        )}
        {loading ? (
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
      <p className="text-sm text-[var(--surface-muted-foreground)]">
        Nenhuma decisão registrada.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase text-[var(--surface-muted-foreground)]">
            <th className="py-2 pr-4">Code</th>
            <th className="py-2 pr-4">Título</th>
            <th className="py-2 pr-4">Valor</th>
            <th className="py-2 pr-4">Status</th>
            <th className="py-2 pr-4">Supersede</th>
            <th className="py-2 pr-4">Decidida</th>
            <th className="py-2 pr-4">Executada</th>
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
