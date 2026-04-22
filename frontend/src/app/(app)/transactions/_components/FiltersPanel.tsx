"use client";

import type { FamilyMemberConfig } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { BANK_OPTIONS } from "./bankOptions";

export interface FilterState {
  bank: string;
  category: string;
  member: string;
  dateFrom: string;
  dateTo: string;
  valueMin: string;
  valueMax: string;
}

export type FilterKey =
  | "bank"
  | "category"
  | "member"
  | "date_from"
  | "date_to"
  | "value_min"
  | "value_max";

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-xs font-medium text-muted-foreground">{label}</label>
      {children}
    </div>
  );
}

export function FiltersPanel({
  state,
  categoryOptions,
  members,
  onApply,
}: {
  state: FilterState;
  categoryOptions: string[];
  members: FamilyMemberConfig[];
  onApply: (key: FilterKey, value: string) => void;
}) {
  return (
    <Card className="mb-6 p-0">
      <div className="grid grid-cols-1 gap-4 px-4 py-4 sm:grid-cols-2 lg:grid-cols-4">
        <Field label="Data início">
          <Input type="date" value={state.dateFrom} onChange={(e) => onApply("date_from", e.target.value)} />
        </Field>
        <Field label="Data fim">
          <Input type="date" value={state.dateTo} onChange={(e) => onApply("date_to", e.target.value)} />
        </Field>
        <Field label="Banco">
          <Select value={state.bank} onValueChange={(v) => onApply("bank", v as string)}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Todos" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Todos</SelectItem>
              {BANK_OPTIONS.map((b) => (
                <SelectItem key={b.value} value={b.value}>
                  {b.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <Field label="Categoria">
          <Select value={state.category} onValueChange={(v) => onApply("category", v as string)}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Todas" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Todas</SelectItem>
              {categoryOptions.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <Field label="Titular">
          <Select value={state.member} onValueChange={(v) => onApply("member", v as string)}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Todos" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Todos</SelectItem>
              {members.map((m) => (
                <SelectItem key={m.key} value={m.key}>
                  {m.short_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
        <Field label="Valor mínimo">
          <Input
            type="number"
            step="0.01"
            placeholder="0,00"
            value={state.valueMin}
            onChange={(e) => onApply("value_min", e.target.value)}
          />
        </Field>
        <Field label="Valor máximo">
          <Input
            type="number"
            step="0.01"
            placeholder="0,00"
            value={state.valueMax}
            onChange={(e) => onApply("value_max", e.target.value)}
          />
        </Field>
      </div>
    </Card>
  );
}
