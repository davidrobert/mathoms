"use client";

// ADR-219 wave 3 — APP_B renderiza snapshot das premissas econômicas (tabela
// editorial com retorno real, sigma, fonte, vigente desde). Sigilo metodológico
// §13: termos como "AUVP" não aparecem em copy user-facing.

import { ReportCard } from "../ReportCard";
import type {
  PremissasEconomicasClassRow,
  PremissasEconomicasData,
} from "@/lib/api";

// Labels editoriais para os enum codes da lookup `economic_asset_class`.
// Fallback ao próprio code se a classe não tem label conhecido (classe nova
// adicionada por operador via console interno — UI degrada limpo).
const CLASSE_LABELS: Readonly<Record<string, string>> = {
  caixa: "Caixa / Liquidez",
  rf_pos: "Renda Fixa pós-fixada",
  rf_pre: "Renda Fixa prefixada",
  rf_inflacao: "Renda Fixa IPCA+",
  acoes_br: "Ações Brasil",
  acoes_intl: "Ações Internacional",
  fii: "FIIs",
  imoveis_diretos: "Imóveis físicos",
  cambio_usd: "Câmbio USD",
  cambio_eur: "Câmbio EUR",
};

function classeLabel(code: string): string {
  return CLASSE_LABELS[code] ?? code;
}

function formatPct(value: string | null): string {
  if (value === null) return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return value;
  return `${num.toFixed(2)}% a.a.`;
}

function safeFormatDate(iso: string | null): string {
  if (iso === null) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString("pt-BR");
}

export function PremissasEconomicasCard({
  premissas,
}: {
  premissas: PremissasEconomicasData | null;
}) {
  if (premissas == null) {
    return (
      <ReportCard variant="neutral" title="Premissas Econômicas" size="full">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Premissas econômicas não disponíveis para este ciclo. Refresh o
          relatório para incluir o baseline corrente (retorno real esperado +
          volatilidade por classe de ativo).
        </p>
      </ReportCard>
    );
  }
  // A37.l10 PD-04 — todas as classes sem premissa vigente: 1 empty-state em
  // vez de N linhas idênticas; o impacto já é sinalizado no banner de
  // qualidade de dados (computePremissasDegrade → status "indisponivel").
  const todasIndisponiveis =
    premissas.classes.length > 0 &&
    premissas.classes.every((c) => c.status === "indisponivel");
  return (
    <ReportCard variant="neutral" title="Premissas Econômicas" size="full">
      <PremissasHeader premissas={premissas} />
      {todasIndisponiveis ? (
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Nenhuma premissa econômica vigente neste ciclo. As projeções usam
          valores padrão, não calibrados à sua carteira. Premissas são
          revisadas trimestralmente — o próximo relatório incorpora os valores
          atualizados.
        </p>
      ) : (
        <PremissasTable classes={premissas.classes} />
      )}
    </ReportCard>
  );
}

function PremissasHeader({ premissas }: { premissas: PremissasEconomicasData }) {
  const snapshotLabel = safeFormatDate(premissas.snapshot_at);
  const statusCls =
    premissas.status === "completo"
      ? "bg-[color-mix(in_srgb,var(--semantic-gain)_15%,transparent)] text-[var(--semantic-gain)]"
      : "bg-[color-mix(in_srgb,var(--semantic-alert)_15%,transparent)] text-[var(--semantic-alert)]";
  return (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2 text-xs">
      <span className={`rounded px-2 py-0.5 font-semibold ${statusCls}`}>
        Status: {premissas.status === "completo" ? "Completo" : "Parcial"}
      </span>
      <span className="text-[var(--surface-muted-foreground)]">
        Snapshot em {snapshotLabel}
      </span>
    </div>
  );
}

function PremissasTable({
  classes,
}: {
  classes: readonly PremissasEconomicasClassRow[];
}) {
  if (classes.length === 0) {
    return (
      <p className="text-sm text-[var(--surface-muted-foreground)]">
        Nenhuma classe ativa para este ciclo.
      </p>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--surface-border)] text-left text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
            <th scope="col" className="pb-2 font-semibold">Classe de ativo</th>
            <th scope="col" className="pb-2 font-semibold">Retorno real esperado</th>
            <th scope="col" className="pb-2 font-semibold">Volatilidade anual</th>
            <th scope="col" className="pb-2 font-semibold">Fonte</th>
            <th scope="col" className="pb-2 font-semibold">Vigente desde</th>
          </tr>
        </thead>
        <tbody>
          {classes.map((c) => (
            <PremissaRow key={c.classe_auvp} row={c} />
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-xs text-[var(--surface-muted-foreground)]">
        Premissas revisadas trimestralmente. Valores ajustados para o seu
        plano aparecem com o selo &ldquo;Ajuste&rdquo;, com justificativa
        registrada.
      </p>
    </div>
  );
}

function PremissaRow({ row }: { row: PremissasEconomicasClassRow }) {
  if (row.status === "indisponivel") {
    return (
      <tr className="border-b border-[var(--surface-border)]/40 last:border-0">
        <td className="py-2 pr-4 font-semibold text-[var(--surface-foreground)]">
          {classeLabel(row.classe_auvp)}
        </td>
        <td
          colSpan={4}
          className="py-2 pr-4 text-sm text-[var(--semantic-alert)]"
          title={row.razao_indisponivel ?? undefined}
        >
          Premissa indisponível — projeção parcial nesta classe.
        </td>
      </tr>
    );
  }
  return (
    <tr className="border-b border-[var(--surface-border)]/40 last:border-0">
      <td className="py-2 pr-4 text-[var(--surface-foreground)]">
        <span className="font-semibold">{classeLabel(row.classe_auvp)}</span>
        {row.fonte_origem === "workspace_override" && (
          <span
            className="ml-2 rounded bg-[color-mix(in_srgb,var(--brand-info)_15%,transparent)] px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[var(--brand-info)]"
            title={row.justificativa ?? "Premissa ajustada para o seu plano"}
          >
            Ajuste
          </span>
        )}
      </td>
      <td className="py-2 pr-4 font-mono tabular-nums text-[var(--surface-foreground)]">
        {formatPct(row.retorno_real_esperado_pct_anual)}
      </td>
      <td className="py-2 pr-4 font-mono tabular-nums text-[var(--surface-foreground)]">
        {formatPct(row.sigma_anual_pct)}
      </td>
      <td className="py-2 pr-4 text-xs text-[var(--surface-muted-foreground)]">
        {row.fonte ?? "—"}
      </td>
      <td className="py-2 pr-4 text-xs text-[var(--surface-muted-foreground)]">
        {safeFormatDate(row.effective_from)}
      </td>
    </tr>
  );
}
