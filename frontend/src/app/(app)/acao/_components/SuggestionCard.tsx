"use client";

// Direção E · Onda 5 · ADR-153 — card de Suggestion no Inbox de /acao.
// Aceitar/Modificar/Descartar via dialogs locais. "Aceitar" cria
// Decision (ADR-136) e status passa a Aceita; ADR-214 fez o code da
// Decision passar a ser server-generated — input some, toast pós-aceite
// educa via `accepted_decision_code` do response.
// "Descartar" exige um motivo controlado (5 chips).
//
// Onda 10 #3 — backward link para a seção do relatório que originou
// a sugestão. Dialogs movidos para `SuggestionDialogs.tsx`.
//
// F5 (PLAN-suggestion-lifecycle) — três correções vindas do dogfood
// 2026-08-11: (1) tokens semânticos no lugar de Tailwind literal
// (ADR-076); (2) mês de origem no meta, porque sem data uma sugestão de
// três relatórios atrás é indistinguível de uma de hoje; (3) `density`,
// que apaga o rótulo em caixa alta fora do grupo de foco — 11 cards
// repetindo "ATENÇÃO" é ruído, não sinal.

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

import { MonetaryValue } from "@/components/report/MonetaryValue";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  type Suggestion,
  type SuggestionSeverity,
} from "@/lib/api";
import { formatMonthShortPtBR } from "@/lib/format";

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

/** `full` mantém o rótulo textual de severidade; `compact` deixa só o
 *  ícone (com aria-label) + a borda. Uma prop em vez de um segundo
 *  componente: duplicar o card duplicaria os 3 dialogs junto. */
export type SuggestionCardDensity = "full" | "compact";

interface SuggestionCardProps {
  suggestion: Suggestion;
  onAccept: AcceptHandler;
  onModify: ModifyHandler;
  onDismiss: DismissHandler;
  density?: SuggestionCardDensity;
}

export function SuggestionCard({
  suggestion,
  onAccept,
  onModify,
  onDismiss,
  density = "full",
}: SuggestionCardProps) {
  const [acceptOpen, setAcceptOpen] = useState(false);
  const [modifyOpen, setModifyOpen] = useState(false);
  const [dismissOpen, setDismissOpen] = useState(false);
  const tone = severityTone(suggestion.severity);

  return (
    <Card
      id={`SUG-${suggestion.id}`}
      data-suggestion-id={suggestion.id}
      data-severity={suggestion.severity}
      className="scroll-mt-24 border-l-4 target:ring-2 target:ring-[var(--brand-info)] target:ring-offset-2"
      style={{ borderLeftColor: tone.borderVar }}
    >
      <CardContent className="flex flex-col gap-3 py-4">
        <SuggestionHeading suggestion={suggestion} density={density} />
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
        open={acceptOpen}
        onOpenChange={setAcceptOpen}
        onAccept={onAccept}
      />
      <ModifyDialog
        suggestion={suggestion}
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

/** ADR-076 — severidade sai dos tokens semânticos, nunca de classe
 * Tailwind literal (`border-l-amber-500` & cia. eram o estado anterior).
 *
 * `borderVar` é o tom cheio (decoração; o significado vai no aria-label
 * do ícone). `textVar` é o par **-on-tint** onde ele existe, porque o tom
 * cheio de `--semantic-alert` sobre `--surface-card` mede 2,06:1 em light
 * — reprova AA com folga. Medido contra `--surface-card` nos dois temas:
 * alert-on-tint 6,22 / 8,67 · loss-on-tint 6,47 / 7,74 ·
 * info-financial (sem par on-tint; o tom cheio já passa) 5,70 / 7,65.
 * `dev/check_tint_contrast.py` não alcança `style` inline — a guarda aqui
 * é o teste que afirma o nome da var; trocar por Tailwind literal falha. */
const SEVERITY_TONE: Record<
  SuggestionSeverity,
  { label: string; Icon: typeof Info; borderVar: string; textVar: string }
> = {
  info: {
    label: "Informativo",
    Icon: Info,
    borderVar: "var(--semantic-info-financial)",
    textVar: "var(--semantic-info-financial)",
  },
  warning: {
    label: "Atenção",
    Icon: AlertTriangle,
    borderVar: "var(--semantic-alert)",
    textVar: "var(--semantic-alert-on-tint)",
  },
  danger: {
    label: "Ação urgente",
    Icon: AlertOctagon,
    borderVar: "var(--semantic-loss)",
    textVar: "var(--semantic-loss-on-tint)",
  },
};

function severityTone(severity: SuggestionSeverity) {
  return SEVERITY_TONE[severity] ?? SEVERITY_TONE.info;
}

function SuggestionHeading({
  suggestion,
  density,
}: {
  suggestion: Suggestion;
  density: SuggestionCardDensity;
}) {
  if (density === "full") {
    return (
      <>
        <SeverityRow severity={suggestion.severity} />
        <p className="text-sm font-semibold leading-snug">{suggestion.title}</p>
      </>
    );
  }
  return <CompactHeading suggestion={suggestion} />;
}

/** Grupos fora do foco: o ícone carrega a severidade sozinho, com
 *  `role="img"` + aria-label para não perder o sinal no leitor de tela. */
function CompactHeading({ suggestion }: { suggestion: Suggestion }) {
  const tone = severityTone(suggestion.severity);
  const Icon = tone.Icon;
  return (
    <p className="flex items-start gap-2 text-sm font-semibold leading-snug">
      <Icon
        role="img"
        aria-label={`Severidade: ${tone.label}`}
        className="mt-0.5 h-4 w-4 shrink-0"
        style={{ color: tone.textVar }}
      />
      {suggestion.title}
    </p>
  );
}

function SeverityRow({ severity }: { severity: SuggestionSeverity }) {
  const tone = severityTone(severity);
  const Icon = tone.Icon;
  return (
    <div
      className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide"
      style={{ color: tone.textVar }}
    >
      <Icon className="h-4 w-4" aria-hidden="true" />
      <span>{tone.label}</span>
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
      <span data-testid="suggestion-created-month">
        {formatMonthShortPtBR(suggestion.created_at)}
      </span>
      {amount !== null && Number.isFinite(amount) && (
        <MonetaryValue value={amount} data-testid="suggestion-amount" />
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
