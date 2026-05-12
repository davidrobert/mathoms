"use client";

// A11.W5 · ADR-192 · S9-T05 — modal de cadastro de apólice.
// Form mínimo (categoria, titular, capital, prêmio/mês, vigência,
// seguradora, policy_ref opcional, coverage_type). Money em decimal
// string (ADR-090); UI exibe pt-BR mas serializa "1234.56".

import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, type FamilyMemberConfig } from "@/lib/api";
import {
  PROTECTION_CATEGORIES,
  PROTECTION_COVERAGE_TYPES,
  type ProtectionCategory,
  type ProtectionCoverageType,
  type ProtectionCreatePayload,
} from "@/lib/api/protections";

interface ProtectionFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  members: FamilyMemberConfig[];
  onCreate: (payload: ProtectionCreatePayload) => Promise<unknown>;
}

interface FormState {
  category: ProtectionCategory;
  holderId: string;
  insurer: string;
  policyRef: string;
  coverageBrl: string;
  premiumMonthlyBrl: string;
  coverageType: ProtectionCoverageType | "";
  startsAt: string;
  endsAt: string;
  notes: string;
}

const EMPTY: FormState = {
  category: "vida",
  holderId: "",
  insurer: "",
  policyRef: "",
  coverageBrl: "",
  premiumMonthlyBrl: "",
  coverageType: "",
  startsAt: "",
  endsAt: "",
  notes: "",
};

function parseDecimalInput(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  // Aceita "1.234,56" (pt-BR) ou "1234.56" (en) — converte para decimal canônico.
  const normalized = trimmed.includes(",")
    ? trimmed.replace(/\./g, "").replace(",", ".")
    : trimmed;
  if (!/^\d+(\.\d{1,2})?$/.test(normalized)) {
    throw new Error(`Valor inválido: "${value}". Use formato 1234,56.`);
  }
  return normalized;
}

function buildPayload(s: FormState): ProtectionCreatePayload {
  const coverage = parseDecimalInput(s.coverageBrl);
  if (!coverage) throw new Error("Capital segurado é obrigatório.");
  if (!s.startsAt) throw new Error("Data de início da vigência é obrigatória.");
  return {
    category: s.category,
    holder_family_member_id: s.holderId || null,
    insurer: s.insurer.trim() || null,
    policy_ref: s.policyRef.trim() || null,
    coverage_brl: coverage,
    premium_monthly_brl: parseDecimalInput(s.premiumMonthlyBrl),
    coverage_type: s.coverageType || null,
    starts_at: s.startsAt,
    ends_at: s.endsAt || null,
    notes: s.notes.trim() || null,
  };
}

export function ProtectionFormDialog({
  open,
  onOpenChange,
  members,
  onCreate,
}: ProtectionFormDialogProps) {
  const [form, setForm] = useState<FormState>(EMPTY);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // Reset state when dialog opens.
  useEffect(() => {
    if (open) {
      setForm(EMPTY);
      setError("");
    }
  }, [open]);

  const memberOptions = useMemo(
    () =>
      members.map((m) => ({
        value: m.id ?? m.key,
        label: m.short_name || m.full_name,
      })),
    [members],
  );

  async function handleSubmit() {
    setError("");
    try {
      const payload = buildPayload(form);
      setSubmitting(true);
      await onCreate(payload);
      onOpenChange(false);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Erro inesperado ao cadastrar apólice.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Cadastrar apólice</DialogTitle>
          <DialogDescription>
            Estimativa baseada em padrões consagrados de planejamento
            patrimonial brasileiro; não constitui recomendação fiduciária.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-2">
          <FormField label="Categoria" htmlFor="category">
            <Select
              value={form.category}
              onValueChange={(v) =>
                setForm((s) => ({ ...s, category: v as ProtectionCategory }))
              }
            >
              <SelectTrigger id="category">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PROTECTION_CATEGORIES.map((c) => (
                  <SelectItem key={c.value} value={c.value}>
                    {c.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>

          <FormField label="Titular" htmlFor="holder">
            <Select
              value={form.holderId || "_none"}
              onValueChange={(v) =>
                setForm((s) => ({ ...s, holderId: v === "_none" ? "" : v }))
              }
            >
              <SelectTrigger id="holder">
                <SelectValue placeholder="Selecione um membro" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="_none">— Sem titular específico —</SelectItem>
                {memberOptions.map((m) => (
                  <SelectItem key={m.value} value={m.value}>
                    {m.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Capital segurado (R$)" htmlFor="coverage">
              <Input
                id="coverage"
                inputMode="decimal"
                placeholder="500000,00"
                value={form.coverageBrl}
                onChange={(e) =>
                  setForm((s) => ({ ...s, coverageBrl: e.target.value }))
                }
                required
              />
            </FormField>

            <FormField label="Prêmio mensal (R$)" htmlFor="premium">
              <Input
                id="premium"
                inputMode="decimal"
                placeholder="350,00"
                value={form.premiumMonthlyBrl}
                onChange={(e) =>
                  setForm((s) => ({
                    ...s,
                    premiumMonthlyBrl: e.target.value,
                  }))
                }
              />
            </FormField>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Início da vigência" htmlFor="starts_at">
              <Input
                id="starts_at"
                type="date"
                value={form.startsAt}
                onChange={(e) =>
                  setForm((s) => ({ ...s, startsAt: e.target.value }))
                }
                required
              />
            </FormField>

            <FormField label="Fim da vigência" htmlFor="ends_at">
              <Input
                id="ends_at"
                type="date"
                value={form.endsAt}
                onChange={(e) =>
                  setForm((s) => ({ ...s, endsAt: e.target.value }))
                }
              />
            </FormField>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <FormField label="Seguradora" htmlFor="insurer">
              <Input
                id="insurer"
                placeholder="Ex.: SulAmérica S/A"
                value={form.insurer}
                onChange={(e) =>
                  setForm((s) => ({ ...s, insurer: e.target.value }))
                }
              />
            </FormField>

            <FormField label="Tipo de cobertura" htmlFor="coverage_type">
              <Select
                value={form.coverageType || "_none"}
                onValueChange={(v) =>
                  setForm((s) => ({
                    ...s,
                    coverageType:
                      v === "_none" ? "" : (v as ProtectionCoverageType),
                  }))
                }
              >
                <SelectTrigger id="coverage_type">
                  <SelectValue placeholder="Selecione" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="_none">— Não informado —</SelectItem>
                  {PROTECTION_COVERAGE_TYPES.map((c) => (
                    <SelectItem key={c.value} value={c.value}>
                      {c.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </FormField>
          </div>

          <FormField label="Nº da apólice (opcional)" htmlFor="policy_ref">
            <Input
              id="policy_ref"
              placeholder="Será armazenado de forma cifrada"
              value={form.policyRef}
              onChange={(e) =>
                setForm((s) => ({ ...s, policyRef: e.target.value }))
              }
              autoComplete="off"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Armazenado no vault Fernet; exibido mascarado por default.
            </p>
          </FormField>

          <FormField label="Notas (opcional)" htmlFor="notes">
            <Textarea
              id="notes"
              rows={2}
              value={form.notes}
              onChange={(e) =>
                setForm((s) => ({ ...s, notes: e.target.value }))
              }
            />
          </FormField>

          {error && (
            <p
              role="alert"
              className="rounded-md border border-[var(--semantic-danger)] bg-[color-mix(in_srgb,var(--semantic-danger)_8%,transparent)] px-3 py-2 text-sm text-[var(--semantic-danger)]"
            >
              {error}
            </p>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting ? "Salvando..." : "Cadastrar apólice"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function FormField({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div className="grid gap-1.5">
      <Label htmlFor={htmlFor}>{label}</Label>
      {children}
    </div>
  );
}
