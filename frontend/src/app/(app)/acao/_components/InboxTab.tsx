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
  type SuggestionDisplayPartition,
} from "@/lib/suggestionOrdering";

import { SuggestionCard, type SuggestionCardDensity } from "./SuggestionCard";

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
 * F5 (PLAN-suggestion-lifecycle) — o cap virou grupos nomeados: "Decidir
 * agora" (3) · "Nesta rodada" (resto do cap) · disclosures para overflow,
 * agendadas (horizonte tático/estratégico, ADR-376 §D4) e informativas.
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

/** Inbox ativo (Pendente): grupos nomeados no lugar da lista plana.
 *
 * F5 (PLAN-suggestion-lifecycle) — o dogfood 2026-08-11 mostrou 15
 * pendentes, das quais 11 acionáveis: o cap de 12 nunca mordeu e a
 * ordenação metodológica, correta, ficou invisível — 11 cards de mesmo
 * peso, ~2,5 viewports, 33 CTAs competindo. Ordenar só prioriza se algo
 * separa o topo; daí "Decidir agora" (3) e "Nesta rodada" (o resto do
 * cap). Táticas/estratégicas saem para "Agendadas" e não disputam o
 * agora — o horizonte é do ADR-376 §D4. */
function PendingInboxList({ suggestions, onAccept, onModify, onDismiss }: InboxBodyProps) {
  const groups = partitionForDisplay(suggestions);
  const handlers = { onAccept, onModify, onDismiss };
  return (
    <div className="flex flex-col gap-4">
      <NamedGroup title="Decidir agora" items={groups.focus} density="full" handlers={handlers} />
      <NamedGroup title="Nesta rodada" items={groups.rest} density="compact" handlers={handlers} />
      <CollapsedGroups groups={groups} handlers={handlers} />
    </div>
  );
}

type InboxHandlers = {
  onAccept: InboxBodyProps["onAccept"];
  onModify: InboxBodyProps["onModify"];
  onDismiss: InboxBodyProps["onDismiss"];
};

interface NamedGroupProps {
  title: string;
  items: Suggestion[];
  density: SuggestionCardDensity;
  handlers: InboxHandlers;
}

/** Grupo aberto com header contado. Vazio ⇒ não renderiza — header de
 *  grupo sem itens sugere que algo sumiu. */
function NamedGroup({ title, items, density, handlers }: NamedGroupProps) {
  if (items.length === 0) return null;
  return (
    <section className="flex flex-col gap-3" data-group={title}>
      <h2 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
        {title} ({items.length})
      </h2>
      {items.map((s) => (
        <SuggestionCard key={s.id} suggestion={s} density={density} {...handlers} />
      ))}
    </section>
  );
}

function CollapsedGroups({
  groups,
  handlers,
}: {
  groups: SuggestionDisplayPartition;
  handlers: InboxHandlers;
}) {
  return (
    <>
      <CollapsedGroup
        id="inbox-overflow-acionaveis"
        label={overflowLabel(groups.overflow.length)}
        suggestions={groups.overflow}
        handlers={handlers}
      />
      <CollapsedGroup
        id="inbox-agendadas"
        label={scheduledLabel(groups.scheduled.length)}
        ariaLabel="Sugestões agendadas — táticas e estratégicas"
        note="Horizonte de meses a anos: ficam fora da fila do agora de propósito, para não competir com o que se decide nesta rodada."
        suggestions={groups.scheduled}
        handlers={handlers}
      />
      <CollapsedGroup
        id="inbox-informativas"
        label={informativeLabel(groups.informative.length)}
        ariaLabel="Sugestões informativas"
        suggestions={groups.informative}
        handlers={handlers}
      />
    </>
  );
}

function overflowLabel(n: number): string {
  return n === 1 ? "Mais 1 sugestão acionável" : `Mais ${n} sugestões acionáveis`;
}

function scheduledLabel(n: number): string {
  return n === 1
    ? "Agendada — tática ou estratégica (1)"
    : `Agendadas — táticas e estratégicas (${n})`;
}

function informativeLabel(n: number): string {
  return n === 1 ? "1 informativa" : `${n} informativas`;
}

interface CollapsedGroupProps {
  id: string;
  label: string;
  ariaLabel?: string;
  /** Microcopy sob o toggle — visível fechado, explica por que o grupo existe. */
  note?: string;
  suggestions: Suggestion[];
  handlers: InboxHandlers;
}

function CollapsedGroup({ id, label, ariaLabel, note, suggestions, handlers }: CollapsedGroupProps) {
  const [expanded, setExpanded] = useState(false);
  if (suggestions.length === 0) return null;
  return (
    <div className="flex flex-col gap-2 border-t border-border pt-3">
      <DisclosureToggle
        controlsId={id}
        expanded={expanded}
        onToggle={() => setExpanded((v) => !v)}
        label={label}
      />
      {note && <p className="text-[11px] text-muted-foreground">{note}</p>}
      <CollapsedGroupPanel
        id={id}
        ariaLabel={ariaLabel ?? label}
        expanded={expanded}
        suggestions={suggestions}
        handlers={handlers}
      />
    </div>
  );
}

function CollapsedGroupPanel({
  id,
  ariaLabel,
  expanded,
  suggestions,
  handlers,
}: {
  id: string;
  ariaLabel: string;
  expanded: boolean;
  suggestions: Suggestion[];
  handlers: InboxHandlers;
}) {
  return (
    <div id={id} role="region" aria-label={ariaLabel} hidden={!expanded}>
      <div className="flex flex-col gap-3">
        {suggestions.map((s) => (
          <SuggestionCard key={s.id} suggestion={s} density="compact" {...handlers} />
        ))}
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
