"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  ApiError,
  upsertAlocacaoGoal,
  type AlocacaoGoalDerived,
  type AlocacaoGoalInputs,
} from "@/lib/api";

import { PRESETS, type Pcts } from "./constants";

interface UseAlocacaoWizardArgs {
  workspaceId: string | undefined;
}

export function useAlocacaoWizard({ workspaceId }: UseAlocacaoWizardArgs) {
  const router = useRouter();

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

  const goToPreviousStep = () =>
    setStep((s) => Math.max(1, s - 1));
  const goToNextStep = () => setStep((s) => s + 1);

  async function handleSave() {
    if (!workspaceId) return;
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
        workspaceId,
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

  return {
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
  };
}
