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
export { AlocacaoAtualVsAlvoCard } from "./AlocacaoAtualVsAlvoCard";
export type {
  AlocacaoAtualVsAlvoCardProps,
  AlocacaoDerived,
} from "./AlocacaoAtualVsAlvoCard";
// Sprint A16 L2 P5 (ADR-236 §D5) — Tributário PJ Cascata Fiscal.
export { CascataFiscalCard } from "./CascataFiscalCard";
export { ConsumoConscienteCard } from "./ConsumoConscienteCard";
export { ContrafluxoCard } from "./ContrafluxoCard";
export type { ContrafluxoData } from "./ContrafluxoCard";
export { DiagnosticoComportamentalCard } from "./DiagnosticoComportamentalCard";
export { EndividamentoCard } from "./EndividamentoCard";
export { ExposicaoCambialCard } from "./ExposicaoCambialCard";
export { EquilibrioCerbasiCard } from "./EquilibrioCerbasiCard";
export { EstrategiaAporteCard } from "./EstrategiaAporteCard";
export type { EstrategiaAporteData } from "./EstrategiaAporteCard";
// InvestimentosClasseCard substituído por AlocacaoAtualVsAlvoCard em A11 (2026-05-11).
// Removido em Fase B com migração v1→v2 (ADR-141).
export { InvestimentosClasseCard } from "./InvestimentosClasseCard";
export type { InvestimentosClasseData } from "./InvestimentosClasseCard";
export { Top15AtivosCard } from "./Top15AtivosCard";
export type { Top15AtivosData, TopAtivo } from "./Top15AtivosCard";
export { OrcamentoProspectivoCard } from "./OrcamentoProspectivoCard";
export { PatrimonioCategoriasCard } from "./PatrimonioCategoriasCard";
export { PerfilFamiliaCard } from "./PerfilFamiliaCard";
export { PosicaoInformeCard } from "./PosicaoInformeCard";
export { PontosFortesCard } from "./PontosFortesCard";
export { PontosUrgentesCard } from "./PontosUrgentesCard";
export { PrevidenciaPgblCard } from "./PrevidenciaPgblCard";
export type { PrevidenciaPgblData } from "./PrevidenciaPgblCard";
// A33.l4 (ADR-238 §L4) — proventos por ativo em S3 (yield sobre custo + valor atual).
export { ProventosYieldCard } from "./ProventosYieldCard";
export { ReceitasFonteCard } from "./ReceitasFonteCard";
export { RentabilidadeCard } from "./RentabilidadeCard";
export { ReservaEmergenciaCard } from "./ReservaEmergenciaCard";
export { TitularesCard } from "./TitularesCard";
export { IrpfRendaAnualCard } from "./IrpfRendaAnualCard";
export { IrpfIrPagoCard } from "./IrpfIrPagoCard";
export { IrpfSplitTrabalhoCapitalCard } from "./IrpfSplitTrabalhoCapitalCard";
export { IrpfPgblCapacidadeCard } from "./IrpfPgblCapacidadeCard";
export { IrpfDependentesCard } from "./IrpfDependentesCard";
export { IrpfDedutiveisAplicadosCard } from "./IrpfDedutiveisAplicadosCard";
// S9-T04 (ADR-192 §D4) — Riscos e Proteção
export { HeroGapProtecaoCard } from "./HeroGapProtecaoCard";
export { CoberturaSegurosCard } from "./CoberturaSegurosCard";
export { SucessaoCard } from "./SucessaoCard";
export { AcoesMitigacaoCard } from "./AcoesMitigacaoCard";
export type {
  ProtectionBundle,
  ProtectionItem,
  ProtectionGapItem,
  ProtectionRecommendation,
  RiskInferred,
  ProtectionThresholds,
  ProtectionCategory,
  ProtectionStatus,
  CoverageType,
  ProtectionPriority,
  MitigationStatus,
} from "./protectionBundle.types";
