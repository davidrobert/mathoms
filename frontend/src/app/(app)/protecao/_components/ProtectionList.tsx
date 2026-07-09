"use client";

// A11.W5 · ADR-192 · S9-T05 — listagem de apólices com filtros + ações.
// Tabela responsiva (mobile vira cards). Cancela via soft-delete.

import { useMemo, useState } from "react";
import { Eye, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { FamilyMemberConfig } from "@/lib/api";
import { formatBRLDecimalString, formatBRLNoCents } from "@/lib/format";
import {
  PROTECTION_CATEGORIES,
  PROTECTION_STATUSES,
  type Protection,
  type ProtectionCategory,
  type ProtectionStatus,
} from "@/lib/api/protections";

import { RevealPolicyRefDialog } from "./RevealPolicyRefDialog";

interface ProtectionListProps {
  protections: Protection[];
  workspaceId: string;
  members: FamilyMemberConfig[];
  onCancel: (protectionId: string) => Promise<void>;
}

type StatusFilter = ProtectionStatus | "all";
type CategoryFilter = ProtectionCategory | "all";

function categoryLabel(value: ProtectionCategory): string {
  return PROTECTION_CATEGORIES.find((c) => c.value === value)?.label ?? value;
}

function statusVariant(status: ProtectionStatus): "default" | "secondary" | "destructive" {
  if (status === "Ativa") return "default";
  if (status === "Cancelada" || status === "Vencida") return "destructive";
  return "secondary";
}

function memberLabel(members: FamilyMemberConfig[], id: string | null): string {
  if (!id) return "—";
  const m = members.find((m) => m.id === id || m.key === id);
  return m?.short_name ?? m?.full_name ?? "—";
}

export function ProtectionList({
  protections,
  workspaceId,
  members,
  onCancel,
}: ProtectionListProps) {
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("Ativa");
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>("all");
  const [revealTarget, setRevealTarget] = useState<Protection | null>(null);
  const [cancelingId, setCancelingId] = useState<string | null>(null);

  const filtered = useMemo(() => {
    return protections.filter((p) => {
      if (statusFilter !== "all" && p.status !== statusFilter) return false;
      if (categoryFilter !== "all" && p.category !== categoryFilter) return false;
      return true;
    });
  }, [protections, statusFilter, categoryFilter]);

  const totals = useMemo(() => {
    const active = filtered.filter((p) => p.status === "Ativa");
    const totalCoverage = active.reduce(
      (sum, p) => sum + Number(p.coverage_brl || "0"),
      0,
    );
    const totalPremium = active.reduce(
      (sum, p) => sum + Number(p.premium_monthly_brl || "0"),
      0,
    );
    return { count: active.length, totalCoverage, totalPremium };
  }, [filtered]);

  async function handleCancel(p: Protection) {
    if (
      !window.confirm(
        `Cancelar apólice de ${categoryLabel(p.category)} (${formatBRLDecimalString(p.coverage_brl)})? Esta ação é soft-delete.`,
      )
    ) {
      return;
    }
    setCancelingId(p.id);
    try {
      await onCancel(p.id);
    } finally {
      setCancelingId(null);
    }
  }

  return (
    <div className="space-y-4">
      <Filters
        statusFilter={statusFilter}
        categoryFilter={categoryFilter}
        onStatus={setStatusFilter}
        onCategory={setCategoryFilter}
      />

      <TotalsStrip
        count={totals.count}
        totalCoverage={totals.totalCoverage}
        totalPremium={totals.totalPremium}
      />

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Categoria</TableHead>
              <TableHead>Titular</TableHead>
              <TableHead className="text-right">Capital</TableHead>
              <TableHead className="text-right">Prêmio/mês</TableHead>
              <TableHead>Vigência</TableHead>
              <TableHead>Seguradora</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Ações</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-sm text-muted-foreground py-8">
                  Nenhuma apólice corresponde aos filtros.
                </TableCell>
              </TableRow>
            ) : (
              filtered.map((p) => (
                <TableRow key={p.id} data-testid={`protection-row-${p.id}`}>
                  <TableCell>{categoryLabel(p.category)}</TableCell>
                  <TableCell>{memberLabel(members, p.holder_family_member_id)}</TableCell>
                  <TableCell className="text-right font-mono tabular-nums">
                    {formatBRLDecimalString(p.coverage_brl)}
                  </TableCell>
                  <TableCell className="text-right font-mono tabular-nums">
                    {formatBRLDecimalString(p.premium_monthly_brl)}
                  </TableCell>
                  <TableCell className="text-xs">
                    {p.starts_at}
                    {p.ends_at ? ` → ${p.ends_at}` : " → —"}
                  </TableCell>
                  <TableCell>
                    {p.insurer ?? "—"}
                    {p.policy_ref_masked && (
                      <button
                        type="button"
                        onClick={() => setRevealTarget(p)}
                        className="ml-2 inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                        aria-label="Mostrar número da apólice"
                      >
                        <Eye className="h-3 w-3" />
                        {p.policy_ref_masked}
                      </button>
                    )}
                  </TableCell>
                  <TableCell>
                    <Badge variant={statusVariant(p.status)}>{p.status}</Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    {p.status === "Ativa" && (
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={cancelingId === p.id}
                        onClick={() => handleCancel(p)}
                        aria-label="Cancelar apólice"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {revealTarget && (
        <RevealPolicyRefDialog
          open={!!revealTarget}
          onOpenChange={(open) => !open && setRevealTarget(null)}
          protectionId={revealTarget.id}
          workspaceId={workspaceId}
          policyRefMasked={revealTarget.policy_ref_masked}
        />
      )}
    </div>
  );
}

function Filters({
  statusFilter,
  categoryFilter,
  onStatus,
  onCategory,
}: {
  statusFilter: StatusFilter;
  categoryFilter: CategoryFilter;
  onStatus: (v: StatusFilter) => void;
  onCategory: (v: CategoryFilter) => void;
}) {
  return (
    <div className="flex flex-wrap gap-3">
      <div className="grid gap-1.5">
        <label className="text-xs font-medium text-muted-foreground">Status</label>
        <Select value={statusFilter} onValueChange={(v) => onStatus(v as StatusFilter)}>
          <SelectTrigger className="w-[140px]" data-testid="filter-status">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos</SelectItem>
            {PROTECTION_STATUSES.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid gap-1.5">
        <label className="text-xs font-medium text-muted-foreground">Categoria</label>
        <Select value={categoryFilter} onValueChange={(v) => onCategory(v as CategoryFilter)}>
          <SelectTrigger className="w-[180px]" data-testid="filter-category">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas</SelectItem>
            {PROTECTION_CATEGORIES.map((c) => (
              <SelectItem key={c.value} value={c.value}>
                {c.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}

function TotalsStrip({
  count,
  totalCoverage,
  totalPremium,
}: {
  count: number;
  totalCoverage: number;
  totalPremium: number;
}) {
  return (
    <div
      className="flex flex-wrap gap-6 rounded-md border bg-[var(--surface-muted)] p-4 text-sm"
      data-testid="protections-totals"
    >
      <span>
        <strong className="text-foreground">{count}</strong>{" "}
        <span className="text-muted-foreground">apólice(s) ativa(s)</span>
      </span>
      <span>
        <span className="text-muted-foreground">Cobertura total:</span>{" "}
        <strong className="font-mono tabular-nums">{formatBRLNoCents(totalCoverage)}</strong>
      </span>
      <span>
        <span className="text-muted-foreground">Prêmio mensal:</span>{" "}
        <strong className="font-mono tabular-nums">{formatBRLNoCents(totalPremium)}</strong>
      </span>
    </div>
  );
}
