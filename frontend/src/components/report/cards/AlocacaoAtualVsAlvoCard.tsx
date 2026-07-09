import type { JSX } from "react";
import { MinusCircle } from "lucide-react";
import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import {
  Badge,
  BulletRow,
  DesktopTable,
  Footnote,
  MobileStack,
  PCT,
  PP,
  labelFor,
  type AlocacaoCaixa,
  type AlocacaoComparavel,
  type AlocacaoDerived,
  type BadgeSeverity,
} from "./alocacaoCardParts";

export type { AlocacaoDerived } from "./alocacaoCardParts";

export interface AlocacaoAtualVsAlvoCardProps {
  /** Bloco `derived` do payload E5. Ausente em payloads pré-PR6 → card oculto. */
  derived: AlocacaoDerived | undefined;
  /** Texto editorial vindo de E5N (`narrativas.charts.alocacao_atual.conclusion`)
   *  usado como override do footer determinístico. Cap em 200 chars no template. */
  llmFooter?: string | null;
}

function computeBadge(
  hasAlvo: boolean,
  rows: readonly AlocacaoComparavel[],
): { severity: BadgeSeverity; label: string } {
  if (!hasAlvo) return { severity: "sem_alvo", label: "Sem alvo definido" };
  const rebalancear = rows.filter((r) => r.severity === "rebalancear").length;
  const atencao = rows.filter((r) => r.severity === "atencao").length;
  if (rebalancear > 0) {
    return { severity: "rebalancear", label: pluralLabel("Rebalancear", rebalancear) };
  }
  if (atencao > 0) {
    return { severity: "atencao", label: pluralLabel("Atenção", atencao) };
  }
  return { severity: "alinhado", label: "Carteira alinhada" };
}

function pluralLabel(prefix: string, n: number): string {
  return n === 1 ? `${prefix}: 1 classe` : `${prefix}: ${n} classes`;
}

function alinhadoFooter(derived: AlocacaoDerived): string {
  // comparaveis já vem ordenado por |desvio| desc; o primeiro com desvio é o maior.
  const top = derived.comparaveis.find((r) => r.desvio_pp !== null);
  if (top && top.desvio_pp !== null) {
    return `Carteira aderente ao alvo. Maior desvio: ${PP.format(top.desvio_pp)} pp em ${labelFor(top.classe)}.`;
  }
  return "Carteira aderente ao alvo.";
}

function desalinhadoFooter(derived: AlocacaoDerived): string {
  const next = derived.next_aporte_classe;
  const sub = next ? derived.comparaveis.find((r) => r.classe === next) : undefined;
  if (sub && sub.desvio_pp !== null) {
    return `Próximo aporte → ${labelFor(sub.classe)} (${PP.format(sub.desvio_pp)} pp vs alvo).`;
  }
  return "Rebalancear classes acima do alvo na próxima janela de aporte.";
}

function buildDeterministicFooter(
  derived: AlocacaoDerived,
  badge: BadgeSeverity,
): string {
  if (!derived.has_alvo) {
    return "Defina sua alocação-alvo em /plano/alocacao para acompanhar desvio.";
  }
  if (badge === "alinhado") return alinhadoFooter(derived);
  return desalinhadoFooter(derived);
}

function pickFooter(
  derived: AlocacaoDerived,
  badge: BadgeSeverity,
  llmFooter: string | null | undefined,
): string {
  const fromLLM = llmFooter?.trim();
  if (fromLLM) return fromLLM;
  return buildDeterministicFooter(derived, badge);
}

interface HeaderProps {
  total: number;
  investivel: number;
  reserva: number;
  badge: { severity: BadgeSeverity; label: string };
}

function CardHeader({ total, investivel, reserva, badge }: HeaderProps): JSX.Element {
  const showSplit = reserva > 0;
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
              value={reserva}
              hideSymbol
              fractionDigits={0}
              className="text-[var(--surface-foreground)]"
            />
          </p>
        )}
      </div>
      <Badge badge={badge} />
    </div>
  );
}

function BulletList({ rows }: { rows: AlocacaoComparavel[] }): JSX.Element {
  return (
    <div
      className="mb-5 rounded-[var(--radius-md)] border border-[var(--surface-border)] bg-[var(--surface-muted)]/30 px-3 py-2"
      role="group"
      aria-label="Comparação visual atual vs alvo por classe"
    >
      {rows.map((row) => (
        <BulletRow key={row.classe} row={row} />
      ))}
    </div>
  );
}

function CaixaLine({ caixa }: { caixa: AlocacaoCaixa }): JSX.Element | null {
  if (caixa.valor_brl <= 0) return null;
  return (
    <div className="mt-4 rounded-[var(--radius-md)] border border-[var(--surface-border)] bg-[var(--surface-muted)]/30 px-3 py-2">
      <div className="flex items-baseline justify-between gap-2 text-sm">
        <span className="flex items-center gap-2 text-[var(--surface-foreground)]">
          <MinusCircle aria-hidden className="size-4 text-[var(--surface-muted-foreground)]" />
          Reserva (Caixa)
        </span>
        <span className="font-mono text-xs tabular-nums text-[var(--surface-muted-foreground)]">
          {PCT.format(caixa.atual_pct_patrimonio)}% do patrimônio{" · "}
          <MonetaryValue
            value={caixa.valor_brl}
            hideSymbol
            fractionDigits={0}
            className="text-[var(--surface-foreground)]"
          />
        </span>
      </div>
      {caixa.sinal_excesso && (
        <p className="mt-1 text-[11px] leading-relaxed text-[var(--semantic-warning)]">
          Excesso de caixa — considere aportar.
        </p>
      )}
    </div>
  );
}

/** F9 · S3 — Card único "Alocação · Atual vs Alvo". Substitui os 2
 *  NarrativeChartCard + InvestimentosClasseCard legados. Consome o bloco
 *  `derived` computado no backend (ADR-141 §Emenda · v2 AUVP); o cálculo de
 *  desvio deixou de ser client-side. Payloads E5 antigos (sem `derived`) →
 *  card oculto graciosamente. Helpers presentacionais em ./alocacaoCardParts. */
export function AlocacaoAtualVsAlvoCard({
  derived,
  llmFooter,
}: AlocacaoAtualVsAlvoCardProps): JSX.Element | null {
  if (!derived) return null;
  const reserva = derived.caixa.valor_brl;
  const total = derived.carteira_liquida_brl + reserva;
  if (total <= 0) return null;
  // fora_alvo só aparece quando tem valor (as 4 classes de investimento
  // sempre exibem, mesmo a 0%); demais comparáveis vêm já ordenadas.
  const rows = derived.comparaveis.filter(
    (r) => r.classe !== "fora_alvo" || r.valor_brl > 0,
  );
  if (rows.length === 0 && reserva <= 0) return null;
  const badge = computeBadge(derived.has_alvo, derived.comparaveis);
  const footer = pickFooter(derived, badge.severity, llmFooter);
  const showFootnote = rows.some((r) => r.classe === "fora_alvo");
  return (
    <ReportCard
      variant="feature"
      title="Alocação · Atual vs Alvo"
      size="full"
      conclusion={footer}
    >
      <CardHeader
        total={total}
        investivel={derived.carteira_liquida_brl}
        reserva={reserva}
        badge={badge}
      />
      <BulletList rows={rows} />
      <DesktopTable rows={rows} hasAlvo={derived.has_alvo} />
      <MobileStack rows={rows} hasAlvo={derived.has_alvo} />
      <CaixaLine caixa={derived.caixa} />
      {showFootnote && <Footnote />}
    </ReportCard>
  );
}
