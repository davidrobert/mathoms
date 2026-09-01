import type {
  IFMonteCarloData,
  PassiveIncomeData,
  PremissasEconomicasData,
} from "@/lib/api/reports";
import type {
  ProventosAtivoData,
  RealEstateData,
  RealEstateExcludedProperty,
  ScoreData,
} from "@/types/report-analysis";
import type { ProtecaoPatrimonialData } from "@/types/protecao";

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasStrings(value: UnknownRecord, keys: readonly string[]): boolean {
  return keys.every((key) => typeof value[key] === "string");
}

function hasNumbers(value: UnknownRecord, keys: readonly string[]): boolean {
  return keys.every(
    (key) => typeof value[key] === "number" && Number.isFinite(value[key]),
  );
}

function hasNullableNumbers(
  value: UnknownRecord,
  keys: readonly string[],
): boolean {
  return keys.every(
    (key) =>
      value[key] === null ||
      (typeof value[key] === "number" && Number.isFinite(value[key])),
  );
}

function hasNullableStrings(
  value: UnknownRecord,
  keys: readonly string[],
): boolean {
  return keys.every(
    (key) => value[key] === null || typeof value[key] === "string",
  );
}

function isStringRecord(value: unknown): value is Record<string, string> {
  return (
    isRecord(value) &&
    Object.values(value).every((item) => typeof item === "string")
  );
}

function isScoreBreakdown(value: unknown): boolean {
  return (
    Array.isArray(value) &&
    value.every(
      (row) =>
        isRecord(row) &&
        hasStrings(row, ["dimensao"]) &&
        hasNumbers(row, ["valor"]),
    )
  );
}

function isScoreData(value: unknown): value is ScoreData {
  if (!isRecord(value) || !hasNumbers(value, ["valor", "max"])) return false;
  if (
    value.classificacao !== undefined &&
    typeof value.classificacao !== "string"
  )
    return false;
  if (value.breakdown !== undefined && !isScoreBreakdown(value.breakdown))
    return false;
  return true;
}

export function readScoreData(value: unknown): ScoreData | undefined {
  return isScoreData(value) ? value : undefined;
}

function isPremissasRow(value: unknown): boolean {
  if (!isRecord(value) || !hasStrings(value, ["classe_auvp", "status"]))
    return false;
  return hasNullableStrings(value, [
    "retorno_real_esperado_pct_anual",
    "sigma_anual_pct",
    "fonte",
    "fonte_origem",
    "effective_from",
    "justificativa",
    "razao_indisponivel",
  ]);
}

function isPremissasEconomicas(
  value: unknown,
): value is PremissasEconomicasData {
  if (
    !isRecord(value) ||
    !["completo", "parcial"].includes(String(value.status))
  ) {
    return false;
  }
  if (typeof value.snapshot_at !== "string" || !Array.isArray(value.classes))
    return false;
  return value.classes.every(isPremissasRow);
}

export function readPremissasEconomicas(
  value: unknown,
): PremissasEconomicasData | undefined {
  return isPremissasEconomicas(value) ? value : undefined;
}

function isProventosRow(value: unknown): value is ProventosAtivoData {
  if (!isRecord(value) || !hasStrings(value, ["ticker"])) return false;
  if (
    !hasNumbers(value, [
      "ano_base",
      "total_proventos_brl",
      "ir_retido_brl",
      "renda_liquida_brl",
    ])
  )
    return false;
  return hasNullableNumbers(value, [
    "custo_total_brl",
    "valor_mercado_brl",
    "yield_on_cost_pct",
    "yield_on_market_pct",
  ]);
}

export function readProventosRows(
  value: unknown,
): readonly ProventosAtivoData[] | undefined {
  if (!Array.isArray(value)) return undefined;
  return value.every(isProventosRow) ? value : undefined;
}

function isSpread(value: unknown): boolean {
  return isRecord(value) && hasNumbers(value, ["vs_cdi", "vs_ntnb", "vs_ifix"]);
}

function isBenchmark(value: unknown): boolean {
  return (
    isRecord(value) &&
    hasNumbers(value, [
      "cdi_liquido_pct",
      "ntnb_liquido_pct",
      "ifix_yield_pct",
    ]) &&
    hasStrings(value, ["as_of_date"])
  );
}

function isRealEstateComponent(value: unknown): boolean {
  return (
    isRecord(value) &&
    hasNumbers(value, ["valor"]) &&
    hasStrings(value, ["origem", "confidence"])
  );
}

function isComponentsMap(value: unknown): boolean {
  return isRecord(value) && Object.values(value).every(isRealEstateComponent);
}

const IMOVEL_STRING_FIELDS = [
  "property_id",
  "descricao",
  "classification",
  "valor_imovel_origem",
  "status_contrato",
  "origem_aluguel",
] as const;
const IMOVEL_NULLABLE_NUMBER_FIELDS = [
  "aluguel_mensal_bruto",
  "taxa_administracao_mensal",
  "iptu_mensal",
  "condominio_mensal",
  "meses_locado_no_ano",
  "vacancia_pct_empirica",
  "cap_rate_bruto_pct",
  "cap_rate_liquido_pct",
  "gap_reajuste_pct",
] as const;
const IMOVEL_NULLABLE_STRING_FIELDS = [
  "indice_reajuste",
  "data_ultimo_reajuste",
  "endereco_display",
  "imobiliaria_nome",
] as const;

function isRealEstateImovel(value: unknown): boolean {
  if (!isRecord(value) || !hasStrings(value, IMOVEL_STRING_FIELDS))
    return false;
  if (!hasNumbers(value, ["valor_imovel", "ir_retido_mensal"])) return false;
  return (
    hasNullableNumbers(value, IMOVEL_NULLABLE_NUMBER_FIELDS) &&
    hasNullableStrings(value, IMOVEL_NULLABLE_STRING_FIELDS)
  );
}

function isExcludedProperty(value: unknown): boolean {
  return (
    isRecord(value) &&
    hasStrings(value, ["property_id", "descricao", "classification", "motivo"])
  );
}

export function readExcludedProperties(
  value: unknown,
): readonly RealEstateExcludedProperty[] {
  if (!isRecord(value) || !Array.isArray(value.excluded_properties)) return [];
  return value.excluded_properties.every(isExcludedProperty)
    ? value.excluded_properties
    : [];
}

function isRealEstateAlert(value: unknown): boolean {
  return isRecord(value) && hasStrings(value, ["code", "severity", "context"]);
}

function hasRealEstateArrays(value: UnknownRecord): boolean {
  if (!Array.isArray(value.imoveis) || !value.imoveis.every(isRealEstateImovel))
    return false;
  if (!Array.isArray(value.excluded_properties)) return false;
  if (!value.excluded_properties.every(isExcludedProperty)) return false;
  return Array.isArray(value.alertas) && value.alertas.every(isRealEstateAlert);
}

function isRealEstateData(value: unknown): value is RealEstateData {
  if (
    !isRecord(value) ||
    !hasNullableNumbers(value, ["cap_rate_liquido_pct", "cap_rate_bruto_pct"])
  )
    return false;
  if (!hasNumbers(value, ["concentracao_pct", "valor_total_imoveis"]))
    return false;
  if (
    !isComponentsMap(value.componentes_calculo) ||
    !isBenchmark(value.benchmarks)
  )
    return false;
  if (!isSpread(value.spreads_pp) || !isSpread(value.spread_brl_anual))
    return false;
  return hasRealEstateArrays(value);
}

export function readRealEstateData(value: unknown): RealEstateData | undefined {
  return isRealEstateData(value) ? value : undefined;
}

function isMonteCarloPath(value: unknown): boolean {
  return (
    Array.isArray(value) &&
    value.every(
      (point) =>
        Array.isArray(point) &&
        point.length === 2 &&
        point.every(
          (item) => typeof item === "number" && Number.isFinite(item),
        ),
    )
  );
}

function isMonteCarloData(value: unknown): value is IFMonteCarloData {
  if (!isRecord(value) || !hasNumbers(value, ["sigma_usado"])) return false;
  if (typeof value.exibir_cone !== "boolean") return false;
  if (
    value.motivo_sem_cone !== null &&
    typeof value.motivo_sem_cone !== "string"
  )
    return false;
  if (
    !isMonteCarloPath(value.caminho_p10) ||
    !isMonteCarloPath(value.caminho_p50)
  )
    return false;
  return isMonteCarloPath(value.caminho_p90);
}

export function readMonteCarloData(
  value: unknown,
): IFMonteCarloData | undefined {
  return isMonteCarloData(value) ? value : undefined;
}

const PASSIVE_OK_NUMBERS = [
  "renda_passiva_anual_brl",
  "renda_passiva_mensal_brl",
  "patrimonio_gerador_brl",
  "trs_efetiva_pct",
  "acumuladores_pct_gerador",
] as const;

function isPassiveIncome(value: unknown): value is PassiveIncomeData {
  if (
    !isRecord(value) ||
    !["ok", "sem_irpf", "gerador_zero"].includes(String(value.status))
  ) {
    return false;
  }
  if (value.status !== "ok") return true;
  if (!hasNumbers(value, PASSIVE_OK_NUMBERS)) return false;
  if (!hasNullableNumbers(value, ["ano_referencia_irpf", "defasagem_meses"]))
    return false;
  return true;
}

export function readPassiveIncome(
  value: unknown,
): PassiveIncomeData | undefined {
  return isPassiveIncome(value) ? value : undefined;
}

function isBemGap(value: unknown): boolean {
  if (
    !isRecord(value) ||
    !hasStrings(value, [
      "veiculo_id",
      "lmi_brl",
      "fipe_brl",
      "gap_pct",
      "sinal",
    ])
  )
    return false;
  return (
    value.veiculo_descricao === undefined ||
    typeof value.veiculo_descricao === "string"
  );
}

function isGapQualitativo(value: unknown): boolean {
  return (
    isRecord(value) &&
    hasStrings(value, ["categoria", "rationale"]) &&
    typeof value.flag === "boolean"
  );
}

const APOLICE_STRING_FIELDS = [
  "apolice_numero",
  "seguradora",
  "vigencia_inicio",
  "vigencia_fim",
  "premio_total_brl",
] as const;

function isApolice(value: unknown): boolean {
  if (!isRecord(value) || !hasStrings(value, APOLICE_STRING_FIELDS))
    return false;
  if (!hasNumbers(value, ["bens_count"])) return false;
  if (
    value.seguradora_nome !== undefined &&
    typeof value.seguradora_nome !== "string"
  )
    return false;
  return (
    value.tipos_bem === undefined ||
    (Array.isArray(value.tipos_bem) &&
      value.tipos_bem.every((item) => typeof item === "string"))
  );
}

function isProtectionScope(value: unknown): boolean {
  if (value === undefined) return true;
  if (
    !isRecord(value) ||
    typeof value.premio_inclui_cadastro_manual !== "boolean"
  )
    return false;
  if (typeof value.veredito_pct_renda_suprimido !== "boolean") return false;
  return (
    Array.isArray(value.categorias_somente_no_cadastro) &&
    value.categorias_somente_no_cadastro.every(
      (item) => typeof item === "string",
    )
  );
}

function hasProtectionArrays(value: UnknownRecord): boolean {
  if (!Array.isArray(value.bens_com_gap_cobertura)) return false;
  if (!value.bens_com_gap_cobertura.every(isBemGap)) return false;
  if (!Array.isArray(value.gap_qualitativo)) return false;
  if (!value.gap_qualitativo.every(isGapQualitativo)) return false;
  return ["apolices_vigentes", "apolices_vencendo", "apolices_vencidas"].every(
    (key) => Array.isArray(value[key]) && value[key].every(isApolice),
  );
}

function isProtecaoPatrimonial(
  value: unknown,
): value is ProtecaoPatrimonialData {
  if (
    !isRecord(value) ||
    !hasStrings(value, ["premio_total_anual_brl", "pct_renda_anual"])
  )
    return false;
  if (
    !isStringRecord(value.premio_decomposicao) ||
    !hasNumbers(value, ["corretoras_count", "seguradoras_count"])
  )
    return false;
  return (
    hasProtectionArrays(value) && isProtectionScope(value.escopo_cobertura)
  );
}

export function readProtecaoPatrimonial(
  value: unknown,
): ProtecaoPatrimonialData | undefined {
  return isProtecaoPatrimonial(value) ? value : undefined;
}

/** [[ADR-431]] — ativo físico publicado sem valor apurado ([[A40.l111]]).
 *
 * Um grão abaixo de `baldes_negativos`: o balde agregado segue positivo e é
 * cego ao item. O que a família precisa saber é a DIREÇÃO do erro — o número
 * publicado é o piso, não o teto.
 */
export interface ItemFisicoSemValor {
  readonly colecao: "imoveis" | "veiculos";
  readonly descricao: string;
  readonly ano: string;
}

function isItemFisicoSemValor(value: unknown): value is ItemFisicoSemValor {
  return (
    isRecord(value) &&
    (value.colecao === "imoveis" || value.colecao === "veiculos") &&
    typeof value.ano === "string"
  );
}

export function readItensSemValor(
  patrimonio: unknown,
): readonly ItemFisicoSemValor[] {
  if (!isRecord(patrimonio) || !isRecord(patrimonio.guarda_de_sinal)) return [];
  const itens = patrimonio.guarda_de_sinal.itens_sem_valor;
  if (!Array.isArray(itens)) return [];
  return itens.every(isItemFisicoSemValor) ? itens : [];
}
