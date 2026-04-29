"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Lightbulb, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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

interface FilterBarProps {
  value: FilterValue;
  onChange: (v: FilterValue) => void;
}

function FilterBar({ value, onChange }: FilterBarProps) {
  return (
    <div
      role="tablist"
      aria-label="Filtrar sugestões"
      className="flex flex-wrap gap-1.5 text-xs"
    >
      {FILTER_TABS.map((tab) => (
        <button
          key={tab.value}
          role="tab"
          aria-selected={value === tab.value}
          onClick={() => onChange(tab.value)}
          className={[
            "rounded-full border px-3 py-1 transition-colors",
            value === tab.value
              ? "border-foreground bg-foreground text-background"
              : "border-border hover:border-muted-foreground/50",
          ].join(" ")}
        >
          {tab.label}
        </button>
      ))}
    </div>
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
  return (
    <div className="flex flex-col gap-3">
      {suggestions.map((s) => (
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
      <CardContent className="py-12">
        <div className="mx-auto max-w-md text-center">
          <Lightbulb className="mx-auto mb-4 h-10 w-10 text-muted-foreground/50" />
          <h2 className="font-heading text-lg font-semibold">
            {isPendente
              ? "Sem sugestões pendentes"
              : "Nenhuma sugestão neste filtro"}
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            {isPendente
              ? "Após cada relatório, sugestões acionáveis aparecerão aqui para você aceitar, modificar ou descartar — viram decisões ligadas à origem no relatório."
              : "Mude o filtro acima para ver sugestões em outros estados."}
          </p>
          {isPendente && (
            <Button
              variant="outline"
              size="sm"
              className="mt-6"
              nativeButton={false}
              render={<Link href="/acao/sugestoes" />}
            >
              <Sparkles className="mr-1.5 h-3.5 w-3.5" />
              Ver sugestões de tarefas (LLM)
            </Button>
          )}
        </div>
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
