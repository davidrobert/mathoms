/**
 * A37.l6 — mapa único de labels pt-BR para códigos de categoria de despesa
 * do pipeline (PD-03 + PD-08). Consumido por OrcamentoProspectivoCard,
 * DespesasDoughnutChart e ConsumoConscienteCard. O código de categoria é
 * contrato estável da API — o DTO permanece cru; humanização é
 * responsabilidade exclusiva desta camada de apresentação.
 */
export const CATEGORY_LABELS: Record<string, string> = {
  alimentacao: "Alimentação",
  aporte_investimento: "Aporte em investimentos",
  assinaturas: "Assinaturas",
  das_simples: "DAS (Simples Nacional)",
  educacao: "Educação",
  financeiro: "Financeiro",
  financiamentos: "Financiamentos",
  folha_pj: "Folha PJ",
  impostos: "Impostos",
  lazer: "Lazer",
  lazer_viagens: "Lazer e viagens",
  melhoria_reforma: "Melhoria e reforma",
  moradia: "Moradia",
  nao_identificado: "Não identificado",
  reserva_desejos: "Reserva de desejos",
  saude: "Saúde",
  seguros: "Seguros",
  servicos_domesticos: "Serviços domésticos",
  suporte_familiar: "Suporte familiar",
  transporte: "Transporte",
  vestuario: "Vestuário",
};

/** Label humano para código de categoria; fallback nunca exibe `_` nem inicia com minúscula. */
export function humanizeCategoryLabel(key: string): string {
  const mapped = CATEGORY_LABELS[key];
  if (mapped) return mapped;
  const spaced = key.replace(/_/g, " ").trim();
  if (spaced.length === 0) return key;
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}
