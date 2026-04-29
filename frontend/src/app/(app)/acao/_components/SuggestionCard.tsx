"use client";

// Direção E · Onda 5 · ADR-153 — card de Suggestion no Inbox de /acao.
// Aceitar/Modificar/Descartar via dialogs locais. "Aceitar" cria
// Decision (ADR-136) com código informado pelo usuário; status passa
// a Aceita. "Descartar" exige um motivo controlado (5 chips).

import { useState } from "react";
import { toast } from "sonner";
import { AlertOctagon, AlertTriangle, ArrowRight, Info, Pencil, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
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
  DISMISS_REASON_LABELS,
  type DismissReason,
  type Suggestion,
  type SuggestionSeverity,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";

import {
  type AcceptHandler,
  type DismissHandler,
  type ModifyHandler,
} from "./suggestionTypes";

interface SuggestionCardProps {
  suggestion: Suggestion;
  /** Sugestão de código sequencial para a próxima Decision (`D{N+1}`). */
  nextDecisionCode: string;
  onAccept: AcceptHandler;
  onModify: ModifyHandler;
  onDismiss: DismissHandler;
}

export function SuggestionCard({
  suggestion,
  nextDecisionCode,
  onAccept,
  onModify,
  onDismiss,
}: SuggestionCardProps) {
  const [acceptOpen, setAcceptOpen] = useState(false);
  const [modifyOpen, setModifyOpen] = useState(false);
  const [dismissOpen, setDismissOpen] = useState(false);

  return (
    <Card
      id={`SUG-${suggestion.id}`}
      data-suggestion-id={suggestion.id}
      className="scroll-mt-24 target:ring-2 target:ring-brand-500 target:ring-offset-2"
    >
      <CardContent className="flex flex-col gap-3 py-4">
        <SeverityRow suggestion={suggestion} />
        <p className="text-sm font-semibold leading-snug">
          {suggestion.title}
        </p>
        <p className="text-xs text-muted-foreground line-clamp-3">
          {suggestion.rationale}
        </p>
        <SuggestionMeta suggestion={suggestion} />
        {suggestion.status === "Pendente" && (
          <SuggestionActions
            onAccept={() => setAcceptOpen(true)}
            onModify={() => setModifyOpen(true)}
            onDismiss={() => setDismissOpen(true)}
          />
        )}
      </CardContent>
      <AcceptDialog
        suggestion={suggestion}
        nextDecisionCode={nextDecisionCode}
        open={acceptOpen}
        onOpenChange={setAcceptOpen}
        onAccept={onAccept}
      />
      <ModifyDialog
        suggestion={suggestion}
        nextDecisionCode={nextDecisionCode}
        open={modifyOpen}
        onOpenChange={setModifyOpen}
        onModify={onModify}
      />
      <DismissDialog
        suggestion={suggestion}
        open={dismissOpen}
        onOpenChange={setDismissOpen}
        onDismiss={onDismiss}
      />
    </Card>
  );
}

const SEVERITY_CONFIG: Record<
  SuggestionSeverity,
  {
    label: string;
    Icon: typeof Info;
    cls: string;
  }
> = {
  info: {
    label: "Informativo",
    Icon: Info,
    cls: "border-l-sky-500 text-sky-700 dark:text-sky-300",
  },
  warning: {
    label: "Atenção",
    Icon: AlertTriangle,
    cls: "border-l-amber-500 text-amber-700 dark:text-amber-300",
  },
  danger: {
    label: "Ação urgente",
    Icon: AlertOctagon,
    cls: "border-l-red-500 text-red-700 dark:text-red-300",
  },
};

function SeverityRow({ suggestion }: { suggestion: Suggestion }) {
  const sev = SEVERITY_CONFIG[suggestion.severity] ?? SEVERITY_CONFIG.info;
  const Icon = sev.Icon;
  return (
    <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide">
      <Icon className={`h-4 w-4 ${sev.cls.split(" ").slice(1).join(" ")}`} />
      <span>{sev.label}</span>
    </div>
  );
}

function SuggestionMeta({ suggestion }: { suggestion: Suggestion }) {
  const amount =
    suggestion.amount_brl !== null ? Number(suggestion.amount_brl) : null;
  const reportLabel = suggestion.report_id
    ? `Relatório · §${suggestion.section_id}`
    : `§${suggestion.section_id}`;
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
      <span>Origem: {reportLabel}</span>
      {amount !== null && Number.isFinite(amount) && (
        <span className="font-mono tabular-nums">
          {formatCurrency(amount)}
        </span>
      )}
      {suggestion.status !== "Pendente" && (
        <span className="font-medium">
          Status: {suggestion.status}
        </span>
      )}
    </div>
  );
}

function SuggestionActions({
  onAccept,
  onModify,
  onDismiss,
}: {
  onAccept: () => void;
  onModify: () => void;
  onDismiss: () => void;
}) {
  return (
    <div className="flex flex-wrap gap-2 pt-1">
      <Button size="sm" onClick={onAccept}>
        Aceitar
        <ArrowRight className="ml-1 h-3.5 w-3.5" />
      </Button>
      <Button size="sm" variant="outline" onClick={onModify}>
        <Pencil className="mr-1 h-3.5 w-3.5" />
        Modificar
      </Button>
      <Button
        size="sm"
        variant="ghost"
        className="text-muted-foreground"
        onClick={onDismiss}
      >
        <X className="mr-1 h-3.5 w-3.5" />
        Descartar
      </Button>
    </div>
  );
}

interface AcceptDialogProps {
  suggestion: Suggestion;
  nextDecisionCode: string;
  open: boolean;
  onOpenChange: (b: boolean) => void;
  onAccept: AcceptHandler;
}

function AcceptDialog({
  suggestion,
  nextDecisionCode,
  open,
  onOpenChange,
  onAccept,
}: AcceptDialogProps) {
  const [code, setCode] = useState(nextDecisionCode);
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.match(/^D\d{1,3}$/)) {
      toast.error("Código deve ser D + número (ex.: D01)");
      return;
    }
    setBusy(true);
    try {
      await onAccept(suggestion.id, { decision_code: code });
      toast.success(`Decisão ${code} criada`);
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "Erro ao aceitar");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>Aceitar sugestão</DialogTitle>
            <DialogDescription>
              Vai criar uma decisão no plano com o conteúdo da sugestão.
              Você pode revisar/editar depois em /plano.
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-md border border-border bg-muted/30 px-3 py-2">
            <p className="text-xs font-medium">{suggestion.title}</p>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label className="text-xs font-medium">Código da decisão</Label>
            <Input
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder={nextDecisionCode}
              maxLength={10}
              required
              autoFocus
            />
            <p className="text-[11px] text-muted-foreground">
              Sugerido: {nextDecisionCode}
            </p>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={busy}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={busy}>
              {busy ? "Aceitando…" : "Aceitar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

interface ModifyDialogProps {
  suggestion: Suggestion;
  nextDecisionCode: string;
  open: boolean;
  onOpenChange: (b: boolean) => void;
  onModify: ModifyHandler;
}

function ModifyDialog({
  suggestion,
  nextDecisionCode,
  open,
  onOpenChange,
  onModify,
}: ModifyDialogProps) {
  const [code, setCode] = useState(nextDecisionCode);
  const [title, setTitle] = useState(suggestion.title);
  const [rationale, setRationale] = useState(suggestion.rationale);
  const [amount, setAmount] = useState(suggestion.amount_brl ?? "");
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.match(/^D\d{1,3}$/)) {
      toast.error("Código deve ser D + número (ex.: D01)");
      return;
    }
    setBusy(true);
    try {
      await onModify(suggestion.id, {
        decision_code: code,
        title: title !== suggestion.title ? title : undefined,
        rationale: rationale !== suggestion.rationale ? rationale : undefined,
        amount_brl: amount !== (suggestion.amount_brl ?? "") ? amount || null : undefined,
      });
      toast.success(`Decisão ${code} criada com modificações`);
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "Erro ao modificar");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>Modificar e aceitar</DialogTitle>
            <DialogDescription>
              Customize título, motivo ou valor antes de virar uma decisão.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-3">
            <Field label="Código">
              <Input
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                maxLength={10}
                required
              />
            </Field>
            <Field label="Título">
              <Input
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                maxLength={500}
                required
              />
            </Field>
            <Field label="Motivo">
              <Textarea
                value={rationale}
                onChange={(e) => setRationale(e.target.value)}
                rows={3}
              />
            </Field>
            <Field label="Valor (R$)" hint="Opcional">
              <Input
                type="number"
                inputMode="decimal"
                step="0.01"
                min="0"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
            </Field>
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={busy}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={busy}>
              {busy ? "Salvando…" : "Aceitar com modificação"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

interface DismissDialogProps {
  suggestion: Suggestion;
  open: boolean;
  onOpenChange: (b: boolean) => void;
  onDismiss: DismissHandler;
}

function DismissDialog({
  suggestion,
  open,
  onOpenChange,
  onDismiss,
}: DismissDialogProps) {
  const [reason, setReason] = useState<DismissReason | "">("");
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason) {
      toast.error("Selecione um motivo");
      return;
    }
    setBusy(true);
    try {
      await onDismiss(suggestion.id, { reason });
      toast.success("Sugestão descartada");
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.detail : "Erro ao descartar");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>Descartar sugestão</DialogTitle>
            <DialogDescription>
              Vamos guardar o motivo para não sugerir o mesmo de novo
              tão cedo.
            </DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {(Object.keys(DISMISS_REASON_LABELS) as DismissReason[]).map(
              (key) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => setReason(key)}
                  className={[
                    "rounded-md border px-3 py-2 text-left text-xs transition-colors",
                    reason === key
                      ? "border-foreground bg-muted/50"
                      : "border-border hover:border-muted-foreground/50",
                  ].join(" ")}
                >
                  {DISMISS_REASON_LABELS[key]}
                </button>
              ),
            )}
          </div>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              disabled={busy}
            >
              Cancelar
            </Button>
            <Button type="submit" disabled={busy || !reason} variant="default">
              {busy ? "Descartando…" : "Descartar"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
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
