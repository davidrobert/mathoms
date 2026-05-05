"use client";

import { useMemo, useState } from "react";
import { Lightbulb } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/EmptyState";
import { useDecisions } from "@/hooks/useDecisions";
import { useSuggestions } from "@/hooks/useSuggestions";
import type { Suggestion, SuggestionAggregateStatus } from "@/lib/api";

import { SuggestionCard } from "./SuggestionCard";

interface InboxTabProps {
  workspaceId: string;
}

const FILTER_TABS: ReadonlyArray<{ value: FilterValue; label: string }> = [
  { value: "Pendente", label: "Pendentes" },
  { value: "Aceita", label: "Aceitas" },
  { value: "Modificada", label: "Modificadas" },
  { value: "Descartada", label: "Descartadas" },
  { value: "Todas", label: "Todas" },
];

type FilterValue = SuggestionAggregateStatus | "Todas";

/** Direção E · Onda 5 · ADR-153 — Inbox de Suggestions em /acao.
 *
 * Sucesso: lista cards filtráveis com Aceitar/Modificar/Descartar.
 * Empty state ensinante quando não há sugestões pendentes — link para
 * fila legada de TaskSuggestion (E5.N) preservado em /acao/sugestoes.
 */
export function InboxTab({ workspaceId }: InboxTabProps) {
  const [filter, setFilter] = useState<FilterValue>("Pendente");
  const status =
    filter === "Todas" ? undefined : (filter as SuggestionAggregateStatus);

  const { suggestions, loading, error, accept, modify, dismiss } = useSuggestions(
    workspaceId,
    status,
  );
  const { decisions } = useDecisions(workspaceId);
  const nextDecisionCode = useMemo(
    () => computeNextDecisionCode(decisions.map((d) => d.code)),
    [decisions],
  );

  return (
    <div className="flex flex-col gap-4">
      <FilterBar value={filter} onChange={setFilter} />
      <InboxBody
        loading={loading}
        error={error}
        filter={filter}
        suggestions={suggestions}
        nextDecisionCode={nextDecisionCode}
        onAccept={accept}
        onModify={modify}
        onDismiss={dismiss}
      />
    </div>
  );
}

function FilterBar({ value, onChange }: { value: FilterValue; onChange: (v: FilterValue) => void }) {
  return (
    <SegmentedTabs
      value={value}
      onChange={onChange}
      options={FILTER_TABS}
      ariaLabel="Filtrar sugestões"
    />
  );
}

interface InboxBodyProps {
  loading: boolean;
  error: string;
  filter: FilterValue;
  suggestions: Suggestion[];
  nextDecisionCode: string;
  onAccept: ReturnType<typeof useSuggestions>["accept"];
  onModify: ReturnType<typeof useSuggestions>["modify"];
  onDismiss: ReturnType<typeof useSuggestions>["dismiss"];
}

function InboxBody({
  loading,
  error,
  filter,
  suggestions,
  nextDecisionCode,
  onAccept,
  onModify,
  onDismiss,
}: InboxBodyProps) {
  if (loading) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-sm text-muted-foreground">
          Carregando sugestões…
        </CardContent>
      </Card>
    );
  }
  if (error) {
    return (
      <Card>
        <CardContent className="py-8 text-center text-sm text-destructive">
          {error}
        </CardContent>
      </Card>
    );
  }
  if (suggestions.length === 0) {
    return <InboxEmpty filter={filter} />;
  }
  // ADR-161 (Onda 8 #4) — sort por severidade desc, depois created_at desc.
  // Cards `danger` aparecem primeiro; entre mesma severidade, mais recente
  // primeiro. Estável: mesmo input → mesma ordem.
  const sorted = [...suggestions].sort(suggestionSortComparator);
  return (
    <div className="flex flex-col gap-3">
      {sorted.map((s) => (
        <SuggestionCard
          key={s.id}
          suggestion={s}
          nextDecisionCode={nextDecisionCode}
          onAccept={onAccept}
          onModify={onModify}
          onDismiss={onDismiss}
        />
      ))}
    </div>
  );
}

function InboxEmpty({ filter }: { filter: FilterValue }) {
  const isPendente = filter === "Pendente";
  return (
    <Card>
      <CardContent className="py-0">
        <EmptyState
          icon={Lightbulb}
          title={isPendente ? "Sem sugestões pendentes" : "Nenhuma sugestão neste filtro"}
          description={
            isPendente
              ? "Após cada relatório, sugestões acionáveis aparecerão aqui para você aceitar, modificar ou descartar — viram decisões ligadas à origem no relatório."
              : "Mude o filtro acima para ver sugestões em outros estados."
          }
          layout="card"
          ctas={
            isPendente
              ? [{ label: "Ver sugestões de tarefas (LLM)", href: "/acao/sugestoes", variant: "secondary" }]
              : undefined
          }
        />
      </CardContent>
    </Card>
  );
}

/** Próximo código `D{N+1}` baseado nos códigos existentes ("D01" → 1). */
export function computeNextDecisionCode(existing: ReadonlyArray<string>): string {
  const numbers = existing
    .map((c) => parseInt(c.replace(/^D/, ""), 10))
    .filter((n) => Number.isFinite(n));
  const next = (numbers.length === 0 ? 0 : Math.max(...numbers)) + 1;
  return `D${String(next).padStart(2, "0")}`;
}

const SEVERITY_RANK: Record<string, number> = { danger: 3, warning: 2, info: 1 };

/** ADR-161 (Onda 8 #4) — comparator estável: severity desc → created_at desc. */
export function suggestionSortComparator(a: Suggestion, b: Suggestion): number {
  const sa = SEVERITY_RANK[a.severity] ?? 0;
  const sb = SEVERITY_RANK[b.severity] ?? 0;
  if (sa !== sb) return sb - sa;
  return (b.created_at ?? "").localeCompare(a.created_at ?? "");
}
