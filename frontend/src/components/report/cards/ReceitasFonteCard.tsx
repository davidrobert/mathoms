"use client";

import { useState } from "react";
import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import { PeriodToggle } from "../PeriodToggle";
import { formatPercent } from "@/lib/format";
import { formatInteractiveWindowBasis } from "../utils/interactiveWindowLabel";
import { ReceitasNaturezaStrip } from "./ReceitasNaturezaStrip";
import type {
  FluxoCaixaSummary,
  FluxoJanelaInterativa,
  FluxoPeriodoInterativo,
  FluxoReceitaMensalRow,
} from "@/types/report-analysis";

const FONTE_LABELS: Record<string, string> = {
  receita_clt: "CLT",
  receita_pj: "PJ",
  receita_aluguel: "Aluguéis",
  receita_investimento: "Rendimentos de Investimento",
  receita_resgate: "Resgates de Aplicações",
  receita_venda_ativo: "Venda de Ativo",
  receita_fgts: "FGTS",
  receita_restituicao: "Restituições",
  outras_receitas: "Outras receitas",
  pro_labore: "Pró-labore",
  lucros_distribuidos: "Lucros distribuídos",
};

function HistoricalReceitasCard() {
  return (
    <ReportCard variant="feature" title="Composição das Receitas">
      <p className="text-sm text-[var(--surface-muted-foreground)]">
        Detalhamento por janela indisponível neste relatório histórico. Gere um
        novo relatório para consultar médias mensais comparáveis.
      </p>
    </ReportCard>
  );
}

function ReceitaWindowSummary({
  janela,
}: {
  readonly janela: FluxoJanelaInterativa;
}) {
  return (
    <div aria-live="polite" data-window-summary>
      <p className="text-sm text-[var(--surface-muted-foreground)]">
        Média mensal observada de entradas
      </p>
      <p className="mt-1 flex items-baseline gap-1">
        <MonetaryValue
          value={janela.receita_mensal_media}
          size="kpi"
          data-testid="receita-window-kpi"
        />
        <span className="text-xs text-[var(--surface-muted-foreground)]">
          /mês
        </span>
      </p>
      <p
        data-window-basis
        className="mt-1 text-xs text-[var(--surface-muted-foreground)]"
      >
        {formatInteractiveWindowBasis(janela)}
      </p>
    </div>
  );
}

function ReceitasTableHead() {
  return (
    <thead>
      <tr className="border-b border-[var(--surface-border)] text-left">
        <th scope="col" className="pb-2 font-display font-semibold">
          Fonte
        </th>
        <th scope="col" className="pb-2 text-right font-display font-semibold">
          Média mensal
        </th>
        <th scope="col" className="pb-2 text-right font-display font-semibold">
          Participação
        </th>
      </tr>
    </thead>
  );
}

function ReceitaRow({ row }: { readonly row: FluxoReceitaMensalRow }) {
  return (
    <tr className="border-b border-[var(--surface-border)]/40 last:border-0">
      <td className="py-2">{FONTE_LABELS[row.fonte] ?? row.fonte}</td>
      <td className="py-2 text-right">
        <MonetaryValue value={row.mensal_media} />
      </td>
      <td className="py-2 text-right font-mono tabular-nums text-[var(--surface-muted-foreground)]">
        {formatPercent(row.participacao_pct, 2)}
      </td>
    </tr>
  );
}

function ReceitasTable({ janela }: { readonly janela: FluxoJanelaInterativa }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <ReceitasTableHead />
        <tbody>
          {janela.tabela_receitas_por_fonte_mensal.map((row) => (
            <ReceitaRow key={row.fonte} row={row} />
          ))}
          <tr className="font-semibold">
            <td className="pt-3">Total mensal observado</td>
            <td className="pt-3 text-right">
              <MonetaryValue value={janela.receita_mensal_media} />
            </td>
            <td className="pt-3 text-right font-mono tabular-nums">
              {formatPercent(100, 2)}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function ReceitasDisclaimer() {
  return (
    <div className="space-y-1 text-xs text-[var(--surface-muted-foreground)]">
      <p>
        Inclui entradas recorrentes e pontuais; não representa renda
        sustentável.
      </p>
      <p>
        PJ agrupa pró-labore e lucros. Outras reúne o que não é trabalho nem
        aluguel.
      </p>
    </div>
  );
}

function ReceitasWindowContent({
  janela,
}: {
  readonly janela: FluxoJanelaInterativa;
}) {
  if (janela.janela_meses === 0) {
    return (
      <p className="text-sm text-[var(--surface-muted-foreground)]">
        Não há meses documentados com movimento nesta janela.
      </p>
    );
  }
  const hasFonte = janela.tabela_receitas_por_fonte_mensal.length !== 0;
  const hasNatureza = janela.tabela_receita_por_natureza_mensal.length !== 0;
  return (
    <div className="space-y-4">
      <ReceitaWindowSummary janela={janela} />
      <ReceitasNaturezaStrip rows={janela.tabela_receita_por_natureza_mensal} />
      {hasFonte ? <ReceitasTable janela={janela} /> : null}
      {hasFonte || hasNatureza ? (
        <ReceitasDisclaimer />
      ) : (
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Sem entradas registradas nesta janela.
        </p>
      )}
    </div>
  );
}

/** A40.l44 PR5+PR6 — seleção pura do agregado table-ready emitido pelo E5. */
export function ReceitasFonteCard({
  fluxo,
}: {
  readonly fluxo: FluxoCaixaSummary | undefined;
}) {
  const [period, setPeriod] = useState<FluxoPeriodoInterativo>("12m");
  if (!fluxo?.janelas) return <HistoricalReceitasCard />;

  const janela = fluxo.janelas[period] as FluxoJanelaInterativa | undefined;
  return (
    <ReportCard
      variant="feature"
      title="Composição das Receitas"
      headerRight={
        <PeriodToggle
          value={period}
          onChange={setPeriod}
          ariaLabel="Janela da composição das receitas"
        />
      }
    >
      {janela ? (
        <ReceitasWindowContent janela={janela} />
      ) : (
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Dados desta janela indisponíveis. Escolha outro período.
        </p>
      )}
    </ReportCard>
  );
}
