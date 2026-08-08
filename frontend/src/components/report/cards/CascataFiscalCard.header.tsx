/** Sprint A16 L2 P5 (ADR-236 §D5) — Preâmbulo do card "Cascata Fiscal":
 * subheader de regime (com badge de enquadramento fator-R) e a micro-copy de
 * proteção + premissas que abre o corpo do card.
 */
import type { CascataPayload } from "@/lib/api";
import { PREMISSAS_SENTENCE, PROTECTION_SENTENCE } from "./CascataFiscalCard.copy";

export function RegimeSubheader({ cascata }: { cascata: CascataPayload }) {
  const showFatorR =
    cascata.regime === "simples" &&
    cascata.fator_r_pct !== null &&
    cascata.fator_r_faixa !== null;

  return (
    <div className="flex flex-wrap items-center justify-end gap-2 text-right">
      <span className="text-xs uppercase tracking-wider text-[var(--surface-muted-foreground)]">
        {cascata.regime_label}
      </span>
      {showFatorR && cascata.fator_r_pct !== null && cascata.fator_r_faixa !== null && (
        <FatorRBadge
          pct={cascata.fator_r_pct}
          faixa={cascata.fator_r_faixa}
        />
      )}
    </div>
  );
}

function FatorRBadge({
  pct,
  faixa,
}: {
  pct: number;
  faixa: "anexo_iii" | "anexo_v";
}) {
  const isAnexoIII = faixa === "anexo_iii";
  const className = isAnexoIII
    ? "bg-[color-mix(in_srgb,var(--semantic-gain)_15%,transparent)] text-[var(--semantic-gain)]"
    : "bg-[color-mix(in_srgb,var(--semantic-warning)_15%,transparent)] text-[var(--semantic-warning)]";
  const label = isAnexoIII ? "Anexo III" : "Anexo V";
  const pctTxt = (pct * 100).toFixed(1).replace(".", ",");
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-[0.65rem] font-semibold uppercase ${className}`}
      aria-label={`Fator-R móvel 12 meses ${pctTxt} por cento — ${label}`}
    >
      Fator-R {pctTxt}% · {label}
    </span>
  );
}

export function ProtectionAndPremises() {
  return (
    <div className="space-y-1.5">
      <p className="text-sm leading-relaxed text-[var(--surface-foreground)]">
        <strong>Não é recomendação:</strong> {PROTECTION_SENTENCE}
      </p>
      <p className="text-[0.7rem] uppercase tracking-wider text-[var(--surface-muted-foreground)]">
        {PREMISSAS_SENTENCE}
      </p>
    </div>
  );
}
