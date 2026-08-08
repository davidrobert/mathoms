/** Sprint A16 L2 P5 (ADR-236 §D5) — Copy do card "Tributário PJ — Cascata
 * Fiscal" compartilhada entre a cascata completa e os estados vazios.
 *
 * Co-design product-designer + financial-planner (2026-05-21): a frase de
 * proteção blinda o card inteiro contra interpretação como conselho. Convive
 * com `CascataFiscalCard.triggers.ts`, que guarda a copy dos 5 triggers.
 */

export const HEADER_TITLE = "Tributário PJ · Cascata Fiscal";

export const PROTECTION_SENTENCE =
  "Esta cascata descreve sua situação atual, não recomenda mudança. " +
  "Decisões de regime, anexo ou estrutura societária são do seu contador.";

export const PREMISSAS_SENTENCE =
  "Base: receita bruta 12 meses móveis · fator-R 12 meses móveis · valores anuais salvo indicação.";

export const DISCLAIMER_SENTENCE =
  "Valores estimados a partir de movimentações reconhecidas e IRPF processado. " +
  "Confirme com seu contador antes de qualquer decisão tributária.";
