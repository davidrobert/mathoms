import { CheckCircle2, AlertTriangle, XCircle, MinusCircle } from "lucide-react";
import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import {
  aggregateAlocacao,
  type AlocacaoAlvoV1,
  type AlocacaoSummary,
  type BadgeSeverity,
  type BucketRow,
  type ClasseAtivoRow,
  type SeverityLevel,
} from "../utils/alocacaoBucketMapper";

export interface AlocacaoAtualVsAlvoCardProps {
  investimentos:
    | {
        tabela_classes?: ClasseAtivoRow[];
        total?: number;
      }
    | undefined;
  alocacaoAlvo: AlocacaoAlvoV1 | undefined;
  /** Texto editorial vindo de E5N (`narrativas.charts.alocacao_atual.conclusion`)
   *  usado como override do footer determinístico. Cap em 200 chars no template. */
  llmFooter?: string | null;
}

const PCT = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const PP = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
  signDisplay: "always",
});

const SEVERITY_BAR_COLOR: Record<SeverityLevel, string> = {
  alinhado: "var(--brand-primary)",
  atencao: "var(--semantic-warning)",
  rebalancear: "var(--semantic-danger)",
  neutro: "var(--surface-muted-foreground)",
};

const SEVERITY_TEXT_CLASS: Record<SeverityLevel, string> = {
  alinhado: "text-[var(--surface-foreground)]",
  atencao: "text-[var(--semantic-warning)]",
  rebalancear: "text-[var(--semantic-danger)]",
  neutro: "text-[var(--surface-muted-foreground)]",
};

const BADGE_COLOR: Record<BadgeSeverity, { bg: string; fg: string }> = {
  alinhado: {
    bg: "color-mix(in srgb, var(--semantic-success) 12%, var(--surface-card))",
    fg: "var(--semantic-success)",
  },
  atencao: {
    bg: "color-mix(in srgb, var(--semantic-warning) 14%, var(--surface-card))",
    fg: "var(--semantic-warning)",
  },
  rebalancear: {
    bg: "color-mix(in srgb, var(--semantic-danger) 14%, var(--surface-card))",
    fg: "var(--semantic-danger)",
  },
  sem_alvo: {
    bg: "var(--surface-muted)",
    fg: "var(--surface-muted-foreground)",
  },
};

function severityIcon(level: SeverityLevel): JSX.Element {
  if (level === "alinhado") {
    return <CheckCircle2 aria-hidden className="size-4 text-[var(--semantic-success)]" />;
  }
  if (level === "atencao") {
    return <AlertTriangle aria-hidden className="size-4 text-[var(--semantic-warning)]" />;
  }
  if (level === "rebalancear") {
    return <XCircle aria-hidden className="size-4 text-[var(--semantic-danger)]" />;
  }
  return (
    <MinusCircle aria-hidden className="size-4 text-[var(--surface-muted-foreground)]" />
  );
}

function ariaLabelFor(row: BucketRow): string {
  const atual = `${PCT.format(row.atual_pct)} por cento atual`;
  if (row.alvo_pct === null || row.desvio_pp === null) {
    return `${row.label}: ${atual}, sem alvo definido`;
  }
  const alvo = `${PCT.format(row.alvo_pct)} por cento alvo`;
  const desvio = `desvio de ${PP.format(row.desvio_pp)} pontos percentuais`;
  return `${row.label}: ${atual} vs ${alvo}, ${desvio}`;
}

interface BulletProps {
  row: BucketRow;
}

function BulletBar({ row }: BulletProps): JSX.Element {
  const atualClamped = Math.max(0, Math.min(100, row.atual_pct));
  const alvoClamped =
    row.alvo_pct === null ? null : Math.max(0, Math.min(100, row.alvo_pct));
  return (
    <div
      className="relative h-2.5 w-full overflow-hidden rounded-[var(--radius-sm)] bg-[var(--surface-muted)]"
      role="presentation"
    >
      <div
        className="absolute inset-y-0 left-0 rounded-[var(--radius-sm)]"
        style={{
          width: `${atualClamped}%`,
          backgroundColor: SEVERITY_BAR_COLOR[row.severity],
        }}
      />
      {alvoClamped !== null && (
        <div
          className="absolute inset-y-[-2px] w-[2px] bg-[var(--surface-foreground)]"
          style={{ left: `calc(${alvoClamped}% - 1px)` }}
        />
      )}
    </div>
  );
}

interface BulletRowProps {
  row: BucketRow;
}

function BulletRow({ row }: BulletRowProps): JSX.Element {
  return (
    <div
      className="grid grid-cols-[minmax(0,1fr)_minmax(0,2fr)_auto] items-center gap-3 py-1.5"
      aria-label={ariaLabelFor(row)}
    >
      <div className="flex items-center gap-2 text-sm">
        {severityIcon(row.severity)}
        <span className="truncate text-[var(--surface-foreground)]">{row.label}</span>
      </div>
      <BulletBar row={row} />
      <span className="font-mono text-xs tabular-nums text-[var(--surface-muted-foreground)] tracking-tight">
        {PCT.format(row.atual_pct)}%
        {row.alvo_pct !== null && (
          <>
            {" / "}
            <span className="text-[var(--surface-foreground)]">
              {PCT.format(row.alvo_pct)}%
            </span>
          </>
        )}
      </span>
    </div>
  );
}

interface BadgeProps {
  badge: AlocacaoSummary["badge"];
}

function Badge({ badge }: BadgeProps): JSX.Element {
  const palette = BADGE_COLOR[badge.severity];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-mono text-[11px] font-semibold uppercase tracking-wide"
      style={{ backgroundColor: palette.bg, color: palette.fg }}
    >
      {severityIcon(severityFromBadge(badge.severity))}
      {badge.label}
    </span>
  );
}

function severityFromBadge(b: BadgeSeverity): SeverityLevel {
  if (b === "alinhado") return "alinhado";
  if (b === "atencao") return "atencao";
  if (b === "rebalancear") return "rebalancear";
  return "neutro";
}

interface TableProps {
  rows: BucketRow[];
  hasAlvo: boolean;
}

function DesktopTable({ rows, hasAlvo }: TableProps): JSX.Element {
  return (
    <div className="hidden overflow-x-auto md:block">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--surface-border)] text-left text-[var(--surface-muted-foreground)]">
            <th className="py-2 font-display font-semibold">Classe</th>
            <th className="py-2 text-right font-display font-semibold">Valor</th>
            <th className="py-2 text-right font-display font-semibold">Atual</th>
            {hasAlvo && (
              <th className="py-2 text-right font-display font-semibold">Alvo</th>
            )}
            {hasAlvo && (
              <th className="py-2 text-right font-display font-semibold">Desvio (pp)</th>
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <DesktopRow key={row.id} row={row} hasAlvo={hasAlvo} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface RowProps {
  row: BucketRow;
  hasAlvo: boolean;
}

function DesktopRow({ row, hasAlvo }: RowProps): JSX.Element {
  return (
    <tr className="border-b border-[var(--surface-border)]/40 last:border-0">
      <td className="py-2">
        <div className="flex items-center gap-2">
          {severityIcon(row.severity)}
          <span>{row.label}</span>
          {row.id === "fora_alvo" && (
            <sup className="text-[var(--surface-muted-foreground)]">1</sup>
          )}
        </div>
      </td>
      <td className="py-2 text-right">
        <MonetaryValue value={row.valor} hideSymbol fractionDigits={0} />
      </td>
      <td className="py-2 text-right font-mono tabular-nums">
        {PCT.format(row.atual_pct)}%
      </td>
      {hasAlvo && (
        <td className="py-2 text-right font-mono tabular-nums text-[var(--surface-muted-foreground)]">
          {row.alvo_pct === null ? "—" : `${PCT.format(row.alvo_pct)}%`}
        </td>
      )}
      {hasAlvo && (
        <td
          className={`py-2 text-right font-mono tabular-nums ${SEVERITY_TEXT_CLASS[row.severity]}`}
        >
          {row.desvio_pp === null ? "—" : PP.format(row.desvio_pp)}
        </td>
      )}
    </tr>
  );
}

function MobileStack({ rows, hasAlvo }: TableProps): JSX.Element {
  return (
    <div className="space-y-3 md:hidden" role="list">
      {rows.map((row) => (
        <MobileCard key={row.id} row={row} hasAlvo={hasAlvo} />
      ))}
    </div>
  );
}

function MobileCard({ row, hasAlvo }: RowProps): JSX.Element {
  return (
    <div
      className="rounded-[var(--radius-md)] border border-[var(--surface-border)] p-3"
      role="listitem"
      aria-label={ariaLabelFor(row)}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-medium">
          {severityIcon(row.severity)}
          {row.label}
        </div>
        {hasAlvo && row.desvio_pp !== null && (
          <span
            className={`font-mono text-xs tabular-nums ${SEVERITY_TEXT_CLASS[row.severity]}`}
          >
            {PP.format(row.desvio_pp)} pp
          </span>
        )}
      </div>
      <BulletBar row={row} />
      <div className="mt-2 flex items-baseline justify-between text-xs text-[var(--surface-muted-foreground)]">
        <span className="font-mono tabular-nums">
          {PCT.format(row.atual_pct)}%
          {row.alvo_pct !== null && (
            <span className="ml-1 text-[var(--surface-muted-foreground)]/70">
              / alvo {PCT.format(row.alvo_pct)}%
            </span>
          )}
        </span>
        <MonetaryValue
          value={row.valor}
          hideSymbol
          fractionDigits={0}
          className="text-[var(--surface-foreground)]"
        />
      </div>
    </div>
  );
}

function maiorDesvio(buckets: readonly BucketRow[]): BucketRow | null {
  return buckets
    .filter((b) => b.desvio_pp !== null)
    .reduce<BucketRow | null>(
      (m, c) =>
        m === null || Math.abs(c.desvio_pp ?? 0) > Math.abs(m.desvio_pp ?? 0) ? c : m,
      null,
    );
}

function alinhadoFooter(summary: AlocacaoSummary): string {
  const top = maiorDesvio(summary.buckets);
  if (top && top.desvio_pp !== null) {
    return `Carteira aderente ao alvo. Maior desvio: ${PP.format(top.desvio_pp)} pp em ${top.label}.`;
  }
  return "Carteira aderente ao alvo.";
}

function desalinhadoFooter(summary: AlocacaoSummary): string {
  const subaloc = summary.buckets.find((b) => b.id === summary.nextAporteBucket);
  if (subaloc && subaloc.desvio_pp !== null) {
    return `Próximo aporte → ${subaloc.label} (${PP.format(subaloc.desvio_pp)} pp vs alvo).`;
  }
  return "Rebalancear classes acima do alvo na próxima janela de aporte.";
}

function buildDeterministicFooter(summary: AlocacaoSummary): string {
  if (!summary.hasAlvo) {
    return "Defina sua alocação-alvo em /plano/alocacao para acompanhar desvio.";
  }
  if (summary.badge.severity === "alinhado") return alinhadoFooter(summary);
  return desalinhadoFooter(summary);
}

function pickFooter(
  summary: AlocacaoSummary,
  llmFooter: string | null | undefined,
): string {
  const fromLLM = llmFooter?.trim();
  if (fromLLM) return fromLLM;
  return buildDeterministicFooter(summary);
}

function Footnote(): JSX.Element {
  return (
    <p className="mt-2 text-[11px] leading-relaxed text-[var(--surface-muted-foreground)]">
      <sup>1</sup> Classes fora do plano (cripto, ativos não-mapeados). Reserva
      em Caixa é exibida separada por não compor a alocação-alvo. Granularidade
      por subclasse refina em próxima versão do plano.
    </p>
  );
}

interface HeaderProps {
  total: number;
  investivel: number;
  summary: AlocacaoSummary;
}

function CardHeader({ total, investivel, summary }: HeaderProps): JSX.Element {
  const showSplit = summary.reserva_caixa_valor > 0;
  return (
    <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="text-xs font-medium uppercase tracking-wide text-[var(--surface-muted-foreground)]">
          Carteira total
        </p>
        <MonetaryValue value={total} size="kpi" fractionDigits={0} />
        {showSplit && (
          <p className="mt-1 text-xs text-[var(--surface-muted-foreground)]">
            Investível{" "}
            <MonetaryValue
              value={investivel}
              hideSymbol
              fractionDigits={0}
              className="text-[var(--surface-foreground)]"
            />{" "}
            · reserva{" "}
            <MonetaryValue
              value={summary.reserva_caixa_valor}
              hideSymbol
              fractionDigits={0}
              className="text-[var(--surface-foreground)]"
            />
          </p>
        )}
      </div>
      <Badge badge={summary.badge} />
    </div>
  );
}

interface BulletListProps {
  rows: BucketRow[];
}

function BulletList({ rows }: BulletListProps): JSX.Element {
  return (
    <div
      className="mb-5 rounded-[var(--radius-md)] border border-[var(--surface-border)] bg-[var(--surface-muted)]/30 px-3 py-2"
      role="group"
      aria-label="Comparação visual atual vs alvo por classe"
    >
      {rows.map((row) => (
        <BulletRow key={row.id} row={row} />
      ))}
    </div>
  );
}

/** F9 · S3 — Card único "Alocação · Atual vs Alvo". Substitui os 2
 *  NarrativeChartCard + InvestimentosClasseCard legados. Roda cálculo de
 *  desvio client-side sobre schema v1 (4 classes); migra para backend em
 *  Fase B (ADR-141 · v2 AUVP). */
export function AlocacaoAtualVsAlvoCard({
  investimentos,
  alocacaoAlvo,
  llmFooter,
}: AlocacaoAtualVsAlvoCardProps): JSX.Element | null {
  const total = investimentos?.total ?? 0;
  const rows = investimentos?.tabela_classes;
  if (total <= 0 && (!rows || rows.length === 0)) {
    return null;
  }
  const summary = aggregateAlocacao(rows, alocacaoAlvo, total);
  if (summary.buckets.length === 0) {
    return null;
  }
  const footer = pickFooter(summary, llmFooter);
  const showFootnote = summary.buckets.some((b) => b.id === "fora_alvo");
  return (
    <ReportCard
      variant="feature"
      title="Alocação · Atual vs Alvo"
      size="full"
      conclusion={footer}
    >
      <CardHeader total={summary.total} investivel={summary.total_investivel} summary={summary} />
      <BulletList rows={summary.buckets} />
      <DesktopTable rows={summary.buckets} hasAlvo={summary.hasAlvo} />
      <MobileStack rows={summary.buckets} hasAlvo={summary.hasAlvo} />
      {showFootnote && <Footnote />}
    </ReportCard>
  );
}
