import { ReportCard } from "../ReportCard";
import { formatPercent } from "@/lib/format";
import type { EquilibrioCerbasiData } from "@/types/report-analysis";

const TITULO = "Equilíbrio entre Presente e Futuro";

/** F9 · F2.B · S2 — Card "Equilíbrio Cerbasi".
 *  Mostra % presente vs futuro e classificação (Gustavo Cerbasi framework).
 */
export function EquilibrioCerbasiCard({
  equilibrio,
}: {
  equilibrio: EquilibrioCerbasiData | undefined;
}) {
  if (!equilibrio) {
    return <EquilibrioVazio texto="Dados de equilíbrio não disponíveis." />;
  }
  // Sem base o produtor omite a divisão (`equilibrio_cerbasi_analyzer.py`): ausente
  // nunca vira "0,0%" (COPY_GUIDELINES §4.3), e um pct sem o par não é dado.
  const divisao = lerDivisao(equilibrio);
  if (!divisao) {
    return (
      <EquilibrioVazio texto="Sem fluxo de caixa no período para calcular a divisão entre presente e futuro." />
    );
  }

  const { presente: pctPresente, futuro: pctFuturo } = divisao;

  return (
    <ReportCard variant="highlight" size="half" title={TITULO}>
      <div className="space-y-4">
        {/* Barra visual presente vs futuro */}
        <div>
          <div className="flex justify-between text-xs text-[var(--surface-muted-foreground)]">
            <span>Presente ({formatPercent(pctPresente)})</span>
            <span>Futuro ({formatPercent(pctFuturo)})</span>
          </div>
          <div
            className="mt-1 flex h-4 overflow-hidden rounded-full"
            role="img"
            aria-label={`Distribuição do fluxo: ${formatPercent(pctPresente)} para o presente, ${formatPercent(pctFuturo)} para o futuro`}
          >
            <div
              className="bg-[var(--brand-primary)] transition-[width]"
              style={{ width: `${pctPresente}%` }}
            />
            <div
              className="bg-[var(--brand-accent)] transition-[width]"
              style={{ width: `${pctFuturo}%` }}
            />
          </div>
        </div>

        {/* Classificação */}
        <div className="text-center">
          <p className="font-display text-lg font-bold text-[var(--brand-primary)]">
            {equilibrio.classificacao ?? "—"}
          </p>
        </div>
      </div>
    </ReportCard>
  );
}

function lerDivisao(
  equilibrio: EquilibrioCerbasiData,
): { presente: number; futuro: number } | null {
  const { pct_presente: presente, pct_futuro: futuro } = equilibrio;
  if (!isPercentual(presente) || !isPercentual(futuro)) return null;
  return { presente, futuro };
}

function isPercentual(valor: unknown): valor is number {
  return typeof valor === "number" && Number.isFinite(valor);
}

function EquilibrioVazio({ texto }: { texto: string }) {
  return (
    <ReportCard variant="highlight" size="half" title={TITULO}>
      <p className="text-sm text-[var(--surface-muted-foreground)]">{texto}</p>
    </ReportCard>
  );
}
