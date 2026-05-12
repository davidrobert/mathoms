"use client";

import { Check, CircleDashed, X } from "lucide-react";

import { MonetaryValue } from "../MonetaryValue";
import { ReportCard } from "../ReportCard";
import {
  CATEGORY_LABELS,
  CATEGORY_ORDER,
  fiduciaryDisclaimer,
  type ProtectionBundle,
  type ProtectionCategory,
  type ProtectionItem,
} from "./protectionBundle.types";

interface CoberturaSegurosCardProps {
  bundle: ProtectionBundle | undefined;
  effectiveDate?: string | null;
}

type RowStatus = "contracted" | "partial" | "missing";

interface CategoryRow {
  category: ProtectionCategory;
  label: string;
  status: RowStatus;
  totalCoverage: number;
  totalPremium: number | null;
  validityRange: string | null;
  policyCount: number;
}

function aggregateByCategory(
  policies: ProtectionItem[],
  gapAnalysis: ProtectionBundle["gap_analysis"],
): CategoryRow[] {
  const byCategory = new Map<ProtectionCategory, ProtectionItem[]>();
  for (const policy of policies) {
    const cat = policy.category as ProtectionCategory;
    if (!CATEGORY_ORDER.includes(cat)) continue;
    if (!byCategory.has(cat)) byCategory.set(cat, []);
    byCategory.get(cat)!.push(policy);
  }
  return CATEGORY_ORDER.map((cat) => buildRow(cat, byCategory.get(cat) ?? [], gapAnalysis?.[cat]));
}

function buildRow(
  category: ProtectionCategory,
  items: ProtectionItem[],
  gap: ProtectionBundle["gap_analysis"][string] | undefined,
): CategoryRow {
  const totalCoverage = items.reduce((acc, p) => acc + (p.coverage_brl ?? 0), 0);
  const totalPremium = items.some((p) => p.premium_monthly_brl != null)
    ? items.reduce((acc, p) => acc + (p.premium_monthly_brl ?? 0), 0)
    : null;
  return {
    category,
    label: CATEGORY_LABELS[category],
    status: deriveRowStatus(items, gap),
    totalCoverage,
    totalPremium,
    validityRange: deriveValidityRange(items),
    policyCount: items.length,
  };
}

function deriveRowStatus(
  items: ProtectionItem[],
  gap: ProtectionBundle["gap_analysis"][string] | undefined,
): RowStatus {
  if (items.length === 0) return "missing";
  if (gap?.gap_brl !== null && gap?.gap_brl !== undefined && gap.gap_brl > 0) return "partial";
  return "contracted";
}

function deriveValidityRange(items: ProtectionItem[]): string | null {
  if (items.length === 0) return null;
  const ends = items.map((p) => p.ends_at).filter((v): v is string => Boolean(v)).sort();
  const starts = items.map((p) => p.starts_at).filter(Boolean).sort();
  if (starts.length && ends.length) return `${starts[0]} → ${ends[ends.length - 1]}`;
  if (starts.length) return `desde ${starts[0]}`;
  return null;
}

function StatusBadge({ status }: { status: RowStatus }) {
  if (status === "contracted") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-[color-mix(in_srgb,var(--semantic-gain)_15%,transparent)] px-2 py-0.5 text-xs font-medium text-[var(--semantic-gain)]" aria-label="Contratado">
        <Check className="h-3 w-3" aria-hidden="true" /> Contratado
      </span>
    );
  }
  if (status === "partial") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-[color-mix(in_srgb,var(--semantic-warning)_15%,transparent)] px-2 py-0.5 text-xs font-medium text-[var(--semantic-warning)]" aria-label="Parcial">
        <CircleDashed className="h-3 w-3" aria-hidden="true" /> Parcial
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-[color-mix(in_srgb,var(--semantic-loss)_15%,transparent)] px-2 py-0.5 text-xs font-medium text-[var(--semantic-loss)]" aria-label="Ausente">
      <X className="h-3 w-3" aria-hidden="true" /> Ausente
    </span>
  );
}

function MoneyCell({ value }: { value: number | null }) {
  if (value === null || value === 0) {
    return <span className="text-[var(--surface-muted-foreground)]">—</span>;
  }
  return <MonetaryValue value={value} compact />;
}

function TableRow({ row }: { row: CategoryRow }) {
  return (
    <tr className="border-b border-[var(--surface-border)] last:border-b-0">
      <th scope="row" className="py-2 font-medium">{row.label}</th>
      <td className="py-2"><StatusBadge status={row.status} /></td>
      <td className="py-2 text-right"><MoneyCell value={row.totalCoverage || null} /></td>
      <td className="py-2 text-right"><MoneyCell value={row.totalPremium} /></td>
      <td className="py-2 text-xs text-[var(--surface-muted-foreground)]">{row.validityRange ?? "—"}</td>
    </tr>
  );
}

function TotalRow({ totalCoverage, totalPremium }: { totalCoverage: number; totalPremium: number | null }) {
  return (
    <tr className="font-semibold">
      <th scope="row" className="pt-3">Total</th>
      <td className="pt-3" />
      <td className="pt-3 text-right"><MonetaryValue value={totalCoverage} compact /></td>
      <td className="pt-3 text-right"><MoneyCell value={totalPremium} /></td>
      <td className="pt-3" />
    </tr>
  );
}

function CoverageTable({ rows, totalCoverage, totalPremium }: { rows: CategoryRow[]; totalCoverage: number; totalPremium: number | null }) {
  return (
    <div className="hidden overflow-x-auto md:block">
      <table className="w-full text-sm" aria-label="Cobertura de seguros por categoria">
        <caption className="sr-only">Status, capital segurado, prêmio mensal e vigência por categoria de seguro.</caption>
        <thead>
          <tr className="border-b border-[var(--surface-border)] text-left text-xs uppercase tracking-wide text-[var(--surface-muted-foreground)]">
            <th scope="col" className="pb-2">Categoria</th>
            <th scope="col" className="pb-2">Status</th>
            <th scope="col" className="pb-2 text-right">Capital</th>
            <th scope="col" className="pb-2 text-right">Prêmio/mês</th>
            <th scope="col" className="pb-2">Vigência</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => <TableRow key={row.category} row={row} />)}
          <TotalRow totalCoverage={totalCoverage} totalPremium={totalPremium} />
        </tbody>
      </table>
    </div>
  );
}

function MobileCard({ row }: { row: CategoryRow }) {
  return (
    <li className="rounded-md border border-[var(--surface-border)] p-3">
      <div className="flex items-center justify-between">
        <span className="font-semibold">{row.label}</span>
        <StatusBadge status={row.status} />
      </div>
      <dl className="mt-2 grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
        <dt className="text-[var(--surface-muted-foreground)]">Capital</dt>
        <dd className="text-right"><MoneyCell value={row.totalCoverage || null} /></dd>
        <dt className="text-[var(--surface-muted-foreground)]">Prêmio/mês</dt>
        <dd className="text-right"><MoneyCell value={row.totalPremium} /></dd>
        {row.validityRange && (
          <>
            <dt className="text-[var(--surface-muted-foreground)]">Vigência</dt>
            <dd className="text-right">{row.validityRange}</dd>
          </>
        )}
      </dl>
    </li>
  );
}

/** S9-T04 (ADR-192 §D4) — Tabela de cobertura por categoria.
 *
 * 6 categorias canônicas; colunas: status, capital, prêmio/mês, vigência.
 * Mobile (<md): cards empilhados. Padrão tipográfico de PrevidenciaPgblCard.
 *
 * TODO: dados reais virão de T03 — `gap_analysis` por categoria define
 * "parcial". Até T03 mergear, qualquer apólice cadastrada vira "contratado".
 */
export function CoberturaSegurosCard({ bundle, effectiveDate }: CoberturaSegurosCardProps) {
  const rows = aggregateByCategory(bundle?.policies ?? [], bundle?.gap_analysis ?? {});
  const totalCoverage = rows.reduce((acc, r) => acc + r.totalCoverage, 0);
  const totalPremium = rows.some((r) => r.totalPremium != null)
    ? rows.reduce((acc, r) => acc + (r.totalPremium ?? 0), 0)
    : null;

  return (
    <ReportCard variant="feature" size="full" title="Cobertura por Categoria">
      <section role="region" aria-labelledby="cobertura-seguros-title" aria-describedby="cobertura-seguros-disclaimer" className="space-y-4">
        <h4 id="cobertura-seguros-title" className="sr-only">Tabela de cobertura de seguros por categoria</h4>
        <CoverageTable rows={rows} totalCoverage={totalCoverage} totalPremium={totalPremium} />
        <ul className="space-y-3 md:hidden" aria-label="Cobertura por categoria (mobile)">
          {rows.map((row) => <MobileCard key={row.category} row={row} />)}
        </ul>
        <p id="cobertura-seguros-disclaimer" className="rounded-md bg-[var(--surface-muted)] p-3 text-[0.7rem] leading-relaxed text-[var(--surface-muted-foreground)]">
          {fiduciaryDisclaimer("wealth management", effectiveDate)}
        </p>
      </section>
    </ReportCard>
  );
}
