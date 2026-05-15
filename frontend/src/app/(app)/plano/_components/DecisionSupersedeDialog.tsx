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
import { Textarea } from "@/components/ui/textarea";
import {
  ApiError,
  type Decision,
  type DecisionCreatePayload,
  type DecisionSupersedePayload,
} from "@/lib/api";

import { formatDecisionDate } from "./decisionsCopy";

const RATIONALE_MIN = 10;
const TITLE_MIN = 3;

// ADR-214 — `defaultCode` removido; server gera o code da nova decisão
// na transação do POST /decisions e devolve para o toast.
interface DecisionSupersedeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  oldDecision: Decision;
  onCreate: (payload: DecisionCreatePayload) => Promise<Decision>;
  onSupersede: (oldId: string, payload: DecisionSupersedePayload) => Promise<void>;
}

export function DecisionSupersedeDialog(props: DecisionSupersedeDialogProps) {
  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <SupersedeBody {...props} />
      </DialogContent>
    </Dialog>
  );
}

interface SupersedeValues {
  title: string;
  rationale: string;
  amountBrl: string;
  note: string;
}

function SupersedeBody({
  oldDecision,
  onCreate,
  onSupersede,
  onOpenChange,
}: DecisionSupersedeDialogProps) {
  const { values, setters } = useSupersedeFormState(oldDecision.id);
  const { busy, errorMsg, handleSubmit } = useSupersedeSubmit({
    oldDecision,
    values,
    onCreate,
    onSupersede,
    onOpenChange,
  });
  const validation = validate(values);
  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <SupersedeHeader oldDecision={oldDecision} />
      <OldDecisionPreview decision={oldDecision} />
      <SupersedeFields values={values} setters={setters} />
      {validation && <p className="text-xs text-destructive">{validation}</p>}
      {errorMsg && <p className="text-xs text-destructive">{errorMsg}</p>}
      <SupersedeFooter
        busy={busy}
        validation={validation}
        onCancel={() => onOpenChange(false)}
      />
    </form>
  );
}

interface SupersedeSetters {
  setTitle: (v: string) => void;
  setRationale: (v: string) => void;
  setAmountBrl: (v: string) => void;
  setNote: (v: string) => void;
}

function useSupersedeFormState(
  oldDecisionId: string,
): { values: SupersedeValues; setters: SupersedeSetters } {
  const [title, setTitle] = useState("");
  const [rationale, setRationale] = useState("");
  const [amountBrl, setAmountBrl] = useState("");
  const [note, setNote] = useState("");
  useEffect(() => {
    setTitle("");
    setRationale("");
    setAmountBrl("");
    setNote("");
  }, [oldDecisionId]);
  return {
    values: { title, rationale, amountBrl, note },
    setters: { setTitle, setRationale, setAmountBrl, setNote },
  };
}

interface SubmitHookProps {
  oldDecision: Decision;
  values: SupersedeValues;
  onCreate: DecisionSupersedeDialogProps["onCreate"];
  onSupersede: DecisionSupersedeDialogProps["onSupersede"];
  onOpenChange: (open: boolean) => void;
}

function useSupersedeSubmit({
  oldDecision,
  values,
  onCreate,
  onSupersede,
  onOpenChange,
}: SubmitHookProps) {
  const [busy, setBusy] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (validate(values)) return;
    setBusy(true);
    setErrorMsg(null);
    try {
      await runSupersede(oldDecision, values, onCreate, onSupersede);
      onOpenChange(false);
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.detail : "Erro ao substituir");
    } finally {
      setBusy(false);
    }
  };
  return { busy, errorMsg, handleSubmit };
}

async function runSupersede(
  oldDecision: Decision,
  values: SupersedeValues,
  onCreate: DecisionSupersedeDialogProps["onCreate"],
  onSupersede: DecisionSupersedeDialogProps["onSupersede"],
): Promise<void> {
  // ADR-214 — code da nova decisão é server-generated; toast usa created.code.
  const created = await onCreate({
    title: values.title,
    rationale: values.rationale,
    amount_brl: values.amountBrl || null,
    status: "Decidido",
  });
  await onSupersede(oldDecision.id, {
    superseded_by_id: created.id,
    note: values.note || null,
  });
  toast.success(`Decisão ${oldDecision.code} substituída por ${created.code}`);
}

function SupersedeHeader({ oldDecision }: { oldDecision: Decision }) {
  return (
    <DialogHeader>
      <DialogTitle>Substituir decisão {oldDecision.code}</DialogTitle>
      <DialogDescription>
        Crie a decisão sucessora. A original fica marcada como substituída,
        preservando o histórico.
      </DialogDescription>
    </DialogHeader>
  );
}

interface FieldsProps {
  values: SupersedeValues;
  setters: SupersedeSetters;
}

function SupersedeFields({ values, setters }: FieldsProps) {
  // ADR-214 — input "Código da nova decisão" removido; foco vai para o título.
  return (
    <>
      <Field label="Título da nova decisão">
        <Input
          value={values.title}
          onChange={(e) => setters.setTitle(e.target.value)}
          required
          autoFocus
          placeholder="Ex.: Aumentar TRS para 5%"
        />
      </Field>
      <Field
        label="Por que essa nova decisão?"
        hint="1 frase com o motivo (obrigatório)"
      >
        <Textarea
          value={values.rationale}
          onChange={(e) => setters.setRationale(e.target.value)}
          required
          rows={3}
          placeholder="Cenário de juros mudou, ajustando taxa de retirada conservadora."
        />
      </Field>
      <Field label="Valor (R$)" hint="Opcional">
        <Input
          type="number"
          inputMode="decimal"
          step="0.01"
          min="0"
          value={values.amountBrl}
          onChange={(e) => setters.setAmountBrl(e.target.value)}
        />
      </Field>
      <Field
        label="Motivo da substituição"
        hint="Opcional — contexto da virada para a próxima"
      >
        <Textarea
          value={values.note}
          onChange={(e) => setters.setNote(e.target.value)}
          rows={2}
          placeholder="Ex.: Selic caiu para 9%, tese da TRS conservadora mudou."
        />
      </Field>
    </>
  );
}

interface FooterProps {
  busy: boolean;
  validation: string | null;
  onCancel: () => void;
}

function SupersedeFooter({ busy, validation, onCancel }: FooterProps) {
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
        {busy ? "Substituindo…" : "Substituir"}
      </Button>
    </DialogFooter>
  );
}

function OldDecisionPreview({ decision }: { decision: Decision }) {
  return (
    <div className="rounded-md border border-dashed border-border bg-muted/30 px-3 py-2 text-xs">
      <p className="font-mono text-muted-foreground">
        {decision.code} • Em vigor desde {formatDecisionDate(decision.decided_at)}
      </p>
      <p className="mt-1 font-medium">{decision.title}</p>
      {decision.rationale && (
        <p className="mt-0.5 text-muted-foreground line-clamp-2">
          {decision.rationale}
        </p>
      )}
    </div>
  );
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

function validate({ title, rationale }: SupersedeValues): string | null {
  // ADR-214 — sem validação de code (server-gen).
  if (title.trim().length < TITLE_MIN)
    return `Título precisa de ao menos ${TITLE_MIN} caracteres.`;
  if (rationale.trim().length < RATIONALE_MIN)
    return `Motivo precisa de ao menos ${RATIONALE_MIN} caracteres.`;
  return null;
}
