"use client";

import { createContext, useContext, useMemo, type ReactNode } from "react";

import type { ReportAnalysisData } from "@/lib/api";

/** A25.l5 (ADR-279) — projeção ESTREITA do `_lineage` para a UI cliente.
 *
 * Lista branca deliberada: label, contagens derivadas e needs_review.
 * Identificadores internos (hashes, ids de run/documento, stage,
 * artifact_key, rule_ref, inputs) ficam fora deste shape — o popover N2
 * nunca tem acesso a eles, por construção.
 */
export interface ProvenanceEntry {
  fieldId: string;
  label: string;
  /** Documentos lidos pela análise — `null` ⇒ verbo sem número. */
  documentsCount: number | null;
  /** Lançamentos conferidos antes da deduplicação — `null` ⇒ verbo omitido. */
  entriesCount: number | null;
  /** Quantos lançamentos apareciam repetidos e contaram só uma vez. */
  repeatedCount: number | null;
  /** Faixa âmbar "Ainda estou conferindo um detalhe deste número." */
  needsReview: boolean;
  /** true ⇒ "Confirmei o saldo direto dos seus extratos." */
  isPassthrough: boolean;
}

const ReportProvenanceContext = createContext<ReadonlyMap<string, ProvenanceEntry> | null>(null);

function parseCount(raw: string | undefined): number | null {
  if (typeof raw !== "string" || !/^\d+$/.test(raw)) return null;
  return Number(raw);
}

function documentsCountFrom(data: ReportAnalysisData): number | null {
  const lineage = data._report_lineage;
  if (!lineage) return null;
  if (lineage.consumed_document_count > 0) return lineage.consumed_document_count;
  if (lineage.source_document_count > 0) return lineage.source_document_count;
  return null;
}

function buildEntry(
  fieldId: string,
  field: { label?: string; edge_type?: string; signals?: Record<string, string> },
  documentsCount: number | null,
): ProvenanceEntry | null {
  if (typeof field.label !== "string" || field.label.length === 0) return null;
  const signals = field.signals ?? {};
  const entriesCount = parseCount(signals.tx_total);
  const repeated = parseCount(signals.dedup_collapsed);
  const review = parseCount(signals.dedup_review);
  const entry: ProvenanceEntry = {
    fieldId,
    label: field.label,
    documentsCount,
    entriesCount: entriesCount !== null && entriesCount > 0 ? entriesCount : null,
    repeatedCount: entriesCount !== null && entriesCount > 0 ? repeated : null,
    needsReview: (review !== null && review > 0) || signals.k4_coverage === "partial",
    isPassthrough: field.edge_type === "passthrough",
  };
  // "Nenhum count → shell não passa provenance" (co-design 2026-06-10 §5).
  if (entry.documentsCount === null && entry.entriesCount === null) return null;
  return entry;
}

function buildEntries(data: ReportAnalysisData): ReadonlyMap<string, ProvenanceEntry> {
  const fields = data._lineage?.fields ?? {};
  const documentsCount = documentsCountFrom(data);
  const entries = new Map<string, ProvenanceEntry>();
  for (const [fieldId, field] of Object.entries(fields)) {
    const entry = buildEntry(fieldId, field, documentsCount);
    if (entry) entries.set(fieldId, entry);
  }
  return entries;
}

interface ReportProvenanceProviderProps {
  data: ReportAnalysisData;
  /** Flag `report_provenance_enabled` — off ⇒ contexto vazio ⇒ zero selo. */
  enabled: boolean;
  children: ReactNode;
}

export function ReportProvenanceProvider({
  data,
  enabled,
  children,
}: ReportProvenanceProviderProps) {
  const entries = useMemo(
    () => (enabled ? buildEntries(data) : null),
    [data, enabled],
  );
  return (
    <ReportProvenanceContext.Provider value={entries}>
      {children}
    </ReportProvenanceContext.Provider>
  );
}

/** Fora do provider, flag off ou campo sem dados ⇒ `undefined` ⇒ render atual. */
export function useProvenanceEntry(fieldId: string | undefined): ProvenanceEntry | undefined {
  const entries = useContext(ReportProvenanceContext);
  if (!entries || !fieldId) return undefined;
  return entries.get(fieldId);
}
