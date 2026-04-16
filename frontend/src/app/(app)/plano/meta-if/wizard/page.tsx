"use client";

/**
 * Wizard de configuração da Meta IF (F8.1, ADR-073).
 *
 * 4 passos:
 *   1. Renda passiva desejada
 *   2. Taxa de Retirada Segura (TRS)
 *   3. Horizonte + retorno esperado
 *   4. Confirmação + simulador
 *
 * A cada passo, chama /goals/if/compute para mostrar o impacto em tempo
 * real. Persiste apenas na confirmação (passo 4).
 */

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Check, Target } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";

import { useCurrentWorkspace } from "@/lib/useCurrentWorkspace";
import {
  computeIFGoal,
  ifMonthlyContributionDisplay,
  listReports,
  upsertIFGoal,
  ApiError,
  type IFGoalInputs,
  type IFGoalDerived,
} from "@/lib/api";
import { formatCurrency } from "@/lib/format";


const DEFAULT_INPUTS: IFGoalInputs = {
  renda_passiva_mensal_brl: 20000,
  trs_pct: 5.0,
  retorno_real_anual_pct: 6.0,
  horizonte_anos: 15,
  taxa_retirada_conservadora_pct: 4.0,
};

const RENDA_PRESETS = [10000, 20000, 30000, 50000];


export default function MetaIFWizardPage() {
  const router = useRouter();
  const { workspace, isLoading: wsLoading } = useCurrentWorkspace();

  const [step, setStep] = useState(1);
  const [inputs, setInputs] = useState<IFGoalInputs>(DEFAULT_INPUTS);
  const [derived, setDerived] = useState<IFGoalDerived | null>(null);
  const [computing, setComputing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reportPatrimonio, setReportPatrimonio] = useState<number | undefined>();

  useEffect(() => {
    if (!workspace?.id) return;
    let cancelled = false;
    listReports()
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

  // Re-compute a cada mudança de inputs (debounce simples via timeout)
  useEffect(() => {
    if (!workspace?.id) return;
    setError(null);
    const handle = setTimeout(async () => {
      setComputing(true);
      try {
        const resp = await computeIFGoal(workspace.id, {
          inputs,
          patrimonio_atual_brl: reportPatrimonio,
        });
        setDerived(resp.derived);
      } catch (err) {
        if (err instanceof ApiError) {
          setError(err.detail);
        } else {
          setError("Erro ao calcular derivados");
        }
      } finally {
        setComputing(false);
      }
    }, 200);
    return () => clearTimeout(handle);
  }, [workspace?.id, inputs, reportPatrimonio]);

  const canAdvance = useMemo(() => {
    if (step === 1) return inputs.renda_passiva_mensal_brl > 0;
    if (step === 2) return inputs.trs_pct > 0 && inputs.trs_pct <= 20;
    if (step === 3)
      return (
        inputs.horizonte_anos >= 1 &&
        inputs.horizonte_anos <= 50 &&
        inputs.retorno_real_anual_pct >= 0
      );
    return true;
  }, [step, inputs]);

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
      await upsertIFGoal(workspace.id, inputs, "Configuração inicial (wizard)");
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
        title="Sua meta de Independência Financeira"
        description={`Passo ${step} de 4`}
      />

      <div className="mb-6 flex gap-2">
        {[1, 2, 3, 4].map((s) => (
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
            <Step1
              value={inputs.renda_passiva_mensal_brl}
              onChange={(v) =>
                setInputs({ ...inputs, renda_passiva_mensal_brl: v })
              }
            />
          )}
          {step === 2 && (
            <Step2
              value={inputs.trs_pct}
              onChange={(v) => setInputs({ ...inputs, trs_pct: v })}
              ifMeta={derived?.if_meta_brl ?? null}
            />
          )}
          {step === 3 && (
            <Step3
              horizonte={inputs.horizonte_anos}
              retorno={inputs.retorno_real_anual_pct}
              onChangeHorizonte={(v) =>
                setInputs({ ...inputs, horizonte_anos: v })
              }
              onChangeRetorno={(v) =>
                setInputs({ ...inputs, retorno_real_anual_pct: v })
              }
              aporte={
                derived
                  ? ifMonthlyContributionDisplay(derived)
                  : null
              }
            />
          )}
          {step === 4 && (
            <Step4
              inputs={inputs}
              derived={derived}
              computing={computing}
            />
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

        {step < 4 ? (
          <Button
            onClick={() => setStep((s) => s + 1)}
            disabled={!canAdvance}
          >
            Próximo <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        ) : (
          <Button onClick={handleSave} disabled={saving || !derived}>
            {saving ? "Salvando..." : "Confirmar"}{" "}
            <Check className="ml-2 h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}


// ─── Steps ────────────────────────────────────────────────────────────


function Step1({
  value,
  onChange,
}: {
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <h2 className="text-lg font-semibold">
        Quanto você quer receber por mês sem trabalhar?
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Pense na renda passiva mensal desejada na sua fase de
        independência financeira. Usamos esse valor para calcular seu
        patrimônio-alvo.
      </p>

      <div className="mt-6">
        <Label htmlFor="renda">Renda passiva mensal (BRL)</Label>
        <Input
          id="renda"
          type="number"
          inputMode="numeric"
          min={1}
          max={10_000_000}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="mt-2 font-mono tabular-nums"
        />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {RENDA_PRESETS.map((preset) => (
          <Button
            key={preset}
            variant={value === preset ? "default" : "outline"}
            size="sm"
            onClick={() => onChange(preset)}
            type="button"
          >
            {formatCurrency(preset)}/mês
          </Button>
        ))}
      </div>
    </div>
  );
}


function Step2({
  value,
  onChange,
  ifMeta,
}: {
  value: number;
  onChange: (v: number) => void;
  ifMeta: number | null;
}) {
  return (
    <div>
      <h2 className="text-lg font-semibold">
        Taxa de Retirada Segura (TRS)
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Percentual do patrimônio que você pode sacar por ano sem comprometer
        o principal. Default 5% (operacional). O Trinity Study clássico usa 4%
        — mais conservador.
      </p>

      <div className="mt-6">
        <Label htmlFor="trs">TRS (% ao ano)</Label>
        <Input
          id="trs"
          type="number"
          step={0.5}
          min={1}
          max={10}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="mt-2 font-mono tabular-nums"
        />
      </div>

      <Separator className="my-4" />

      {ifMeta !== null && (
        <p className="text-sm">
          Com TRS de <b>{value.toFixed(1)}%</b>, seu patrimônio-alvo é{" "}
          <b className="font-mono tabular-nums">
            {formatCurrency(ifMeta)}
          </b>
          .
        </p>
      )}
    </div>
  );
}


function Step3({
  horizonte,
  retorno,
  onChangeHorizonte,
  onChangeRetorno,
  aporte,
}: {
  horizonte: number;
  retorno: number;
  onChangeHorizonte: (v: number) => void;
  onChangeRetorno: (v: number) => void;
  aporte: number | null;
}) {
  return (
    <div>
      <h2 className="text-lg font-semibold">
        Em quantos anos você quer chegar lá?
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Horizonte e retorno real esperado (acima da inflação) determinam
        o aporte mensal constante necessário.
      </p>

      <div className="mt-6 grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="horizonte">Horizonte (anos)</Label>
          <Input
            id="horizonte"
            type="number"
            min={1}
            max={50}
            value={horizonte}
            onChange={(e) => onChangeHorizonte(Number(e.target.value))}
            className="mt-2 font-mono tabular-nums"
          />
        </div>
        <div>
          <Label htmlFor="retorno">Retorno real a.a. (%)</Label>
          <Input
            id="retorno"
            type="number"
            step={0.5}
            min={0}
            max={15}
            value={retorno}
            onChange={(e) => onChangeRetorno(Number(e.target.value))}
            className="mt-2 font-mono tabular-nums"
          />
        </div>
      </div>

      <Separator className="my-4" />

      {aporte !== null && (
        <p className="text-sm">
          Para atingir a meta em <b>{horizonte} anos</b> a{" "}
          <b>{retorno.toFixed(1)}% real a.a.</b>, você precisa aportar{" "}
          <b className="font-mono tabular-nums">
            {formatCurrency(aporte)}
          </b>{" "}
          por mês.
        </p>
      )}
    </div>
  );
}


function Step4({
  inputs,
  derived,
  computing,
}: {
  inputs: IFGoalInputs;
  derived: IFGoalDerived | null;
  computing: boolean;
}) {
  if (computing || !derived) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-20" />
      </div>
    );
  }

  return (
    <div>
      <h2 className="flex items-center gap-2 text-lg font-semibold">
        <Target className="h-5 w-5" />
        Confirme sua meta
      </h2>
      <p className="mt-2 text-sm text-muted-foreground">
        Você pode revisar esses valores a qualquer momento.
      </p>

      <dl className="mt-6 space-y-3 rounded-lg border p-4 text-sm">
        <div className="flex justify-between">
          <dt className="text-muted-foreground">Patrimônio-alvo (IF)</dt>
          <dd className="font-mono tabular-nums font-semibold">
            {formatCurrency(derived.if_meta_brl)}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-muted-foreground">
            Renda passiva projetada
          </dt>
          <dd className="font-mono tabular-nums">
            {formatCurrency(inputs.renda_passiva_mensal_brl)}/mês
          </dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-muted-foreground">Aporte mensal necessário</dt>
          <dd className="font-mono tabular-nums">
            {formatCurrency(ifMonthlyContributionDisplay(derived))}/mês
          </dd>
        </div>
        <Separator />
        <div className="flex justify-between text-xs text-muted-foreground">
          <dt>
            Meta conservadora (TRS{" "}
            {(inputs.taxa_retirada_conservadora_pct ?? 4).toFixed(1)}%)
          </dt>
          <dd className="font-mono tabular-nums">
            {formatCurrency(derived.if_meta_conservadora_brl)}
          </dd>
        </div>
        <div className="flex justify-between text-xs text-muted-foreground">
          <dt>
            Horizonte · TRS · Retorno real
          </dt>
          <dd className="font-mono tabular-nums">
            {inputs.horizonte_anos}a · {inputs.trs_pct}% · {inputs.retorno_real_anual_pct}%
          </dd>
        </div>
      </dl>
    </div>
  );
}
