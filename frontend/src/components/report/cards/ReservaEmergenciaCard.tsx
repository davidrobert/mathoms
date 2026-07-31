import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import { InfoTooltip } from "@/components/ui/InfoTooltip";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { formatJanelaTooltip, parseJanelaRotulo } from "../utils/janelaLabel";
import type { CardVariant } from "@/generated/report-layout";
import type { ReservaEmergenciaData } from "@/types/report-analysis";

interface ReservaEmergenciaCardProps {
  reserva: ReservaEmergenciaData | undefined;
  /** Variant vinda do YAML. Default: "warn" (conforme layout S1). */
  variant?: CardVariant;
}

/** A28.l1 (PR 787) — rótulos legíveis dos perfis de renda que definem o alvo. */
const PERFIL_RENDA_LABELS: Record<string, string> = {
  clt_estavel: "CLT estável",
  clt_unica_fonte: "CLT única fonte",
  renda_mista: "renda mista",
  pj_relevante: "PJ relevante",
  pj_dominante: "PJ dominante",
};

function perfilRendaLabel(perfil: string | undefined): string | null {
  if (!perfil) return null;
  return PERFIL_RENDA_LABELS[perfil] ?? perfil.replace(/_/g, " ");
}

interface AlvoInfo {
  readonly mesesAlvo: number;
  readonly alvoBrl: number;
  readonly gapBrl: number | null;
  readonly perfilLabel: string | null;
}

/** Alvo por perfil de renda (A28.l1); `null` em payload antigo → UI cai no
 * fallback genérico 6/12 meses. */
function resolveAlvo(reserva: ReservaEmergenciaData | undefined): AlvoInfo | null {
  const mesesAlvo = reserva?.meses_alvo;
  const alvoBrl = reserva?.alvo_brl;
  if (mesesAlvo == null || mesesAlvo <= 0 || alvoBrl == null || alvoBrl <= 0) return null;
  return {
    mesesAlvo,
    alvoBrl,
    gapBrl: typeof reserva?.gap_brl === "number" ? reserva.gap_brl : null,
    perfilLabel: perfilRendaLabel(reserva?.perfil_renda),
  };
}

/** F9 · F2.A · S1 — Card "Reserva de Emergência".
 *
 * Cobertura em meses vs alvo do perfil de renda (A28.l1: CLT 6 · mista 12 ·
 * PJ-dominante 18) + avaliação qualitativa. Payload antigo sem `meses_alvo`
 * degrada para as metas genéricas de 6 e 12 meses.
 *
 * Regra de variant (F3.2 refinará): se cobertura < 3 meses, força critical;
 * entre 3 e 6 warn; ≥ 6 success. Respeita override do layout.yaml.
 */
export function ReservaEmergenciaCard({
  reserva,
  variant = "warn",
}: ReservaEmergenciaCardProps) {
  const cobertura = reserva?.cobertura_meses ?? 0;
  const total = reserva?.total_liquida ?? 0;
  const despesasMensais = reserva?.despesas_mensais ?? 0;
  const nivel12 = reserva?.nivel_12_meses ?? 0;
  // ADR-306 (A28.l4) — rótulo da janela de mensalização; payload antigo omite.
  const janelaTooltip = formatJanelaTooltip(
    parseJanelaRotulo(reserva?.janela, reserva?.janela_meses),
  );
  const alvo = resolveAlvo(reserva);
  const alvoRefBrl = alvo?.alvoBrl ?? nivel12;
  const pctRumoAlvo = alvoRefBrl > 0 ? Math.min(100, (total / alvoRefBrl) * 100) : 0;
  const progressAria = alvo
    ? `Progresso rumo ao alvo de ${alvo.mesesAlvo} meses de reserva`
    : "Progresso rumo à reserva de 12 meses";
  const progressCaption = alvo
    ? `do alvo de ${alvo.mesesAlvo} meses`
    : "da meta de 12 meses";

  const computedVariant: CardVariant =
    cobertura < 3 ? "critical" : cobertura < 6 ? "warn" : "success";

  return (
    <ReportCard
      variant={variant === "warn" ? computedVariant : variant}
      size="half"
      title="Reserva de Emergência"
    >
      <div className="space-y-4">
        <div>
          <p className="font-mono text-3xl font-semibold tabular-nums text-[var(--surface-foreground)]">
            {cobertura.toFixed(1).replace(".", ",")} meses
          </p>
          <p className="text-sm text-[var(--surface-muted-foreground)]">
            de cobertura • {reserva?.avaliacao_liquidity ?? "—"}
          </p>
        </div>

        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <dt className="text-[var(--surface-muted-foreground)]">Total líquido</dt>
            <dd>
              <MonetaryValue
                value={total}
                provenance={{ fieldId: "reserva_emergencia.total_liquida" }}
              />
            </dd>
          </div>
          <div>
            <dt className="text-[var(--surface-muted-foreground)]">
              <span className="inline-flex items-center gap-1">
                Despesas/mês
                {janelaTooltip && (
                  <InfoTooltip
                    ariaLabel="Sobre a janela de mensalização das despesas"
                    content={janelaTooltip}
                  />
                )}
              </span>
            </dt>
            <dd>
              <MonetaryValue value={despesasMensais} />
            </dd>
          </div>
          {alvo ? <AlvoCells alvo={alvo} /> : <MetasGenericasCells reserva={reserva} />}
        </dl>

        <div>
          <ProgressBar
            value={pctRumoAlvo}
            ariaLabel={progressAria}
            barClassName="bg-[var(--semantic-gain)]"
          />
          <p className="mt-1 text-xs text-[var(--surface-muted-foreground)]">
            {pctRumoAlvo.toFixed(0)}% {progressCaption}
          </p>
        </div>
      </div>
    </ReportCard>
  );
}

/** A28.l1 — células do alvo por perfil de renda + gap até o alvo. */
function AlvoCells({ alvo }: { alvo: AlvoInfo }) {
  return (
    <>
      <div>
        <dt className="text-[var(--surface-muted-foreground)]">
          <span className="inline-flex items-center gap-1">
            Alvo ({alvo.mesesAlvo} meses)
            {alvo.perfilLabel && (
              <InfoTooltip
                ariaLabel="Sobre o alvo da reserva"
                content={`Alvo definido pelo perfil de renda da família (${alvo.perfilLabel}): quanto menos previsível a renda, maior a reserva recomendada.`}
              />
            )}
          </span>
        </dt>
        <dd>
          <MonetaryValue value={alvo.alvoBrl} />
        </dd>
      </div>
      <div>
        <dt className="text-[var(--surface-muted-foreground)]">Gap até o alvo</dt>
        <dd>
          {alvo.gapBrl != null ? <MonetaryValue value={alvo.gapBrl} /> : "—"}
        </dd>
      </div>
    </>
  );
}

/** Fallback pré-A28.l1: metas genéricas de 6 e 12 meses. */
function MetasGenericasCells({ reserva }: { reserva: ReservaEmergenciaData | undefined }) {
  return (
    <>
      <div>
        <dt className="text-[var(--surface-muted-foreground)]">Meta 6 meses</dt>
        <dd>
          <MonetaryValue value={reserva?.nivel_6_meses ?? 0} />
        </dd>
      </div>
      <div>
        <dt className="text-[var(--surface-muted-foreground)]">Meta 12 meses</dt>
        <dd>
          <MonetaryValue value={reserva?.nivel_12_meses ?? 0} />
        </dd>
      </div>
    </>
  );
}
