"use client";

/**
 * /plano/alocacao — formulario de edicao da alocacao-alvo.
 *
 * 4 classes de ativo com % + soma validada.
 * Barra visual de proporcao + instrumentos preferidos.
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, CheckCircle2, Save, XCircle } from "lucide-react";
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
} from "@/lib/api";


const DEFAULT_INPUTS: AlocacaoGoalInputs = {
  renda_fixa_pct: 40,
  acoes_pct: 30,
  imoveis_reits_pct: 15,
  liquidez_usd_pct: 15,
  instrumentos_rf: "",
  instrumentos_rv: "",
  rebalanceamento: "Anual",
};

const COLORS = {
  renda_fixa: "bg-blue-500",
  acoes: "bg-emerald-500",
  imoveis: "bg-amber-500",
  usd: "bg-purple-500",
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

  const soma =
    inputs.renda_fixa_pct +
    inputs.acoes_pct +
    inputs.imoveis_reits_pct +
    inputs.liquidez_usd_pct;
  const somaValida = soma === 100;

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

  async function handleSave() {
    if (!workspace) return;
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
        title="Alocacao-alvo"
        description="Distribuicao ideal por classe de ativo"
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
          {/* Percentage inputs */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="rf">Renda fixa (%)</Label>
              <Input
                id="rf"
                type="number"
                min={0}
                max={100}
                value={inputs.renda_fixa_pct}
                onChange={(e) =>
                  setInputs({
                    ...inputs,
                    renda_fixa_pct: Number(e.target.value),
                  })
                }
                className="mt-2 font-mono tabular-nums"
              />
            </div>
            <div>
              <Label htmlFor="acoes">Acoes (%)</Label>
              <Input
                id="acoes"
                type="number"
                min={0}
                max={100}
                value={inputs.acoes_pct}
                onChange={(e) =>
                  setInputs({
                    ...inputs,
                    acoes_pct: Number(e.target.value),
                  })
                }
                className="mt-2 font-mono tabular-nums"
              />
            </div>
            <div>
              <Label htmlFor="imoveis">Imoveis/REITs (%)</Label>
              <Input
                id="imoveis"
                type="number"
                min={0}
                max={100}
                value={inputs.imoveis_reits_pct}
                onChange={(e) =>
                  setInputs({
                    ...inputs,
                    imoveis_reits_pct: Number(e.target.value),
                  })
                }
                className="mt-2 font-mono tabular-nums"
              />
            </div>
            <div>
              <Label htmlFor="usd">Liquidez USD (%)</Label>
              <Input
                id="usd"
                type="number"
                min={0}
                max={100}
                value={inputs.liquidez_usd_pct}
                onChange={(e) =>
                  setInputs({
                    ...inputs,
                    liquidez_usd_pct: Number(e.target.value),
                  })
                }
                className="mt-2 font-mono tabular-nums"
              />
            </div>
          </div>

          {/* Sum indicator */}
          <div className="flex items-center gap-2 text-sm">
            {somaValida ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            ) : (
              <XCircle className="h-4 w-4 text-destructive" />
            )}
            <span
              className={somaValida ? "text-emerald-600" : "text-destructive"}
            >
              Total: <span className="font-mono tabular-nums">{soma}%</span>
              {!somaValida && " — deve somar 100%"}
            </span>
          </div>

          {/* Visual bar */}
          <div className="h-4 w-full overflow-hidden rounded-full bg-muted">
            <div className="flex h-full">
              {inputs.renda_fixa_pct > 0 && (
                <div
                  className={`${COLORS.renda_fixa} transition-all`}
                  style={{ width: `${inputs.renda_fixa_pct}%` }}
                  title={`Renda fixa: ${inputs.renda_fixa_pct}%`}
                />
              )}
              {inputs.acoes_pct > 0 && (
                <div
                  className={`${COLORS.acoes} transition-all`}
                  style={{ width: `${inputs.acoes_pct}%` }}
                  title={`Acoes: ${inputs.acoes_pct}%`}
                />
              )}
              {inputs.imoveis_reits_pct > 0 && (
                <div
                  className={`${COLORS.imoveis} transition-all`}
                  style={{ width: `${inputs.imoveis_reits_pct}%` }}
                  title={`Imoveis/REITs: ${inputs.imoveis_reits_pct}%`}
                />
              )}
              {inputs.liquidez_usd_pct > 0 && (
                <div
                  className={`${COLORS.usd} transition-all`}
                  style={{ width: `${inputs.liquidez_usd_pct}%` }}
                  title={`Liquidez USD: ${inputs.liquidez_usd_pct}%`}
                />
              )}
            </div>
          </div>

          {/* Legend */}
          <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <span className={`inline-block h-2 w-2 rounded-full ${COLORS.renda_fixa}`} />
              Renda fixa
            </span>
            <span className="flex items-center gap-1">
              <span className={`inline-block h-2 w-2 rounded-full ${COLORS.acoes}`} />
              Acoes
            </span>
            <span className="flex items-center gap-1">
              <span className={`inline-block h-2 w-2 rounded-full ${COLORS.imoveis}`} />
              Imoveis/REITs
            </span>
            <span className="flex items-center gap-1">
              <span className={`inline-block h-2 w-2 rounded-full ${COLORS.usd}`} />
              Liquidez USD
            </span>
          </div>

          <Separator />

          {/* Instruments */}
          <div>
            <Label htmlFor="rf-inst">Instrumentos de renda fixa</Label>
            <Input
              id="rf-inst"
              type="text"
              placeholder="Ex: Tesouro IPCA+, CDB, LCI"
              value={inputs.instrumentos_rf ?? ""}
              onChange={(e) =>
                setInputs({ ...inputs, instrumentos_rf: e.target.value })
              }
              className="mt-2"
            />
          </div>

          <div>
            <Label htmlFor="rv-inst">Instrumentos de renda variavel</Label>
            <Input
              id="rv-inst"
              type="text"
              placeholder="Ex: ETFs, FIIs, IVVB11"
              value={inputs.instrumentos_rv ?? ""}
              onChange={(e) =>
                setInputs({ ...inputs, instrumentos_rv: e.target.value })
              }
              className="mt-2"
            />
          </div>

          <div>
            <Label htmlFor="rebal">Rebalanceamento</Label>
            <Input
              id="rebal"
              type="text"
              placeholder="Anual"
              value={inputs.rebalanceamento ?? "Anual"}
              onChange={(e) =>
                setInputs({ ...inputs, rebalanceamento: e.target.value })
              }
              className="mt-2"
            />
          </div>

          <div>
            <Label htmlFor="notes">Motivo da mudanca (opcional)</Label>
            <Textarea
              id="notes"
              placeholder="Ex: revisao de perfil de risco"
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
                Voce esta acompanhando — edicao indisponivel.
              </span>
            )}
            <Button
              onClick={handleSave}
              disabled={saving || !somaValida || !canWrite}
              title={
                !canWrite
                  ? "Apenas owner/coadministrador pode editar"
                  : !somaValida
                    ? "A soma dos percentuais deve ser 100%"
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
