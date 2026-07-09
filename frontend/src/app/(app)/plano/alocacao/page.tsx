"use client";

/**
 * /plano/alocacao — formulario de edicao da alocacao-alvo.
 *
 * 7 classes AUVP (v2, ADR-141) agrupadas por família com subtotal + soma
 * validada. Compartilha os componentes de distribuição e rebalanceamento
 * com o wizard (ADR-141 §Emenda item 11).
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Save } from "lucide-react";
import Link from "next/link";

import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";

import { useCurrentWorkspace } from "@/lib/useCurrentWorkspace";
import { usePermissions } from "@/lib/usePermissions";
import {
  getAlocacaoGoal,
  upsertAlocacaoGoal,
  ApiError,
  type AlocacaoGoalInputs,
  type AlocacaoGoalResponse,
  type AlocacaoGoalDerived,
  type RebalanceamentoModo,
} from "@/lib/api";
import { GoalPremissasCard } from "@/components/plano/GoalPremissasCard";

import { AlocacaoDistributionFields } from "./wizard/_components/AlocacaoDistributionFields";
import { RebalanceamentoModeSelector } from "./wizard/_components/RebalanceamentoModeSelector";
import type { AlocacaoProgressState } from "./wizard/_components/AlocacaoProgress";
import {
  completeWithCaixa,
  PRESETS,
  sumPcts,
  type Pcts,
} from "./wizard/_components/constants";

const DEFAULT_INPUTS: AlocacaoGoalInputs = {
  ...PRESETS.Moderado,
  rebalanceamento_modo: "por_aporte",
  instrumentos: undefined,
};

export default function AlocacaoEditPage() {
  const router = useRouter();
  const { workspace, isLoading: wsLoading } = useCurrentWorkspace();
  const { canWrite } = usePermissions();

  const [inputs, setInputs] = useState<AlocacaoGoalInputs>(DEFAULT_INPUTS);
  const [goal, setGoal] = useState<AlocacaoGoalResponse | null>(null);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Vermelho só ao tentar salvar com Σ≠100 (ADR-141 emenda item 11).
  const [attemptedSave, setAttemptedSave] = useState(false);

  const soma = sumPcts(inputs);
  const somaValida = soma === 100;
  const progressState: AlocacaoProgressState = somaValida
    ? "ok"
    : attemptedSave
      ? "danger"
      : "warning";

  const alocacaoDerived: AlocacaoGoalDerived = { soma_percentuais: soma };

  // Load existing goal
  useEffect(() => {
    if (!workspace?.id) return;
    let cancelled = false;
    setLoading(true);
    getAlocacaoGoal(workspace.id)
      .then((g) => {
        if (cancelled) return;
        setInputs(g.inputs);
        setGoal(g);
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          router.replace("/plano/alocacao/wizard");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [workspace?.id, router]);

  function updateInputs(next: Partial<AlocacaoGoalInputs>) {
    setInputs((prev) => ({ ...prev, ...next }));
    setAttemptedSave(false);
  }

  function setPcts(next: Pcts) {
    updateInputs(next);
  }

  function setInstrumento(key: "renda_fixa" | "renda_variavel", value: string) {
    setInputs((prev) => ({
      ...prev,
      instrumentos: { ...(prev.instrumentos ?? {}), [key]: value },
    }));
  }

  async function handleSave() {
    if (!workspace) return;
    if (!somaValida) {
      setAttemptedSave(true);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await upsertAlocacaoGoal(workspace.id, inputs, notes || undefined);
      router.push("/plano");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.detail);
      } else {
        setError("Erro ao salvar meta");
      }
      setSaving(false);
    }
  }

  if (wsLoading || loading) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-8">
        <Skeleton className="mb-6 h-8 w-64" />
        <Skeleton className="h-96" />
      </div>
    );
  }

  if (!workspace) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-8">
        <p className="text-muted-foreground">Nenhum workspace encontrado.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      <PageHeader
        title="Alocação-alvo"
        description="Distribuição ideal por classe de ativo"
        actions={
          <Button
            variant="ghost"
            nativeButton={false}
            render={<Link href="/plano" />}
          >
            <ArrowLeft className="mr-2 h-4 w-4" /> Voltar
          </Button>
        }
      />

      {goal?.converted_from != null && (
        <p className="mb-3 text-xs text-muted-foreground">
          Alvo convertido automaticamente — revise e confirme.
        </p>
      )}

      {goal && (goal.created_by_name || goal.updated_at) && (
        <p className="mb-3 text-xs text-muted-foreground">
          Última edição
          {goal.created_by_name ? ` por ${goal.created_by_name}` : ""}
          {goal.updated_at
            ? ` em ${new Date(goal.updated_at).toLocaleDateString("pt-BR")}`
            : ""}
          .
        </p>
      )}

      <GoalPremissasCard
        className="mb-4"
        kind="alocacao"
        mode="draft"
        inputs={inputs}
        derived={alocacaoDerived}
        existingEffectiveFrom={goal?.effective_from ?? null}
      />

      <Card>
        <CardContent className="space-y-6 py-6">
          <AlocacaoDistributionFields
            pcts={inputs}
            onChange={setPcts}
            soma={soma}
            progressState={progressState}
            onCompleteWithCaixa={() => updateInputs(completeWithCaixa(inputs))}
          />

          <Separator />

          {/* Instruments */}
          <div>
            <Label htmlFor="rf-inst">Instrumentos de renda fixa</Label>
            <Input
              id="rf-inst"
              type="text"
              placeholder="Ex: Tesouro IPCA+, CDB, LCI"
              value={inputs.instrumentos?.renda_fixa ?? ""}
              onChange={(e) => setInstrumento("renda_fixa", e.target.value)}
              className="mt-2"
            />
          </div>

          <div>
            <Label htmlFor="rv-inst">Instrumentos de renda variável</Label>
            <Input
              id="rv-inst"
              type="text"
              placeholder="Ex: ETFs, FIIs, IVVB11"
              value={inputs.instrumentos?.renda_variavel ?? ""}
              onChange={(e) => setInstrumento("renda_variavel", e.target.value)}
              className="mt-2"
            />
          </div>

          <div>
            <Label>Rebalanceamento</Label>
            <div className="mt-2">
              <RebalanceamentoModeSelector
                value={inputs.rebalanceamento_modo}
                onChange={(v: RebalanceamentoModo) =>
                  updateInputs({ rebalanceamento_modo: v })
                }
              />
            </div>
          </div>

          <div>
            <Label htmlFor="notes">Motivo da mudança (opcional)</Label>
            <Textarea
              id="notes"
              placeholder="Ex: revisão de perfil de risco"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="mt-2"
              rows={2}
              maxLength={1000}
            />
          </div>

          <Separator />

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex items-center justify-end gap-3">
            {!canWrite && (
              <span className="text-xs text-muted-foreground">
                Você está acompanhando — edição indisponível.
              </span>
            )}
            <Button
              onClick={handleSave}
              disabled={saving || !canWrite}
              title={
                !canWrite
                  ? "Apenas owner/coadministrador pode editar"
                  : !somaValida
                    ? "A soma dos percentuais deve ser 100%"
                    : undefined
              }
            >
              {saving ? "Salvando..." : "Salvar nova versão"}
              <Save className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
