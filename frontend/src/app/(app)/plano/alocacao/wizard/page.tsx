"use client";

/**
 * Wizard de configuracao da alocacao-alvo (F8.5).
 *
 * 3 passos:
 *   1. Distribuicao percentual (com presets)
 *   2. Instrumentos preferidos
 *   3. Rebalanceamento
 */

import { ArrowLeft, ArrowRight, Check } from "lucide-react";

import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { GoalPremissasCard } from "@/components/plano/GoalPremissasCard";
import { useCurrentWorkspace } from "@/lib/useCurrentWorkspace";

import { Step1Distribution } from "./_components/Step1Distribution";
import { Step2Instruments } from "./_components/Step2Instruments";
import { Step3Rebalance } from "./_components/Step3Rebalance";
import { useAlocacaoWizard } from "./_components/useAlocacaoWizard";

export default function AlocacaoWizardPage() {
  const { workspace, isLoading: wsLoading } = useCurrentWorkspace();
  const wizard = useAlocacaoWizard({ workspaceId: workspace?.id });

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

  const {
    step,
    pcts,
    setPcts,
    instrumentosRf,
    setInstrumentosRf,
    instrumentosRv,
    setInstrumentosRv,
    rebalanceamento,
    setRebalanceamento,
    saving,
    error,
    soma,
    somaValida,
    canAdvance,
    draftAlocacaoInputs,
    alocacaoDraftDerived,
    goToPreviousStep,
    goToNextStep,
    handleSave,
  } = wizard;

  return (
    <div className="mx-auto max-w-2xl px-6 py-8">
      <PageHeader title="Alocacao-alvo" description={`Passo ${step} de 3`} />

      <StepProgressBar step={step} />

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
            <Step1Distribution
              pcts={pcts}
              onChange={setPcts}
              soma={soma}
              somaValida={somaValida}
            />
          )}
          {step === 2 && (
            <Step2Instruments
              instrumentosRf={instrumentosRf}
              instrumentosRv={instrumentosRv}
              onChangeRf={setInstrumentosRf}
              onChangeRv={setInstrumentosRv}
            />
          )}
          {step === 3 && (
            <Step3Rebalance
              rebalanceamento={rebalanceamento}
              onChangeRebalanceamento={setRebalanceamento}
              pcts={pcts}
              instrumentosRf={instrumentosRf}
              instrumentosRv={instrumentosRv}
            />
          )}

          {error && (
            <p className="mt-4 text-sm text-destructive">{error}</p>
          )}
        </CardContent>
      </Card>

      <WizardNavigation
        step={step}
        saving={saving}
        canAdvance={canAdvance}
        somaValida={somaValida}
        onBack={goToPreviousStep}
        onNext={goToNextStep}
        onSave={handleSave}
      />
    </div>
  );
}

function StepProgressBar({ step }: { step: number }) {
  return (
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
  );
}

function WizardNavigation({
  step,
  saving,
  canAdvance,
  somaValida,
  onBack,
  onNext,
  onSave,
}: {
  step: number;
  saving: boolean;
  canAdvance: boolean;
  somaValida: boolean;
  onBack: () => void;
  onNext: () => void;
  onSave: () => void;
}) {
  return (
    <div className="mt-6 flex items-center justify-between">
      <Button
        variant="ghost"
        onClick={onBack}
        disabled={step === 1 || saving}
      >
        <ArrowLeft className="mr-2 h-4 w-4" /> Voltar
      </Button>

      {step < 3 ? (
        <Button onClick={onNext} disabled={!canAdvance}>
          Proximo <ArrowRight className="ml-2 h-4 w-4" />
        </Button>
      ) : (
        <Button onClick={onSave} disabled={saving || !somaValida}>
          {saving ? "Salvando..." : "Confirmar"}{" "}
          <Check className="ml-2 h-4 w-4" />
        </Button>
      )}
    </div>
  );
}
