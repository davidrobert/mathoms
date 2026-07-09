"use client";

import { Wallet } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ALOCACAO_FAMILIES, type AlocacaoClass } from "@/lib/alocacaoClasses";

import { AlocacaoBar } from "./AlocacaoBar";
import {
  AlocacaoProgress,
  type AlocacaoProgressState,
} from "./AlocacaoProgress";
import { PCT_KEYS, PRESETS, type Pcts } from "./constants";

interface AlocacaoDistributionFieldsProps {
  pcts: Pcts;
  onChange: (next: Pcts) => void;
  soma: number;
  progressState: AlocacaoProgressState;
  onCompleteWithCaixa: () => void;
}

/**
 * Núcleo reutilizável da edição de alocação: presets AUVP + inputs inteiros
 * agrupados por família com subtotal + barra Σ→100 + "Completar com Caixa".
 * Consumido pelo Step 1 do wizard e pela página de edição.
 */
export function AlocacaoDistributionFields({
  pcts,
  onChange,
  soma,
  progressState,
  onCompleteWithCaixa,
}: AlocacaoDistributionFieldsProps) {
  const setField = (key: keyof Pcts, value: number) =>
    onChange({ ...pcts, [key]: value });

  return (
    <div>
      <PresetButtons pcts={pcts} onSelect={onChange} />

      <div className="mt-6 space-y-4">
        {ALOCACAO_FAMILIES.map((family) => (
          <FamilyFieldset
            key={family.id}
            title={family.label}
            classes={family.classes}
            pcts={pcts}
            onChangeField={setField}
          />
        ))}
      </div>

      <div className="mt-5 flex items-start justify-between gap-4">
        <AlocacaoProgress
          className="flex-1"
          soma={soma}
          state={progressState}
        />
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={onCompleteWithCaixa}
          disabled={soma === 100}
          className="mt-0.5 shrink-0"
        >
          <Wallet className="mr-2 h-4 w-4" />
          Completar com Caixa
        </Button>
      </div>

      <AlocacaoBar className="mt-4" pcts={pcts} />
    </div>
  );
}

function FamilyFieldset({
  title,
  classes,
  pcts,
  onChangeField,
}: {
  title: string;
  classes: readonly AlocacaoClass[];
  pcts: Pcts;
  onChangeField: (key: keyof Pcts, value: number) => void;
}) {
  const subtotal = classes.reduce((acc, c) => acc + pcts[c.id], 0);
  return (
    <fieldset className="rounded-lg border p-3">
      <legend className="px-1 text-xs font-medium text-muted-foreground">
        {title} · <span className="font-mono tabular-nums">{subtotal}%</span>
      </legend>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        {classes.map((c) => (
          <PctInput
            key={c.id}
            id={c.id}
            label={c.label}
            colorVar={c.colorVar}
            value={pcts[c.id]}
            onChange={(v) => onChangeField(c.id, v)}
          />
        ))}
      </div>
    </fieldset>
  );
}

function PctInput({
  id,
  label,
  colorVar,
  value,
  onChange,
}: {
  id: string;
  label: string;
  colorVar: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <Label htmlFor={id} className="flex items-center gap-1.5">
        <span
          className="inline-block h-2 w-2 shrink-0 rounded-full"
          style={{ backgroundColor: colorVar }}
          aria-hidden="true"
        />
        {label}
      </Label>
      <Input
        id={id}
        type="number"
        inputMode="numeric"
        min={0}
        max={100}
        step={1}
        value={value}
        onChange={(e) => onChange(clampPct(e.target.value))}
        className="mt-2 font-mono tabular-nums"
      />
    </div>
  );
}

function clampPct(raw: string): number {
  const n = Math.round(Number(raw));
  if (!Number.isFinite(n)) return 0;
  return Math.min(100, Math.max(0, n));
}

function PresetButtons({
  pcts,
  onSelect,
}: {
  pcts: Pcts;
  onSelect: (next: Pcts) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      <span className="mr-1 self-center text-xs text-muted-foreground">
        Perfil sugerido:
      </span>
      {Object.entries(PRESETS).map(([name, preset]) => {
        const isActive = PCT_KEYS.every((key) => pcts[key] === preset[key]);
        return (
          <Button
            key={name}
            type="button"
            variant={isActive ? "default" : "outline"}
            size="sm"
            onClick={() => onSelect(preset)}
          >
            {name}
          </Button>
        );
      })}
    </div>
  );
}
