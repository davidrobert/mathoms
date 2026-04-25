"use client";

import { ReportSection } from "../ReportSection";
import { ReportCard } from "../ReportCard";
import { SectionSummary } from "../SectionSummary";
import { ChangelogList, type ChangelogEntry } from "../ui/ChangelogList";
import { deriveSectionSummary } from "../utils/conclusionUtils";
import type { ReportAnalysisData } from "@/lib/api";

function getNarrativas(data: ReportAnalysisData): Record<string, unknown> | undefined {
  return data.narrativas as Record<string, unknown> | undefined;
}

function SectionFallback({
  narrativas,
  sectionId,
  text,
}: {
  narrativas: Record<string, unknown> | undefined;
  sectionId: string;
  text: string | null;
}) {
  if (!text || narrativas?.[sectionId]) return null;
  return (
    <p className="md:col-span-2 text-sm text-[var(--surface-muted-foreground)]">
      {text}
    </p>
  );
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
              <th key={h} className="pb-2 font-semibold">
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

/** ADR-117/122 · Fase 10 — APP_B: Premissas e Metodologia.
 *
 * Lista premissas do snapshot E5 (goals.premissas_snapshot) quando presentes
 * + metodologias estáticas (Perini / Cerbasi / AUVP / Score próprio).
 */
export function ApendiceBSection({ data }: { data: ReportAnalysisData }) {
  const narrativas = getNarrativas(data);
  const fallback = deriveSectionSummary("APP_B", data);
  const goals = data.goals as Record<string, unknown> | undefined;
  const snapshot =
    goals && typeof goals === "object" && goals.premissas_snapshot != null
      ? (goals.premissas_snapshot as Record<string, unknown>)
      : null;

  const snapshotRows: Array<[string, string]> = snapshot
    ? Object.entries(snapshot).map(([k, v]) => [
        k,
        typeof v === "object" && v != null ? JSON.stringify(v) : String(v),
      ])
    : [];

  return (
    <ReportSection id="APP_B" title="Apêndice B — Premissas e Metodologia">
      <SectionSummary narrativas={narrativas} sectionId="APP_B" />
      <SectionFallback narrativas={narrativas} sectionId="APP_B" text={fallback} />

      <ReportCard variant="feature" title="Premissas Econômicas" size="full">
        {snapshotRows.length > 0 ? (
          <SimpleTable
            headers={["Variável", "Valor"]}
            rows={snapshotRows}
          />
        ) : (
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            Premissas econômicas não registradas neste ciclo. Serão exibidas
            quando o snapshot de metas for gerado junto ao relatório.
          </p>
        )}
      </ReportCard>

      <ReportCard variant="neutral" title="Metodologias Utilizadas" size="full">
        <div className="space-y-4 text-sm text-[var(--surface-foreground)]">
          <section>
            <h4 className="font-display font-semibold">Bruno Perini — Viver de Renda</h4>
            <p className="text-[var(--surface-muted-foreground)]">
              Número da Independência Financeira = despesa anual desejada ÷ TRS.
              Projeção de prazo com aporte constante e juros compostos sobre
              retorno real (acima da inflação).
            </p>
          </section>
          <section>
            <h4 className="font-display font-semibold">
              Gustavo Cerbasi — Equilíbrio Presente × Futuro
            </h4>
            <p className="text-[var(--surface-muted-foreground)]">
              Classificação comportamental dos gastos: proporção ideal ~70%
              presente / 30% futuro. Gastador (&lt;10% futuro), Equilibrado
              (20–40%), Poupador (&gt;40%).
            </p>
          </section>
          <section>
            <h4 className="font-display font-semibold">
              Raul Sena / AUVP — Contrafluxo
            </h4>
            <p className="text-[var(--surface-muted-foreground)]">
              Comprar ativos atrelados ao indexador fora de moda; análise
              fundamentalista em ações (P/L, ROE, DY) e FIIs (DY, vacância,
              P/VP).
            </p>
          </section>
          <section>
            <h4 className="font-display font-semibold">
              Score Financeiro — Metodologia Própria
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

/** ADR-117/122 · Fase 10 — APP_C: Cenários Alternativos.
 *
 * Resume cenário atual vs alternativo. Usa data.cenarios_mariana ou
 * data.programa_milhas; fallback "sem cenários" se ausentes.
 */
export function ApendiceCSection({ data }: { data: ReportAnalysisData }) {
  const narrativas = getNarrativas(data);
  const fallback = deriveSectionSummary("APP_C", data);
  const cenarios = data.cenarios_mariana as
    | {
        labels?: string[];
        aportes?: number[];
        prazos_if?: number[];
        anos_if?: number[];
      }
    | undefined;
  const milhas = data.programa_milhas as
    | {
        saldo_total?: number;
        valor_estimado?: number;
        observacao?: string;
      }
    | undefined;

  const hasCenarios = !!cenarios?.labels && cenarios.labels.length > 0;
  const hasMilhas =
    !!milhas && (milhas.saldo_total != null || milhas.valor_estimado != null);

  return (
    <ReportSection id="APP_C" title="Apêndice C — Cenários Alternativos">
      <SectionSummary narrativas={narrativas} sectionId="APP_C" />
      <SectionFallback narrativas={narrativas} sectionId="APP_C" text={fallback} />

      {hasCenarios && (
        <ReportCard variant="feature" title="Cenários IF — Cônjuge" size="full">
          <SimpleTable
            headers={["Cenário", "Aporte/mês", "Prazo (anos)", "Ano IF"]}
            rows={(cenarios?.labels ?? []).map((label, i) => [
              label,
              cenarios?.aportes?.[i] != null
                ? cenarios.aportes[i].toLocaleString("pt-BR", {
                    style: "currency",
                    currency: "BRL",
                    maximumFractionDigits: 0,
                  })
                : "—",
              cenarios?.prazos_if?.[i]?.toFixed(1) ?? "—",
              cenarios?.anos_if?.[i] ?? "—",
            ])}
          />
        </ReportCard>
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
                  {milhas.valor_estimado.toLocaleString("pt-BR", {
                    style: "currency",
                    currency: "BRL",
                    maximumFractionDigits: 0,
                  })}
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

      {!hasCenarios && !hasMilhas && (
        <ReportCard variant="neutral" title="Cenários Alternativos" size="full">
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            Sem cenários alternativos registrados neste ciclo.
          </p>
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
  const narrativas = getNarrativas(data);
  const fallback = deriveSectionSummary("APP_D", data);
  const lineage = data._report_lineage;

  return (
    <ReportSection id="APP_D" title="Apêndice D — Referências e Fontes">
      <SectionSummary narrativas={narrativas} sectionId="APP_D" />
      <SectionFallback narrativas={narrativas} sectionId="APP_D" text={fallback} />

      <ReportCard variant="neutral" title="Metodologias Referenciadas" size="half">
        <SimpleTable
          headers={["Autor / Método", "Tema"]}
          rows={[
            ["Bruno Perini (Viver de Renda)", "Independência financeira e montagem de carteira"],
            ["Gustavo Cerbasi", "Equilíbrio presente × futuro, comportamento financeiro"],
            ["Raul Sena / AUVP", "Contrafluxo e análise fundamentalista"],
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

interface ChangelogEntryData {
  readonly id?: string;
  readonly headline?: string;
  readonly meta?: string;
  readonly severity?: "info" | "change" | "highlight";
}

/** ADR-117/122 · Fase 10 — APP_E: Próximos Ciclos e Roadmap.
 *
 * Renderiza ChangelogList consumindo narrativas.changelog quando presente;
 * caso contrário, mostra empty state positivo.
 */
export function ApendiceESection({ data }: { data: ReportAnalysisData }) {
  const narrativas = getNarrativas(data);
  const fallback = deriveSectionSummary("APP_E", data);
  const changelogRaw = narrativas?.changelog as
    | { ciclo?: string; entries?: ChangelogEntryData[] }
    | undefined;

  const entries: ChangelogEntry[] =
    changelogRaw?.entries
      ?.filter((e): e is ChangelogEntryData => !!e && !!e.headline)
      .map((e, i) => ({
        id: e.id ?? `changelog-${i}`,
        headline: e.headline ?? "",
        meta: e.meta,
        severity: e.severity ?? "change",
      })) ?? [];

  return (
    <ReportSection id="APP_E" title="Apêndice E — Próximos Ciclos e Roadmap">
      <SectionSummary narrativas={narrativas} sectionId="APP_E" />
      <SectionFallback narrativas={narrativas} sectionId="APP_E" text={fallback} />

      <ReportCard variant="highlight" title="Histórico de Ciclos" size="full">
        {entries.length > 0 ? (
          <ChangelogList ciclo={changelogRaw?.ciclo} entries={entries} />
        ) : (
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            Sem histórico de ciclos ainda — este é o primeiro relatório
            publicado ou o snapshot não inclui changelog.
          </p>
        )}
      </ReportCard>
    </ReportSection>
  );
}
