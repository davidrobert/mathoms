import type { ProtectionBundle } from "../cards";

/** Estado da S9 sobre as DUAS fontes de apólice (ADR-395 §D2/§D3).
 *
 * `apurado`  — o cadastro sustenta ao menos um cálculo.
 * `parcial`  — nada calculado, mas os documentos identificaram apólice.
 * `nao_apurado` — nenhuma fonte trouxe evidência.
 *
 * O predicado antigo lia só o bundle do cadastro e imprimia "sem riscos
 * cadastrados" enquanto a seção vizinha listava apólices vigentes (PD-4 /
 * RV6-20). Os quatro sinais saíam da MESMA fonte, então consertar só o render
 * era no-op por construção (#1476).
 */
export type ProtectionSectionState = "apurado" | "parcial" | "nao_apurado";

export function protectionSectionState(
  bundle: ProtectionBundle | null | undefined,
): ProtectionSectionState {
  if (!bundle) return "nao_apurado";
  if (hasRegisteredProtectionInputs(bundle)) return "apurado";
  return hasDocumentaryEvidence(bundle) ? "parcial" : "nao_apurado";
}

/** Insumo do CADASTRO — o que sustenta gap e prescrição (ADR-192). */
export function hasRegisteredProtectionInputs(bundle: ProtectionBundle): boolean {
  if (bundle.policies.length > 0) return true;
  if (Object.keys(bundle.gap_analysis).length > 0) return true;
  if (bundle.recommendations.length > 0) return true;
  return Object.values(bundle.calculation_status).some(
    (item) => item.status === "computed",
  );
}

/** Evidência DOCUMENTAL — desmente o vazio, não fecha gap (ADR-395 §D1). */
export function hasDocumentaryEvidence(bundle: ProtectionBundle): boolean {
  const documentary = bundle.documentary_coverage;
  if (!documentary) return false;
  return (
    documentary.active_policies_count > 0 ||
    documentary.unconfirmed_categories.length > 0
  );
}

/** @deprecated Use `protectionSectionState`; mantido para call-sites legados. */
export function hasRealProtectionInputs(
  bundle: ProtectionBundle | null | undefined,
): boolean {
  return protectionSectionState(bundle) !== "nao_apurado";
}
