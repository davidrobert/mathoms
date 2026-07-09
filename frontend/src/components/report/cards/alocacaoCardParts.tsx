import type { JSX } from "react";
import { CheckCircle2, AlertTriangle, XCircle, MinusCircle } from "lucide-react";
import { MonetaryValue } from "../MonetaryValue";

// ── Contrato `derived` emitido pelo backend em goals.alocacao_alvo.derived
//    (ADR-141 §Emenda). Espelha AlocacaoDeviationResult.to_dict() em
//    pipeline/domain/services/alocacao_alvo_deviation.py. O desvio é
//    computado no backend; o card apenas renderiza. ──
export type ComparableClasse = "renda_fixa" | "acoes_br" | "acoes_int" | "fiis" | "fora_alvo";
export type SeverityLevel = "alinhado" | "atencao" | "rebalancear" | "neutro";
export type BadgeSeverity = "alinhado" | "atencao" | "rebalancear" | "sem_alvo";

export interface AlocacaoComparavel {
  classe: ComparableClasse;
  valor_brl: number;
  componentes: string[];
  atual_pct: number;
  alvo_pct: number | null;
  desvio_pp: number | null;
  severity: SeverityLevel;
}

export interface AlocacaoCaixa {
  valor_brl: number;
  atual_pct_patrimonio: number;
  alvo_pct: number | null;
  excesso_pp: number | null;
  sinal_excesso: boolean;
}

export interface AlocacaoDerived {
  comparaveis: AlocacaoComparavel[];
  desvio_max_pct: number | null;
  next_aporte_classe: string | null;
  carteira_liquida_brl: number;
  caixa: AlocacaoCaixa;
  imoveis_fisicos_brl: number;
  has_alvo: boolean;
  rf_comparacao: string;
  alvo_renormalizado_defensivo: boolean;
}

const CLASSE_LABEL: Record<ComparableClasse, string> = {
  renda_fixa: "Renda Fixa",
  acoes_br: "Ações BR",
  acoes_int: "Ações Int.",
  fiis: "FIIs",
  fora_alvo: "Fora do alvo",
};

export function labelFor(classe: ComparableClasse): string {
  return CLASSE_LABEL[classe];
}

export const PCT = new Intl.NumberFormat("pt-BR", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

export const PP = new Intl.NumberFormat("pt-BR", {
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

export function severityIcon(level: SeverityLevel): JSX.Element {
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

export function ariaLabelFor(row: AlocacaoComparavel): string {
  const atual = `${PCT.format(row.atual_pct)} por cento atual`;
  if (row.alvo_pct === null || row.desvio_pp === null) {
    return `${labelFor(row.classe)}: ${atual}, sem alvo definido`;
  }
  const alvo = `${PCT.format(row.alvo_pct)} por cento alvo`;
  const desvio = `desvio de ${PP.format(row.desvio_pp)} pontos percentuais`;
  return `${labelFor(row.classe)}: ${atual} vs ${alvo}, ${desvio}`;
}

interface RowProps {
  row: AlocacaoComparavel;
}

export function BulletBar({ row }: RowProps): JSX.Element {
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

export function BulletRow({ row }: RowProps): JSX.Element {
  return (
    <div
      className="grid grid-cols-[minmax(0,1fr)_minmax(0,2fr)_auto] items-center gap-3 py-1.5"
      aria-label={ariaLabelFor(row)}
    >
      <div className="flex items-center gap-2 text-sm">
        {severityIcon(row.severity)}
        <span className="truncate text-[var(--surface-foreground)]">{labelFor(row.classe)}</span>
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

function severityFromBadge(b: BadgeSeverity): SeverityLevel {
  if (b === "alinhado") return "alinhado";
  if (b === "atencao") return "atencao";
  if (b === "rebalancear") return "rebalancear";
  return "neutro";
}

interface BadgeProps {
  badge: { severity: BadgeSeverity; label: string };
}

export function Badge({ badge }: BadgeProps): JSX.Element {
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

interface TableProps {
  rows: AlocacaoComparavel[];
  hasAlvo: boolean;
}

export function DesktopTable({ rows, hasAlvo }: TableProps): JSX.Element {
  return (
    <div className="hidden overflow-x-auto md:block">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--surface-border)] text-left text-[var(--surface-muted-foreground)]">
            <th scope="col" className="py-2 font-display font-semibold">Classe</th>
            <th scope="col" className="py-2 text-right font-display font-semibold">Valor</th>
            <th scope="col" className="py-2 text-right font-display font-semibold">Atual</th>
            {hasAlvo && (
              <th scope="col" className="py-2 text-right font-display font-semibold">Alvo</th>
            )}
            {hasAlvo && (
              <th scope="col" className="py-2 text-right font-display font-semibold">Desvio (pp)</th>
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <DesktopRow key={row.classe} row={row} hasAlvo={hasAlvo} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface DesktopRowProps {
  row: AlocacaoComparavel;
  hasAlvo: boolean;
}

function DesktopRow({ row, hasAlvo }: DesktopRowProps): JSX.Element {
  return (
    <tr className="border-b border-[var(--surface-border)]/40 last:border-0">
      <td className="py-2">
        <div className="flex items-center gap-2">
          {severityIcon(row.severity)}
          <span>{labelFor(row.classe)}</span>
          {row.classe === "fora_alvo" && (
            <sup className="text-[var(--surface-muted-foreground)]">1</sup>
          )}
        </div>
      </td>
      <td className="py-2 text-right">
        <MonetaryValue value={row.valor_brl} hideSymbol fractionDigits={0} />
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

export function MobileStack({ rows, hasAlvo }: TableProps): JSX.Element {
  return (
    <div className="space-y-3 md:hidden" role="list">
      {rows.map((row) => (
        <MobileCard key={row.classe} row={row} hasAlvo={hasAlvo} />
      ))}
    </div>
  );
}

function MobileCard({ row, hasAlvo }: DesktopRowProps): JSX.Element {
  return (
    <div
      className="rounded-[var(--radius-md)] border border-[var(--surface-border)] p-3"
      role="listitem"
      aria-label={ariaLabelFor(row)}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm font-medium">
          {severityIcon(row.severity)}
          {labelFor(row.classe)}
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
          value={row.valor_brl}
          hideSymbol
          fractionDigits={0}
          className="text-[var(--surface-foreground)]"
        />
      </div>
    </div>
  );
}

export function Footnote(): JSX.Element {
  return (
    <p className="mt-2 text-[11px] leading-relaxed text-[var(--surface-muted-foreground)]">
      <sup>1</sup> Classes fora do plano (cripto, ativos não-mapeados). Reserva
      em Caixa é exibida separada por não compor a alocação-alvo. Granularidade
      por subclasse refina em próxima versão do plano.
    </p>
  );
}
