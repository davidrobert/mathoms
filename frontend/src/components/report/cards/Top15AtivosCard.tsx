"use client";

import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import { cn } from "@/lib/cn";
import { formatPercent } from "@/lib/format";
import type { Classification } from "@/lib/api/properties";
import type { MotivoBaldeImovel, VereditoBaldeImovel } from "@/types/patrimonio-imovel";

export interface TopAtivo {
  posicao: number;
  nome: string;
  classe: string;
  membro: string;
  instituicao: string;
  valor: number;
  /** `null` = sem peso: imóvel com uso não apurado fica fora da base (ADR-444 D4). */
  pct_carteira: number | null;
  tipo_origem: "investimento" | "imovel";
  /** Uso do imóvel (ADR-444 D4); ausente em investimento. */
  classificacao_imovel?: Exclude<Classification, "residencia_principal"> | null;
}

export interface Top15AtivosData {
  top_ativos?: TopAtivo[];
}

interface Top15AtivosCardProps {
  data: Top15AtivosData | undefined;
  /** Veredito publicado da residência (`patrimonio.cobertura_classificacao_imovel`). */
  residencia?: VereditoBaldeImovel;
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
  "Imóveis com uso não apurado": "var(--surface-muted-foreground)",
};

function classeColor(classe: string): string {
  return CLASSE_TOKEN[classe] ?? "var(--surface-muted-foreground)";
}

// ADR-444: o rótulo da linha sem peso é o único longo o bastante para estourar a caixa
// A4 do PDF; só ele quebra linha — as classes curtas seguem `nowrap` e o print delas
// não se move.
const CLASSE_LONGA = "Imóveis com uso não apurado";

function ClasseBadge({ classe }: { classe: string }) {
  const color = classeColor(classe);
  return (
    <span
      aria-label={`Classe: ${classe}`}
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
        classe === CLASSE_LONGA ? "whitespace-normal" : "whitespace-nowrap",
      )}
      style={{
        color,
        backgroundColor: `color-mix(in srgb, ${color} 12%, transparent)`,
      }}
    >
      {classe}
    </span>
  );
}

function SemPesoCell() {
  return (
    <div className="flex items-center justify-end gap-3">
      <span className="w-12 text-right font-mono text-xs tabular-nums">
        <span aria-hidden="true">—</span>
        <span className="sr-only">sem % da carteira</span>
      </span>
    </div>
  );
}

function PctCarteiraCell({
  pct,
  color,
  alpha,
}: {
  pct: number | null;
  color: string;
  alpha: string;
}) {
  if (pct === null) return <SemPesoCell />;
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
        {formatPercent(pct)}
      </span>
    </div>
  );
}

const LIMIAR_CONCENTRACAO_PCT = 25;

// ADR-444 D5: o CTA segue o motivo do veredito. Em `nao_localizada` o override já existe —
// pedir "marque" mandaria a família refazer o que fez.
const CTA_DA_RESIDENCIA: Partial<Record<MotivoBaldeImovel, string>> = {
  nao_localizada:
    "Não localizamos nesta declaração o imóvel marcado como residência; não é preciso marcá-lo de novo.",
  sem_valor:
    "A residência marcada está sem valor apurado em 31/12. Se a família mudou de casa, marque a nova em Configurações → Membros.",
  nao_classificada: "Marque qual imóvel é a residência em Configurações → Membros.",
  nao_declarada:
    "Indique em Configurações → Membros se a família mora em imóvel próprio.",
};

type AtivoComPeso = TopAtivo & { pct_carteira: number };

const fmtBrl = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});

function comPeso(rows: TopAtivo[]): AtivoComPeso[] {
  return rows.filter((r): r is AtivoComPeso => r.pct_carteira !== null);
}

function somaTop3(rows: AtivoComPeso[]): number {
  return rows.slice(0, 3).reduce((acc, r) => acc + r.pct_carteira, 0);
}

// O alarme de concentração passa ao maior item COM peso: item sem % não concentra carteira.
function fraseDoMaiorComPeso(rows: TopAtivo[]): string | undefined {
  const pesados = comPeso(rows);
  if (pesados.length === 0) return undefined;
  const maior = pesados[0];
  const pct = formatPercent(maior.pct_carteira);
  const top3 = formatPercent(somaTop3(pesados));
  if (maior.pct_carteira > LIMIAR_CONCENTRACAO_PCT) {
    return `Atenção: ${maior.nome} (#${maior.posicao}) concentra ${pct} da carteira (${fmtBrl.format(maior.valor)}). Considere diversificação — os 3 maiores com % somam ${top3}.`;
  }
  return `${maior.nome} (#${maior.posicao}) é o maior ativo com % (${pct} = ${fmtBrl.format(maior.valor)}). Os 3 maiores com % somam ${top3} da carteira.`;
}

function insightSemPeso(rows: TopAtivo[], residencia?: VereditoBaldeImovel): string {
  const abertura = `O maior item é um imóvel com uso não apurado (${fmtBrl.format(rows[0].valor)}), sem % da carteira.`;
  const cta = residencia?.motivo ? CTA_DA_RESIDENCIA[residencia.motivo] : undefined;
  return [abertura, cta, fraseDoMaiorComPeso(rows)].filter(Boolean).join(" ");
}

// `piso` (ADR-439 D2): a residência está identificada, mas a cota do cônjuge sem id pode
// estar no desconhecido — diversificar a casa não é conselho (ADR-444 D5/D6).
function podeSerParteDaResidencia(top1: AtivoComPeso, residencia?: VereditoBaldeImovel): boolean {
  return (
    top1.classificacao_imovel === "desconhecido" &&
    residencia?.piso === true &&
    top1.pct_carteira > LIMIAR_CONCENTRACAO_PCT
  );
}

function deriveInsight(
  rows: TopAtivo[],
  residencia?: VereditoBaldeImovel,
): string | undefined {
  if (rows.length === 0) return undefined;
  const top1 = rows[0];
  if (top1.pct_carteira === null) return insightSemPeso(rows, residencia);
  const top1ComPeso = top1 as AtivoComPeso;
  const pct1 = formatPercent(top1ComPeso.pct_carteira);
  const top3 = formatPercent(somaTop3(comPeso(rows)));
  const valorTop1 = fmtBrl.format(top1.valor);
  if (podeSerParteDaResidencia(top1ComPeso, residencia)) {
    return `${top1.nome} concentra ${pct1} da carteira (${valorTop1}) e pode ser parte da residência. Confira a classificação em Configurações → Membros antes de diversificar. Top 3 somam ${top3}.`;
  }
  if (top1ComPeso.pct_carteira > LIMIAR_CONCENTRACAO_PCT) {
    return `Atenção: ${top1.nome} concentra ${pct1} da carteira (${valorTop1}). Considere diversificação — top 3 somam ${top3}.`;
  }
  return `${top1.nome} é o maior ativo individual (${pct1} = ${valorTop1}). Top 3 somam ${top3} da carteira.`;
}

const CARD_TITLE = "Top 15 Ativos da Carteira";
const CARD_SUBTITLE =
  "Investimentos financeiros e imóveis, ranqueados por valor. " +
  "Não inclui residência principal nem bens de uso pessoal — esses aparecem " +
  "em Composição Patrimonial.";
// ADR-444 D3: com item sem peso, a promessa de excluir a residência deixa de ser verdade.
const CARD_SUBTITLE_SEM_PESO =
  "Investimentos financeiros e imóveis, ranqueados por valor. " +
  "Imóveis com uso não apurado aparecem com valor e sem %: podem incluir a " +
  "residência principal, que fica fora da carteira. Veículos aparecem em " +
  "Composição Patrimonial.";

function CardSubtitle({ semPeso = false }: { semPeso?: boolean }) {
  return (
    <p className="-mt-2 mb-4 text-xs leading-snug text-[var(--surface-muted-foreground)]">
      {semPeso ? CARD_SUBTITLE_SEM_PESO : CARD_SUBTITLE}
    </p>
  );
}

export function Top15AtivosCard({ data, residencia }: Top15AtivosCardProps) {
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

  const insight = deriveInsight(rows, residencia);
  const temItemSemPeso = rows.some((r) => r.pct_carteira === null);

  return (
    <ReportCard variant="feature" title={CARD_TITLE} conclusion={insight}>
      <CardSubtitle semPeso={temItemSemPeso} />
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
              {/* Titular some do PDF com `md:` sozinho (caixa A4 = 703px).
                  `print:table-cell` devolve a coluna no papel; `sm:table-cell`
                  esmagaria Ativo no ecrã 640–767 (barra de % já come 180px).
                  ADR-381 D2: o que o papel faz de diferente da tela é print. */}
              <th
                scope="col"
                className="hidden whitespace-nowrap pb-2 pr-4 font-display font-semibold print:table-cell md:table-cell"
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
                  <td className="hidden whitespace-nowrap py-2 pr-4 text-[var(--surface-muted-foreground)] print:table-cell md:table-cell">
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
