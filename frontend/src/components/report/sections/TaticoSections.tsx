"use client";

import { ReportSection } from "../ReportSection";
import { ReportCard } from "../ReportCard";
import type { ReportAnalysisData } from "@/lib/api";

/** F9 · F2.H — Seções T1–T6 do modo Tático (Dashboard Operacional).
 *
 * O modo tático consome dados mais granulares (despesas vs tetos por
 * categoria, aportes, checklist tarefas, alertas, timeline 15 dias).
 * Na versão atual, renderiza os dados que existem no E5 JSON +
 * placeholders para os que virão da integração tasks (F8.3).
 */

export function T1FluxoOperacionalSection({ data }: { data: ReportAnalysisData }) {
  const fluxo = data.fluxo_caixa as Record<string, unknown> | undefined;
  const categorias = (fluxo?.despesas_por_categoria ?? {}) as Record<string, number>;
  const entries = Object.entries(categorias).filter(([, v]) => v > 0).sort(([, a], [, b]) => b - a);

  return (
    <ReportSection id="T1" title="Fluxo Operacional — Despesas vs Tetos">
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

export function T2AportesSection({ data }: { data: ReportAnalysisData }) {
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

const PRIORIDADE_COLOR: Record<string, string> = {
  alta: "var(--semantic-loss)",
  media: "var(--semantic-alert)",
  baixa: "var(--semantic-gain)",
};

const PRIORIDADE_LABEL: Record<string, string> = {
  alta: "Alta",
  media: "Média",
  baixa: "Baixa",
};

export function T3TarefasSection({ data }: { data: ReportAnalysisData }) {
  type Tarefa = { n?: number; t?: string; p?: string; e?: string; categoria?: string; impacto?: string };
  const tarefas = (data.tarefas ?? []) as Tarefa[];
  const tarefasStatus = (data.tarefas_status ?? {}) as Record<string, string>;

  return (
    <ReportSection id="T3" title="Checklist de Tarefas">
      <ReportCard variant="feature" title="Tarefas">
        {tarefas.length === 0 ? (
          <p className="text-sm text-[var(--surface-muted-foreground)]">Nenhuma tarefa registrada.</p>
        ) : (
          <ul className="space-y-2">
            {tarefas.slice(0, 20).map((tarefa, i) => {
              const num = Number.isFinite(tarefa.n) ? tarefa.n : i + 1;
              const status = tarefasStatus[String(num)] ?? "pendente";
              const isDone = status === "feito";
              const prioridade = tarefa.p ?? "media";
              return (
                <li key={`tarefa-${i}`} className="flex items-start gap-3 text-sm">
                  {/* Status dot */}
                  <span
                    className="mt-1.5 inline-block h-2 w-2 shrink-0 rounded-full"
                    style={{ background: isDone ? "var(--semantic-gain)" : "var(--surface-muted-foreground)" }}
                  />
                  <span className="flex-1 leading-snug" style={{ textDecoration: isDone ? "line-through" : "none", opacity: isDone ? 0.6 : 1 }}>
                    {tarefa.t ?? "—"}
                  </span>
                  {/* Priority badge */}
                  <span
                    className="shrink-0 rounded px-1.5 py-0.5 font-mono text-xs font-semibold"
                    style={{ color: PRIORIDADE_COLOR[prioridade] ?? "inherit", background: "var(--surface-muted)" }}
                  >
                    {PRIORIDADE_LABEL[prioridade] ?? prioridade}
                  </span>
                  {/* Due date */}
                  {tarefa.e && tarefa.e !== "—" && (
                    <span className="shrink-0 font-mono text-xs text-[var(--surface-muted-foreground)]">
                      {tarefa.e}
                    </span>
                  )}
                </li>
              );
            })}
            {tarefas.length > 20 && (
              <li className="text-xs text-[var(--surface-muted-foreground)]">
                + {tarefas.length - 20} tarefas adicionais
              </li>
            )}
          </ul>
        )}
      </ReportCard>
    </ReportSection>
  );
}

export function T4AlertasSection({ data }: { data: ReportAnalysisData }) {
  // alertas is string[] in E5 JSON (generated by e5_analyze.py)
  const alertas = (data.alertas ?? []) as string[];
  return (
    <ReportSection id="T4" title="Alertas e Pendências">
      <ReportCard variant={alertas.length > 0 ? "warn" : "feature"} title="Alertas">
        {alertas.length === 0 ? (
          <p className="text-sm text-[var(--surface-muted-foreground)]">Nenhum alerta pendente.</p>
        ) : (
          <ul className="space-y-2">
            {alertas.map((msg, i) => (
              <li key={i} className="flex items-start gap-2 rounded-md border border-[var(--surface-border)] bg-[var(--surface-muted)] p-3 text-sm">
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

export function T5ProximosPassosSection() {
  return (
    <ReportSection id="T5" title="Próximos Passos">
      <ReportCard variant="feature" title="Timeline 15 dias">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Timeline operacional será alimentada pela integração de tarefas com datas de vencimento.
        </p>
      </ReportCard>
    </ReportSection>
  );
}

export function T6NotasSection() {
  return (
    <ReportSection id="T6" title="Notas e Observações">
      <ReportCard variant="neutral" title="Notas">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Área reservada para observações do consultor e da família.
        </p>
      </ReportCard>
    </ReportSection>
  );
}
