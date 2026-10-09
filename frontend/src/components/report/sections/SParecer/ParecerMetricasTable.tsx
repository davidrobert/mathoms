"use client";

// ADR-199 Ato 5 §5b — Métricas observáveis. A40.l92: a coluna "Situação" desenha o
// veredito que o backend publica (`comparador` / `nivel_confianca`); nada aqui re-deriva
// número de string renderizada — era a regex que comia o glifo e fazia a barra de um
// teto encher conforme a métrica piorava.

import type { Metrica } from "@/lib/api";
import { severityIcon } from "@/components/report/cards/alocacaoCardParts";
import { situacaoDaMetrica } from "@/lib/parecerSituacaoCopy";

interface ParecerMetricasTableProps {
  metricas: Metrica[];
  /** Teaser tier free — sinaliza count gated. */
  gatedCount?: number;
}

export function ParecerMetricasTable({
  metricas,
  gatedCount = 0,
}: ParecerMetricasTableProps) {
  if (metricas.length === 0 && gatedCount === 0) return null;

  return (
    <section
      className="md:col-span-2"
      aria-labelledby="parecer-metricas-title"
      data-testid="parecer-metricas-table"
    >
      <header className="mb-2 flex items-baseline justify-between gap-2">
        <h3
          id="parecer-metricas-title"
          className="font-heading text-lg font-semibold text-[var(--surface-foreground)]"
        >
          Métricas a observar
        </h3>
        {gatedCount > 0 && (
          <span className="text-xs text-[var(--surface-muted-foreground)]">
            +{gatedCount} no Premium
          </span>
        )}
      </header>

      {metricas.length === 0 ? (
        <p className="rounded-md border border-dashed border-[var(--surface-border)] p-4 text-center text-sm text-[var(--surface-muted-foreground)]">
          Destrave Premium para acompanhar métricas observáveis.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="whitespace-nowrap text-left text-xs uppercase text-[var(--surface-muted-foreground)]">
                <th scope="col" className="py-2 pr-4">Métrica</th>
                <th scope="col" className="py-2 pr-4">Valor atual</th>
                <th scope="col" className="py-2 pr-4">Alvo</th>
                <th scope="col" className="py-2 pr-4">Situação</th>
                <th scope="col" className="py-2 pr-4">Revisão</th>
                <th scope="col" className="py-2 pr-4">§</th>
              </tr>
            </thead>
            <tbody>
              {metricas.map((m, idx) => (
                <MetricaRow key={`${m.nome}-${idx}`} metrica={m} />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function MetricaRow({ metrica }: { metrica: Metrica }) {
  return (
    <tr
      className="border-t border-[var(--surface-border)]"
      data-alvo={metrica.target ? "presente" : "ausente"}
    >
      <td className="py-2 pr-4 font-medium">{metrica.nome}</td>
      <td className="py-2 pr-4 font-mono text-xs">{metrica.valor_atual ?? "—"}</td>
      <td className="py-2 pr-4 min-w-[9rem] text-xs">
        {metrica.target ? (
          <span className="font-mono">{metrica.target}</span>
        ) : (
          <>
            <span className="font-medium text-[var(--surface-muted-foreground)]">
              Não afirmamos um alvo
            </span>
            {metrica.target_motivo && (
              <span className="mt-0.5 block text-[11px] text-[var(--surface-muted-foreground)]">
                {metrica.target_motivo}
              </span>
            )}
          </>
        )}
      </td>
      <td className="py-2 pr-4">
        <SituacaoCell metrica={metrica} />
      </td>
      <td className="whitespace-nowrap py-2 pr-4 text-xs capitalize">{metrica.frequencia_revisao}</td>
      <td className="whitespace-nowrap py-2 pr-4 text-xs text-[var(--surface-muted-foreground)]">
        §{metrica.section_id}
      </td>
    </tr>
  );
}

// Ícone + texto em toda linha com veredito: só a barra de piso faria do status uma segunda
// gramática na mesma coluna. A exceção salta (foreground, medium) e a conformidade recua.
function SituacaoCell({ metrica }: { metrica: Metrica }) {
  const situacao = situacaoDaMetrica(metrica);
  if (!situacao) {
    return (
      <>
        <span aria-hidden="true" className="text-[10px] text-[var(--surface-muted-foreground)]">
          —
        </span>
        <span className="sr-only">Sem comparação publicada</span>
      </>
    );
  }
  const atencao = situacao.tom === "atencao";
  const tom = atencao
    ? "font-medium text-[var(--surface-foreground)]"
    : "text-[var(--surface-muted-foreground)]";
  return (
    <div className="flex flex-col gap-1" data-situacao={situacao.tom}>
      <span className={`flex items-center gap-1 whitespace-nowrap text-xs ${tom}`}>
        {severityIcon(atencao ? "atencao" : "alinhado")}
        {situacao.texto}
      </span>
      {situacao.progressoPct !== null && (
        <progress
          value={situacao.progressoPct}
          max={100}
          aria-valuetext={`${metrica.valor_atual} de ${metrica.target}`}
          className="parecer-progress h-1.5 w-24 appearance-none overflow-hidden rounded-full bg-[var(--surface-muted)] [&::-moz-progress-bar]:bg-[var(--brand-primary)] [&::-webkit-progress-bar]:bg-[var(--surface-muted)] [&::-webkit-progress-value]:bg-[var(--brand-primary)]"
        />
      )}
    </div>
  );
}
