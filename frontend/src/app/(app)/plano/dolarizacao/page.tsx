"use client";

/**
 * /plano/dolarizacao — formulario de edicao da meta de dolarizacao.
 *
 * Live compute via computeDolarGoal (debounce 200ms).
 * Mostra horizonte estimado em meses + cambio utilizado.
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
  computeDolarGoal,
  getDolarGoal,
  upsertDolarGoal,
  ApiError,
  type DolarGoalInputs,
  type DolarGoalComputeResponse,
  type DolarGoalResponse,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";


const DEFAULT_INPUTS: DolarGoalInputs = {
  meta_usd: 20000,
  aporte_mensal_brl: 2000,
};


export default function DolarizacaoEditPage() {
  const router = useRouter();
  const { workspace, isLoading: wsLoading } = useCurrentWorkspace();
  const { canWrite } = usePermissions();

  const [inputs, setInputs] = useState<DolarGoalInputs>(DEFAULT_INPUTS);
  const [computed, setComputed] = useState<DolarGoalComputeResponse | null>(
    null
  );
  const [goal, setGoal] = useState<DolarGoalResponse | null>(null);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load existing goal
  useEffect(() => {
    if (!workspace?.id) return;
    let cancelled = false;
    setLoading(true);
    getDolarGoal(workspace.id)
      .then((g) => {
        if (cancelled) return;
        setInputs(g.inputs);
        setGoal(g);
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          router.replace("/plano/dolarizacao/wizard");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [workspace?.id, router]);

  // Live compute (debounced)
  useEffect(() => {
    if (!workspace?.id || loading) return;
    const handle = setTimeout(async () => {
      try {
        const resp = await computeDolarGoal(workspace.id, inputs);
        setComputed(resp);
        setError(null);
      } catch (err) {
        if (err instanceof ApiError) setError(err.detail);
      }
    }, 200);
    return () => clearTimeout(handle);
  }, [workspace?.id, inputs, loading]);

  async function handleSave() {
    if (!workspace) return;
    setSaving(true);
    setError(null);
    try {
      await upsertDolarGoal(workspace.id, inputs, notes || undefined);
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

  const meses = computed?.derived.horizonte_estimado_meses ?? 0;
  const anos = (meses / 12).toFixed(1);
  const cambio = computed?.cambio_utilizado ?? 0;

  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      <PageHeader
        title="Dolarizacao"
        description="Meta de acumulacao em USD"
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
          Ultima edicao
          {goal.created_by_name ? ` por ${goal.created_by_name}` : ""}
          {goal.updated_at
            ? ` em ${new Date(goal.updated_at).toLocaleDateString("pt-BR")}`
            : ""}
          .
        </p>
      )}

      <Card>
        <CardContent className="space-y-6 py-6">
          <div>
            <Label htmlFor="metausd">Meta de acumulacao (USD)</Label>
            <Input
              id="metausd"
              type="number"
              min={1}
              value={inputs.meta_usd}
              onChange={(e) =>
                setInputs({ ...inputs, meta_usd: Number(e.target.value) })
              }
              className="mt-2 font-mono tabular-nums"
            />
          </div>

          <div>
            <Label htmlFor="aportebrl">Aporte mensal (BRL)</Label>
            <Input
              id="aportebrl"
              type="number"
              min={1}
              value={inputs.aporte_mensal_brl}
              onChange={(e) =>
                setInputs({
                  ...inputs,
                  aporte_mensal_brl: Number(e.target.value),
                })
              }
              className="mt-2 font-mono tabular-nums"
            />
          </div>

          <div>
            <Label htmlFor="notes">Motivo da mudanca (opcional)</Label>
            <Textarea
              id="notes"
              placeholder="Ex: revisao de meta"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="mt-2"
              rows={2}
              maxLength={1000}
            />
          </div>

          <Separator />

          {computed && (
            <div className="rounded-lg bg-muted/50 p-4 text-sm">
              <dl className="space-y-2">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">
                    Horizonte estimado
                  </dt>
                  <dd className="font-mono tabular-nums font-semibold">
                    {meses} meses (~{anos} anos)
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Cambio utilizado</dt>
                  <dd className="font-mono tabular-nums">
                    {formatCurrency(cambio)}
                  </dd>
                </div>
              </dl>
              <p className="mt-2 text-xs text-muted-foreground">
                Estimativa: {meses} meses (~{anos} anos) ao cambio de{" "}
                {formatCurrency(cambio)}
              </p>
            </div>
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}

          <div className="flex items-center justify-end gap-3">
            {!canWrite && (
              <span className="text-xs text-muted-foreground">
                Voce esta acompanhando — edicao indisponivel.
              </span>
            )}
            <Button
              onClick={handleSave}
              disabled={saving || !computed || !canWrite}
              title={
                !canWrite
                  ? "Apenas owner/coadministrador pode editar"
                  : undefined
              }
            >
              {saving ? "Salvando..." : "Salvar nova versao"}
              <Save className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
