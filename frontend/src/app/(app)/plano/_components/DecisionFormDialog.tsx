"use client";

import { useEffect, useState } from "react";
import { toast } from "sonner";

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
import {
  ApiError,
  type Decision,
  type DecisionCreatePayload,
  type DecisionHorizon,
  type DecisionStatus,
  type DecisionUpdatePayload,
} from "@/lib/api";

import { DecisionImpactFields, parsePriority } from "./DecisionImpactFields";

const RATIONALE_MIN = 10;
const TITLE_MIN = 3;
const TITLE_MAX = 500;

type CreatableStatus = Extract<DecisionStatus, "Pendente" | "Decidido">;

const CREATABLE_STATUSES: ReadonlyArray<CreatableStatus> = [
  "Pendente",
  "Decidido",
];

const CREATABLE_STATUS_LABEL: Record<CreatableStatus, string> = {
  Pendente: "A decidir",
  Decidido: "Em vigor (já decidida)",
};

export type DecisionFormMode =
  | { kind: "create"; defaultCode: string }
  | { kind: "edit"; decision: Decision };

interface DecisionFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: DecisionFormMode;
  onCreate: (payload: DecisionCreatePayload) => Promise<Decision>;
  onUpdate: (decisionId: string, payload: DecisionUpdatePayload) => Promise<void>;
}

export function DecisionFormDialog(props: DecisionFormDialogProps) {
  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogFormBody {...props} />
      </DialogContent>
    </Dialog>
  );
}

interface FormValues {
  code: string;
  title: string;
  rationale: string;
  amountBrl: string;
  status: DecisionStatus;
  // ADR-179
  impact1yBrl: string;
  impact10yBrl: string;
  horizon: DecisionHorizon;
  priority: string; // input type=number — string para preservar empty
}

const DEFAULT_HORIZON: DecisionHorizon = "short_6_12m";

function DialogFormBody({
  mode,
  onCreate,
  onUpdate,
  onOpenChange,
}: DecisionFormDialogProps) {
  const { values, setters } = useDecisionFormState(mode);
  const { busy, errorMsg, handleSubmit } = useDecisionFormSubmit({
    mode,
    values,
    onCreate,
    onUpdate,
    onOpenChange,
  });
  const validation = validateForm(values);
  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <DecisionFormHeader mode={mode} />
      <DecisionFormFields mode={mode} values={values} setters={setters} />
      {validation && <p className="text-xs text-destructive">{validation}</p>}
      {errorMsg && <p className="text-xs text-destructive">{errorMsg}</p>}
      <DecisionFormFooter
        mode={mode}
        busy={busy}
        validation={validation}
        onCancel={() => onOpenChange(false)}
      />
    </form>
  );
}

interface Setters {
  setCode: (v: string) => void;
  setTitle: (v: string) => void;
  setRationale: (v: string) => void;
  setAmountBrl: (v: string) => void;
  setStatus: (v: DecisionStatus) => void;
  // ADR-179
  setImpact1yBrl: (v: string) => void;
  setImpact10yBrl: (v: string) => void;
  setHorizon: (v: DecisionHorizon) => void;
  setPriority: (v: string) => void;
}

function useDecisionFormState(mode: DecisionFormMode): {
  values: FormValues;
  setters: Setters;
} {
  const [code, setCode] = useState(initialCode(mode));
  const [title, setTitle] = useState(initialTitle(mode));
  const [rationale, setRationale] = useState(initialRationale(mode));
  const [amountBrl, setAmountBrl] = useState(initialAmount(mode));
  const [status, setStatus] = useState<DecisionStatus>(initialStatus(mode));
  const [impact1yBrl, setImpact1yBrl] = useState(initialImpact1y(mode));
  const [impact10yBrl, setImpact10yBrl] = useState(initialImpact10y(mode));
  const [horizon, setHorizon] = useState<DecisionHorizon>(initialHorizon(mode));
  const [priority, setPriority] = useState(initialPriority(mode));
  useEffect(() => {
    setCode(initialCode(mode));
    setTitle(initialTitle(mode));
    setRationale(initialRationale(mode));
    setAmountBrl(initialAmount(mode));
    setStatus(initialStatus(mode));
    setImpact1yBrl(initialImpact1y(mode));
    setImpact10yBrl(initialImpact10y(mode));
    setHorizon(initialHorizon(mode));
    setPriority(initialPriority(mode));
  }, [mode]);
  return {
    values: { code, title, rationale, amountBrl, status, impact1yBrl, impact10yBrl, horizon, priority },
    setters: {
      setCode,
      setTitle,
      setRationale,
      setAmountBrl,
      setStatus,
      setImpact1yBrl,
      setImpact10yBrl,
      setHorizon,
      setPriority,
    },
  };
}

interface SubmitHookProps {
  mode: DecisionFormMode;
  values: FormValues;
  onCreate: DecisionFormDialogProps["onCreate"];
  onUpdate: DecisionFormDialogProps["onUpdate"];
  onOpenChange: (open: boolean) => void;
}

function useDecisionFormSubmit({
  mode,
  values,
  onCreate,
  onUpdate,
  onOpenChange,
}: SubmitHookProps) {
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  useEffect(() => setErrorMsg(null), [mode]);
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (validateForm(values)) return;
    setBusy(true);
    setErrorMsg(null);
    try {
      await persistDecision(mode, values, onCreate, onUpdate);
      onOpenChange(false);
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.detail : "Erro ao salvar");
    } finally {
      setBusy(false);
    }
  };
  return { busy, errorMsg, handleSubmit };
}

function buildDecisionPayload(values: FormValues) {
  return {
    title: values.title,
    rationale: values.rationale,
    amount_brl: values.amountBrl || null,
    status: values.status,
    impact_1y_brl: values.impact1yBrl || null,
    impact_10y_brl: values.impact10yBrl || null,
    horizon: values.horizon,
    priority: parsePriority(values.priority),
  };
}

async function persistDecision(
  mode: DecisionFormMode,
  values: FormValues,
  onCreate: DecisionFormDialogProps["onCreate"],
  onUpdate: DecisionFormDialogProps["onUpdate"],
): Promise<void> {
  const payload = buildDecisionPayload(values);
  if (mode.kind === "create") {
    await onCreate({ code: values.code, ...payload });
    toast.success("Decisão registrada");
    return;
  }
  await onUpdate(mode.decision.id, payload);
  toast.success("Decisão atualizada");
}

function DecisionFormHeader({ mode }: { mode: DecisionFormMode }) {
  return (
    <DialogHeader>
      <DialogTitle>
        {mode.kind === "create"
          ? "Nova decisão de plano"
          : `Editar decisão ${mode.decision.code}`}
      </DialogTitle>
      <DialogDescription>
        Registre uma inflexão estruturante no seu plano (mudança de alocação,
        aporte, objetivo). O motivo é obrigatório.
      </DialogDescription>
    </DialogHeader>
  );
}

interface FieldsProps {
  mode: DecisionFormMode;
  values: FormValues;
  setters: Setters;
}

function DecisionFormFields({ mode, values, setters }: FieldsProps) {
  return (
    <>
      <FormField label="Código" hint="Ex.: D01, D02">
        <Input
          value={values.code}
          onChange={(e) => setters.setCode(e.target.value.toUpperCase())}
          disabled={mode.kind === "edit"}
          maxLength={10}
          required
          autoFocus={mode.kind === "create"}
        />
      </FormField>
      <FormField label="Título">
        <Input
          value={values.title}
          onChange={(e) => setters.setTitle(e.target.value)}
          maxLength={TITLE_MAX}
          required
          placeholder="Ex.: Quitar financiamento do apartamento"
        />
      </FormField>
      <FormField
        label="Por que essa decisão?"
        hint="1 frase com o motivo (obrigatório)"
      >
        <Textarea
          value={values.rationale}
          onChange={(e) => setters.setRationale(e.target.value)}
          required
          rows={3}
          placeholder="Liberar R$ 3.500/mês de fluxo livre para aporte mensal."
        />
      </FormField>
      <AmountAndStatusFields values={values} setters={setters} />
      <DecisionImpactFields values={values} setters={setters} />
    </>
  );
}

interface AmountAndStatusProps {
  values: FormValues;
  setters: Setters;
}

function AmountAndStatusFields({ values, setters }: AmountAndStatusProps) {
  return (
    <>
      <FormField label="Valor (R$)" hint="Opcional — só se a decisão tem valor monetário">
        <Input
          type="number"
          inputMode="decimal"
          step="0.01"
          min="0"
          value={values.amountBrl}
          onChange={(e) => setters.setAmountBrl(e.target.value)}
          placeholder="117430.00"
        />
      </FormField>
      <FormField label="Status">
        <Select
          value={values.status}
          onValueChange={(v) => setters.setStatus(v as DecisionStatus)}
        >
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {CREATABLE_STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {CREATABLE_STATUS_LABEL[s]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FormField>
    </>
  );
}

interface FooterProps {
  mode: DecisionFormMode;
  busy: boolean;
  validation: string | null;
  onCancel: () => void;
}

function DecisionFormFooter({ mode, busy, validation, onCancel }: FooterProps) {
  const submitLabel = busy
    ? "Salvando…"
    : mode.kind === "create"
      ? "Registrar"
      : "Salvar";
  return (
    <DialogFooter>
      <Button
        type="button"
        variant="outline"
        onClick={onCancel}
        disabled={busy}
      >
        Cancelar
      </Button>
      <Button type="submit" disabled={busy || Boolean(validation)}>
        {submitLabel}
      </Button>
    </DialogFooter>
  );
}

interface FormFieldProps {
  label: string;
  hint?: string;
  children: React.ReactNode;
}

function FormField({ label, hint, children }: FormFieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label className="text-xs font-medium">{label}</Label>
      {children}
      {hint && <p className="text-[11px] text-muted-foreground">{hint}</p>}
    </div>
  );
}

function initialCode(mode: DecisionFormMode): string {
  return mode.kind === "create" ? mode.defaultCode : mode.decision.code;
}

function initialTitle(mode: DecisionFormMode): string {
  return mode.kind === "create" ? "" : mode.decision.title;
}

function initialRationale(mode: DecisionFormMode): string {
  return mode.kind === "create" ? "" : (mode.decision.rationale ?? "");
}

function initialAmount(mode: DecisionFormMode): string {
  return mode.kind === "create" ? "" : (mode.decision.amount_brl ?? "");
}

function initialStatus(mode: DecisionFormMode): DecisionStatus {
  if (mode.kind === "create") return "Pendente";
  return isCreatable(mode.decision.status) ? mode.decision.status : "Pendente";
}

// ADR-179 — inicializadores dos 4 campos novos (impacto + horizonte + prioridade).
function initialImpact1y(mode: DecisionFormMode): string {
  return mode.kind === "create" ? "" : (mode.decision.impact_1y_brl ?? "");
}

function initialImpact10y(mode: DecisionFormMode): string {
  return mode.kind === "create" ? "" : (mode.decision.impact_10y_brl ?? "");
}

function initialHorizon(mode: DecisionFormMode): DecisionHorizon {
  return mode.kind === "create" ? DEFAULT_HORIZON : mode.decision.horizon;
}

function initialPriority(mode: DecisionFormMode): string {
  if (mode.kind === "create") return "";
  return mode.decision.priority === null ? "" : String(mode.decision.priority);
}

function isCreatable(s: DecisionStatus): s is CreatableStatus {
  return s === "Pendente" || s === "Decidido";
}

function validateForm({ code, title, rationale }: FormValues): string | null {
  if (!code.match(/^D\d{1,3}$/)) return "Código deve ser D + número (ex.: D01).";
  if (title.trim().length < TITLE_MIN)
    return `Título precisa de ao menos ${TITLE_MIN} caracteres.`;
  if (rationale.trim().length < RATIONALE_MIN)
    return `Motivo precisa de ao menos ${RATIONALE_MIN} caracteres — registre o porquê.`;
  return null;
}
