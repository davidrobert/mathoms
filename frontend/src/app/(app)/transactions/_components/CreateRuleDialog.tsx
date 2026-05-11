"use client";

/**
 * CreateRuleDialog — modal "Criar regra de categorização" (A12 P4).
 *
 * Fluxo:
 *   1. Defaults pré-preenchidos (keyword = descrição da tx; target = categoria escolhida).
 *   2. "Ver impacto" → POST /preview → contadores (total, fechados, manual prévio).
 *   3. "Criar" → POST /rules:
 *        - 201 sync (≤500 matches) → toast sucesso + close.
 *        - 202 async (>500)        → toast "background" + polling silencioso.
 *        - 409 conflito            → mostra regra existente.
 *        - 422 hard cap            → toast erro + close.
 *   4. ``requires_user_confirmation`` → warning amarelo + checkbox obrigatório.
 */

import { useState } from "react";
import { toast } from "sonner";
import { ApiError, getErrorCode } from "@/lib/api";
import type {
  ConflictEntry,
  RulePreviewResponse,
} from "@/lib/api";
import {
  createCategorizationRule,
  previewCategorizationRule,
  getRuleApplyStatus,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Lock, TriangleAlert } from "lucide-react";
import { formatCurrency } from "@/lib/format";

interface CreateRuleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string;
  defaultKeyword: string;
  defaultTargetCategory: string;
  categoryOptions: string[];
  /** Chamado após criação síncrona OU async (ambos ok pra refetch). */
  onCreated?: () => void;
}

function logEvent(name: string, payload: Record<string, unknown>): void {
  // Logging estruturado (sem PII — só length de keyword + counts numéricos).
  console.info("[learning_loop]", name, payload);
}

function PreviewSummary({ preview }: { preview: RulePreviewResponse }) {
  const valorBRL = preview.matches_amount_total_brl_cents / 100;
  const willApply =
    preview.matches_total -
    preview.matches_in_closed_months -
    preview.matches_with_manual_override -
    preview.matches_blocked_internal_transfers;
  return (
    <div className="rounded-md border border-border bg-muted/40 p-3 text-xs">
      <div className="mb-2 font-medium text-foreground">Impacto:</div>
      <ul className="space-y-1 text-muted-foreground">
        <li>
          <strong className="text-foreground">{preview.matches_total}</strong>{" "}
          transações no total
        </li>
        {preview.matches_in_closed_months > 0 && (
          <li className="text-[var(--semantic-warning)] inline-flex items-center gap-1">
            <Lock className="h-3 w-3" />
            <span>
              <strong>{preview.matches_in_closed_months}</strong> em meses já
              publicados (preservados)
            </span>
          </li>
        )}
        {preview.matches_with_manual_override > 0 && (
          <li>
            <strong className="text-foreground">
              {preview.matches_with_manual_override}
            </strong>{" "}
            com override manual prévio (preservados)
          </li>
        )}
        {preview.matches_blocked_internal_transfers > 0 && (
          <li>
            <strong className="text-foreground">
              {preview.matches_blocked_internal_transfers}
            </strong>{" "}
            transferências internas (preservadas)
          </li>
        )}
        <li>
          <strong className="text-foreground">{Math.max(0, willApply)}</strong>{" "}
          serão re-categorizadas
        </li>
        <li>
          <strong className="text-foreground">
            {formatCurrency(valorBRL, "BRL")}
          </strong>{" "}
          total impactado
        </li>
      </ul>
    </div>
  );
}

function ConflictNotice({ conflicts }: { conflicts: ConflictEntry[] }) {
  if (conflicts.length === 0) return null;
  return (
    <div className="rounded-md border border-border bg-muted/40 p-3 text-xs text-muted-foreground">
      <div className="mb-1 font-medium text-foreground">
        Já existe regra(s) com esta keyword:
      </div>
      <ul className="list-disc pl-4">
        {conflicts.map((c) => (
          <li key={c.rule_id}>
            <code>{c.rule_id.slice(0, 8)}</code> → {c.target_category} (prio{" "}
            {c.priority})
          </li>
        ))}
      </ul>
    </div>
  );
}

function WarningNotice({
  warnings,
}: {
  warnings: { code: string; message: string }[];
}) {
  if (warnings.length === 0) return null;
  return (
    <div className="space-y-1">
      {warnings.map((w) => (
        <div
          key={w.code}
          className="flex items-start gap-2 rounded-md border border-[var(--semantic-warning)]/30 bg-[var(--semantic-warning)]/5 p-2 text-xs text-[var(--semantic-warning)]"
        >
          <TriangleAlert className="mt-0.5 h-3.5 w-3.5 flex-shrink-0" />
          <span>{w.message}</span>
        </div>
      ))}
    </div>
  );
}

export function CreateRuleDialog({
  open,
  onOpenChange,
  workspaceId,
  defaultKeyword,
  defaultTargetCategory,
  categoryOptions,
  onCreated,
}: CreateRuleDialogProps) {
  const [keyword, setKeyword] = useState(defaultKeyword);
  const [targetCategory, setTargetCategory] = useState(defaultTargetCategory);
  const [preview, setPreview] = useState<RulePreviewResponse | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [confirmedImpact, setConfirmedImpact] = useState(false);

  // Reset quando reabre.
  function handleOpenChange(next: boolean) {
    if (!next) {
      setPreview(null);
      setPreviewError(null);
      setConfirmedImpact(false);
    } else {
      setKeyword(defaultKeyword);
      setTargetCategory(defaultTargetCategory);
    }
    onOpenChange(next);
  }

  async function handlePreview() {
    setPreviewing(true);
    setPreviewError(null);
    try {
      const resp = await previewCategorizationRule(workspaceId, {
        keyword,
        target_category: targetCategory,
      });
      setPreview(resp);
      logEvent("category_rule.preview", {
        keyword_len: keyword.length,
        matches_total: resp.matches_total,
        requires_confirmation: resp.requires_user_confirmation,
      });
    } catch (err) {
      setPreviewError(
        err instanceof ApiError ? err.detail : "Erro ao buscar impacto",
      );
    } finally {
      setPreviewing(false);
    }
  }

  function pollAsyncStatus(ruleId: string) {
    const started = Date.now();
    const interval = setInterval(async () => {
      if (Date.now() - started > 60_000) {
        clearInterval(interval);
        return;
      }
      try {
        const status = await getRuleApplyStatus(workspaceId, ruleId);
        if (status.status === "completed") {
          clearInterval(interval);
          toast.success(
            `Regra aplicada · ${status.applied_count} transações re-categorizadas`,
          );
          onCreated?.();
        } else if (status.status === "failed") {
          clearInterval(interval);
          toast.error(`Falha ao aplicar regra: ${status.error ?? "desconhecido"}`);
        }
      } catch {
        // Polling silencioso — não interrompe se 1 request falhar.
      }
    }, 5_000);
  }

  async function handleCreate() {
    setCreating(true);
    try {
      const result = await createCategorizationRule(workspaceId, {
        keyword,
        target_category: targetCategory,
        confirmed_visualized_months_impact: confirmedImpact,
      });
      logEvent("category_rule.created", {
        keyword_len: keyword.length,
        kind: result.kind,
      });
      if (result.kind === "async") {
        toast.info(
          "Aplicação em background · você será notificado quando concluir",
        );
        pollAsyncStatus(result.pending.rule_id);
      } else {
        toast.success(
          `Regra criada · ${result.rule.applied_count} transações re-categorizadas`,
        );
      }
      onCreated?.();
      handleOpenChange(false);
    } catch (err) {
      if (err instanceof ApiError) {
        const code = getErrorCode(err);
        if (err.status === 409 || code === "rule_already_exists") {
          toast.error("Já existe regra com esta keyword. Cancele ou edite a regra existente.");
        } else if (err.status === 422 && code === "hard_cap_exceeded") {
          toast.error(
            "Limite de 200 regras atingido. Desabilite regras inativas para criar mais.",
          );
          handleOpenChange(false);
        } else {
          toast.error(err.detail);
        }
      } else {
        toast.error("Erro ao criar regra");
      }
    } finally {
      setCreating(false);
    }
  }

  const needsConfirmation =
    preview?.requires_user_confirmation === true && !confirmedImpact;
  const canCreate =
    !!preview &&
    !creating &&
    keyword.length >= 2 &&
    !!targetCategory &&
    !needsConfirmation;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Criar regra de categorização</DialogTitle>
          <DialogDescription>
            Toda transação cujo texto contenha a palavra-chave será categorizada
            automaticamente.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-foreground">
              Palavra-chave
            </label>
            <Input
              value={keyword}
              onChange={(e) => {
                setKeyword(e.target.value);
                setPreview(null);
              }}
              data-testid="rule-keyword-input"
              minLength={2}
              maxLength={255}
            />
            {keyword.length > 0 && keyword.length < 4 && (
              <p className="mt-1 text-[10px] text-[var(--semantic-warning)]">
                Palavras curtas (&lt;4 caracteres) podem produzir muitos
                matches.
              </p>
            )}
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-foreground">
              Categorizada como
            </label>
            <select
              value={targetCategory}
              onChange={(e) => {
                setTargetCategory(e.target.value);
                setPreview(null);
              }}
              data-testid="rule-target-select"
              className="h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm outline-none focus:border-ring focus:ring-1 focus:ring-ring/50"
            >
              {categoryOptions.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {!preview && (
            <Button
              variant="outline"
              size="sm"
              onClick={handlePreview}
              disabled={previewing || keyword.length < 2}
              data-testid="rule-preview-button"
            >
              {previewing ? "Calculando…" : "Ver impacto antes de criar"}
            </Button>
          )}

          {previewError && (
            <div className="rounded-md border border-loss/30 bg-loss/5 p-2 text-xs text-loss">
              {previewError}
            </div>
          )}

          {preview && (
            <>
              <PreviewSummary preview={preview} />
              <ConflictNotice conflicts={preview.conflicts} />
              <WarningNotice warnings={preview.warnings} />

              {preview.requires_user_confirmation && (
                <label className="flex items-start gap-2 rounded-md border border-[var(--semantic-warning)]/30 bg-[var(--semantic-warning)]/5 p-2 text-xs">
                  <input
                    type="checkbox"
                    checked={confirmedImpact}
                    onChange={(e) => setConfirmedImpact(e.target.checked)}
                    data-testid="rule-confirm-impact"
                    className="mt-0.5"
                  />
                  <span className="text-foreground">
                    Sim, confirmo que esta regra vai recategorizar transações em
                    meses não-publicados que já visualizei.
                  </span>
                </label>
              )}
            </>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={creating}
          >
            Cancelar
          </Button>
          <Button
            onClick={handleCreate}
            disabled={!canCreate}
            data-testid="rule-create-button"
          >
            {creating ? "Criando…" : "Criar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
