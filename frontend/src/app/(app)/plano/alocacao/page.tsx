"use client";

/**
 * /plano/alocacao — formulario de edicao da alocacao-alvo.
 *
 * 7 classes AUVP (v2, ADR-141) com % + soma validada.
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

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

import {
  CLASS_META,
  PRESETS,
  REBAL_OPTIONS,
  sumPcts,
} from "./wizard/_components/constants";
import { AlocacaoBar } from "./wizard/_components/AlocacaoBar";

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

  const soma = sumPcts(inputs);
  const somaValida = soma === 100;

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

  function setInstrumento(key: "renda_fixa" | "renda_variavel", value: string) {
    setInputs((prev) => ({
      ...prev,
      instrumentos: { ...(prev.instrumentos ?? {}), [key]: value },
    }));
  }

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

      {goal?.converted_from != null && (
        <p className="mb-3 text-xs text-muted-foreground">
          Alvo convertido automaticamente — revise e confirme.
        </p>
      )}

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
          {/* Percentage inputs — 7 classes v2 */}
          <div className="grid grid-cols-2 gap-4">
            {CLASS_META.map(({ key, label }) => (
              <div key={key}>
                <Label htmlFor={key}>{label} (%)</Label>
                <Input
                  id={key}
                  type="number"
                  min={0}
                  max={100}
                  step={1}
                  value={inputs[key]}
                  onChange={(e) =>
                    setInputs({ ...inputs, [key]: Number(e.target.value) })
                  }
                  className="mt-2 font-mono tabular-nums"
                />
              </div>
            ))}
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
          <AlocacaoBar pcts={inputs} />

          {/* Legend */}
          <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
            {CLASS_META.map(({ key, label, color }) => (
              <span key={key} className="flex items-center gap-1">
                <span
                  className="inline-block h-2 w-2 rounded-full"
                  style={{ backgroundColor: color }}
                />
                {label}
              </span>
            ))}
          </div>

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
            <Label htmlFor="rv-inst">Instrumentos de renda variavel</Label>
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
            <Label htmlFor="rebal">Rebalanceamento</Label>
            <Select
              value={inputs.rebalanceamento_modo}
              onValueChange={(v) =>
                setInputs({
                  ...inputs,
                  rebalanceamento_modo: v as RebalanceamentoModo,
                })
              }
            >
              <SelectTrigger id="rebal" className="mt-2 w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {REBAL_OPTIONS.map(({ value, label }) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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
