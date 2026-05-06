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
  "Renda Fixa": "var(--brand-info)",
  "Ações": "var(--brand-primary)",
  Cripto: "var(--semantic-warning)",
  "Contas Bancárias": "var(--surface-muted-foreground)",
  "Imóveis Investimento": "var(--brand-secondary)",
  Outros: "var(--surface-muted-foreground)",
};

function classeColor(classe: string): string {
  return CLASSE_TOKEN[classe] ?? "var(--surface-muted-foreground)";
}

function firstName(membro: string): string {
  if (!membro) return "—";
  const trimmed = membro.trim();
  return trimmed.charAt(0).toUpperCase() + trimmed.slice(1).toLowerCase();
}

function ClasseBadge({ classe }: { classe: string }) {
  const color = classeColor(classe);
  return (
    <span
      aria-label={`Classe: ${classe}`}
      className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium"
      style={{
        color,
        backgroundColor: `color-mix(in srgb, ${color} 12%, transparent)`,
      }}
    >
      {classe}
    </span>
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

export function Top15AtivosCard({ data }: Top15AtivosCardProps) {
  const rows = data?.top_ativos ?? [];

  if (rows.length === 0) {
    return (
      <ReportCard variant="neutral" title="Top 15 Ativos Financeiros">
        <p className="text-sm text-[var(--surface-muted-foreground)]">
          Sem ativos individualizados neste período. Conecte instituições em /plano para detalhar a carteira.
        </p>
      </ReportCard>
    );
  }

  const insight = deriveInsight(rows);

  return (
    <ReportCard
      variant="feature"
      title="Top 15 Ativos Financeiros"
      conclusion={insight}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--surface-border)] text-left">
              <th
                scope="col"
                className="w-8 pb-2 font-display text-xs font-semibold text-[var(--surface-muted-foreground)]"
              >
                #
              </th>
              <th scope="col" className="pb-2 font-display font-semibold">
                Ativo
              </th>
              <th scope="col" className="pb-2 font-display font-semibold">
                Classe
              </th>
              <th
                scope="col"
                className="hidden pb-2 font-display font-semibold md:table-cell"
              >
                Membro
              </th>
              <th
                scope="col"
                className="pb-2 text-right font-display font-semibold"
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
                  <td className="py-2 font-mono text-xs tabular-nums text-[var(--surface-muted-foreground)]">
                    {r.posicao}
                  </td>
                  <td className="py-2">
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
                  <td className="py-2">
                    <ClasseBadge classe={r.classe} />
                  </td>
                  <td className="hidden py-2 text-[var(--surface-muted-foreground)] md:table-cell">
                    {firstName(r.membro)}
                  </td>
                  <td className="py-2 text-right">
                    <MonetaryValue value={r.valor} />
                  </td>
                  <td className="py-2">
                    <div className="relative h-5 w-full" aria-hidden="true">
                      <div
                        className="absolute inset-y-0 right-0 rounded-sm"
                        style={{
                          width: `${Math.max(r.pct_carteira, 0)}%`,
                          backgroundColor: `color-mix(in srgb, ${barColor} ${alpha}, transparent)`,
                        }}
                      />
                      <span className="relative z-10 flex h-full items-center justify-end pr-1 font-mono text-xs tabular-nums">
                        {r.pct_carteira.toFixed(1)}%
                      </span>
                    </div>
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
