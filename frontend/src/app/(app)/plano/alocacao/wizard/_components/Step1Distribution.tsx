"use client";

import { CheckCircle2, XCircle } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { AlocacaoBar } from "./AlocacaoBar";
import { PCT_KEYS, PRESETS, type Pcts } from "./constants";

interface FamilyGroup {
  title: string;
  fields: { key: keyof Pcts; label: string }[];
}

const FAMILY_GROUPS: FamilyGroup[] = [
  {
    title: "Renda fixa",
    fields: [
      { key: "rf_pos_pct", label: "RF · Pós (%)" },
      { key: "rf_pre_pct", label: "RF · Pré (%)" },
      { key: "rf_ipca_pct", label: "RF · IPCA+ (%)" },
    ],
  },
  {
    title: "Renda variável",
    fields: [
      { key: "acoes_br_pct", label: "Ações BR (%)" },
      { key: "acoes_int_pct", label: "Ações Int. (%)" },
    ],
  },
  {
    title: "Imobiliário",
    fields: [{ key: "fiis_pct", label: "FIIs (%)" }],
  },
  {
    title: "Liquidez",
    fields: [{ key: "caixa_pct", label: "Caixa (%)" }],
  },
];

interface Step1DistributionProps {
  pcts: Pcts;
  onChange: (next: Pcts) => void;
  soma: number;
  somaValida: boolean;
}

export function Step1Distribution({
  pcts,
  onChange,
  soma,
  somaValida,
}: Step1DistributionProps) {
  const setField = (key: keyof Pcts, value: number) => {
    onChange({ ...pcts, [key]: value });
  };

  return (
    <div>
      <h2 className="text-lg font-semibold">Distribua seus investimentos</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Defina a alocacao percentual ideal por classe de ativo.
      </p>

      <PresetButtons pcts={pcts} onSelect={onChange} />

      <div className="mt-6 space-y-4">
        {FAMILY_GROUPS.map((group) => (
          <FamilyFieldset
            key={group.title}
            group={group}
            pcts={pcts}
            onChangeField={setField}
          />
        ))}
      </div>

      <SumIndicator soma={soma} somaValida={somaValida} />

      <AlocacaoBar className="mt-3" pcts={pcts} />
    </div>
  );
}

function FamilyFieldset({
  group,
  pcts,
  onChangeField,
}: {
  group: FamilyGroup;
  pcts: Pcts;
  onChangeField: (key: keyof Pcts, value: number) => void;
}) {
  const subtotal = group.fields.reduce((acc, f) => acc + pcts[f.key], 0);
  return (
    <fieldset className="rounded-lg border p-3">
      <legend className="px-1 text-xs font-medium text-muted-foreground">
        {group.title} ·{" "}
        <span className="font-mono tabular-nums">{subtotal}%</span>
      </legend>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        {group.fields.map((field) => (
          <PctInput
            key={field.key}
            id={field.key}
            label={field.label}
            value={pcts[field.key]}
            onChange={(v) => onChangeField(field.key, v)}
          />
        ))}
      </div>
    </fieldset>
  );
}

function PresetButtons({
  pcts,
  onSelect,
}: {
  pcts: Pcts;
  onSelect: (next: Pcts) => void;
}) {
  return (
    <div className="mt-4 flex flex-wrap gap-2">
      {Object.entries(PRESETS).map(([name, preset]) => {
        const isActive = PCT_KEYS.every((key) => pcts[key] === preset[key]);
        return (
          <Button
            key={name}
            variant={isActive ? "default" : "outline"}
            size="sm"
            onClick={() => onSelect(preset)}
            type="button"
          >
            {name}
          </Button>
        );
      })}
    </div>
  );
}

function PctInput({
  id,
  label,
  value,
  onChange,
}: {
  id: string;
  label: string;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        type="number"
        min={0}
        max={100}
        step={1}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="mt-2 font-mono tabular-nums"
      />
    </div>
  );
}

function SumIndicator({
  soma,
  somaValida,
}: {
  soma: number;
  somaValida: boolean;
}) {
  return (
    <div className="mt-4 flex items-center gap-2 text-sm">
      {somaValida ? (
        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
      ) : (
        <XCircle className="h-4 w-4 text-destructive" />
      )}
      <span className={somaValida ? "text-emerald-600" : "text-destructive"}>
        Total: <span className="font-mono tabular-nums">{soma}%</span>
        {!somaValida && " — deve somar 100%"}
      </span>
    </div>
  );
}
