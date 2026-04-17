"use client";

/**
 * Wizard de configuracao da alocacao-alvo (F8.5).
 *
 * 3 passos:
 *   1. Distribuicao percentual (com presets)
 *   2. Instrumentos preferidos
 *   3. Rebalanceamento
 */

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  PieChart,
  XCircle,
} from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";

import { useCurrentWorkspace } from "@/lib/useCurrentWorkspace";
import {
  upsertAlocacaoGoal,
  ApiError,
  type AlocacaoGoalInputs,
  type AlocacaoGoalDerived,
} from "@/lib/api";
import { GoalPremissasCard } from "@/components/plano/GoalPremissasCard";


interface Pcts {
  renda_fixa_pct: number;
  acoes_pct: number;
  imoveis_reits_pct: number;
  liquidez_usd_pct: number;
}

const PRESETS: Record<string, Pcts> = {
  Conservador: {
    renda_fixa_pct: 60,
    acoes_pct: 20,
    imoveis_reits_pct: 10,
    liquidez_usd_pct: 10,
  },
  Moderado: {
    renda_fixa_pct: 40,
    acoes_pct: 30,
    imoveis_reits_pct: 15,
    liquidez_usd_pct: 15,
  },
  Agressivo: {
    renda_fixa_pct: 25,
    acoes_pct: 45,
    imoveis_reits_pct: 15,
    liquidez_usd_pct: 15,
  },
};

const REBAL_OPTIONS = ["Semestral", "Anual", "Quando desviar >5%"];

const COLORS = {
  renda_fixa: "bg-blue-500",
  acoes: "bg-emerald-500",
  imoveis: "bg-amber-500",
  usd: "bg-purple-500",
};


export default function AlocacaoWizardPage() {
  const router = useRouter();
  const { workspace, isLoading: wsLoading } = useCurrentWorkspace();

  const [step, setStep] = useState(1);
  const [pcts, setPcts] = useState<Pcts>(PRESETS.Moderado);
  const [instrumentosRf, setInstrumentosRf] = useState("");
  const [instrumentosRv, setInstrumentosRv] = useState("");
  const [rebalanceamento, setRebalanceamento] = useState("Anual");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const soma =
    pcts.renda_fixa_pct +
    pcts.acoes_pct +
    pcts.imoveis_reits_pct +
    pcts.liquidez_usd_pct;
  const somaValida = soma === 100;

  const draftAlocacaoInputs: AlocacaoGoalInputs = useMemo(
    () => ({
      ...pcts,
      instrumentos_rf: instrumentosRf || undefined,
      instrumentos_rv: instrumentosRv || undefined,
      rebalanceamento: rebalanceamento || "Anual",
    }),
    [pcts, instrumentosRf, instrumentosRv, rebalanceamento]
  );

  const alocacaoDraftDerived: AlocacaoGoalDerived = useMemo(
    () => ({ soma_percentuais: soma }),
    [soma]
  );

  const canAdvance = useMemo(() => {
    if (step === 1) return somaValida;
    return true;
  }, [step, somaValida]);

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

    const inputs: AlocacaoGoalInputs = {
      ...pcts,
      instrumentos_rf: instrumentosRf || undefined,
      instrumentos_rv: instrumentosRv || undefined,
      rebalanceamento: rebalanceamento || "Anual",
    };

    try {
      await upsertAlocacaoGoal(
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
        title="Alocacao-alvo"
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

      <GoalPremissasCard
        className="mb-4"
        kind="alocacao"
        mode="draft"
        inputs={draftAlocacaoInputs}
        derived={alocacaoDraftDerived}
      />

      <Card>
        <CardContent className="py-6">
          {step === 1 && (
            <div>
              <h2 className="text-lg font-semibold">
                Distribua seus investimentos
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Defina a alocacao percentual ideal por classe de ativo.
              </p>

              {/* Presets */}
              <div className="mt-4 flex flex-wrap gap-2">
                {Object.entries(PRESETS).map(([name, preset]) => {
                  const isActive =
                    pcts.renda_fixa_pct === preset.renda_fixa_pct &&
                    pcts.acoes_pct === preset.acoes_pct &&
                    pcts.imoveis_reits_pct === preset.imoveis_reits_pct &&
                    pcts.liquidez_usd_pct === preset.liquidez_usd_pct;
                  return (
                    <Button
                      key={name}
                      variant={isActive ? "default" : "outline"}
                      size="sm"
                      onClick={() => setPcts(preset)}
                      type="button"
                    >
                      {name}
                    </Button>
                  );
                })}
              </div>

              <div className="mt-6 grid grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="rf">Renda fixa (%)</Label>
                  <Input
                    id="rf"
                    type="number"
                    min={0}
                    max={100}
                    value={pcts.renda_fixa_pct}
                    onChange={(e) =>
                      setPcts({
                        ...pcts,
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
                    value={pcts.acoes_pct}
                    onChange={(e) =>
                      setPcts({
                        ...pcts,
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
                    value={pcts.imoveis_reits_pct}
                    onChange={(e) =>
                      setPcts({
                        ...pcts,
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
                    value={pcts.liquidez_usd_pct}
                    onChange={(e) =>
                      setPcts({
                        ...pcts,
                        liquidez_usd_pct: Number(e.target.value),
                      })
                    }
                    className="mt-2 font-mono tabular-nums"
                  />
                </div>
              </div>

              {/* Sum indicator */}
              <div className="mt-4 flex items-center gap-2 text-sm">
                {somaValida ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                ) : (
                  <XCircle className="h-4 w-4 text-destructive" />
                )}
                <span
                  className={
                    somaValida ? "text-emerald-600" : "text-destructive"
                  }
                >
                  Total:{" "}
                  <span className="font-mono tabular-nums">{soma}%</span>
                  {!somaValida && " — deve somar 100%"}
                </span>
              </div>

              {/* Visual bar */}
              <div className="mt-3 h-4 w-full overflow-hidden rounded-full bg-muted">
                <div className="flex h-full">
                  {pcts.renda_fixa_pct > 0 && (
                    <div
                      className={`${COLORS.renda_fixa} transition-all`}
                      style={{ width: `${pcts.renda_fixa_pct}%` }}
                    />
                  )}
                  {pcts.acoes_pct > 0 && (
                    <div
                      className={`${COLORS.acoes} transition-all`}
                      style={{ width: `${pcts.acoes_pct}%` }}
                    />
                  )}
                  {pcts.imoveis_reits_pct > 0 && (
                    <div
                      className={`${COLORS.imoveis} transition-all`}
                      style={{ width: `${pcts.imoveis_reits_pct}%` }}
                    />
                  )}
                  {pcts.liquidez_usd_pct > 0 && (
                    <div
                      className={`${COLORS.usd} transition-all`}
                      style={{ width: `${pcts.liquidez_usd_pct}%` }}
                    />
                  )}
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div>
              <h2 className="text-lg font-semibold">
                Instrumentos preferidos
              </h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Quais produtos voce prefere em cada classe? Opcional.
              </p>

              <div className="mt-6 space-y-4">
                <div>
                  <Label htmlFor="rf-inst">Renda fixa</Label>
                  <Input
                    id="rf-inst"
                    type="text"
                    placeholder="Ex: Tesouro IPCA+, CDB, LCI"
                    value={instrumentosRf}
                    onChange={(e) => setInstrumentosRf(e.target.value)}
                    className="mt-2"
                  />
                </div>
                <div>
                  <Label htmlFor="rv-inst">Renda variavel</Label>
                  <Input
                    id="rv-inst"
                    type="text"
                    placeholder="Ex: ETFs, FIIs, IVVB11"
                    value={instrumentosRv}
                    onChange={(e) => setInstrumentosRv(e.target.value)}
                    className="mt-2"
                  />
                </div>
              </div>
            </div>
          )}

          {step === 3 && (
            <div>
              <h2 className="text-lg font-semibold">Rebalanceamento</h2>
              <p className="mt-2 text-sm text-muted-foreground">
                Com qual frequencia voce pretende rebalancear a carteira?
              </p>

              <div className="mt-4 flex flex-wrap gap-2">
                {REBAL_OPTIONS.map((opt) => (
                  <Button
                    key={opt}
                    variant={rebalanceamento === opt ? "default" : "outline"}
                    size="sm"
                    onClick={() => setRebalanceamento(opt)}
                    type="button"
                  >
                    {opt}
                  </Button>
                ))}
              </div>

              <Separator className="my-4" />

              {/* Summary */}
              <div className="rounded-lg border p-4 text-sm">
                <div className="mb-3 flex items-center gap-2">
                  <PieChart className="h-4 w-4" />
                  <h3 className="font-semibold">Resumo da alocacao</h3>
                </div>

                {/* Visual bar */}
                <div className="mb-3 h-4 w-full overflow-hidden rounded-full bg-muted">
                  <div className="flex h-full">
                    {pcts.renda_fixa_pct > 0 && (
                      <div
                        className={`${COLORS.renda_fixa} transition-all`}
                        style={{ width: `${pcts.renda_fixa_pct}%` }}
                      />
                    )}
                    {pcts.acoes_pct > 0 && (
                      <div
                        className={`${COLORS.acoes} transition-all`}
                        style={{ width: `${pcts.acoes_pct}%` }}
                      />
                    )}
                    {pcts.imoveis_reits_pct > 0 && (
                      <div
                        className={`${COLORS.imoveis} transition-all`}
                        style={{ width: `${pcts.imoveis_reits_pct}%` }}
                      />
                    )}
                    {pcts.liquidez_usd_pct > 0 && (
                      <div
                        className={`${COLORS.usd} transition-all`}
                        style={{ width: `${pcts.liquidez_usd_pct}%` }}
                      />
                    )}
                  </div>
                </div>

                <dl className="space-y-1">
                  <div className="flex justify-between">
                    <dt className="flex items-center gap-1 text-muted-foreground">
                      <span className={`inline-block h-2 w-2 rounded-full ${COLORS.renda_fixa}`} />
                      Renda fixa
                    </dt>
                    <dd className="font-mono tabular-nums">
                      {pcts.renda_fixa_pct}%
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="flex items-center gap-1 text-muted-foreground">
                      <span className={`inline-block h-2 w-2 rounded-full ${COLORS.acoes}`} />
                      Acoes
                    </dt>
                    <dd className="font-mono tabular-nums">
                      {pcts.acoes_pct}%
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="flex items-center gap-1 text-muted-foreground">
                      <span className={`inline-block h-2 w-2 rounded-full ${COLORS.imoveis}`} />
                      Imoveis/REITs
                    </dt>
                    <dd className="font-mono tabular-nums">
                      {pcts.imoveis_reits_pct}%
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="flex items-center gap-1 text-muted-foreground">
                      <span className={`inline-block h-2 w-2 rounded-full ${COLORS.usd}`} />
                      Liquidez USD
                    </dt>
                    <dd className="font-mono tabular-nums">
                      {pcts.liquidez_usd_pct}%
                    </dd>
                  </div>
                  <Separator className="my-2" />
                  {instrumentosRf && (
                    <div className="flex justify-between text-xs">
                      <dt className="text-muted-foreground">Instr. RF</dt>
                      <dd>{instrumentosRf}</dd>
                    </div>
                  )}
                  {instrumentosRv && (
                    <div className="flex justify-between text-xs">
                      <dt className="text-muted-foreground">Instr. RV</dt>
                      <dd>{instrumentosRv}</dd>
                    </div>
                  )}
                  <div className="flex justify-between text-xs">
                    <dt className="text-muted-foreground">Rebalanceamento</dt>
                    <dd>{rebalanceamento}</dd>
                  </div>
                </dl>
              </div>
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
          <Button onClick={handleSave} disabled={saving || !somaValida}>
            {saving ? "Salvando..." : "Confirmar"}{" "}
            <Check className="ml-2 h-4 w-4" />
          </Button>
        )}
      </div>
    </div>
  );
}
