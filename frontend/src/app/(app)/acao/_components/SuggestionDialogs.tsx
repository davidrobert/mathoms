"use client";

// Direção E · Onda 5 · ADR-153 — dialogs locais do `<SuggestionCard/>`.
//
// Aceitar/Modificar/Descartar geram a Decision (ADR-136) ou registram
// o motivo de dispensa. Extraídos para arquivo próprio em Onda 10 #3
// para manter `SuggestionCard.tsx` < 500 linhas (CLAUDE.md §code-style).

import { useState } from "react";
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
  DISMISS_REASON_LABELS,
  type DismissReason,
  type Suggestion,
} from "@/lib/api";

import {
  type AcceptHandler,
  type DismissHandler,
  type ModifyHandler,
} from "./suggestionTypes";

interface AcceptDialogProps {
  suggestion: Suggestion;
  nextDecisionCode: string;
  open: boolean;
  onOpenChange: (b: boolean) => void;
  onAccept: AcceptHandler;
}

export function AcceptDialog({
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

export function ModifyDialog({
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
        amount_brl:
          amount !== (suggestion.amount_brl ?? "") ? amount || null : undefined,
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

export function DismissDialog({
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
