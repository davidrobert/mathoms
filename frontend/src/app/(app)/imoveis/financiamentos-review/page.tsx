"use client";

/**
 * Batch review de Debts pendentes (ADR-227 §D6 · Sprint A15 Onda 5).
 *
 * Lista Debts com `needs_review=true` (originadas do backfill ADR-227
 * §D6) e permite atribuir property_id ou dispensar bulk. Pattern de
 * "fluxo de admin pós-migration" — não dialog modal.
 */

import { useCallback, useEffect, useState } from "react";

import { DebtList } from "@/components/debts/DebtList";
import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/PageHeader";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/Spinner";
import { useWorkspace } from "@/lib/WorkspaceProvider";
import { listDebts, updateDebt, type DebtResponse } from "@/lib/api/debts";
import { listProperties, type PropertyResponse } from "@/lib/api/properties";

interface PropertyOption {
  id: string;
  label: string;
}

function _propertyLabel(p: PropertyResponse): string {
  return p.descricao_sample ?? p.endereco_canonical ?? `Imóvel ${p.codigo_rfb}`;
}

async function _loadInitial(
  workspaceId: string,
): Promise<{ debts: DebtResponse[]; properties: PropertyOption[]; labels: Record<string, string> }> {
  const [debts, propsResp] = await Promise.all([
    listDebts(workspaceId, { needsReview: true }),
    listProperties(workspaceId),
  ]);
  const properties = propsResp.properties.map((p) => ({
    id: p.property_id,
    label: _propertyLabel(p),
  }));
  const labels = Object.fromEntries(properties.map((p) => [p.id, p.label]));
  return { debts, properties, labels };
}

export default function FinanciamentosReviewPage() {
  const { workspace } = useWorkspace();
  const [debts, setDebts] = useState<DebtResponse[]>([]);
  const [properties, setProperties] = useState<PropertyOption[]>([]);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!workspace) return;
    setLoading(true);
    try {
      const initial = await _loadInitial(workspace.id);
      setDebts(initial.debts);
      setProperties(initial.properties);
      setLabels(initial.labels);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [workspace]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleAssign = async (debtId: string, propertyId: string | null) => {
    if (!workspace) return;
    await updateDebt(workspace.id, debtId, {
      property_id: propertyId,
      needs_review: false,
    });
    await refresh();
  };

  const handleBulkSkip = async () => {
    if (!workspace) return;
    await Promise.all(
      debts.map((d) =>
        updateDebt(workspace.id, d.id, { needs_review: false, property_id: null }),
      ),
    );
    await refresh();
  };

  if (loading) return <Spinner />;
  if (error) {
    return (
      <p role="alert" style={{ color: "var(--semantic-danger)" }}>
        Erro ao carregar: {error}
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Revisão de financiamentos"
        description="Vincule cada dívida ao imóvel correspondente, ou dispense quando não houver vínculo."
      />
      {debts.length === 0 ? (
        <EmptyState
          title="Nenhuma revisão pendente"
          description="Todas as dívidas migradas já foram revisadas."
        />
      ) : (
        <>
          <div className="flex justify-end">
            <Button variant="outline" onClick={handleBulkSkip}>
              Marcar todas como sem vínculo
            </Button>
          </div>
          <DebtList
            debts={debts}
            propertyLabels={labels}
            renderActions={(debt) => (
              <DebtRowActions
                debt={debt}
                properties={properties}
                onAssign={(propertyId) => handleAssign(debt.id, propertyId)}
              />
            )}
          />
        </>
      )}
    </div>
  );
}

interface DebtRowActionsProps {
  debt: DebtResponse;
  properties: PropertyOption[];
  onAssign: (propertyId: string | null) => Promise<void>;
}

function DebtRowActions({ debt, properties, onAssign }: DebtRowActionsProps) {
  const [submitting, setSubmitting] = useState(false);
  const handleChange = async (value: string | null) => {
    setSubmitting(true);
    try {
      await onAssign(value === "__none__" ? null : value);
    } finally {
      setSubmitting(false);
    }
  };
  return (
    <Select
      value={debt.property_id ?? "__placeholder__"}
      onValueChange={handleChange}
      disabled={submitting}
    >
      <SelectTrigger className="w-48">
        <SelectValue placeholder="Atribuir imóvel" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="__none__">Sem vínculo (dispensar)</SelectItem>
        {properties.map((p) => (
          <SelectItem key={p.id} value={p.id}>
            {p.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
