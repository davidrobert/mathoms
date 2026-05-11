/**
 * F11.6a — rótulos e linhas para o bloco "Premissas" nas metas (/plano).
 * Valores monetários: usar formatCurrency no componente.
 */

import { formatCurrency } from "@/lib/format";
import type {
  AlocacaoGoalInputs,
  AlocacaoGoalDerived,
  AporteGoalInputs,
  AporteGoalDerived,
  DolarGoalInputs,
  DolarGoalDerived,
  IFGoalInputs,
  IFGoalDerived,
} from "@/lib/api";

export interface PremissaRow {
  label: string;
  value: string;
}

/** Data-only YYYY-MM-DD → dd/mm/aaaa (sem ambiguidade de fuso). */
export function formatGoalVigenciaDate(iso: string): string {
  const d = iso.slice(0, 10);
  const p = d.split("-");
  if (p.length !== 3) return iso;
  const [y, m, day] = p;
  return `${day}/${m}/${y}`;
}

const GOAL_TYPE_LABELS: Record<string, string> = {
  INDEPENDENCIA_FINANCEIRA: "Independência Financeira",
  APORTE_MENSAL: "Aporte mensal",
  DOLARIZACAO: "Dolarização da carteira",
  ALOCACAO_ALVO: "Alocação-alvo da carteira",
};

export function humanizeGoalType(type: string): string {
  return GOAL_TYPE_LABELS[type] ?? type;
}

/** Goal types que devem aparecer no card "Metas vigentes neste ciclo".
 * Mantém pareado com `VALID_GOAL_TYPES` do backend (ADR-073 + ADR-180).
 */
export function isDisplayableGoalType(type: string): boolean {
  return type in GOAL_TYPE_LABELS;
}

export function buildIFPremissasRows(
  inputs: IFGoalInputs,
  derived: IFGoalDerived | null
): PremissaRow[] {
  const taxaCons = inputs.taxa_retirada_conservadora_pct ?? 4;
  const rows: PremissaRow[] = [
    {
      label: "Renda passiva desejada",
      value: `${formatCurrency(inputs.renda_passiva_mensal_brl)}/mês`,
    },
    { label: "TRS (taxa de retirada segura)", value: `${inputs.trs_pct}% a.a.` },
    {
      label: "Retorno real esperado",
      value: `${inputs.retorno_real_anual_pct}% a.a. (acima da inflação)`,
    },
    { label: "Horizonte", value: `${inputs.horizonte_anos} anos` },
    {
      label: "Taxa conservadora (Trinity)",
      value: `${taxaCons}% a.a.`,
    },
  ];
  if (derived) {
    rows.push(
      {
        label: "Patrimônio-alvo (operacional)",
        value: formatCurrency(derived.if_meta_brl),
      },
      {
        label: "Patrimônio-alvo (conservador)",
        value: formatCurrency(derived.if_meta_conservadora_brl),
      }
    );
  }
  return rows;
}

export function buildAportePremissasRows(
  inputs: AporteGoalInputs,
  derived: AporteGoalDerived | null
): PremissaRow[] {
  const rows: PremissaRow[] = [
    {
      label: "Aporte mensal total",
      value: `${formatCurrency(inputs.meta_aporte_mensal_brl)}/mês`,
    },
    { label: "Dia do aporte", value: `Dia ${inputs.dia_aporte}` },
    {
      label: "Início",
      value: inputs.periodo_inicio?.trim() || "Imediato",
    },
  ];
  if (derived) {
    rows.push({
      label: "Aporte anual (derivado)",
      value: formatCurrency(derived.aporte_anual_brl),
    });
    const keys = Object.keys(derived.distribuicao_pct || {});
    if (keys.length > 0) {
      rows.push({
        label: "Distribuição",
        value: keys
          .map((k) => `${k}: ${(derived.distribuicao_pct[k] ?? 0).toFixed(1)}%`)
          .join(" · "),
      });
    }
  }
  if (inputs.distribuicao && Object.keys(inputs.distribuicao).length > 0) {
    rows.push({
      label: "Destinos (valores)",
      value: Object.entries(inputs.distribuicao)
        .map(([k, v]) => `${k}: ${formatCurrency(v)}`)
        .join(" · "),
    });
  }
  return rows;
}

export function buildDolarPremissasRows(
  inputs: DolarGoalInputs,
  derived: DolarGoalDerived | null,
  cambioUtilizado?: number | null
): PremissaRow[] {
  const rows: PremissaRow[] = [
    {
      label: "Meta em USD",
      value: `US$ ${inputs.meta_usd.toLocaleString("pt-BR")}`,
    },
    {
      label: "Aporte mensal (BRL)",
      value: `${formatCurrency(inputs.aporte_mensal_brl)}/mês`,
    },
  ];
  if (cambioUtilizado != null && cambioUtilizado > 0) {
    rows.push({
      label: "Câmbio usado na estimativa",
      value: `${formatCurrency(cambioUtilizado)} BRL/USD`,
    });
  }
  if (derived) {
    const m = derived.horizonte_estimado_meses;
    rows.push({
      label: "Horizonte estimado",
      value:
        m > 0
          ? `${m} meses (~${(m / 12).toFixed(1)} anos)`
          : "—",
    });
  }
  return rows;
}

export function buildAlocacaoPremissasRows(
  inputs: AlocacaoGoalInputs,
  derived: AlocacaoGoalDerived | null
): PremissaRow[] {
  const rows: PremissaRow[] = [
    { label: "Renda fixa", value: `${inputs.renda_fixa_pct}%` },
    { label: "Ações", value: `${inputs.acoes_pct}%` },
    { label: "Imóveis / REITs", value: `${inputs.imoveis_reits_pct}%` },
    { label: "Liquidez USD", value: `${inputs.liquidez_usd_pct}%` },
  ];
  if (inputs.instrumentos_rf?.trim()) {
    rows.push({ label: "Instrumentos RF", value: inputs.instrumentos_rf.trim() });
  }
  if (inputs.instrumentos_rv?.trim()) {
    rows.push({ label: "Instrumentos RV", value: inputs.instrumentos_rv.trim() });
  }
  if (inputs.rebalanceamento?.trim()) {
    rows.push({
      label: "Rebalanceamento",
      value: inputs.rebalanceamento.trim(),
    });
  }
  if (derived) {
    rows.push({
      label: "Soma dos percentuais",
      value: `${derived.soma_percentuais}%`,
    });
  }
  return rows;
}
