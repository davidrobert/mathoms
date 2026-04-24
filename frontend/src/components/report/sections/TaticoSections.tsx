"use client";

import { useCallback, useEffect, useState } from "react";
import { ReportSection } from "../ReportSection";
import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import { Kanban, NotasCard, Timeline } from "../ui";
import type {
  KanbanItem as KanbanUIItem,
  KanbanColumn,
  NotasSaveState,
  TimelineItem,
} from "../ui";
import { adaptProximos15dToTimeline } from "../utils/timelineAdapter";
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

export function T2AportesSection({ data: _data }: { data: ReportAnalysisData }) {
  return (
    <ReportSection id="T2" title="Aportes e Investimentos">
      <ReportCard variant="feature" title="Aportes e Variação Patrimonial">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Dados de aportes detalhados estarão disponíveis com a integração do dashboard operacional.
        </p>
      </ReportCard>
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
