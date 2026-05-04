"use client";

// Direção E · Onda 5 · ADR-153 — card de Suggestion no Inbox de /acao.
// Aceitar/Modificar/Descartar via dialogs locais. "Aceitar" cria
// Decision (ADR-136) com código informado pelo usuário; status passa
// a Aceita. "Descartar" exige um motivo controlado (5 chips).
//
// Onda 10 #3 — backward link para a seção do relatório que originou
// a sugestão. Dialogs movidos para `SuggestionDialogs.tsx`.

import { useState } from "react";
import Link from "next/link";
import {
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  ExternalLink,
  Info,
  Pencil,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  type Suggestion,
  type SuggestionSeverity,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";

import {
  AcceptDialog,
  DismissDialog,
  ModifyDialog,
} from "./SuggestionDialogs";
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
      className={[
        "scroll-mt-24 target:ring-2 target:ring-brand-500 target:ring-offset-2",
        // ADR-161 (Onda 8 #4) — borda esquerda colorida por severidade,
        // antes definida em SEVERITY_CONFIG.cls mas nunca aplicada ao Card.
        SEVERITY_BORDER[suggestion.severity] ?? SEVERITY_BORDER.info,
      ].join(" ")}
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
        <SuggestionReportLink suggestion={suggestion} />
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

// ADR-161 (Onda 8 #4) — classes Tailwind aplicadas ao Card root para
// borda esquerda colorida visível. Separadas de SEVERITY_CONFIG.cls
// (que mistura ícone+texto) para evitar acoplamento.
const SEVERITY_BORDER: Record<SuggestionSeverity, string> = {
  danger: "border-l-4 border-l-red-500",
  warning: "border-l-4 border-l-amber-500",
  info: "border-l-4 border-l-sky-500",
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

/** Onda 10 #3 — backward link para a seção do relatório que originou
 * a sugestão. Onda 7 #3 entregou forward (relatório → /acao#SUG-XXX);
 * sem o caminho de volta a sugestão fica órfã do contexto. Quando
 * `report_id` é null (sugestão sem relatório de origem, edge case),
 * o link é omitido — não renderizamos um item disabled. */
function SuggestionReportLink({ suggestion }: { suggestion: Suggestion }) {
  if (!suggestion.report_id) return null;
  return (
    <Link
      href={`/reports/${suggestion.report_id}#${suggestion.section_id}`}
      data-testid="suggestion-report-backlink"
      className="inline-flex items-center gap-1.5 self-start text-[11px] font-medium text-muted-foreground hover:text-foreground hover:underline"
    >
      Ver no relatório do mês · §{suggestion.section_id}
      <ExternalLink className="h-3 w-3" aria-hidden />
    </Link>
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
