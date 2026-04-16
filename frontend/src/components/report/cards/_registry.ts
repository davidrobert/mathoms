/**
 * F9 · F2.A — Registry de card builders migrados para React.
 *
 * Chave = card ID do report_layout.yaml. Valor = componente React.
 * Cards que ainda não migraram NÃO aparecem aqui — o ReportShell
 * renderiza um ReportSectionStub para eles.
 *
 * Cada lote (F2.A–F2.H) adiciona entradas incrementalmente.
 */
export { PatrimonioCategoriasCard } from "./PatrimonioCategoriasCard";
export { ReceitasFonteCard } from "./ReceitasFonteCard";
export { ReservaEmergenciaCard } from "./ReservaEmergenciaCard";
export { EndividamentoCard } from "./EndividamentoCard";

/** IDs dos cards já migrados — usados pelo ReportShell para decidir
 *  render real vs stub. */
export const MIGRATED_CARD_IDS = new Set([
  "patrimonio_categorias",
  "receitas_fonte",
  "reserva_emergencia",
  "endividamento",
]);
