"use client";

import { Button } from "@/components/ui/button";
import type { RebalanceamentoModo } from "@/lib/api";

import { REBAL_GROUPS, rebalGroupOf, type RebalGroup } from "./constants";

interface RebalanceamentoModeSelectorProps {
  value: RebalanceamentoModo;
  onChange: (value: RebalanceamentoModo) => void;
}

/**
 * Rebalanceamento em 3 escolhas agrupadas (ADR-141 emenda item 11): No aporte
 * (recomendado) · Periódico (sub-select) · Por gatilho (sub-select). O modo
 * persistido segue sendo o enum plano `RebalanceamentoModo`.
 */
export function RebalanceamentoModeSelector({
  value,
  onChange,
}: RebalanceamentoModeSelectorProps) {
  const activeGroup = rebalGroupOf(value);

  return (
    <div
      role="radiogroup"
      aria-label="Modo de rebalanceamento"
      className="space-y-2"
    >
      {REBAL_GROUPS.map((group) => (
        <GroupCard
          key={group.id}
          group={group}
          isActive={activeGroup === group.id}
          value={value}
          onChange={onChange}
        />
      ))}
    </div>
  );
}

function GroupCard({
  group,
  isActive,
  value,
  onChange,
}: {
  group: RebalGroup;
  isActive: boolean;
  value: RebalanceamentoModo;
  onChange: (value: RebalanceamentoModo) => void;
}) {
  const selectGroup = () =>
    onChange(group.value ?? group.defaultValue ?? value);

  return (
    <div
      className={
        "rounded-lg border p-3 transition-colors " +
        (isActive ? "border-primary bg-primary/5" : "border-border")
      }
    >
      <button
        type="button"
        role="radio"
        aria-checked={isActive}
        onClick={selectGroup}
        className="flex w-full items-center gap-2 text-left text-sm font-medium"
      >
        <span
          className={
            "flex h-4 w-4 shrink-0 items-center justify-center rounded-full border " +
            (isActive ? "border-primary" : "border-muted-foreground/40")
          }
          aria-hidden="true"
        >
          {isActive && <span className="h-2 w-2 rounded-full bg-primary" />}
        </span>
        {group.label}
        {group.recommended && (
          <span className="text-xs font-normal text-muted-foreground">
            (recomendado)
          </span>
        )}
      </button>

      {group.options && isActive && (
        <div className="mt-3 flex flex-wrap gap-2 pl-6">
          {group.options.map((opt) => (
            <Button
              key={opt.value}
              type="button"
              size="sm"
              variant={value === opt.value ? "default" : "outline"}
              onClick={() => onChange(opt.value)}
            >
              {opt.label}
            </Button>
          ))}
        </div>
      )}
    </div>
  );
}
