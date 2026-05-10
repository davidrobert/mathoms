"use client";

import { useMemo, useState, type FormEvent } from "react";
import { Plus, X, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/cn";

/** Set diff client-side de keywords (W4 · ADR-185 §4).
 *
 * 3 estados visuais por chip:
 * - **default** (`--surface-muted`): keyword herdada do template, não tocada.
 * - **adicionada** (`--brand-accent` border + bg suave): inserida pelo workspace.
 * - **removida** (riscada, `--surface-muted-foreground`): keyword do template
 *   que o workspace decidiu omitir; agrupada em accordion no fim para reduzir ruído.
 *
 * Normalização: `.trim()` em ambos lados antes do diff — evita falso-positivo
 * em whitespace; ainda preserva caracteres unicode visíveis (diacríticos).
 *
 * Diff é puramente derivado — `current` é a fonte de verdade para o backend.
 */

interface CategoryChipDiffProps {
  /** Keywords atuais do workspace (resolved). */
  current: readonly string[];
  /** Keywords default do template global. */
  defaultKeywords: readonly string[];
  /** Editor controlado — recebe a nova lista completa. */
  onChange: (next: string[]) => void;
  /** Modo readonly omite controles de adicionar/remover (apenas exibição). */
  readOnly?: boolean;
  /** Classe extra do container raiz. */
  className?: string;
}

type ChipKind = "default" | "added" | "removed";

interface Chip {
  key: string;
  kind: ChipKind;
}

function normalize(value: string): string {
  return value.trim();
}

function buildChips(current: readonly string[], defaults: readonly string[]): Chip[] {
  const currentSet = new Set(current.map(normalize).filter(Boolean));
  const defaultSet = new Set(defaults.map(normalize).filter(Boolean));
  const chips: Chip[] = [];
  // Ordem: default-presentes primeiro (estável vs template), adicionadas em
  // seguida, removidas no final no accordion.
  for (const k of defaultSet) {
    if (currentSet.has(k)) chips.push({ key: k, kind: "default" });
  }
  for (const k of currentSet) {
    if (!defaultSet.has(k)) chips.push({ key: k, kind: "added" });
  }
  for (const k of defaultSet) {
    if (!currentSet.has(k)) chips.push({ key: k, kind: "removed" });
  }
  return chips;
}

export function CategoryChipDiff({
  current,
  defaultKeywords,
  onChange,
  readOnly = false,
  className,
}: CategoryChipDiffProps) {
  const [draft, setDraft] = useState("");
  const [showRemoved, setShowRemoved] = useState(false);

  const chips = useMemo(() => buildChips(current, defaultKeywords), [current, defaultKeywords]);
  const visible = chips.filter((c) => c.kind !== "removed");
  const removed = chips.filter((c) => c.kind === "removed");

  function commit(next: string[]) {
    // De-dup preservando ordem de inserção; remove vazios após trim.
    const seen = new Set<string>();
    const out: string[] = [];
    for (const raw of next) {
      const v = normalize(raw);
      if (!v || seen.has(v)) continue;
      seen.add(v);
      out.push(v);
    }
    onChange(out);
  }

  function handleAdd(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const value = normalize(draft);
    if (!value) return;
    commit([...current, value]);
    setDraft("");
  }

  function handleRemove(key: string) {
    commit(current.filter((k) => normalize(k) !== key));
  }

  function handleRestore(key: string) {
    commit([...current, key]);
  }

  return (
    <div className={cn("space-y-2", className)} data-testid="category-chip-diff">
      <div className="flex flex-wrap items-center gap-1.5">
        {visible.length === 0 && (
          <span className="text-xs text-muted-foreground italic">
            Sem keywords ativas
          </span>
        )}
        {visible.map((chip) => (
          <ChipPill
            key={`${chip.kind}-${chip.key}`}
            chip={chip}
            onRemove={readOnly ? undefined : () => handleRemove(chip.key)}
          />
        ))}
        {!readOnly && (
          <form onSubmit={handleAdd} className="inline-flex items-center gap-1">
            <Input
              type="text"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Nova keyword"
              className="h-7 w-32 text-xs"
              aria-label="Adicionar keyword"
            />
            <Button
              type="submit"
              size="sm"
              variant="ghost"
              className="h-7 px-2"
              disabled={!normalize(draft)}
              aria-label="Adicionar"
            >
              <Plus className="h-3.5 w-3.5" />
            </Button>
          </form>
        )}
      </div>

      {removed.length > 0 && (
        <div>
          <button
            type="button"
            onClick={() => setShowRemoved((s) => !s)}
            className="text-xs text-muted-foreground underline-offset-2 hover:underline"
            aria-expanded={showRemoved}
          >
            {showRemoved ? "Ocultar" : "Mostrar"} {removed.length} keyword
            {removed.length > 1 ? "s" : ""} removida{removed.length > 1 ? "s" : ""} do padrão
          </button>
          {showRemoved && (
            <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
              {removed.map((chip) => (
                <ChipPill
                  key={`removed-${chip.key}`}
                  chip={chip}
                  onRestore={readOnly ? undefined : () => handleRestore(chip.key)}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ChipPill({
  chip,
  onRemove,
  onRestore,
}: {
  chip: Chip;
  onRemove?: () => void;
  onRestore?: () => void;
}) {
  // Cores: 3 estados via combinações de tokens canônicos (ADR-076).
  // - default: bg surface-muted neutro, sem afford de "personalizada".
  // - added: border + bg accent (ramo brand-accent já é semântica de
  //   alteração positiva no design system; mantém AAA contra texto).
  // - removed: opacity + line-through, fica contextual no accordion.
  const variantClass =
    chip.kind === "default"
      ? "border-transparent bg-[var(--surface-muted)] text-[var(--surface-foreground)]"
      : chip.kind === "added"
        ? "border-[var(--brand-accent)] bg-[var(--brand-accent)]/10 text-[var(--brand-accent)]"
        : "border-dashed border-[var(--surface-border)] bg-transparent text-[var(--surface-muted-foreground)] line-through";

  return (
    <span
      data-testid={`chip-${chip.kind}`}
      data-chip-kind={chip.kind}
      className={cn(
        "inline-flex h-6 items-center gap-1 rounded-full border px-2 text-xs font-medium",
        variantClass,
      )}
    >
      <span>{chip.key}</span>
      {chip.kind !== "removed" && onRemove && (
        <button
          type="button"
          onClick={onRemove}
          className="rounded-full p-0.5 hover:bg-black/5"
          aria-label={`Remover ${chip.key}`}
        >
          <X className="h-3 w-3" />
        </button>
      )}
      {chip.kind === "removed" && onRestore && (
        <button
          type="button"
          onClick={onRestore}
          className="rounded-full p-0.5 hover:bg-black/5"
          aria-label={`Restaurar ${chip.key}`}
        >
          <RotateCcw className="h-3 w-3" />
        </button>
      )}
    </span>
  );
}
