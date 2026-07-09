"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import {
  ApiError,
  upsertAlocacaoGoal,
  type AlocacaoGoalDerived,
  type AlocacaoGoalInputs,
  type RebalanceamentoModo,
} from "@/lib/api";

import type { AlocacaoProgressState } from "./AlocacaoProgress";
import { completeWithCaixa, PRESETS, sumPcts, type Pcts } from "./constants";

interface UseAlocacaoWizardArgs {
  workspaceId: string | undefined;
}

function buildInstrumentos(
  instrumentosRf: string,
  instrumentosRv: string,
): Record<string, string> | undefined {
  const dict: Record<string, string> = {};
  if (instrumentosRf.trim()) dict.renda_fixa = instrumentosRf.trim();
  if (instrumentosRv.trim()) dict.renda_variavel = instrumentosRv.trim();
  return Object.keys(dict).length > 0 ? dict : undefined;
}

export function useAlocacaoWizard({ workspaceId }: UseAlocacaoWizardArgs) {
  const router = useRouter();

  const [step, setStep] = useState(1);
  const [pcts, setPctsState] = useState<Pcts>(PRESETS.Moderado);
  const [instrumentosRf, setInstrumentosRf] = useState("");
  const [instrumentosRv, setInstrumentosRv] = useState("");
  const [rebalanceamento, setRebalanceamento] =
    useState<RebalanceamentoModo>("por_aporte");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Editar qualquer percentual limpa o estado de erro "danger" — o vermelho
  // só aparece ao tentar avançar com Σ≠100 (ADR-141 emenda item 11).
  const [attemptedAdvance, setAttemptedAdvance] = useState(false);

  const soma = sumPcts(pcts);
  const somaValida = soma === 100;

  const setPcts = (next: Pcts) => {
    setPctsState(next);
    setAttemptedAdvance(false);
  };
  const completeCaixa = () => setPcts(completeWithCaixa(pcts));

  const progressState: AlocacaoProgressState = somaValida
    ? "ok"
    : attemptedAdvance
      ? "danger"
      : "warning";

  const draftAlocacaoInputs: AlocacaoGoalInputs = useMemo(
    () => ({
      ...pcts,
      rebalanceamento_modo: rebalanceamento,
      instrumentos: buildInstrumentos(instrumentosRf, instrumentosRv),
    }),
    [pcts, instrumentosRf, instrumentosRv, rebalanceamento],
  );

  const alocacaoDraftDerived: AlocacaoGoalDerived = useMemo(
    () => ({ soma_percentuais: soma }),
    [soma],
  );

  const goToPreviousStep = () => setStep((s) => Math.max(1, s - 1));
  const goToNextStep = () => {
    if (step === 1 && !somaValida) {
      setAttemptedAdvance(true);
      return;
    }
    setStep((s) => s + 1);
  };

  async function handleSave() {
    if (!workspaceId) return;
    setSaving(true);
    setError(null);

    try {
      await upsertAlocacaoGoal(
        workspaceId,
        draftAlocacaoInputs,
        "Configuracao inicial (wizard)",
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
    progressState,
    completeCaixa,
    draftAlocacaoInputs,
    alocacaoDraftDerived,
    goToPreviousStep,
    goToNextStep,
    handleSave,
  };
}
