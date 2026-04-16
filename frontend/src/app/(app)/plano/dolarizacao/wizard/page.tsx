"use client";

/**
 * Wizard de configuracao da meta de dolarizacao (F8.5).
 *
 * 2 passos:
 *   1. Meta de acumulacao em USD
 *   2. Aporte mensal em BRL (com horizonte live)
 */

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Check, DollarSign } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

import { useCurrentWorkspace } from "@/lib/useCurrentWorkspace";
import {
  computeDolarGoal,
  upsertDolarGoal,
  ApiError,
  type DolarGoalComputeResponse,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";


const USD_PRESETS = [10000, 20000, 50000, 100000];


export default function DolarizacaoWizardPage() {
  const router = useRouter();
  const { workspace, isLoading: wsLoading } = useCurrentWorkspace();

  const [step, setStep] = useState(1);
  const [metaUsd, setMetaUsd] = useState(20000);
  const [aporteBrl, setAporteBrl] = useState(2000);
  const [computed, setComputed] = useState<DolarGoalComputeResponse | null>(
    null
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canAdvance = useMemo(() => {
    if (step === 1) return metaUsd > 0;
    return aporteBrl > 0;
  }, [step, metaUsd, aporteBrl]);

  // Live compute on step 2
  useEffect(() => {
    if (!workspace?.id || step < 2) return;
    const handle = setTimeout(async () => {
      try {
        const resp = await computeDolarGoal(workspace.id, {
          meta_usd: metaUsd,
          aporte_mensal_brl: aporteBrl,
        });
        setComputed(resp);
      } catch {
        // non-blocking
      }
    }, 200);
    return () => clearTimeout(handle);
  }, [workspace?.id, step, metaUsd, aporteBrl]);

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
    try {
      await upsertDolarGoal(
        workspace.id,
        { meta_usd: metaUsd, aporte_mensal_brl: aporteBrl },
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

  const meses = computed?.derived.horizonte_estimado_meses ?? 0;
  const anos = (meses / 12).toFixed(1);
  const cambio = computed?.cambio_utilizado ?? 0;

  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      <PageHeader
        title="Meta de dolarizacao"
        description={`Passo ${step} de 2`}
      />

      {/* Progress bar */}
      <div className="mb-6 flex gap-2">
        {[1, 2].map((s) => (
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
                Meta de acumulacao em USD
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Quanto voce quer acumular em dolares? Esse e o saldo-alvo
                em moeda forte.
              </p>

              <div className="mt-6">
                <Label htmlFor="metausd">Meta (USD)</Label>
                <Input
                  id="metausd"
                  type="number"
                  inputMode="numeric"
                  min={1}
                  value={metaUsd}
                  onChange={(e) => setMetaUsd(Number(e.target.value))}
                  className="mt-2 font-mono tabular-nums"
                />
              </div>

              <div className="mt-4 flex flex-wrap gap-2">
                {USD_PRESETS.map((preset) => (
                  <Button
                    key={preset}
                    variant={metaUsd === preset ? "default" : "outline"}
                    size="sm"
                    onClick={() => setMetaUsd(preset)}
                    type="button"
                  >
                    US$ {preset.toLocaleString("pt-BR")}
                  </Button>
                ))}
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <h2 className="text-lg font-semibold">
                Aporte mensal em BRL
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Quanto voce pretende converter por mes? Calculamos o tempo
                estimado para atingir a meta.
              </p>

              <div className="mt-6">
                <Label htmlFor="aportebrl">Aporte mensal (BRL)</Label>
                <Input
                  id="aportebrl"
                  type="number"
                  inputMode="numeric"
                  min={1}
                  value={aporteBrl}
                  onChange={(e) => setAporteBrl(Number(e.target.value))}
                  className="mt-2 font-mono tabular-nums"
                />
              </div>

              {computed && (
                <>
                  <Separator className="my-4" />
                  <p className="text-sm">
                    Estimativa:{" "}
                    <b className="font-mono tabular-nums">{meses} meses</b>{" "}
                    (~{anos} anos) ao cambio de{" "}
                    <b className="font-mono tabular-nums">
                      {formatCurrency(cambio)}
                    </b>
                  </p>
                </>
              )}

              <Separator className="my-4" />

              {/* Review */}
              <dl className="space-y-2 rounded-lg border p-4 text-sm">
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Meta USD</dt>
                  <dd className="font-mono tabular-nums font-semibold">
                    US$ {metaUsd.toLocaleString("pt-BR")}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Aporte mensal</dt>
                  <dd className="font-mono tabular-nums">
                    {formatCurrency(aporteBrl)}/mes
                  </dd>
                </div>
                {computed && (
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <dt>Horizonte estimado</dt>
                    <dd className="font-mono tabular-nums">
                      {meses} meses (~{anos} anos)
                    </dd>
                  </div>
                )}
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

        {step < 2 ? (
          <Button
            onClick={() => setStep((s) => s + 1)}
            disabled={!canAdvance}
          >
            Proximo <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        ) : (
          <Button onClick={handleSave} disabled={saving || !canAdvance}>
            {saving ? "Salvando..." : "Confirmar"}{" "}
            <Check className="ml-2 h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
