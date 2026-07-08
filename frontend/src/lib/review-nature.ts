/**
 * Taxonomia de natureza dos reasons de reconciliação (A32.l6 PR2).
 *
 * Mapa DECLARATIVO code→natureza: a tela de review diz DE QUEM é o erro —
 * "Falha na nossa leitura" (defeito provável do produto), "Problema no seu
 * documento" (dado do usuário) ou "Documento faltando" (cobertura). Decisão
 * Q4 do owner: selo na review principal, sem aba separada; warnings
 * não-bloqueantes ficam com selo rebaixando os prováveis-nossos.
 *
 * WCAG: a distinção nunca é só cor — cada natureza tem ícone + rótulo +
 * forma (borda tracejada para "Documento faltando"). Tokens semânticos
 * existentes via StatusVariant; nenhum token novo.
 */

import type { StatusVariant } from "@/lib/format";

export type ReviewNature =
  | "nossa_leitura"
  | "seu_documento"
  | "documento_faltando";

/** code → natureza. Cobertura completa dos 6 ReviewReasonCode projetados
 * em REVIEW_REASON_COPY — teste de completude em review-nature.test.ts. */
export const REVIEW_REASON_NATURE: Record<string, ReviewNature> = {
  // Extração não confirmou a instituição no conteúdo (diagnóstico A32:
  // 100% causa-produto na run dogfood; contrato E2-llm corrigido na l2).
  "extract.missing_required_field": "nossa_leitura",
  // Período lido implausível (2100/1899) — parser nosso (corrigido na l3).
  "dedup.sentinel_period": "nossa_leitura",
  // Guard descartou lançamentos que interpretamos com data fora da janela.
  "domain.anachronic_transaction": "nossa_leitura",
  // Saldo não continua: provavelmente falta um extrato entre os dois.
  "domain.balance_gap": "documento_faltando",
  // Dias sem cobertura entre extratos da mesma conta.
  "domain.temporal_gap": "documento_faltando",
  // Extrato × IRPF divergem — dois documentos do usuário em conflito.
  "domain.baseline_divergence": "seu_documento",
};

/** Codes em que a atribuição é incerta → rótulo com hedge "provavelmente". */
const HEDGED_CODES = new Set([
  "extract.missing_required_field",
  "domain.anachronic_transaction",
  "domain.balance_gap",
]);

export interface NatureSpec {
  /** Rótulo sem hedge (fato estabelecido). */
  label: string;
  /** Rótulo com hedge para codes de atribuição incerta. */
  hedgedLabel: string;
  /** Token semântico existente (StatusBadge). */
  variant: StatusVariant;
  /** Forma: borda tracejada distingue "faltando" sem depender de cor. */
  dashed: boolean;
}

export const NATURE_SPEC: Record<ReviewNature, NatureSpec> = {
  nossa_leitura: {
    label: "Falha na nossa leitura",
    hedgedLabel: "Provável falha na nossa leitura",
    variant: "info",
    dashed: false,
  },
  seu_documento: {
    label: "Problema no seu documento",
    hedgedLabel: "Provável problema no seu documento",
    variant: "warning",
    dashed: false,
  },
  documento_faltando: {
    label: "Documento faltando",
    hedgedLabel: "Provável documento faltando",
    variant: "muted",
    dashed: true,
  },
};

export function natureForCode(code: string): ReviewNature | null {
  return REVIEW_REASON_NATURE[code] ?? null;
}

/** Rótulo do selo para um code — aplica hedge quando a atribuição é incerta. */
export function natureLabelForCode(code: string): string | null {
  const nature = natureForCode(code);
  if (!nature) return null;
  const spec = NATURE_SPEC[nature];
  return HEDGED_CODES.has(code) ? spec.hedgedLabel : spec.label;
}
