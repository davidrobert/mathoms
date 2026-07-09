/** Sprint A16 L2 P5 (ADR-236 §D6) — Copy + severity styling dos 5
 * decision triggers da Cascata Fiscal.
 *
 * Co-design `financial-planner` 2026-05-21:
 *   - T1 título: "Trade-off observado" (descritivo, não imperativo).
 *   - T1 body: threshold "vale enquanto a alíquota marginal IR > 15%".
 *   - T3 body: "10 anos de cada aporte" (NÃO "no fundo" — folclore).
 *   - T4 título: "Cenário observado" (não "Considere avaliar holding").
 *   - T2 body: "Anexo V tem alíquotas mais altas em todas as faixas"
 *     (sem hardcode de "9,5pp" que só vale na faixa 1).
 *   - T5 body: "avalie com seu contador" (descritivo).
 */
import { AlertTriangle, Info, Lightbulb } from "lucide-react";

import type { CascataTrigger } from "@/lib/api";
import { formatBRLDecimalString } from "@/lib/format";

export interface SeverityStyle {
  borderClass: string;
  iconClass: string;
  Icon: typeof Lightbulb;
  ariaSeverity: string;
}

export const SEVERITY: Record<CascataTrigger["severity"], SeverityStyle> = {
  oportunidade: {
    borderClass: "border-[var(--semantic-gain)]",
    iconClass: "text-[var(--semantic-gain)]",
    Icon: Lightbulb,
    ariaSeverity: "oportunidade",
  },
  atencao: {
    borderClass: "border-[var(--semantic-warning)]",
    iconClass: "text-[var(--semantic-warning)]",
    Icon: AlertTriangle,
    ariaSeverity: "sinal de atenção",
  },
  considere: {
    borderClass: "border-[var(--brand-info)]",
    iconClass: "text-[var(--brand-info)]",
    Icon: Info,
    ariaSeverity: "trade-off observado",
  },
};

export const TRIGGER_TITLE: Record<CascataTrigger["code"], string> = {
  T1: "Trade-off observado: pró-labore × lucros distribuídos",
  T2: "Sinal de atenção: fator-R próximo do corte Anexo III × V",
  T3: "Oportunidade: PGBL dedutível dentro do seu perfil",
  T4: "Cenário observado: imóveis locados em pessoa física",
  T5: "Sinal de atenção: receita próxima do sublimite Simples",
};

function fmtPct(decimalStr: string | undefined): string {
  if (!decimalStr) return "—";
  const value = Number(decimalStr);
  if (!Number.isFinite(value)) return "—";
  return `${value.toFixed(1).replace(".", ",")}%`;
}

function renderT1(p: Record<string, string>): string {
  const delta = formatBRLDecimalString(p.delta_pro_labore_mensal_brl);
  const aporte = formatBRLDecimalString(p.aporte_pgbl_extra_anual_brl);
  const economia = formatBRLDecimalString(p.economia_ir_anual_brl);
  const inss = formatBRLDecimalString(p.custo_inss_patronal_anual_brl);
  const marginal = fmtPct(p.ir_marginal_potencial_pct);
  return (
    `Aumentar o pró-labore mensal em ${delta} expandiria a base PGBL em ${aporte}/ano, ` +
    `reduzindo aproximadamente ${economia} de IR (alíquota marginal projetada ${marginal}). ` +
    `Custo adicional: INSS patronal de ${inss}/ano (no Simples a contribuição patronal está ` +
    `embutida no DAS — não adicionar). Trade-off favorável enquanto a alíquota marginal IR > 15%.`
  );
}

function renderT2(p: Record<string, string>): string {
  const atual = fmtPct(p.fator_r_pct);
  const limiar = fmtPct(p.fator_r_limiar_pct);
  const deltaMensal = formatBRLDecimalString(p.delta_folha_mensal_brl);
  const deltaAnual = formatBRLDecimalString(p.delta_folha_anual_brl);
  return (
    `Fator-R móvel 12 meses em ${atual} (corte Anexo III × V em ${limiar}). ` +
    `Subir folha em ${deltaMensal}/mês (${deltaAnual}/ano) manteria o Anexo III. ` +
    `Anexo V tem alíquotas mais altas em todas as faixas — o impacto exato varia conforme a receita.`
  );
}

function renderT3(p: Record<string, string>): string {
  const marginal = fmtPct(p.ir_marginal_estimado_pct);
  const limite = formatBRLDecimalString(p.pgbl_limite_anual_brl);
  return (
    `Alíquota IR marginal estimada em ${marginal}. PGBL é dedutível no modelo completo ` +
    `e oferece tabela regressiva (10% após 10 anos de cada aporte). ` +
    `Limite anual disponível: ${limite}.`
  );
}

function renderT4(p: Record<string, string>): string {
  const count = p.imoveis_alugados_count;
  const receita = formatBRLDecimalString(p.receita_aluguel_anual_brl);
  return (
    `Workspace tem ${count} imóveis locados gerando ${receita}/ano. ` +
    `A diferença efetiva entre tributação PF (carnê-leão até 27,5%) e PJ-aluguel ` +
    `(Lucro Presumido, ~11,33% s/ receita bruta) depende de volume, horizonte e sucessão — ` +
    `avalie com tributarista antes de qualquer movimento.`
  );
}

function renderT5(p: Record<string, string>): string {
  const receita = formatBRLDecimalString(p.receita_anual_brl);
  const distancia = formatBRLDecimalString(p.distancia_brl);
  const sublimite = formatBRLDecimalString(p.sublimite_brl);
  return (
    `Receita bruta 12m em ${receita}, a ${distancia} do sublimite nacional de ${sublimite}. ` +
    `Acima do sublimite, o estado pode exigir ICMS/ISS fora do DAS. ` +
    `Avalie com seu contador o impacto de desenquadramento ou desdobramento.`
  );
}

const TRIGGER_RENDERERS: Record<
  CascataTrigger["code"],
  (params: Record<string, string>) => string
> = {
  T1: renderT1,
  T2: renderT2,
  T3: renderT3,
  T4: renderT4,
  T5: renderT5,
};

export function renderTriggerBody(trigger: CascataTrigger): string {
  const renderer = TRIGGER_RENDERERS[trigger.code];
  return renderer ? renderer(trigger.params) : trigger.title;
}
