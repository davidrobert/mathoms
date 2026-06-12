"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Lightbulb, X } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { DisclosureToggle } from "@/components/ui/DisclosureToggle";
import { EmptyState } from "@/components/ui/EmptyState";
import { SegmentedTabs } from "@/components/ui/SegmentedTabs";
import { useSuggestions } from "@/hooks/useSuggestions";
import type { Suggestion, SuggestionAggregateStatus } from "@/lib/api";
import {
  partitionForDisplay,
  suggestionPriorityComparator,
} from "@/lib/suggestionOrdering";

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
 * ADR-290 F3 — hierarquia de display: ordering metodológico compartilhado
 * (`suggestionOrdering.ts`), cap de 12 acionáveis em destaque (excedente em
 * disclosure compacta, nunca escondido — KR5), `info` colapsada por default
 * e fora do cap. Deep-link `/acao?tab=inbox&section=S3` pré-filtra por seção
 * (cards inline do relatório).
 *
 * ADR-214 — `nextDecisionCode` removido do prop drilling; server gera
 * o code da Decision na transação do aceite e expõe via
 * `accepted_decision_code` no response (toast educa).
 */
export function InboxTab({ workspaceId }: InboxTabProps) {
  const [filter, setFilter] = useState<FilterValue>("Pendente");
  const searchParams = useSearchParams();
  const [sectionFilter, setSectionFilter] = useState<string | null>(
    () => searchParams?.get("section") ?? null,
  );
  const status =
    filter === "Todas" ? undefined : (filter as SuggestionAggregateStatus);

  const { suggestions, loading, error, accept, modify, dismiss } = useSuggestions(
    workspaceId,
    status,
  );
  const visible = sectionFilter
    ? suggestions.filter((s) => s.section_id === sectionFilter)
    : suggestions;

  return (
    <div className="flex flex-col gap-4">
      <FilterBar value={filter} onChange={setFilter} />
      {sectionFilter && (
        <SectionFilterChip
          section={sectionFilter}
          onClear={() => setSectionFilter(null)}
        />
      )}
      <InboxBody
        loading={loading}
        error={error}
        filter={filter}
        suggestions={visible}
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

function SectionFilterChip({
  section,
  onClear,
}: {
  section: string;
  onClear: () => void;
}) {
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <span>
        Filtrando pela seção <span className="font-medium">§{section}</span>
      </span>
      <button
        type="button"
        onClick={onClear}
        aria-label={`Remover filtro da seção ${section}`}
        className="inline-flex items-center gap-1 rounded border border-border px-1.5 py-0.5 hover:text-foreground"
      >
        <X className="h-3 w-3" aria-hidden="true" />
        limpar
      </button>
    </div>
  );
}

interface InboxBodyProps {
  loading: boolean;
  error: string;
  filter: FilterValue;
  suggestions: Suggestion[];
  onAccept: ReturnType<typeof useSuggestions>["accept"];
  onModify: ReturnType<typeof useSuggestions>["modify"];
  onDismiss: ReturnType<typeof useSuggestions>["dismiss"];
}

function InboxBody(props: InboxBodyProps) {
  const { loading, error, filter, suggestions } = props;
  if (loading) {
    return <InboxNotice text="Carregando sugestões…" />;
  }
  if (error) {
    return <InboxNotice text={error} destructive />;
  }
  if (suggestions.length === 0) {
    return <InboxEmpty filter={filter} />;
  }
  if (filter === "Pendente") {
    return <PendingInboxList {...props} />;
  }
  return <FlatInboxList {...props} />;
}

function InboxNotice({ text, destructive }: { text: string; destructive?: boolean }) {
  return (
    <Card>
      <CardContent
        className={`py-8 text-center text-sm ${destructive ? "text-destructive" : "text-muted-foreground"}`}
      >
        {text}
      </CardContent>
    </Card>
  );
}

/** Filtros terminais (Aceita/Descartada/…): lista única no ordering canônico. */
function FlatInboxList({ suggestions, onAccept, onModify, onDismiss }: InboxBodyProps) {
  const sorted = [...suggestions].sort(suggestionPriorityComparator);
  return (
    <div className="flex flex-col gap-3">
      {sorted.map((s) => (
        <SuggestionCard
          key={s.id}
          suggestion={s}
          onAccept={onAccept}
          onModify={onModify}
          onDismiss={onDismiss}
        />
      ))}
    </div>
  );
}

/** Inbox ativo (Pendente): ≤12 acionáveis em destaque + overflow e `info`
 *  atrás de disclosures (ADR-290 F3). */
function PendingInboxList({ suggestions, onAccept, onModify, onDismiss }: InboxBodyProps) {
  const { primary, overflow, informative } = partitionForDisplay(suggestions);
  const handlers = { onAccept, onModify, onDismiss };
  return (
    <div className="flex flex-col gap-3">
      {primary.map((s) => (
        <SuggestionCard key={s.id} suggestion={s} {...handlers} />
      ))}
      {overflow.length > 0 && (
        <CollapsedGroup
          id="inbox-overflow-acionaveis"
          label={overflowLabel(overflow.length)}
          suggestions={overflow}
          handlers={handlers}
        />
      )}
      {informative.length > 0 && (
        <CollapsedGroup
          id="inbox-informativas"
          label={informativeLabel(informative.length)}
          ariaLabel="Sugestões informativas"
          suggestions={informative}
          handlers={handlers}
        />
      )}
    </div>
  );
}

function overflowLabel(n: number): string {
  return n === 1 ? "Mais 1 sugestão acionável" : `Mais ${n} sugestões acionáveis`;
}

function informativeLabel(n: number): string {
  return n === 1 ? "1 informativa" : `${n} informativas`;
}

interface CollapsedGroupProps {
  id: string;
  label: string;
  ariaLabel?: string;
  suggestions: Suggestion[];
  handlers: {
    onAccept: InboxBodyProps["onAccept"];
    onModify: InboxBodyProps["onModify"];
    onDismiss: InboxBodyProps["onDismiss"];
  };
}

function CollapsedGroup({ id, label, ariaLabel, suggestions, handlers }: CollapsedGroupProps) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="flex flex-col gap-3 border-t border-border pt-3">
      <DisclosureToggle
        controlsId={id}
        expanded={expanded}
        onToggle={() => setExpanded((v) => !v)}
        label={label}
      />
      <div id={id} role="region" aria-label={ariaLabel ?? label} hidden={!expanded}>
        <div className="flex flex-col gap-3">
          {suggestions.map((s) => (
            <SuggestionCard key={s.id} suggestion={s} {...handlers} />
          ))}
        </div>
      </div>
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

// ADR-214 — `computeNextDecisionCode` deletado. Geração do `D{N}` agora
// é server-side via DecisionRepository.next_code (advisory lock per-workspace).
// ADR-290 F3 — `suggestionSortComparator` (severity → created_at) substituído
// pelo ordering metodológico compartilhado em `@/lib/suggestionOrdering`.
