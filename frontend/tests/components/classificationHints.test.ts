import { describe, expect, it } from "vitest";

import type { DocumentResponse } from "@/lib/api";
import { isClassificationUncertain } from "@/app/(app)/documents/_components/classificationHints";

const baseDoc: DocumentResponse = {
  id: "doc-1",
  workspace_id: "ws-1",
  original_name: "x.pdf",
  doc_type: "irpf",
  status: "processed",
  bank_code: null,
  period: null,
  classification_meta: null,
  classification_confidence: null,
  needs_review: false,
  pipeline_e2_extract_ok: null,
  pipeline_extract_notes: null,
  pipeline_last_run_at: null,
  uploaded_at: "2026-04-30T12:00:00Z",
  file_size_bytes: 1,
  content_hash: null,
  content_type: "application/pdf",
  error_message: null,
  possible_duplicate_of_id: null,
} as DocumentResponse;

describe("isClassificationUncertain", () => {
  it("returns true when needs_review is set and no extract", () => {
    expect(
      isClassificationUncertain({
        ...baseDoc,
        needs_review: true,
        pipeline_e2_extract_ok: null,
      }),
    ).toBe(true);
  });

  it("returns true when classification_confidence is below threshold", () => {
    expect(
      isClassificationUncertain({
        ...baseDoc,
        classification_confidence: 0.5,
        pipeline_e2_extract_ok: null,
      }),
    ).toBe(true);
  });

  it("returns false when extraction succeeded even with low confidence", () => {
    expect(
      isClassificationUncertain({
        ...baseDoc,
        needs_review: true,
        classification_confidence: 0.5,
        pipeline_e2_extract_ok: true,
      }),
    ).toBe(false);
  });

  it("returns false when extraction succeeded with no other flags", () => {
    expect(
      isClassificationUncertain({
        ...baseDoc,
        pipeline_e2_extract_ok: true,
      }),
    ).toBe(false);
  });

  it("returns false when status is not classified-ok", () => {
    expect(
      isClassificationUncertain({
        ...baseDoc,
        status: "uploaded",
        needs_review: true,
      }),
    ).toBe(false);
  });
});
