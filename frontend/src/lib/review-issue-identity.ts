/**
 * Identidade legível do documento por trás de um ValidationIssue (A32.l6).
 *
 * O backend projeta em `issue.context` os campos do documento resolvido
 * (`doc_bank_code`, `doc_type`, `doc_e0_type`, `doc_period`, `document_id`).
 * Aqui eles viram o rótulo "Instituição · Tipo · Período" via
 * `documentDisplayLabel` — o artifact_key com prefixo sha256 NUNCA aparece
 * no corpo visível do card (só sob "Detalhes técnicos").
 */

import type { ValidationIssue } from "@/lib/api/pipeline";
import type { DocumentType } from "@/lib/api";
import { documentDisplayLabel } from "@/lib/documentTypeLabels";

/** Prefixo content-addressed sha256[:12] dos artifact_keys (ADR-084). */
const HASH_PREFIX_RE = /^[0-9a-f]{12}_/;
/** Sufixo de stage do filename legado (ex.: `-3_reconciled.json`). */
const STAGE_SUFFIX_RE = /-[\d.]+[a-z]*_[a-z_]+\.json$/i;

/** Rótulo do grupo de reasons cross-documento (artifact_key vazio). */
export const CROSS_DOC_LABEL = "Sequência de contas";

function contextString(issue: ValidationIssue, key: string): string | null {
  const value = issue.context[key];
  return typeof value === "string" && value.length > 0 ? value : null;
}

/** `documents.id` do documento resolvido pelo backend, se houver. */
export function issueDocumentId(issue: ValidationIssue): string | null {
  return contextString(issue, "document_id");
}

/** Rótulo "Instituição · Tipo · Período" quando o backend resolveu o documento. */
export function issueDocumentLabel(issue: ValidationIssue): string | null {
  const bankCode = contextString(issue, "doc_bank_code");
  const e0DocType = contextString(issue, "doc_e0_type");
  const docType = contextString(issue, "doc_type");
  const period = contextString(issue, "doc_period");
  if (!bankCode && !e0DocType && !docType) return null;
  return documentDisplayLabel({
    doc_type: (docType as DocumentType | null) ?? null,
    e0_doc_type: e0DocType,
    bank_code: bankCode,
    period,
  });
}

/** Versão exibível do artifact_key: sem prefixo sha256 e sem sufixo de stage. */
export function humanizeArtifactKey(key: string): string {
  return key.replace(HASH_PREFIX_RE, "").replace(STAGE_SUFFIX_RE, "").trim();
}

/**
 * Rótulo legível da ocorrência, nesta ordem de preferência:
 * 1. identidade do documento resolvida pelo backend;
 * 2. artifact_key humanizado (nunca o hash cru);
 * 3. "Sequência de contas" para reasons cross-doc sem artifact_key;
 * 4. mensagem técnica original (último recurso).
 */
export function occurrenceIdentityLabel(issue: ValidationIssue): string {
  const docLabel = issueDocumentLabel(issue);
  if (docLabel) return docLabel;
  const key = contextString(issue, "artifact_key");
  if (key) {
    const humanized = humanizeArtifactKey(key);
    if (humanized.length > 0) return humanized;
  }
  if (key === null && issue.context["artifact_key"] !== undefined) {
    return CROSS_DOC_LABEL;
  }
  return issue.legacy_message || CROSS_DOC_LABEL;
}
