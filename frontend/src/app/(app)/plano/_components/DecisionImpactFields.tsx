"use client";

// ADR-179 — quantificação de impacto + horizonte + prioridade da Decision.
// Usado por DecisionFormDialog. 4 campos opcionais que alimentam a
// ordenação do card S10 ("Top 5 Decisões de Impacto") via projeção do
// aggregate (lane A10.5).

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  type DecisionHorizon,
  DECISION_HORIZON_LABEL,
  DECISION_HORIZON_ORDER,
} from "@/lib/api";

export interface DecisionImpactFieldValues {
  impact1yBrl: string;
  impact10yBrl: string;
  horizon: DecisionHorizon;
  priority: string;
}

export interface DecisionImpactFieldSetters {
  setImpact1yBrl: (v: string) => void;
  setImpact10yBrl: (v: string) => void;
  setHorizon: (v: DecisionHorizon) => void;
  setPriority: (v: string) => void;
}

interface FieldProps {
  label: string;
  hint?: string;
  children: React.ReactNode;
}

function Field({ label, hint, children }: FieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label className="text-xs font-medium">{label}</Label>
      {children}
      {hint && <p className="text-[11px] text-muted-foreground">{hint}</p>}
    </div>
  );
}

interface DecisionImpactFieldsProps {
  values: DecisionImpactFieldValues;
  setters: DecisionImpactFieldSetters;
}

export function DecisionImpactFields({
  values,
  setters,
}: DecisionImpactFieldsProps) {
  return (
    <>
      <Field
        label="Impacto em 1 ano (R$)"
        hint="Opcional — quanto essa decisão movimenta nos próximos 12 meses."
      >
        <Input
          type="number"
          inputMode="decimal"
          step="0.01"
          min="0"
          value={values.impact1yBrl}
          onChange={(e) => setters.setImpact1yBrl(e.target.value)}
          placeholder="36000.00"
        />
      </Field>
      <Field
        label="Impacto em 10 anos (R$)"
        hint="Opcional — projeção do efeito acumulado em 10 anos."
      >
        <Input
          type="number"
          inputMode="decimal"
          step="0.01"
          min="0"
          value={values.impact10yBrl}
          onChange={(e) => setters.setImpact10yBrl(e.target.value)}
          placeholder="420000.00"
        />
      </Field>
      <Field label="Horizonte">
        <Select
          value={values.horizon}
          onValueChange={(v) => setters.setHorizon(v as DecisionHorizon)}
        >
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {DECISION_HORIZON_ORDER.map((h) => (
              <SelectItem key={h} value={h}>
                {DECISION_HORIZON_LABEL[h]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </Field>
      <Field
        label="Prioridade (1–99)"
        hint="Opcional — 1 = mais urgente. Vazio ordena por impacto em 1 ano."
      >
        <Input
          type="number"
          inputMode="numeric"
          step="1"
          min={1}
          max={99}
          value={values.priority}
          onChange={(e) => setters.setPriority(e.target.value)}
          placeholder="—"
        />
      </Field>
    </>
  );
}

/** Parse priority input → integer ou null. Aceita 1..99; vazio/inválido → null. */
export function parsePriority(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const n = Number(trimmed);
  if (!Number.isFinite(n) || !Number.isInteger(n)) return null;
  if (n < 1 || n > 99) return null;
  return n;
}
