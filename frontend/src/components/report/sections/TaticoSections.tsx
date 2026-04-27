"use client";

import { useCallback, useEffect, useState } from "react";
import { ReportSection } from "../ReportSection";
import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import { SectionSnapshotDiff } from "../SectionSnapshotDiff";
import { Kanban, NotasCard, Timeline } from "../ui";
import type {
  KanbanItem as KanbanUIItem,
  KanbanColumn,
  NotasSaveState,
  TimelineItem,
} from "../ui";
import { adaptProximos15dToTimeline } from "../utils/timelineAdapter";
import {
  deriveAporteSummary,
  deriveInvestimentosDelta,
  type AporteSummary,
  type InvestimentoDeltaRow,
} from "../utils/aportesAdapter";
import {
  getReportNotes,
  listKanbanItems,
  putReportNotes,
  updateKanbanItem,
  type KanbanItemPayload,
  type ReportAnalysisData,
} from "@/lib/api";
import { ApiError } from "@/lib/api";
import type {
  FluxoCaixaSummary,
  OrcamentoProspectivoData,
  ConsumoConscienteData,
} from "@/types/report-analysis";

/** F9 · Fase 8 — Seções T1–T6 do modo Tático (Dashboard Operacional).
 *
 * T3 (tarefas) + T6 (notas) consomem ADR-123 endpoints de colaboração.
 * T5 consome timelineAdapter derivando de `dashboard.proximos_15d`.
 * T4 permanece read-only a partir de `data.alertas`.
 */

export function T1FluxoOperacionalSection({ data }: { data: ReportAnalysisData }) {
  const fluxo = data.fluxo_caixa as FluxoCaixaSummary | undefined;
  const orcamento = data.orcamento_prospectivo as OrcamentoProspectivoData | undefined;
  const consumo = data.consumo_consciente as ConsumoConscienteData | undefined;

  const kpis = [
    { label: "Receita Total", value: <MonetaryValue value={fluxo?.receita_total} /> },
    { label: "Despesas Totais", value: <MonetaryValue value={fluxo?.despesa_total} /> },
    { label: "Folga Mensal", value: <MonetaryValue value={consumo?.folga_mensal} /> },
    { label: "Orçamento Mensal", value: <MonetaryValue value={orcamento?.total} /> },
  ];

  const categorias = (fluxo?.despesas_por_categoria ?? {}) as Record<string, number>;
  const entries = Object.entries(categorias).filter(([, v]) => v > 0).sort(([, a], [, b]) => b - a);

  return (
    <ReportSection id="T1" title="Fluxo Operacional — Despesas vs Tetos">
      <div className="md:col-span-2 mb-2 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {kpis.map(({ label, value }) => (
          <div
            key={label}
            className="rounded-[var(--radius-card)] border border-[var(--surface-border)] bg-[var(--surface-card)] p-4 shadow-[var(--shadow-sm)]"
          >
            <p className="text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">{label}</p>
            <p className="mt-2 text-xl font-semibold leading-tight text-[var(--surface-foreground)]">{value}</p>
          </div>
        ))}
      </div>

      <ReportCard variant="feature" title="Despesas Acumuladas por Categoria">
        {entries.length === 0 ? (
          <p className="text-sm text-[var(--surface-muted-foreground)]">Sem dados de despesas.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--surface-border)] text-left">
                  <th className="pb-2 font-display font-semibold">Categoria</th>
                  <th className="pb-2 text-right font-display font-semibold">Acumulado</th>
                </tr>
              </thead>
              <tbody>
                {entries.map(([cat, val]) => (
                  <tr key={cat} className="border-b border-[var(--surface-border)]/40 last:border-0">
                    <td className="py-2 capitalize">{cat.replace(/_/g, " ")}</td>
                    <td className="py-2 text-right font-mono tabular-nums">
                      {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(val)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </ReportCard>
    </ReportSection>
  );
}

// ═════════════════════════════════════════════════════════════════════
// T2 — Aportes e Investimentos (v2.4)
// ═════════════════════════════════════════════════════════════════════

function aportesT2Conclusion(
  summary: AporteSummary | null,
  rows: readonly InvestimentoDeltaRow[],
  data: ReportAnalysisData,
): string | undefined {
  const fromLLM = (data.narrativas as Record<string, unknown> | undefined)?.[
    "t2_aportes"
  ] as { conclusion?: string } | undefined;
  if (typeof fromLLM?.conclusion === "string" && fromLLM.conclusion.length > 0) {
    return fromLLM.conclusion;
  }
  if (!summary) return undefined;
  const totalDelta = rows.reduce((s, r) => s + r.delta, 0);
  const fmt = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
  const cobertura = summary.total_meta > 0
    ? Math.round((summary.total_realizado / summary.total_meta) * 100)
    : 0;
  return `${summary.destinos_concluidos}/${summary.destinos_total} aportes do ciclo concluídos (${cobertura}% da meta de ${fmt.format(summary.total_meta)}). Variação patrimonial agregada: ${fmt.format(totalDelta)}.`;
}

function AporteCardItem({
  label,
  feito,
  valorMeta,
  valorEfetivo,
}: {
  label: string;
  feito: boolean;
  valorMeta: number;
  valorEfetivo: number | null;
}) {
  const status = feito ? "OK" : "Pendente";
  const tone = feito ? "var(--semantic-gain)" : "var(--semantic-alert)";
  return (
    <div className="rounded-[var(--radius-card)] border border-[var(--surface-border)] bg-[var(--surface-card)] p-4 shadow-[var(--shadow-sm)]">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wider text-[var(--surface-muted-foreground)]">
          {label}
        </p>
        <span
          className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase"
          style={{ color: tone, borderColor: tone, borderWidth: 1 }}
        >
          {status}
        </span>
      </div>
      <p className="mt-2 text-xl font-semibold leading-tight text-[var(--surface-foreground)]">
        {feito ? (
          <MonetaryValue value={valorEfetivo ?? valorMeta} />
        ) : (
          <span className="text-[var(--surface-muted-foreground)]">Pendente</span>
        )}
      </p>
      <p className="mt-1 text-xs text-[var(--surface-muted-foreground)]">
        Meta: <MonetaryValue value={valorMeta} hideSymbol={false} />
      </p>
    </div>
  );
}

function AporteKpis({ summary }: { summary: AporteSummary }) {
  const cobertura = summary.total_meta > 0
    ? Math.round((summary.total_realizado / summary.total_meta) * 100)
    : 0;
  const kpis = [
    { label: "Destinos do ciclo", value: <span>{summary.destinos_total}</span> },
    {
      label: "Concluídos",
      value: <span>{summary.destinos_concluidos}/{summary.destinos_total}</span>,
    },
    { label: "Total realizado", value: <MonetaryValue value={summary.total_realizado} /> },
    { label: "Meta do ciclo", value: <MonetaryValue value={summary.total_meta} /> },
    { label: "Cobertura", value: <span>{cobertura}%</span> },
  ];
  return (
    <div className="md:col-span-2 mb-2 grid grid-cols-2 gap-3 lg:grid-cols-5">
      {kpis.map(({ label, value }) => (
        <div
          key={label}
          className="rounded-[var(--radius-card)] border border-[var(--surface-border)] bg-[var(--surface-card)] p-4 shadow-[var(--shadow-sm)]"
        >
          <p className="text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">{label}</p>
          <p className="mt-2 text-xl font-semibold leading-tight text-[var(--surface-foreground)]">{value}</p>
        </div>
      ))}
    </div>
  );
}

function InvestimentoDeltaTable({ rows }: { rows: readonly InvestimentoDeltaRow[] }) {
  if (rows.length === 0) {
    return (
      <p className="text-sm text-[var(--surface-muted-foreground)]">
        Sem dados de variação patrimonial neste ciclo.
      </p>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--surface-border)] text-left">
            <th className="pb-2 font-display font-semibold">Bloco</th>
            <th className="pb-2 text-right font-display font-semibold">Anterior</th>
            <th className="pb-2 text-right font-display font-semibold">Atual</th>
            <th className="pb-2 text-right font-display font-semibold">Δ</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} className="border-b border-[var(--surface-border)]/40 last:border-0">
              <td className="py-2">{r.label}</td>
              <td className="py-2 text-right"><MonetaryValue value={r.anterior} /></td>
              <td className="py-2 text-right"><MonetaryValue value={r.atual} /></td>
              <td className="py-2 text-right">
                <MonetaryValue value={r.delta} signed />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function T2AportesSection({ data }: { data: ReportAnalysisData }) {
  const summary = deriveAporteSummary(data);
  const deltaRows = deriveInvestimentosDelta(data);
  const conclusion = aportesT2Conclusion(summary, deltaRows, data);

  return (
    <ReportSection id="T2" title="Aportes e Investimentos">
      {summary ? (
        <>
          <AporteKpis summary={summary} />
          <ReportCard
            variant="feature"
            title="Status dos Aportes do Ciclo"
            conclusion={conclusion}
          >
            <div
              data-chart="aportes_status_cards"
              className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3"
            >
              {summary.cards.map((card) => (
                <AporteCardItem
                  key={card.id}
                  label={card.label}
                  feito={card.feito}
                  valorMeta={card.valor_meta}
                  valorEfetivo={card.valor_efetivo}
                />
              ))}
            </div>
          </ReportCard>
        </>
      ) : (
        <ReportCard variant="feature" title="Aportes do Ciclo">
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            Nenhum aporte registrado no dashboard deste ciclo. Configure os
            destinos em <code>config/definitions.md</code> (estratégia de
            aportes mensais) para acompanhar o progresso aqui.
          </p>
        </ReportCard>
      )}
      <ReportCard variant="feature" title="Variação Patrimonial por Bloco">
        <InvestimentoDeltaTable rows={deltaRows} />
      </ReportCard>
      {/* v2.8 (ADR-148) — comparisons + changelog vs relatório anterior. */}
      <SectionSnapshotDiff sectionId="T2" data={data} />
    </ReportSection>
  );
}

// ═════════════════════════════════════════════════════════════════════
// T3 — Kanban (ADR-123)
// ═════════════════════════════════════════════════════════════════════

function payloadToUI(p: KanbanItemPayload): KanbanUIItem {
  return {
    id: p.id,
    titulo: p.titulo,
    coluna: p.coluna,
    prioridade: p.prioridade ?? undefined,
    prazoIso: p.prazo ?? undefined,
    categoria: p.categoria ?? undefined,
  };
}

export function T3TarefasSection({
  data,
  workspaceId,
  reportId,
}: {
  data: ReportAnalysisData;
  workspaceId: string;
  reportId: string;
}) {
  const [items, setItems] = useState<readonly KanbanUIItem[]>([]);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setStatus("loading");
    listKanbanItems(workspaceId, reportId)
      .then((res) => {
        if (cancelled) return;
        setItems(res.items.map(payloadToUI));
        setStatus("ready");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Falha ao carregar tarefas.");
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId, reportId]);

  const handleMove = useCallback(
    (itemId: string, to: KanbanColumn) => {
      const prev = items;
      setItems((curr) =>
        curr.map((it) => (it.id === itemId ? { ...it, coluna: to } : it)),
      );
      updateKanbanItem(workspaceId, reportId, itemId, { coluna: to }).catch(
        (err: unknown) => {
          setItems(prev);
          setError(
            err instanceof ApiError
              ? err.message
              : err instanceof Error
                ? err.message
                : "Falha ao mover tarefa.",
          );
        },
      );
    },
    [items, workspaceId, reportId],
  );

  const tarefasFromSnapshot = Array.isArray(data.tarefas) ? data.tarefas.length : 0;

  return (
    <ReportSection id="T3" title="Checklist de Tarefas">
      <ReportCard variant="feature" title="Kanban">
        {status === "loading" && (
          <p className="text-sm text-[var(--surface-muted-foreground)]">Carregando tarefas…</p>
        )}
        {status === "error" && (
          <p className="text-sm text-[var(--semantic-loss)]">
            {error ?? "Erro desconhecido."}
          </p>
        )}
        {status === "ready" && items.length === 0 && (
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            Nenhuma tarefa registrada no Kanban.
            {tarefasFromSnapshot > 0 && (
              <span>
                {" "}O relatório lista {tarefasFromSnapshot} tarefa(s) no snapshot; crie items no Kanban para acompanhar.
              </span>
            )}
          </p>
        )}
        {status === "ready" && items.length > 0 && (
          <Kanban items={items} onMove={handleMove} />
        )}
      </ReportCard>
      {/* v2.8 (ADR-148) — comparisons + changelog vs relatório anterior. */}
      <SectionSnapshotDiff sectionId="T3" data={data} />
    </ReportSection>
  );
}

// ═════════════════════════════════════════════════════════════════════
// T4 — Alertas (read-only)
// ═════════════════════════════════════════════════════════════════════

export function T4AlertasSection({ data }: { data: ReportAnalysisData }) {
  const alertas = (data.alertas ?? []) as string[];
  return (
    <ReportSection id="T4" title="Alertas e Pendências">
      <ReportCard variant={alertas.length > 0 ? "warn" : "feature"} title="Alertas">
        {alertas.length === 0 ? (
          <p className="text-sm text-[var(--surface-muted-foreground)]">Nenhum alerta pendente.</p>
        ) : (
          <ul className="space-y-2">
            {alertas.map((msg, i) => (
              <li
                key={i}
                className="flex items-start gap-2 rounded-md border border-[var(--surface-border)] bg-[var(--surface-muted)] p-3 text-sm"
              >
                <span className="mt-0.5 shrink-0 text-[var(--semantic-alert)]">⚠</span>
                <span>{typeof msg === "string" ? msg : JSON.stringify(msg)}</span>
              </li>
            ))}
          </ul>
        )}
      </ReportCard>
    </ReportSection>
  );
}

// ═════════════════════════════════════════════════════════════════════
// T5 — Timeline 15 dias
// ═════════════════════════════════════════════════════════════════════

export function T5ProximosPassosSection({ data }: { data: ReportAnalysisData }) {
  const items: readonly TimelineItem[] = adaptProximos15dToTimeline(data);
  return (
    <ReportSection id="T5" title="Próximos Passos">
      <ReportCard variant="feature" title="Timeline 15 dias">
        {items.length === 0 ? (
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            Nenhuma ação agendada nos próximos 15 dias.
          </p>
        ) : (
          <Timeline items={items} />
        )}
      </ReportCard>
      {/* v2.8 (ADR-148) — comparisons + changelog vs relatório anterior. */}
      <SectionSnapshotDiff sectionId="T5" data={data} />
    </ReportSection>
  );
}

// ═════════════════════════════════════════════════════════════════════
// T6 — Notas (ADR-123)
// ═════════════════════════════════════════════════════════════════════

export function T6NotasSection({
  workspaceId,
  reportId,
}: {
  workspaceId: string;
  reportId: string;
}) {
  const [content, setContent] = useState("");
  const [saveState, setSaveState] = useState<NotasSaveState>("idle");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getReportNotes(workspaceId, reportId)
      .then((res) => {
        if (cancelled) return;
        setContent(res?.content ?? "");
        setLoaded(true);
      })
      .catch(() => {
        if (cancelled) return;
        setLoaded(true);
        setSaveState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceId, reportId]);

  const handleChange = useCallback(
    (next: string) => {
      setContent(next);
      setSaveState("saving");
      putReportNotes(workspaceId, reportId, next)
        .then(() => setSaveState("saved"))
        .catch(() => setSaveState("error"));
    },
    [workspaceId, reportId],
  );

  if (!loaded) {
    return (
      <ReportSection id="T6" title="Notas e Observações">
        <ReportCard variant="neutral" title="Notas">
          <p className="text-sm text-[var(--surface-muted-foreground)]">Carregando notas…</p>
        </ReportCard>
      </ReportSection>
    );
  }

  return (
    <ReportSection id="T6" title="Notas e Observações">
      <NotasCard value={content} onChange={handleChange} saveState={saveState} />
    </ReportSection>
  );
}
