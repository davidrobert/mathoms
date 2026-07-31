"use client";

import { ReportSection } from "../ReportSection";
import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import { SectionSummary } from "../SectionSummary";
import { PremissasEconomicasCard } from "../cards/PremissasEconomicasCard";
import { StressScenarioCard } from "../cards/StressScenarioCard";
import type { ReportAnalysisData } from "@/lib/api";
import { formatDate } from "@/lib/format";
import {
  formatGoalVigenciaDate,
  humanizeGoalType,
  isDisplayableGoalType,
} from "@/lib/goalPremissas";

interface ActiveGoalRef {
  readonly type: string;
  readonly id?: string;
  readonly effective_from?: string;
}

interface PremissasSnapshotShape {
  readonly schema?: number;
  readonly captured_at?: string;
  readonly goals_json_sha256?: string | null;
  readonly active_goals?: ReadonlyArray<ActiveGoalRef>;
}

function safeFormatDate(iso: string): string | null {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return formatDate(iso);
}

function SimpleTable({
  headers,
  rows,
}: {
  headers: readonly string[];
  rows: ReadonlyArray<readonly (string | number)[]>;
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--surface-border)] text-left text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
            {headers.map((h) => (
              <th key={h} scope="col" className="pb-2 font-semibold">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              className="border-b border-[var(--surface-border)]/40 last:border-0"
            >
              {row.map((cell, j) => (
                <td key={j} className="py-2 pr-4 text-[var(--surface-foreground)]">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function MetasVigentesCard({
  snapshot,
}: {
  snapshot: PremissasSnapshotShape | null;
}) {
  // Filtra tipos não-canônicos (resíduo pré-ADR-180 — ex.: PLANNING_CONTEXT
  // em snapshots de relatórios gerados antes do fix backend).
  const activeGoals: ReadonlyArray<ActiveGoalRef> = (
    snapshot?.active_goals ?? []
  ).filter((g) => isDisplayableGoalType(g.type));
  const capturedAtLabel = snapshot?.captured_at
    ? safeFormatDate(snapshot.captured_at)
    : null;

  return (
    <ReportCard variant="feature" title="Metas vigentes neste ciclo" size="full">
      {activeGoals.length > 0 ? (
        <ul className="divide-y divide-[var(--surface-border)]/40">
          {activeGoals.map((g, i) => (
            <li
              key={g.id ?? `${g.type}-${i}`}
              className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-3 first:pt-0 last:pb-0"
            >
              <span className="font-display font-semibold text-[var(--surface-foreground)]">
                {humanizeGoalType(g.type)}
              </span>
              {g.effective_from && (
                <span className="text-sm text-[var(--surface-muted-foreground)]">
                  Vigente desde {formatGoalVigenciaDate(g.effective_from)}
                </span>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Nenhuma meta vigente neste ciclo. Cadastre metas em{" "}
          <strong>Plano &gt; Metas</strong> para acompanhar progresso nos
          próximos relatórios.
        </p>
      )}
      {capturedAtLabel && (
        <p className="mt-4 text-xs text-[var(--surface-muted-foreground)]">
          Snapshot capturado em {capturedAtLabel}.
        </p>
      )}
    </ReportCard>
  );
}

/** ADR-117/122 · Fase 10 — APP_B: Premissas e Metodologia.
 *
 * Lista metas vigentes do snapshot E5 (goals.premissas_snapshot.active_goals)
 * + premissas econômicas auditáveis (ADR-219, retorno real + sigma por classe)
 * + metodologias estáticas (Perini / Cerbasi / AUVP / Score próprio).
 */
export function ApendiceBSection({ data }: { data: ReportAnalysisData }) {
  const goals = data.goals as Record<string, unknown> | undefined;
  const snapshot: PremissasSnapshotShape | null =
    goals && typeof goals === "object" && goals.premissas_snapshot != null
      ? (goals.premissas_snapshot as PremissasSnapshotShape)
      : null;

  return (
    <ReportSection id="APP_B" title="Apêndice B — Premissas e Metodologia">
      <SectionSummary data={data} sectionId="APP_B" />

      <MetasVigentesCard snapshot={snapshot} />
      <PremissasEconomicasCard premissas={data.premissas_economicas ?? null} />

      <ReportCard variant="neutral" title="Pilares Metodológicos" size="full">
        <div className="space-y-4 text-sm text-[var(--surface-foreground)]">
          <p className="text-[var(--surface-muted-foreground)]">
            Este relatório aplica regras consagradas de planejamento
            patrimonial brasileiro, organizadas em pilares complementares.
          </p>
          <section>
            <h4 className="font-display font-semibold">Patrimônio gerador de renda</h4>
            <p className="text-[var(--surface-muted-foreground)]">
              Número da Independência Financeira = despesa anual desejada ÷ TRS.
              Projeção de prazo com aporte constante e juros compostos sobre
              retorno real (acima da inflação).
            </p>
          </section>
          <section>
            <h4 className="font-display font-semibold">
              Equilíbrio entre presente e futuro
            </h4>
            <p className="text-[var(--surface-muted-foreground)]">
              Classificação comportamental dos gastos: proporção ideal ~70%
              presente / 30% futuro. Gastador (&lt;10% futuro), Equilibrado
              (20–40%), Poupador (&gt;40%).
            </p>
          </section>
          <section>
            <h4 className="font-display font-semibold">
              Alocação contracíclica e análise fundamentalista
            </h4>
            <p className="text-[var(--surface-muted-foreground)]">
              Priorizar indexadores de renda fixa fora do ciclo aquecido;
              análise fundamentalista em ações (P/L, ROE, DY) e FIIs (DY,
              vacância, P/VP).
            </p>
          </section>
          <section>
            <h4 className="font-display font-semibold">
              Score Financeiro Mathoms — metodologia própria
            </h4>
            <p className="text-[var(--surface-muted-foreground)]">
              Média ponderada de 5 componentes (0–10): Taxa de Poupança (2,0),
              Cobertura de Despesas (1,5), Endividamento invertido (1,5),
              Progresso IF (2,0), Diversificação (1,0).
            </p>
          </section>
        </div>
      </ReportCard>
    </ReportSection>
  );
}

/** ADR-167 (A8.4 PR3) — APP_C: Cenários de Estresse.
 *
 * Hide-when-empty com numeração estável: quando `data.cenarios_conjuge`
 * (e `data.programa_milhas`) ausentes, seção retorna `null` — APP_D
 * permanece rotulado "D" porque a numeração no YAML é literal, não
 * recomputada.
 *
 * Visualização (D3 do plano A8.4): comparativo lado-a-lado base vs.
 * cenário de estresse com delta explícito + parágrafo "Leitura:" para
 * justificar o stress test em tom não-alarmista (CVM/Susep).
 */
export function ApendiceCSection({ data }: { data: ReportAnalysisData }) {
  const cenarios = data.cenarios_conjuge as
    | {
        labels?: string[];
        aportes?: number[];
        prazos_if?: number[];
        anos_if?: number[];
        cenarios?: Array<{ aporte_mensal?: number; prazo_if_anos?: number; ano_if?: number; resumo?: string }>;
        premissas?: { aporte_base?: number };
      }
    | undefined;
  const milhas = data.programa_milhas as
    | {
        saldo_total?: number;
        valor_estimado?: number;
        observacao?: string;
      }
    | undefined;
  // A37.l10 PD-09 — o payload E5 (IFProjection.to_legacy_dict) expõe
  // prazo_anos_realista/ano_if; sentinela 999 = "não atinge" (if_projector)
  // degrada a coluna base para "—" em vez de exibir "999a".
  const rawGoals = data.goals as
    | { prazo_anos_realista?: number; ano_if?: number }
    | undefined;
  const goalsAtingeIF = rawGoals != null && rawGoals.prazo_anos_realista !== 999;
  const goals = goalsAtingeIF
    ? { if_prazo_anos: rawGoals.prazo_anos_realista, if_ano: rawGoals.ano_if }
    : undefined;

  const hasCenarios = !!cenarios?.labels && cenarios.labels.length > 0;
  const hasMilhas =
    !!milhas && (milhas.saldo_total != null || milhas.valor_estimado != null);

  // ADR-167 hide-when-empty: workspace inelegível (gate retorna False) →
  // seção some completamente. Numeração A/B/D/E preservada.
  if (!hasCenarios && !hasMilhas) {
    return null;
  }

  return (
    <ReportSection id="APP_C" title="Apêndice C — Cenários de Estresse">
      {/* A40.l4: a APP_C é o único apêndice com parágrafo de abertura
          AUTORAL (tom CVM/Susep: "não são previsões"). O derivado dizia a
          mesma coisa mais pobre — "validar a margem de segurança do plano"
          aparecia nos dois, um sob o outro. Sem <SectionSummary> aqui; o
          layout registra `summary: false` para a regra 6 do gate estático
          não acusar flag sem render site. */}
      <p className="md:col-span-2 text-sm text-[var(--surface-muted-foreground)]">
        Como o seu plano se comporta se uma premissa central mudar. Não são
        previsões — são testes de resiliência para validar a margem de
        segurança do plano atual.
      </p>

      {hasCenarios && (
        <StressScenarioCard cenarios={cenarios!} goals={goals} />
      )}

      {hasMilhas && (
        <ReportCard variant="neutral" title="Programa de Milhas" size="full">
          <dl className="grid grid-cols-2 gap-4 text-sm">
            {milhas?.saldo_total != null && (
              <div>
                <dt className="text-xs text-[var(--surface-muted-foreground)]">
                  Saldo total
                </dt>
                <dd className="font-mono tabular-nums">
                  {milhas.saldo_total.toLocaleString("pt-BR")}
                </dd>
              </div>
            )}
            {milhas?.valor_estimado != null && (
              <div>
                <dt className="text-xs text-[var(--surface-muted-foreground)]">
                  Valor estimado
                </dt>
                <dd className="font-mono tabular-nums">
                  <MonetaryValue value={milhas.valor_estimado} fractionDigits={0} />
                </dd>
              </div>
            )}
          </dl>
          {milhas?.observacao && (
            <p className="mt-3 text-xs text-[var(--surface-muted-foreground)]">
              {milhas.observacao}
            </p>
          )}
        </ReportCard>
      )}
    </ReportSection>
  );
}


/** ADR-117/122 · Fase 10 — APP_D: Referências e Fontes.
 *
 * Metodologias de referência + lineage do relatório (pipeline_run_id,
 * contagem de documentos) do _report_lineage injetado pela API.
 */
export function ApendiceDSection({ data }: { data: ReportAnalysisData }) {
  const lineage = data._report_lineage;

  return (
    <ReportSection id="APP_D" title="Apêndice D — Referências e Fontes">
      <SectionSummary data={data} sectionId="APP_D" />

      <ReportCard variant="neutral" title="Pilares Metodológicos" size="half">
        <SimpleTable
          headers={["Pilar", "Aplicação"]}
          rows={[
            ["Patrimônio gerador de renda", "Independência financeira e montagem de carteira"],
            ["Equilíbrio presente × futuro", "Comportamento financeiro do casal e família"],
            ["Alocação contracíclica + análise fundamentalista", "Otimização de classes de ativos"],
            ["Score Mathoms", "Metodologia própria (5 componentes ponderados)"],
          ]}
        />
      </ReportCard>

      <ReportCard variant="neutral" title="Lineage do Relatório" size="half">
        {lineage ? (
          <dl className="space-y-2 text-sm">
            <div>
              <dt className="text-xs text-[var(--surface-muted-foreground)]">
                Pipeline run
              </dt>
              <dd className="font-mono text-xs tabular-nums">
                {lineage.pipeline_run_id ?? "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-[var(--surface-muted-foreground)]">
                Documentos analisados
              </dt>
              <dd className="font-mono tabular-nums">
                {lineage.consumed_document_count ?? 0}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-[var(--surface-muted-foreground)]">
                Prontos no workspace
              </dt>
              <dd className="font-mono tabular-nums">
                {lineage.source_document_count}
              </dd>
            </div>
          </dl>
        ) : (
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            Sem informação de lineage disponível.
          </p>
        )}
      </ReportCard>
    </ReportSection>
  );
}

/** ADR-117/122 · Fase 10 — APP_E: Próximos Ciclos e Roadmap.
 *
 * Seção forward-looking: roadmap e próximos passos, texto de abertura via
 * <SectionSummary> (precedência ADR-356). Variação vs. relatório
 * anterior é responsabilidade da seção V0 (`VariacaoSection`, ADR-190
 * §Emenda) — o card "Histórico de Ciclos" foi removido em 2026-06-12
 * (TRACK-remove-historico-ciclos-app-e): duplicava `data.changelog`
 * single-pair com rótulo enganoso.
 */
export function ApendiceESection({ data }: { data: ReportAnalysisData }) {
  return (
    <ReportSection id="APP_E" title="Apêndice E — Próximos Ciclos e Roadmap">
      <SectionSummary data={data} sectionId="APP_E" />
    </ReportSection>
  );
}
