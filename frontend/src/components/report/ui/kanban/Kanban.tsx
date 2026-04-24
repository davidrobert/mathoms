"use client";

import type { ReactNode } from "react";
import { PriorityBadge, type PriorityLevel } from "../badges/PriorityBadge";
import { DeadlineBadge } from "../badges/DeadlineBadge";

export type KanbanColumn = "a_fazer" | "em_andamento" | "concluido";

const COLUMN_LABEL: Record<KanbanColumn, string> = {
  a_fazer: "A fazer",
  em_andamento: "Em andamento",
  concluido: "Concluído",
};

export interface KanbanItem {
  readonly id: string;
  readonly titulo: string;
  readonly coluna: KanbanColumn;
  readonly prioridade?: PriorityLevel;
  readonly prazoIso?: string;
  readonly categoria?: string;
}

/** ADR-117/123 · Fase 3 — Kanban UI-only.
 *
 * Backend persistence + drag-and-drop (@dnd-kit) entram na Fase 8,
 * consumindo endpoints /v1/reports/{id}/kanban (ADR-123). Por ora:
 * exibição read-only com optional `onMove` callback (noop default).
 */
export function Kanban({
  items,
  onMove,
  className,
}: {
  readonly items: readonly KanbanItem[];
  readonly onMove?: (itemId: string, to: KanbanColumn) => void;
  readonly className?: string;
}) {
  const byColumn = groupByColumn(items);

  return (
    <div
      className={className}
      style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr 1fr",
        gap: 16,
        marginTop: 12,
      }}
      data-kanban-board
    >
      {(["a_fazer", "em_andamento", "concluido"] as const).map((col) => (
        <KanbanColumnView
          key={col}
          column={col}
          items={byColumn[col]}
          onMove={onMove}
        />
      ))}
    </div>
  );
}

function groupByColumn(
  items: readonly KanbanItem[],
): Record<KanbanColumn, KanbanItem[]> {
  const result: Record<KanbanColumn, KanbanItem[]> = {
    a_fazer: [],
    em_andamento: [],
    concluido: [],
  };
  for (const item of items) result[item.coluna].push(item);
  return result;
}

function KanbanColumnView({
  column,
  items,
  onMove,
}: {
  column: KanbanColumn;
  items: KanbanItem[];
  onMove?: (itemId: string, to: KanbanColumn) => void;
}) {
  return (
    <div
      data-kanban-column={column}
      style={{
        background: "var(--surface-background)",
        borderRadius: "var(--radius-card, 12px)",
        padding: 12,
        border: "1px solid var(--surface-border)",
        minHeight: 120,
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: 12,
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "0.5px",
          marginBottom: 10,
          paddingBottom: 8,
          borderBottom: "2px solid var(--surface-border)",
        }}
      >
        <span>{COLUMN_LABEL[column]}</span>
        <span
          style={{
            background: "var(--brand-primary)",
            color: "#fff",
            borderRadius: 10,
            padding: "1px 8px",
            fontSize: 11,
          }}
        >
          {items.length}
        </span>
      </header>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {items.map((item) => (
          <KanbanCardView key={item.id} item={item} onMove={onMove} />
        ))}
      </ul>
    </div>
  );
}

function KanbanCardView({
  item,
  onMove,
}: {
  item: KanbanItem;
  onMove?: (itemId: string, to: KanbanColumn) => void;
}) {
  const prioridadeBorder =
    item.prioridade === "alta"
      ? "var(--brand-danger)"
      : item.prioridade === "media"
        ? "var(--brand-primary)"
        : "var(--surface-muted-foreground)";
  return (
    <li
      data-kanban-item
      data-item-id={item.id}
      style={{
        background: "var(--surface-card)",
        borderRadius: "var(--radius-sm, 4px)",
        padding: "8px 10px",
        marginBottom: 6,
        borderLeft: `3px solid ${prioridadeBorder}`,
        fontSize: 13,
        boxShadow: "var(--shadow-card)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
        <span style={{ fontWeight: 500 }}>{item.titulo}</span>
        {item.prioridade && <PriorityBadge level={item.prioridade} />}
      </div>
      <div
        style={{
          fontSize: 11,
          color: "var(--surface-muted-foreground)",
          marginTop: 4,
          display: "flex",
          gap: 6,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        {item.categoria && <span>{item.categoria}</span>}
        {item.prazoIso && <DeadlineBadge iso={item.prazoIso} />}
      </div>
      {onMove && <MoveButtons item={item} onMove={onMove} />}
    </li>
  );
}

function MoveButtons({
  item,
  onMove,
}: {
  item: KanbanItem;
  onMove: (itemId: string, to: KanbanColumn) => void;
}) {
  const targets: KanbanColumn[] = (["a_fazer", "em_andamento", "concluido"] as const).filter(
    (c) => c !== item.coluna,
  );
  return (
    <div style={{ display: "flex", gap: 4, marginTop: 6 }}>
      {targets.map((target) => (
        <button
          key={target}
          type="button"
          onClick={() => onMove(item.id, target)}
          aria-label={`Mover para ${COLUMN_LABEL[target]}`}
          style={{
            fontSize: 10,
            padding: "2px 6px",
            border: "1px solid var(--surface-border)",
            borderRadius: 3,
            background: "transparent",
            cursor: "pointer",
            color: "var(--surface-muted-foreground)",
          }}
        >
          → {COLUMN_LABEL[target]}
        </button>
      ))}
    </div>
  );
}

export { type ReactNode };
