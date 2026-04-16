"use client";

/**
 * Wizard de configuracao da meta de aportes mensais (F8.5).
 *
 * 3 passos:
 *   1. Quanto aportar por mes
 *   2. Dia do aporte e periodo de inicio
 *   3. Distribuicao por destinos
 */

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Check, Plus, Trash2, Wallet } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

import { useCurrentWorkspace } from "@/lib/useCurrentWorkspace";
import {
  upsertAporteGoal,
  ApiError,
  type AporteGoalInputs,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";


interface DistRow {
  destino: string;
  valor: number;
}

const APORTE_PRESETS = [5000, 10000, 15000, 20000];


export default function AportesWizardPage() {
  const router = useRouter();
  const { workspace, isLoading: wsLoading } = useCurrentWorkspace();

  const [step, setStep] = useState(1);
  const [metaMensal, setMetaMensal] = useState(10000);
  const [diaAporte, setDiaAporte] = useState(5);
  const [periodoInicio, setPeriodoInicio] = useState("Imediato");
  const [rows, setRows] = useState<DistRow[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const distSum = rows.reduce((s, r) => s + r.valor, 0);

  const canAdvance = useMemo(() => {
    if (step === 1) return metaMensal > 0;
    if (step === 2) return diaAporte >= 1 && diaAporte <= 28;
    return true;
  }, [step, metaMensal, diaAporte]);

  if (wsLoading) {
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

  async function handleSave() {
    if (!workspace) return;
    setSaving(true);
    setError(null);

    const distribuicao: Record<string, number> = {};
    for (const r of rows) {
      if (r.destino.trim()) distribuicao[r.destino.trim()] = r.valor;
    }

    const inputs: AporteGoalInputs = {
      meta_aporte_mensal_brl: metaMensal,
      dia_aporte: diaAporte,
      periodo_inicio: periodoInicio || "Imediato",
      distribuicao:
        Object.keys(distribuicao).length > 0 ? distribuicao : undefined,
    };

    try {
      await upsertAporteGoal(
        workspace.id,
        inputs,
        "Configuracao inicial (wizard)"
      );
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

  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      <PageHeader
        title="Configure seus aportes mensais"
        description={`Passo ${step} de 3`}
      />

      {/* Progress bar */}
      <div className="mb-6 flex gap-2">
        {[1, 2, 3].map((s) => (
          <div
            key={s}
            className={
              "h-1 flex-1 rounded-full transition-colors " +
              (s <= step ? "bg-primary" : "bg-muted")
            }
          />
        ))}
      </div>

      <Card>
        <CardContent className="py-6">
          {step === 1 && (
            <div>
              <h2 className="text-lg font-semibold">
                Quanto aportar por mes?
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Defina o valor total que voce pretende investir mensalmente.
              </p>

              <div className="mt-6">
                <Label htmlFor="meta">Aporte mensal (BRL)</Label>
                <Input
                  id="meta"
                  type="number"
                  inputMode="numeric"
                  min={1}
                  value={metaMensal}
                  onChange={(e) => setMetaMensal(Number(e.target.value))}
                  className="mt-2 font-mono tabular-nums"
                />
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                {APORTE_PRESETS.map((preset) => (
                  <Button
                    key={preset}
                    variant={metaMensal === preset ? "default" : "outline"}
                    size="sm"
                    onClick={() => setMetaMensal(preset)}
                    type="button"
                  >
                    {formatCurrency(preset)}/mes
                  </Button>
                ))}
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <h2 className="text-lg font-semibold">
                Dia do aporte e quando comecar?
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Escolha o dia do mes para realizar o aporte e quando deseja
                iniciar.
              </p>

              <div className="mt-6 grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="dia">Dia do aporte (1-28)</Label>
                  <Input
                    id="dia"
                    type="number"
                    min={1}
                    max={28}
                    value={diaAporte}
                    onChange={(e) => setDiaAporte(Number(e.target.value))}
                    className="mt-2 font-mono tabular-nums"
                  />
                </div>
                <div>
                  <Label htmlFor="periodo">Periodo de inicio</Label>
                  <Input
                    id="periodo"
                    type="text"
                    value={periodoInicio}
                    onChange={(e) => setPeriodoInicio(e.target.value)}
                    className="mt-2"
                    placeholder="Imediato"
                  />
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <h2 className="text-lg font-semibold">Distribuicao</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Opcionalmente, divida o aporte entre destinos diferentes.
              </p>

              <div className="mt-4 space-y-2">
                {rows.map((row, idx) => (
                  <div key={idx} className="flex items-center gap-2">
                    <Input
                      placeholder="Destino (ex: Tesouro IPCA+)"
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
                      onClick={() =>
                        setRows(rows.filter((_, i) => i !== idx))
                      }
                    >
                      <Trash2 className="h-4 w-4 text-muted-foreground" />
                    </Button>
                  </div>
                ))}
              </div>

              <Button
                variant="outline"
                size="sm"
                type="button"
                className="mt-3"
                onClick={() =>
                  setRows([...rows, { destino: "", valor: 0 }])
                }
              >
                <Plus className="mr-1 h-3 w-3" /> Adicionar destino
              </Button>

              {rows.length > 0 && (
                <p className="mt-3 text-xs text-muted-foreground">
                  Total distribuido:{" "}
                  <span className="font-mono tabular-nums">
                    {formatCurrency(distSum)}
                  </span>{" "}
                  / {formatCurrency(metaMensal)}
                </p>
              )}

              <Separator className="my-4" />

              {/* Confirm summary */}
              <dl className="space-y-2 rounded-lg border p-4 text-sm">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Aporte mensal</dt>
                  <dd className="font-mono tabular-nums font-semibold">
                    {formatCurrency(metaMensal)}/mes
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Dia do aporte</dt>
                  <dd className="font-mono tabular-nums">{diaAporte}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Inicio</dt>
                  <dd>{periodoInicio || "Imediato"}</dd>
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <dt>Aporte anual</dt>
                  <dd className="font-mono tabular-nums">
                    {formatCurrency(metaMensal * 12)}
                  </dd>
                </div>
              </dl>
            </div>
          )}

          {error && (
            <p className="mt-4 text-sm text-destructive">{error}</p>
          )}
        </CardContent>
      </Card>

      <div className="mt-6 flex items-center justify-between">
        <Button
          variant="ghost"
          onClick={() => setStep((s) => Math.max(1, s - 1))}
          disabled={step === 1 || saving}
        >
          <ArrowLeft className="mr-2 h-4 w-4" /> Voltar
        </Button>

        {step < 3 ? (
          <Button
            onClick={() => setStep((s) => s + 1)}
            disabled={!canAdvance}
          >
            Proximo <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        ) : (
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "Salvando..." : "Confirmar"}{" "}
            <Check className="ml-2 h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
