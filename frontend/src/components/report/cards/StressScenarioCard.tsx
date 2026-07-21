"use client";

/** ADR-167 (A8.4 PR3) — Card comparativo "base vs estresse" para APP_C.
 *
 * Visualização lado-a-lado decidida com product-designer (D3 do plano):
 * cards comparativos com delta explícito (sinal+cor, a11y AA) e parágrafo
 * "Leitura:" justificando o stress test em tom não-alarmista.
 */
import { formatBRLNoCents } from "@/lib/format";
import { ReportCard } from "../ReportCard";

type StressCenarios = {
  labels?: string[];
  aportes?: number[];
  prazos_if?: number[];
  anos_if?: number[];
  premissas?: { aporte_base?: number };
};

type StressGoals = { if_prazo_anos?: number; if_ano?: number };

function fmtAnosMeses(prazo: number | null | undefined): string {
  if (prazo == null) return "—";
  const anos = Math.floor(prazo);
  const meses = Math.round((prazo - anos) * 12);
  return meses > 0 ? `${anos}a ${meses}m` : `${anos}a`;
}

function deltaTexto(n: number | null, fmt: (v: number) => string): string {
  if (n == null) return "";
  const sinal = n > 0 ? "+" : "";
  return ` (${sinal}${fmt(n)})`;
}

/** Frase do parágrafo "Leitura:", ou null quando não há fragmento (A37.l10).
 *
 * Em produção o cenário reduz a capacidade de aporte (fator < 1 no
 * CenariosConjugeAnalyzer), então o delta negativo é o caminho principal.
 */
function leituraTexto(deltaAportePct: number | null, deltaPrazo: number | null): string | null {
  const aporte =
    deltaAportePct == null || deltaAportePct === 0
      ? null
      : deltaAportePct > 0
        ? `a ausência da segunda renda exige aporte ${deltaAportePct.toFixed(0)}% maior`
        : `a ausência da segunda renda reduz a capacidade de aporte em ${Math.abs(deltaAportePct).toFixed(0)}%`;
  const prazo =
    deltaPrazo != null && deltaPrazo > 0 ? `estende a IF em ${fmtAnosMeses(deltaPrazo)}` : null;
  if (aporte != null && prazo != null) {
    return deltaAportePct != null && deltaAportePct > 0
      ? `${aporte} ou ${prazo}`
      : `${aporte}, o que ${prazo}`;
  }
  if (prazo != null) return `o cenário ${prazo}`;
  return aporte;
}

export function StressScenarioCard({
  cenarios,
  goals,
}: {
  cenarios: StressCenarios;
  goals?: StressGoals;
}) {
  const label = cenarios.labels?.[0] ?? "Cenário de estresse";
  const aporteEstresse = cenarios.aportes?.[0];
  const prazoEstresse = cenarios.prazos_if?.[0];
  const anoEstresse = cenarios.anos_if?.[0];

  const aporteBase = cenarios.premissas?.aporte_base;
  const prazoBase = goals?.if_prazo_anos;
  const anoBase = goals?.if_ano;

  const deltaAportePct =
    aporteBase != null && aporteEstresse != null && aporteBase > 0
      ? ((aporteEstresse - aporteBase) / aporteBase) * 100
      : null;
  const deltaPrazo =
    prazoBase != null && prazoEstresse != null && prazoEstresse !== 999
      ? prazoEstresse - prazoBase
      : null;
  const deltaAno =
    anoBase != null && anoEstresse != null ? anoEstresse - anoBase : null;
  const leitura = leituraTexto(deltaAportePct, deltaPrazo);

  return (
    <ReportCard variant="feature" title={`Premissa testada: ${label}`} size="full">
      <div className="grid grid-cols-2 gap-6 text-sm">
        <div>
          <h4 className="font-display font-semibold mb-3 text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
            Cenário base
          </h4>
          <dl className="space-y-2">
            <div className="flex justify-between">
              <dt className="text-[var(--surface-muted-foreground)]">Aporte mensal</dt>
              <dd className="font-mono tabular-nums">{formatBRLNoCents(aporteBase)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[var(--surface-muted-foreground)]">Prazo até IF</dt>
              <dd className="font-mono tabular-nums">{fmtAnosMeses(prazoBase)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[var(--surface-muted-foreground)]">Ano IF</dt>
              <dd className="font-mono tabular-nums">{anoBase ?? "—"}</dd>
            </div>
          </dl>
        </div>
        <div>
          <h4 className="font-display font-semibold mb-3 text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
            Cenário de estresse
          </h4>
          <dl className="space-y-2">
            <div className="flex justify-between">
              <dt className="text-[var(--surface-muted-foreground)]">Aporte mensal</dt>
              <dd className="font-mono tabular-nums">
                {formatBRLNoCents(aporteEstresse)}
                <span
                  className={
                    deltaAportePct != null && deltaAportePct > 0
                      ? "text-[var(--semantic-warning)] ml-1"
                      : "ml-1"
                  }
                  aria-label={
                    deltaAportePct != null
                      ? `delta de ${deltaAportePct.toFixed(0)} por cento`
                      : undefined
                  }
                >
                  {deltaTexto(deltaAportePct, (n) => `${n.toFixed(0)}%`)}
                </span>
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[var(--surface-muted-foreground)]">Prazo até IF</dt>
              <dd className="font-mono tabular-nums">
                {prazoEstresse === 999 ? "Não atinge" : fmtAnosMeses(prazoEstresse)}
                {prazoEstresse !== 999 && (
                  <span
                    className={
                      deltaPrazo != null && deltaPrazo > 0
                        ? "text-[var(--semantic-warning)] ml-1"
                        : "ml-1"
                    }
                  >
                    {deltaTexto(deltaPrazo, fmtAnosMeses)}
                  </span>
                )}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[var(--surface-muted-foreground)]">Ano IF</dt>
              <dd className="font-mono tabular-nums">
                {prazoEstresse === 999 ? "—" : (anoEstresse ?? "—")}
                {prazoEstresse !== 999 && deltaAno != null && deltaAno !== 0 && (
                  <span
                    className={deltaAno > 0 ? "text-[var(--semantic-warning)] ml-1" : "ml-1"}
                  >
                    {deltaAno > 0 ? `(+${deltaAno} anos)` : `(${deltaAno} anos)`}
                  </span>
                )}
              </dd>
            </div>
          </dl>
        </div>
      </div>
      {leitura != null && (
        <p className="mt-6 text-sm text-[var(--surface-foreground)]">
          <strong>Leitura:</strong> {leitura}. Reforce a reserva de emergência e revise a
          alocação para mais conservadora se a dependência de renda do cônjuge for material
          para o plano.
        </p>
      )}
    </ReportCard>
  );
}
