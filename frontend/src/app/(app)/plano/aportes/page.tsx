"use client";

/**
 * /plano/aportes — formulario de edicao da meta de aportes mensais.
 *
 * Pattern: mesmo que meta-if/page.tsx.
 * Distribuicao: rows dinamicas com destino + valor.
 * Live compute via computeAporteGoal (debounce 200ms).
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Plus, Save, Trash2 } from "lucide-react";
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
  computeAporteGoal,
  getAporteGoal,
  upsertAporteGoal,
  ApiError,
  type AporteGoalInputs,
  type AporteGoalDerived,
  type AporteGoalResponse,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";


interface DistRow {
  destino: string;
  valor: number;
}

const DEFAULT_INPUTS: AporteGoalInputs = {
  meta_aporte_mensal_brl: 10000,
  dia_aporte: 5,
  periodo_inicio: "Imediato",
  distribuicao: {},
};

function inputsFromRows(
  base: AporteGoalInputs,
  rows: DistRow[]
): AporteGoalInputs {
  const distribuicao: Record<string, number> = {};
  for (const r of rows) {
    if (r.destino.trim()) distribuicao[r.destino.trim()] = r.valor;
  }
  return { ...base, distribuicao };
}

function rowsFromInputs(inputs: AporteGoalInputs): DistRow[] {
  if (!inputs.distribuicao || Object.keys(inputs.distribuicao).length === 0)
    return [];
  return Object.entries(inputs.distribuicao).map(([destino, valor]) => ({
    destino,
    valor,
  }));
}


export default function AportesEditPage() {
  const router = useRouter();
  const { workspace, isLoading: wsLoading } = useCurrentWorkspace();
  const { canWrite } = usePermissions();

  const [inputs, setInputs] = useState<AporteGoalInputs>(DEFAULT_INPUTS);
  const [rows, setRows] = useState<DistRow[]>([]);
  const [derived, setDerived] = useState<AporteGoalDerived | null>(null);
  const [goal, setGoal] = useState<AporteGoalResponse | null>(null);
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load existing goal
  useEffect(() => {
    if (!workspace?.id) return;
    let cancelled = false;
    setLoading(true);
    getAporteGoal(workspace.id)
      .then((g) => {
        if (cancelled) return;
        setInputs(g.inputs);
        setRows(rowsFromInputs(g.inputs));
        setGoal(g);
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 404) {
          router.replace("/plano/aportes/wizard");
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
    const fullInputs = inputsFromRows(inputs, rows);
    const handle = setTimeout(async () => {
      try {
        const resp = await computeAporteGoal(workspace.id, fullInputs);
        setDerived(resp.derived);
        setError(null);
      } catch (err) {
        if (err instanceof ApiError) setError(err.detail);
      }
    }, 200);
    return () => clearTimeout(handle);
  }, [workspace?.id, inputs, rows, loading]);

  const distSum = rows.reduce((s, r) => s + r.valor, 0);
  const distMismatch =
    rows.length > 0 && distSum !== inputs.meta_aporte_mensal_brl;

  async function handleSave() {
    if (!workspace) return;
    setSaving(true);
    setError(null);
    try {
      const fullInputs = inputsFromRows(inputs, rows);
      await upsertAporteGoal(workspace.id, fullInputs, notes || undefined);
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
        title="Aportes mensais"
        description="Edicao cria nova versao — historico e preservado"
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
            <Label htmlFor="meta">Meta de aporte mensal (BRL)</Label>
            <Input
              id="meta"
              type="number"
              min={1}
              value={inputs.meta_aporte_mensal_brl}
              onChange={(e) =>
                setInputs({
                  ...inputs,
                  meta_aporte_mensal_brl: Number(e.target.value),
                })
              }
              className="mt-2 font-mono tabular-nums"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="dia">Dia do aporte (1-28)</Label>
              <Input
                id="dia"
                type="number"
                min={1}
                max={28}
                value={inputs.dia_aporte}
                onChange={(e) =>
                  setInputs({
                    ...inputs,
                    dia_aporte: Number(e.target.value),
                  })
                }
                className="mt-2 font-mono tabular-nums"
              />
            </div>
            <div>
              <Label htmlFor="periodo">Periodo de inicio</Label>
              <Input
                id="periodo"
                type="text"
                value={inputs.periodo_inicio ?? ""}
                onChange={(e) =>
                  setInputs({ ...inputs, periodo_inicio: e.target.value })
                }
                className="mt-2"
                placeholder="Imediato"
              />
            </div>
          </div>

          <Separator />

          {/* Distribuicao */}
          <div>
            <div className="mb-3 flex items-center justify-between">
              <Label>Distribuicao por destino</Label>
              <Button
                variant="outline"
                size="sm"
                type="button"
                onClick={() =>
                  setRows([...rows, { destino: "", valor: 0 }])
                }
              >
                <Plus className="mr-1 h-3 w-3" /> Adicionar
              </Button>
            </div>

            {rows.length === 0 && (
              <p className="text-xs text-muted-foreground">
                Nenhum destino definido. Opcional.
              </p>
            )}

            <div className="space-y-2">
              {rows.map((row, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <Input
                    placeholder="Destino (ex: Tesouro Direto)"
                    value={row.destino}
                    onChange={(e) => {
                      const next = [...rows];
                      next[idx] = { ...next[idx], destino: e.target.value };
                      setRows(next);
                    }}
                    className="flex-1"
                  />
                  <Input
                    type="number"
                    min={0}
                    value={row.valor}
                    onChange={(e) => {
                      const next = [...rows];
                      next[idx] = {
                        ...next[idx],
                        valor: Number(e.target.value),
                      };
                      setRows(next);
                    }}
                    className="w-32 font-mono tabular-nums"
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    type="button"
                    onClick={() => setRows(rows.filter((_, i) => i !== idx))}
                  >
                    <Trash2 className="h-4 w-4 text-muted-foreground" />
                  </Button>
                </div>
              ))}
            </div>

            {rows.length > 0 && (
              <p
                className={
                  "mt-2 text-xs " +
                  (distMismatch ? "text-destructive" : "text-muted-foreground")
                }
              >
                Total distribuido:{" "}
                <span className="font-mono tabular-nums">
                  {formatCurrency(distSum)}
                </span>{" "}
                / {formatCurrency(inputs.meta_aporte_mensal_brl)}
                {distMismatch && " — soma nao confere com a meta"}
              </p>
            )}
          </div>

          <div>
            <Label htmlFor="notes">Motivo da mudanca (opcional)</Label>
            <Textarea
              id="notes"
              placeholder="Ex: ajuste de aportes pos-bonus"
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
                  <dt className="text-muted-foreground">Aporte anual</dt>
                  <dd className="font-mono tabular-nums font-semibold">
                    {formatCurrency(derived.aporte_anual_brl)}
                  </dd>
                </div>
                {Object.entries(derived.distribuicao_pct).length > 0 && (
                  <div>
                    <dt className="mb-1 text-muted-foreground">
                      Distribuicao (%)
                    </dt>
                    {Object.entries(derived.distribuicao_pct).map(
                      ([dest, pct]) => (
                        <dd
                          key={dest}
                          className="flex justify-between text-xs"
                        >
                          <span>{dest}</span>
                          <span className="font-mono tabular-nums">
                            {pct.toFixed(1)}%
                          </span>
                        </dd>
                      )
                    )}
                  </div>
                )}
              </dl>
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
              disabled={saving || !derived || !canWrite}
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
