"use client";

/**
 * /plano/meta-if — formulário de edição da meta IF vigente.
 *
 * Mostra todos os parâmetros num único form com simulador live.
 * Diferença vs. wizard: assume usuário experiente, não particiona em passos.
 * Edição = nova versão (append-only, preserva histórico).
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
  computeIFGoal,
  getIFGoal,
  ifMonthlyContributionDisplay,
  listReports,
  upsertIFGoal,
  ApiError,
  type IFGoalInputs,
  type IFGoalDerived,
  type IFGoalResponse,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";
import { GoalPremissasCard } from "@/components/plano/GoalPremissasCard";


const DEFAULT_INPUTS: IFGoalInputs = {
  renda_passiva_mensal_brl: 20000,
  trs_pct: 5.0,
  retorno_real_anual_pct: 6.0,
  horizonte_anos: 15,
  taxa_retirada_conservadora_pct: 4.0,
};


export default function MetaIFEditPage() {

  const router = useRouter();
  const { workspace, isLoading: wsLoading } = useCurrentWorkspace();
  const { canWrite } = usePermissions();

  const [inputs, setInputs] = useState<IFGoalInputs>(DEFAULT_INPUTS);
  const [derived, setDerived] = useState<IFGoalDerived | null>(null);
  const [goal, setGoal] = useState<IFGoalResponse | null>(null);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reportPatrimonio, setReportPatrimonio] = useState<number | undefined>();

  // Patrimônio do último relatório (para aporte ajustado no simulador)
  useEffect(() => {
    if (!workspace?.id) return;
    let cancelled = false;
    listReports(workspace.id)
      .then(({ reports }) => {
        if (cancelled) return;
        const p = reports.find((r) => r.patrimonio_liquido != null)
          ?.patrimonio_liquido;
        setReportPatrimonio(p ?? undefined);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [workspace?.id]);

  // Carrega goal vigente
  useEffect(() => {
    if (!workspace?.id) return;
    let cancelled = false;
    setLoading(true);
    getIFGoal(workspace.id)
      .then((g) => {
        if (cancelled) return;
        setInputs(g.inputs);
        setGoal(g);
      })
      .catch((err) => {
        // 404 = ainda não configurou; manda para wizard
        if (err instanceof ApiError && err.status === 404) {
          router.replace("/plano/meta-if/wizard");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [workspace?.id, router]);

  // Re-compute live
  useEffect(() => {
    if (!workspace?.id || loading) return;
    const handle = setTimeout(async () => {
      try {
        const resp = await computeIFGoal(workspace.id, {
          inputs,
          patrimonio_atual_brl: reportPatrimonio,
        });
        setDerived(resp.derived);
        setError(null);
      } catch (err) {
        if (err instanceof ApiError) setError(err.detail);
      }
    }, 200);
    return () => clearTimeout(handle);
  }, [workspace?.id, inputs, loading, reportPatrimonio]);

  async function handleSave() {
    if (!workspace) return;
    setSaving(true);
    setError(null);
    try {
      await upsertIFGoal(workspace.id, inputs, notes || undefined);
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
        title="Revisar meta IF"
        description="Edição cria nova versão — histórico é preservado"
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
        kind="if"
        mode="draft"
        inputs={inputs}
        derived={derived}
        existingEffectiveFrom={goal?.effective_from ?? null}
      />

      <Card>
        <CardContent className="space-y-6 py-6">
          <div>
            <Label htmlFor="renda">Renda passiva mensal (BRL)</Label>
            <Input
              id="renda"
              type="number"
              min={1}
              max={10_000_000}
              value={inputs.renda_passiva_mensal_brl}
              onChange={(e) =>
                setInputs({
                  ...inputs,
                  renda_passiva_mensal_brl: Number(e.target.value),
                })
              }
              className="mt-2 font-mono tabular-nums"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="trs">TRS (% a.a.)</Label>
              <Input
                id="trs"
                type="number"
                step={0.5}
                min={1}
                max={10}
                value={inputs.trs_pct}
                onChange={(e) =>
                  setInputs({ ...inputs, trs_pct: Number(e.target.value) })
                }
                className="mt-2 font-mono tabular-nums"
              />
            </div>
            <div>
              <Label htmlFor="conserv">TRS conservadora (% a.a.)</Label>
              <Input
                id="conserv"
                type="number"
                step={0.5}
                min={1}
                max={10}
                value={inputs.taxa_retirada_conservadora_pct ?? 4.0}
                onChange={(e) =>
                  setInputs({
                    ...inputs,
                    taxa_retirada_conservadora_pct: Number(e.target.value),
                  })
                }
                className="mt-2 font-mono tabular-nums"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="horizonte">Horizonte (anos)</Label>
              <Input
                id="horizonte"
                type="number"
                min={1}
                max={50}
                value={inputs.horizonte_anos}
                onChange={(e) =>
                  setInputs({
                    ...inputs,
                    horizonte_anos: Number(e.target.value),
                  })
                }
                className="mt-2 font-mono tabular-nums"
              />
            </div>
            <div>
              <Label htmlFor="retorno">Retorno real (% a.a.)</Label>
              <Input
                id="retorno"
                type="number"
                step={0.5}
                min={0}
                max={15}
                value={inputs.retorno_real_anual_pct}
                onChange={(e) =>
                  setInputs({
                    ...inputs,
                    retorno_real_anual_pct: Number(e.target.value),
                  })
                }
                className="mt-2 font-mono tabular-nums"
              />
            </div>
          </div>

          <div>
            <Label htmlFor="notes">Motivo da mudança (opcional)</Label>
            <Textarea
              id="notes"
              placeholder="Ex: revisão anual, mudou horizonte, etc."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="mt-2"
              rows={2}
              maxLength={1000}
            />
          </div>

          <Separator />

          {derived && (
            <div className="rounded-lg bg-muted/50 p-4 text-sm">
              <dl className="space-y-2">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Patrimônio-alvo</dt>
                  <dd className="font-mono tabular-nums font-semibold">
                    {formatCurrency(derived.if_meta_brl)}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">
                    Aporte mensal necessário
                  </dt>
                  <dd className="font-mono tabular-nums">
                    {formatCurrency(ifMonthlyContributionDisplay(derived))}/mês
                  </dd>
                </div>
                <div className="flex justify-between text-xs">
                  <dt className="text-muted-foreground">Meta conservadora</dt>
                  <dd className="font-mono tabular-nums text-muted-foreground">
                    {formatCurrency(derived.if_meta_conservadora_brl)}
                  </dd>
                </div>
              </dl>
              {derived.aporte_mensal_com_patrimonio_atual_brl != null &&
                derived.patrimonio_atual_utilizado_brl != null &&
                derived.aporte_mensal_com_patrimonio_atual_brl !==
                  derived.aporte_necessario_mensal_brl && (
                  <p className="mt-2 text-xs text-muted-foreground">
                    Simulação com patrimônio do último relatório (
                    {formatCurrency(derived.patrimonio_atual_utilizado_brl)}).
                    Partindo de zero:{" "}
                    {formatCurrency(derived.aporte_necessario_mensal_brl)}/mês.
                  </p>
                )}
            </div>
          )}

          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          <div className="flex items-center justify-end gap-3">
            {!canWrite && (
              <span className="text-xs text-muted-foreground">
                Você está acompanhando — edição indisponível.
              </span>
            )}
            <Button
              onClick={handleSave}
              disabled={saving || !derived || !canWrite}
              title={!canWrite ? "Apenas owner/coadministrador pode editar" : undefined}
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
