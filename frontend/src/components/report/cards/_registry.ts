/**
 * F9 · F2.A — Registry de card builders migrados para React.
 *
 * Chave = card ID do report_layout.yaml. Valor = componente React.
 * Cards que ainda não migraram NÃO aparecem aqui — o ReportShell
 * renderiza um ReportSectionStub para eles.
 *
 * Cada lote (F2.A–F2.H) adiciona entradas incrementalmente.
 */
// Lote A (S1)
export { PatrimonioCategoriasCard } from "./PatrimonioCategoriasCard";
export { ReceitasFonteCard } from "./ReceitasFonteCard";
export { ReservaEmergenciaCard } from "./ReservaEmergenciaCard";
export { EndividamentoCard } from "./EndividamentoCard";
// Lote B (S2)
export { OrcamentoProspectivoCard } from "./OrcamentoProspectivoCard";
export { ConsumoConscienteCard } from "./ConsumoConscienteCard";
export { DiagnosticoComportamentalCard } from "./DiagnosticoComportamentalCard";
export { EquilibrioCerbasiCard } from "./EquilibrioCerbasiCard";

/** IDs dos cards já migrados — usados pelo ReportShell para decidir
 *  render real vs stub. */
export const MIGRATED_CARD_IDS = new Set([
  // Lote A
  "patrimonio_categorias",
  "receitas_fonte",
  "reserva_emergencia",
  "endividamento",
  // Lote B
  "orcamento_prospectivo",
  "consumo_consciente",
  "diagnostico_comportamental",
  "equilibrio_cerbasi",
]);
