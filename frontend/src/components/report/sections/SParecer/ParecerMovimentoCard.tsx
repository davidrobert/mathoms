"use client";

// ADR-199 Ato 5 §5b/§5c — Card de "movimento" (sugestão LLM).
// 3 ações inline: Promover para ação | Já considerei | Descartar com motivo.
// Promover delega para `useSuggestionActions.accept` que chama o endpoint
// existente /suggestions/{id}/accept (ADR-153).

import { useState } from "react";
import { ArrowRight, Check, ChevronDown, X } from "lucide-react";

import { MonetaryValue } from "../../MonetaryValue";
import { ParecerAncoraChips } from "./ParecerAncoraChips";
import type { ImpactoTipo, Prioridade, Sugestao } from "@/lib/api";
import { useSuggestionActions } from "@/hooks/useSuggestionActions";

// Mesma separação de `SEVERIDADE_TONE` (A40.l22): `token` é decorativo (bolinha
// + `border-left`), `textToken` é o rótulo. P1 em `--semantic-alert` sobre
// `--surface-card` dava 2,06:1 a 10px — não aparecia no axe só porque nenhuma
// fixture tinha sugestão P1, que é verde-por-fixture, não ausência de defeito.
const PRIORIDADE_TONE: Record<
  Prioridade,
  { token: string; textToken: string; label: string }
> = {
  P0: {
    token: "var(--semantic-loss)",
    textToken: "var(--semantic-loss)",
    label: "Urgente",
  },
  P1: {
    token: "var(--semantic-alert)",
    textToken: "var(--report-alert-warning-text)",
    label: "Importante",
  },
  P2: {
    token: "var(--semantic-info-financial)",
    textToken: "var(--semantic-info-financial)",
    label: "Oportunidade",
  },
};

// ADR-220: label semântico do impacto por tipo. Evita "Impacto estimado: R$ X"
// genérico que confunde fluxo com estoque. Fallback para "outro" / ausente.
const IMPACTO_TIPO_LABEL: Record<ImpactoTipo, string> = {
  patrimonio_alvo: "Patrimônio-alvo",
  fluxo_anual: "Fluxo anual estimado",
  economia_anual_irpf: "Economia anual em IR",
  gap_protecao: "Capital de seguro faltante",
  outro: "Impacto estimado",
};

function impactoLabel(tipo: ImpactoTipo | null | undefined): string {
  if (tipo == null) return IMPACTO_TIPO_LABEL.outro;
  return IMPACTO_TIPO_LABEL[tipo] ?? IMPACTO_TIPO_LABEL.outro;
}

type DismissReason = "nao_se_aplica" | "discordo_diagnostico" | "outro";
const DISMISS_REASONS: Array<{ value: DismissReason; label: string }> = [
  { value: "nao_se_aplica", label: "Não se aplica" },
  { value: "discordo_diagnostico", label: "Discordo do diagnóstico" },
  { value: "outro", label: "Outro motivo" },
];

interface ParecerMovimentoCardProps {
  sugestao: Sugestao;
  workspaceId: string;
  /** Override para testes/PDF — esconde ações. */
  readOnly?: boolean;
  /** Callback após aceite/descarte — caller pode invalidar parecer. */
  onMutate?: () => void | Promise<void>;
}

export function ParecerMovimentoCard({
  sugestao,
  workspaceId,
  readOnly = false,
  onMutate,
}: ParecerMovimentoCardProps) {
  const actions = useSuggestionActions(workspaceId);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [showDismiss, setShowDismiss] = useState(false);

  const tone = PRIORIDADE_TONE[sugestao.prioridade];
  const impactoEstimado = sugestao.impacto_estimado;

  async function handleAccept() {
    setBusy(true);
    try {
      // ADR-214 — server gera o code da Decision (D{N}); response inclui
      // `accepted_decision_code` que poderíamos exibir em toast, mas
      // aqui o feedback é genérico (card está em modo read-only de parecer).
      const result = await actions.accept({
        suggestionRef: sugestao.suggestion_dedup_key,
      });
      const codeMsg = result.accepted_decision_code
        ? `Promovida como ${result.accepted_decision_code} no plano.`
        : "Promovida para o plano de ação.";
      setFeedback(codeMsg);
      await onMutate?.();
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : "Erro ao promover.");
    } finally {
      setBusy(false);
    }
  }

  async function handleDismiss(reason: DismissReason | "ja_considerei") {
    setBusy(true);
    try {
      await actions.dismiss({
        suggestionRef: sugestao.suggestion_dedup_key,
        reason,
      });
      setFeedback("Movimento descartado.");
      setShowDismiss(false);
      await onMutate?.();
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : "Erro ao descartar.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <article
      className="rounded-[var(--radius-card)] border border-[var(--surface-border)] border-l-[3px] bg-[var(--surface-card)] p-4"
      style={{ borderLeftColor: tone.token }}
      aria-labelledby={`movimento-${sugestao.suggestion_dedup_key}-title`}
      data-testid="parecer-movimento-card"
      data-priority={sugestao.prioridade}
    >
      <header className="mb-2 flex items-baseline justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className="inline-flex h-2 w-2 shrink-0 rounded-full"
            style={{ backgroundColor: tone.token }}
            aria-hidden="true"
          />
          <span
            className="text-[10px] font-semibold uppercase tracking-wide"
            style={{ color: tone.textToken }}
          >
            {sugestao.prioridade} · {tone.label}
          </span>
        </div>
        <span className="text-[10px] text-[var(--surface-muted-foreground)]">
          §{sugestao.section_id} · {sugestao.tema_canonico}
        </span>
      </header>

      <h4
        id={`movimento-${sugestao.suggestion_dedup_key}-title`}
        className="font-heading text-base font-semibold text-[var(--surface-foreground)]"
      >
        {sugestao.acao}
      </h4>
      <p className="mt-1 text-sm text-[var(--surface-muted-foreground)]">
        {sugestao.impacto_qualitativo}
      </p>

      {impactoEstimado && (
        <p className="mt-2 text-xs">
          <span className="text-[var(--surface-muted-foreground)]">
            {impactoLabel(impactoEstimado.tipo)}:{" "}
          </span>
          <MonetaryValue
            value={Number(impactoEstimado.valor_estimado_brl)}
            size="body"
          />
          {impactoEstimado.tipo !== "patrimonio_alvo" && (
            <span className="text-[var(--surface-muted-foreground)]">
              {" "}/ {impactoEstimado.unidade === "ano" ? "ano" : "mês"}
            </span>
          )}
          <span
            className="ml-1 text-[10px] text-[var(--surface-muted-foreground)]"
            title={impactoEstimado.caveat}
          >
            (estimativa)
          </span>
        </p>
      )}

      <ParecerAncoraChips ancoras={sugestao.ancoras} />

      {!readOnly && (
        <div className="parecer-action mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={handleAccept}
            disabled={busy}
            className="inline-flex items-center gap-1 rounded-md border border-[var(--brand-accent)] bg-[var(--brand-accent)] px-3 py-1.5 text-xs font-medium text-[var(--surface-card)] hover:opacity-90 disabled:opacity-50"
            data-testid="movimento-promover"
          >
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
            Promover para ação
          </button>
          <button
            type="button"
            onClick={() => handleDismiss("ja_considerei")}
            disabled={busy}
            className="inline-flex items-center gap-1 rounded-md border border-[var(--surface-border)] px-3 py-1.5 text-xs text-[var(--surface-foreground)] hover:bg-[var(--surface-muted)] disabled:opacity-50"
          >
            <Check className="h-3.5 w-3.5" aria-hidden="true" />
            Já considerei
          </button>
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowDismiss(!showDismiss)}
              disabled={busy}
              className="inline-flex items-center gap-1 rounded-md border border-[var(--surface-border)] px-3 py-1.5 text-xs text-[var(--surface-muted-foreground)] hover:bg-[var(--surface-muted)] disabled:opacity-50"
              aria-haspopup="menu"
              aria-expanded={showDismiss}
            >
              <X className="h-3.5 w-3.5" aria-hidden="true" />
              Descartar com motivo
              <ChevronDown className="h-3 w-3" aria-hidden="true" />
            </button>
            {showDismiss && (
              <div
                role="menu"
                className="absolute right-0 z-10 mt-1 w-48 rounded-md border border-[var(--surface-border)] bg-[var(--surface-card)] py-1 shadow"
              >
                {DISMISS_REASONS.map((r) => (
                  <button
                    key={r.value}
                    type="button"
                    role="menuitem"
                    onClick={() => handleDismiss(r.value)}
                    className="block w-full px-3 py-1.5 text-left text-xs text-[var(--surface-foreground)] hover:bg-[var(--surface-muted)]"
                  >
                    {r.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {feedback && (
        <p
          className="mt-2 text-xs text-[var(--surface-muted-foreground)]"
          role="status"
          aria-live="polite"
        >
          {feedback}
        </p>
      )}
    </article>
  );
}
