// Labels para subtipos de documento (códigos E0) e helper de display label.
// Extraído de `format.ts` para manter aquele arquivo abaixo do limite (T2).
//
// Quando o backend conhece o subtipo (`e0_doc_type` derivado do
// `classification_meta.content.doc_type`), o subtipo é mais informativo
// que o tipo amplo do enum. Ex.: um informe IRPF não é "uma declaração para
// a Receita" — é insumo emitido pela fonte pagadora (banco, administradora).
// Ver ADR-081.

import type { DocumentType } from "./api";
import { docTypeLabel, formatDocPeriod, institutionLabel } from "./format";

export const E0_DOC_TYPE_MAP: Record<string, string> = {
  irpfdeclaracao: "Declaração IRPF",
  irpfrecibo: "Recibo IRPF",
  informerendimentos: "Informe de rendimentos (IRPF)",
  informerendimentosaluguel: "Informe de aluguéis (IRPF)",
  faturaaluguel: "Fatura de aluguel",
  faturaunique: "Fatura Unique",
  faturacarbon: "Fatura Carbon",
  faturapaoacucar: "Fatura Pão de Açúcar",
  faturasantander: "Fatura Santander",
  fatura: "Fatura",
  investimentosposicao: "Posição de investimentos",
  carteirarendafixa: "Carteira de renda fixa",
  cdbdetalhes: "CDB",
  extratopoupanca: "Extrato de poupança",
  extratoconta: "Extrato",
  extratocontausd: "Extrato (USD)",
  extratocontaglobalusd: "Extrato global (USD)",
  extratocontaglobaleur: "Extrato global (EUR)",
};

/** Label específico do subtipo E0 quando disponível; senão fallback para `docTypeLabel`. */
export function docSubtypeLabel(
  e0DocType: string | null | undefined,
  fallback: DocumentType | null,
): string {
  if (e0DocType && E0_DOC_TYPE_MAP[e0DocType]) return E0_DOC_TYPE_MAP[e0DocType];
  return docTypeLabel(fallback);
}

/** Rótulo de negócio derivado dos campos classificados — `QuintoAndar · Informe de aluguéis (IRPF) · 2025`. */
export function documentDisplayLabel(doc: {
  doc_type: DocumentType | null;
  e0_doc_type?: string | null;
  bank_code: string | null;
  period: string | null;
}): string | null {
  const inst = doc.bank_code ? institutionLabel(doc.bank_code) : null;
  const subtype =
    doc.e0_doc_type && E0_DOC_TYPE_MAP[doc.e0_doc_type] ? E0_DOC_TYPE_MAP[doc.e0_doc_type] : null;
  const type = subtype ?? (doc.doc_type && doc.doc_type !== "other" ? docTypeLabel(doc.doc_type) : null);
  if (!inst && !type) return null;
  const period = doc.period ? formatDocPeriod(doc.period) : null;
  const parts = [inst, type, period && period !== "—" ? period : null].filter(
    (p): p is string => !!p,
  );
  return parts.length >= 1 ? parts.join(" · ") : null;
}
