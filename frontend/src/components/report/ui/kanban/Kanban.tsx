"use client";

import type { CSSProperties, ReactNode } from "react";
import {
  DndContext,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { PriorityBadge, type PriorityLevel } from "../badges/PriorityBadge";
import { DeadlineBadge } from "../badges/DeadlineBadge";

export type KanbanColumn = "a_fazer" | "em_andamento" | "concluido";

const COLUMNS_ORDER: readonly KanbanColumn[] = [
  "a_fazer",
  "em_andamento",
  "concluido",
] as const;

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

/** v2.7 — Kanban com drag-and-drop real via `@dnd-kit/core`.
 *
 * API `onMove(id, to)` preservada de ADR-117/123 — chamada quando o
 * usuário arrasta um card sobre uma coluna diferente OU clica nos
 * botões "→ Coluna" do fallback mobile. Reordenação dentro de uma
 * mesma coluna não é persistida (campo `ordem` do backend continua
 * gerenciado fora desta primitiva).
 *
 * **Fallback mobile (`<767px`):** drag em touch exige long-press, o
 * que conflita com scroll natural; mantemos os botões "→ Coluna"
 * visíveis nesse breakpoint via media query inline. Em desktop os
 * botões somem (DnD é a interação primária).
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
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    }),
  );

  const handleDragEnd = (event: DragEndEvent) => {
    if (!onMove) return;
    const overId = event.over?.id;
    if (!overId) return;
    const target = parseColumnId(String(overId));
    if (!target) return;
    const itemId = String(event.active.id);
    const item = items.find((it) => it.id === itemId);
    if (!item || item.coluna === target) return;
    onMove(itemId, target);
  };

  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <div className={className} style={BOARD_STYLE} data-kanban-board>
        {COLUMNS_ORDER.map((col) => (
          <KanbanColumnView
            key={col}
            column={col}
            items={byColumn[col]}
            onMove={onMove}
          />
        ))}
      </div>
    </DndContext>
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
  const { isOver, setNodeRef } = useDroppable({ id: dropZoneId(column) });
  return (
    <div
      ref={setNodeRef}
      data-kanban-column={column}
      data-droppable-over={isOver ? "true" : "false"}
      style={{
        ...COLUMN_STYLE,
        outline: isOver ? "2px dashed var(--brand-primary)" : "none",
        outlineOffset: -2,
      }}
    >
      <header style={COLUMN_HEADER_STYLE}>
        <span>{COLUMN_LABEL[column]}</span>
        <span style={COLUMN_BADGE_STYLE}>{items.length}</span>
      </header>
      <ul style={LIST_STYLE}>
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
  const { attributes, listeners, setNodeRef, isDragging, transform } =
    useDraggable({ id: item.id });
  const prioridadeBorder =
    item.prioridade === "alta"
      ? "var(--brand-danger)"
      : item.prioridade === "media"
        ? "var(--brand-primary)"
        : "var(--surface-muted-foreground)";
  const transformStyle = transform
    ? { transform: `translate3d(${transform.x}px, ${transform.y}px, 0)` }
    : undefined;
  return (
    <li
      ref={setNodeRef}
      data-kanban-item
      data-item-id={item.id}
      data-dragging={isDragging ? "true" : "false"}
      style={{
        ...CARD_STYLE,
        borderLeft: `3px solid ${prioridadeBorder}`,
        opacity: isDragging ? 0.4 : 1,
        cursor: onMove ? "grab" : "default",
        ...transformStyle,
      }}
      {...listeners}
      {...attributes}
    >
      <div style={CARD_HEADER_STYLE}>
        <span style={CARD_TITLE_STYLE}>{item.titulo}</span>
        {item.prioridade && <PriorityBadge level={item.prioridade} />}
      </div>
      <div style={CARD_META_STYLE}>
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
  const targets = COLUMNS_ORDER.filter((c) => c !== item.coluna);
  return (
    <div
      data-kanban-move-buttons
      className="kanban-move-buttons"
      style={MOVE_BUTTONS_STYLE}
    >
      {targets.map((target) => (
        <button
          key={target}
          type="button"
          onPointerDown={(e) => e.stopPropagation()}
          onClick={(e) => {
            e.stopPropagation();
            onMove(item.id, target);
          }}
          aria-label={`Mover para ${COLUMN_LABEL[target]}`}
          style={MOVE_BUTTON_STYLE}
        >
          → {COLUMN_LABEL[target]}
        </button>
      ))}
    </div>
  );
}

const DROP_ZONE_PREFIX = "kanban-col:";

function dropZoneId(col: KanbanColumn): string {
  return `${DROP_ZONE_PREFIX}${col}`;
}

function parseColumnId(id: string): KanbanColumn | null {
  if (!id.startsWith(DROP_ZONE_PREFIX)) return null;
  const value = id.slice(DROP_ZONE_PREFIX.length);
  return COLUMNS_ORDER.includes(value as KanbanColumn)
    ? (value as KanbanColumn)
    : null;
}

const BOARD_STYLE: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "1fr 1fr 1fr",
  gap: 16,
  marginTop: 12,
};

const COLUMN_STYLE: CSSProperties = {
  background: "var(--surface-background)",
  borderRadius: "var(--radius-card, 12px)",
  padding: 12,
  border: "1px solid var(--surface-border)",
  minHeight: 120,
};

const COLUMN_HEADER_STYLE: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  fontSize: 12,
  fontWeight: 700,
  textTransform: "uppercase",
  letterSpacing: "0.5px",
  marginBottom: 10,
  paddingBottom: 8,
  borderBottom: "2px solid var(--surface-border)",
};

const COLUMN_BADGE_STYLE: CSSProperties = {
  background: "var(--brand-primary)",
  color: "#fff",
  borderRadius: 10,
  padding: "1px 8px",
  fontSize: 11,
};

const LIST_STYLE: CSSProperties = { listStyle: "none", padding: 0, margin: 0 };

const CARD_STYLE: CSSProperties = {
  background: "var(--surface-card)",
  borderRadius: "var(--radius-sm, 4px)",
  padding: "8px 10px",
  marginBottom: 6,
  fontSize: 13,
  boxShadow: "var(--shadow-card)",
  touchAction: "none",
};

const CARD_HEADER_STYLE: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  gap: 8,
};

const CARD_TITLE_STYLE: CSSProperties = { fontWeight: 500 };

const CARD_META_STYLE: CSSProperties = {
  fontSize: 11,
  color: "var(--surface-muted-foreground)",
  marginTop: 4,
  display: "flex",
  gap: 6,
  alignItems: "center",
  flexWrap: "wrap",
};

const MOVE_BUTTONS_STYLE: CSSProperties = {
  display: "flex",
  gap: 4,
  marginTop: 6,
};

const MOVE_BUTTON_STYLE: CSSProperties = {
  fontSize: 10,
  padding: "2px 6px",
  border: "1px solid var(--surface-border)",
  borderRadius: 3,
  background: "transparent",
  cursor: "pointer",
  color: "var(--surface-muted-foreground)",
};

export { type ReactNode };
