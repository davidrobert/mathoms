"use client";

import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import { cn } from "@/lib/cn";

export interface TopAtivo {
  posicao: number;
  nome: string;
  classe: string;
  membro: string;
  instituicao: string;
  valor: number;
  pct_carteira: number;
  tipo_origem: "investimento" | "imovel";
}

export interface Top15AtivosData {
  top_ativos?: TopAtivo[];
}

interface Top15AtivosCardProps {
  data: Top15AtivosData | undefined;
}

const CLASSE_TOKEN: Record<string, string> = {
  // Taxonomia canônica de 10 buckets (ADR-193).
  Cripto: "var(--semantic-warning)",
  Previdência: "var(--brand-secondary)",
  FIIs: "var(--brand-secondary)",
  Internacional: "var(--brand-info)",
  "Ações BR": "var(--brand-primary)",
  "Renda Fixa": "var(--brand-info)",
  Fundos: "var(--brand-primary)",
  Caixa: "var(--surface-muted-foreground)",
  "Imóveis Investimento": "var(--brand-secondary)",
  Outros: "var(--surface-muted-foreground)",
};

function classeColor(classe: string): string {
  return CLASSE_TOKEN[classe] ?? "var(--surface-muted-foreground)";
}

function ClasseBadge({ classe }: { classe: string }) {
  const color = classeColor(classe);
  return (
    <span
      aria-label={`Classe: ${classe}`}
      className="inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium"
      style={{
        color,
        backgroundColor: `color-mix(in srgb, ${color} 12%, transparent)`,
      }}
    >
      {classe}
    </span>
  );
}

function PctCarteiraCell({
  pct,
  color,
  alpha,
}: {
  pct: number;
  color: string;
  alpha: string;
}) {
  const clamped = Math.min(Math.max(pct, 0), 100);
  return (
    <div className="flex items-center justify-end gap-3">
      <div
        className="relative h-1.5 w-[110px] overflow-hidden rounded-full bg-[var(--surface-border)]/40"
        aria-hidden="true"
      >
        <div
          className="absolute inset-y-0 left-0 rounded-full"
          style={{
            width: `${clamped}%`,
            backgroundColor: `color-mix(in srgb, ${color} ${alpha}, transparent)`,
          }}
        />
      </div>
      <span className="w-12 text-right font-mono text-xs tabular-nums">
        {pct.toFixed(1)}%
      </span>
    </div>
  );
}

function deriveInsight(rows: TopAtivo[]): string | undefined {
  if (rows.length === 0) return undefined;
  const top1 = rows[0];
  const pct1 = top1.pct_carteira;
  const top3Pct = rows
    .slice(0, 3)
    .reduce((acc, r) => acc + r.pct_carteira, 0);
  const fmtPct = (n: number) => `${n.toFixed(1)}%`;
  const fmtBrl = new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  });
  const valorTop1 = fmtBrl.format(top1.valor);
  if (pct1 > 25) {
    return `Atenção: ${top1.nome} concentra ${fmtPct(pct1)} da carteira (${valorTop1}). Considere diversificação — top 3 somam ${fmtPct(top3Pct)}.`;
  }
  return `${top1.nome} é o maior ativo individual (${fmtPct(pct1)} = ${valorTop1}). Top 3 somam ${fmtPct(top3Pct)} da carteira.`;
}

const CARD_TITLE = "Top 15 Ativos da Carteira";
const CARD_SUBTITLE =
  "Investimentos financeiros e imóveis de renda, ranqueados por valor. " +
  "Não inclui residência principal nem bens de uso pessoal — esses aparecem " +
  "em Composição Patrimonial.";

function CardSubtitle() {
  return (
    <p className="-mt-2 mb-4 text-xs leading-snug text-[var(--surface-muted-foreground)]">
      {CARD_SUBTITLE}
    </p>
  );
}

export function Top15AtivosCard({ data }: Top15AtivosCardProps) {
  const rows = data?.top_ativos ?? [];

  if (rows.length === 0) {
    return (
      <ReportCard variant="neutral" title={CARD_TITLE}>
        <CardSubtitle />
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Sem ativos de carteira neste período. Investimentos e imóveis de
          renda aparecem aqui após o processamento das posições e do IRPF.
        </p>
      </ReportCard>
    );
  }

  const insight = deriveInsight(rows);

  return (
    <ReportCard variant="feature" title={CARD_TITLE} conclusion={insight}>
      <CardSubtitle />
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--surface-border)] text-left">
              <th
                scope="col"
                className="w-8 pb-2 pr-2 font-display text-xs font-semibold text-[var(--surface-muted-foreground)]"
              >
                #
              </th>
              <th scope="col" className="pb-2 pr-4 font-display font-semibold">
                Ativo
              </th>
              <th scope="col" className="pb-2 pr-4 font-display font-semibold">
                Classe
              </th>
              <th
                scope="col"
                className="hidden whitespace-nowrap pb-2 pr-4 font-display font-semibold md:table-cell"
              >
                Membro
              </th>
              <th
                scope="col"
                className="pb-2 pr-4 text-right font-display font-semibold"
              >
                Valor
              </th>
              <th
                scope="col"
                className="w-[180px] pb-2 text-right font-display font-semibold"
              >
                %
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const isTop3 = r.posicao <= 3;
              const barColor = classeColor(r.classe);
              const alpha = isTop3 ? "100%" : "55%";
              return (
                <tr
                  key={`top-${r.posicao}`}
                  className="border-b border-[var(--surface-border)]/40 last:border-0"
                >
                  <td className="py-2 pr-2 font-mono text-xs tabular-nums text-[var(--surface-muted-foreground)]">
                    {r.posicao}
                  </td>
                  <td className="py-2 pr-4">
                    <div
                      className={cn(
                        "leading-tight",
                        isTop3 && "font-semibold",
                      )}
                    >
                      {r.nome}
                    </div>
                    {r.instituicao && (
                      <div className="text-xs text-[var(--surface-muted-foreground)]">
                        {r.instituicao}
                      </div>
                    )}
                  </td>
                  <td className="py-2 pr-4">
                    <ClasseBadge classe={r.classe} />
                  </td>
                  <td className="hidden whitespace-nowrap py-2 pr-4 text-[var(--surface-muted-foreground)] md:table-cell">
                    {r.membro || "—"}
                  </td>
                  <td className="py-2 pr-4 text-right">
                    <MonetaryValue value={r.valor} />
                  </td>
                  <td className="py-2">
                    <PctCarteiraCell
                      pct={r.pct_carteira}
                      color={barColor}
                      alpha={alpha}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </ReportCard>
  );
}
