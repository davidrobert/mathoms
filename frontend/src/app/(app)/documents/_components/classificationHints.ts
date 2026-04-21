import type { DocumentResponse } from "@/lib/api";
import { isDocumentClassifiedOk } from "@/lib/format";

/** Alinhado a ``_REVIEW_CONFIDENCE_THRESHOLD`` no backend (document_classification). */
const CLASSIFICATION_LOW_CONFIDENCE = 0.7;

export function isClassificationUncertain(doc: DocumentResponse): boolean {
  if (!isDocumentClassifiedOk(doc.status)) return false;
  if (doc.needs_review) return true;
  const c = doc.classification_confidence;
  return c != null && c < CLASSIFICATION_LOW_CONFIDENCE;
}
