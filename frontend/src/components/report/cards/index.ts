/**
 * Section-composer cards do relatório premium.
 *
 * Camada **acima** dos primitivos `ui/` (`Alert`, `Badge`, `Kpi`, `ScoreCard`,
 * `ChangelogList`…) e **abaixo** dos `sections/` (S1, S2, …). Cada card aqui:
 *
 *   - assume um shape de dados específico do DTO (`PatrimonioData`,
 *     `OrcamentoProspectivoData`, `EquilibrioCerbasiData`…);
 *   - delega o frame visual ao primitivo canônico `ReportCard`;
 *   - é importado por exatamente uma `sections/<S>.tsx` (ou pelo
 *     `ReportShell` no caso do `PerfilFamiliaCard`).
 *
 * **Não migrar para `ui/`.** Primitivos em `ui/` são section-agnostic; os
 * cards aqui carregam lógica de domínio do relatório (ex.: tabela de
 * composição patrimonial, semáforo de reserva, agregação por fonte) e
 * pertencem a esta camada por design — decisão registrada em v2.6
 * (2026-04-27) e em [REPORT_PREMIUM_PLAN.md §17.9](../../../../../docs/REPORT_PREMIUM_PLAN.md).
 */
export { ConsumoConscienteCard } from "./ConsumoConscienteCard";
export { ContrafluxoCard } from "./ContrafluxoCard";
export type { ContrafluxoData } from "./ContrafluxoCard";
export { DiagnosticoComportamentalCard } from "./DiagnosticoComportamentalCard";
export { EndividamentoCard } from "./EndividamentoCard";
export { EquilibrioCerbasiCard } from "./EquilibrioCerbasiCard";
export { EstrategiaAporteCard } from "./EstrategiaAporteCard";
export type { EstrategiaAporteData } from "./EstrategiaAporteCard";
export { InvestimentosClasseCard } from "./InvestimentosClasseCard";
export type { InvestimentosClasseData } from "./InvestimentosClasseCard";
export { Top15AtivosCard } from "./Top15AtivosCard";
export type { Top15AtivosData, TopAtivo } from "./Top15AtivosCard";
export { OrcamentoProspectivoCard } from "./OrcamentoProspectivoCard";
export { PatrimonioCategoriasCard } from "./PatrimonioCategoriasCard";
export { PerfilFamiliaCard } from "./PerfilFamiliaCard";
export { PontosFortesCard } from "./PontosFortesCard";
export { PontosUrgentesCard } from "./PontosUrgentesCard";
export { PrevidenciaPgblCard } from "./PrevidenciaPgblCard";
export type { PrevidenciaPgblData } from "./PrevidenciaPgblCard";
export { ReceitasFonteCard } from "./ReceitasFonteCard";
export { ReservaEmergenciaCard } from "./ReservaEmergenciaCard";
export { IrpfRendaAnualCard } from "./IrpfRendaAnualCard";
export { IrpfIrPagoCard } from "./IrpfIrPagoCard";
export { IrpfSplitTrabalhoCapitalCard } from "./IrpfSplitTrabalhoCapitalCard";
export { IrpfPgblCapacidadeCard } from "./IrpfPgblCapacidadeCard";
