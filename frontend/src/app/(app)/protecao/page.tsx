"use client";

/**
 * /protecao — cadastro e listagem de apólices (ADR-192 · S9-T05).
 *
 * UX decision (gate triplo · product-designer): página dedicada (vs.
 * tab em /plano) — 6 categorias × N apólices é escopo suficiente para
 * uma surface dedicada; tab em /plano somaria carga cognitiva à home
 * única (ADR-155).
 *
 * Componentes:
 * - `ProtectionFormDialog` — modal de cadastro.
 * - `ProtectionList` — tabela + filtros + cancelar.
 * - `InferredRisksCard` — auto-inferência do bundle, 1-click → Risk.
 *
 * Coordenação T04: este arquivo NÃO toca `S9RiscosSection.tsx` nem
 * `AcoesMitigacaoCard.tsx`. O hook `useAcceptInferredRisk` é
 * standalone e pode ser hookado em S9 via prop callback no merge de T04.
 */

import { useEffect, useState } from "react";
import { Plus, ShieldCheck } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useProtections } from "@/hooks/useProtections";
import {
  type FamilyMemberConfig,
  getProtectionBundle,
  listMembers,
  type ProtectionBundle,
} from "@/lib/api";
import { useWorkspace } from "@/lib/WorkspaceProvider";

import { InferredRisksCard } from "./_components/InferredRisksCard";
import { ProtectionFormDialog } from "./_components/ProtectionFormDialog";
import { ProtectionList } from "./_components/ProtectionList";

export default function ProtecaoPage() {
  const { workspace, isLoading: wsLoading } = useWorkspace();
  const workspaceId = workspace?.id;
  const { protections, loading, error, create, cancel } = useProtections(workspaceId);
  const [members, setMembers] = useState<FamilyMemberConfig[]>([]);
  const [bundle, setBundle] = useState<ProtectionBundle | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    if (!workspaceId) return;
    listMembers(workspaceId)
      .then((r) => setMembers(r.members))
      .catch(() => setMembers([]));
    getProtectionBundle(workspaceId)
      .then((b) => setBundle(b))
      .catch(() => setBundle(null));
  }, [workspaceId]);

  if (wsLoading) {
    return <LoadingState />;
  }
  if (!workspace || !workspaceId) {
    return <NoWorkspaceState />;
  }

  return (
    <div className="mx-auto max-w-content px-6 py-8">
      <PageHeader
        title="Proteção"
        description="Apólices contratadas, cobertura por categoria e ações de mitigação."
        actions={
          <Button onClick={() => setDialogOpen(true)} data-testid="add-protection">
            <Plus className="mr-1 h-4 w-4" />
            Cadastrar apólice
          </Button>
        }
      />

      {error && (
        <div
          role="alert"
          className="mb-4 rounded-md border border-[var(--semantic-danger)] bg-[color-mix(in_srgb,var(--semantic-danger)_8%,transparent)] px-4 py-3 text-sm text-[var(--semantic-danger)]"
        >
          {error}
        </div>
      )}

      <div className="space-y-6">
        {bundle && bundle.auto_inferred_risks.length > 0 && (
          <InferredRisksCard
            workspaceId={workspaceId}
            inferred={bundle.auto_inferred_risks}
          />
        )}

        {loading ? (
          <Skeleton className="h-64 w-full" />
        ) : protections.length === 0 ? (
          <EmptyState
            icon={ShieldCheck}
            title="Sem apólices cadastradas"
            description="Cadastre a primeira apólice para acompanhar a cobertura por categoria e detectar gaps de proteção."
            action={{
              label: "Cadastrar primeira apólice",
              onClick: () => setDialogOpen(true),
            }}
          />
        ) : (
          <ProtectionList
            protections={protections}
            workspaceId={workspaceId}
            members={members}
            onCancel={async (id) => {
              await cancel(id);
            }}
          />
        )}

        <p className="text-xs text-muted-foreground italic">
          Estimativa baseada em padrões consagrados de planejamento
          patrimonial brasileiro; não constitui recomendação fiduciária.
          Consultar corretor habilitado para contratação.
        </p>
      </div>

      <ProtectionFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        members={members}
        onCreate={create}
      />
    </div>
  );
}

function LoadingState() {
  return (
    <div className="mx-auto max-w-content px-6 py-8">
      <PageHeader title="Proteção" description="Carregando..." />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}

function NoWorkspaceState() {
  return (
    <div className="mx-auto max-w-content px-6 py-8">
      <PageHeader
        title="Proteção"
        description="Selecione um workspace para continuar."
      />
    </div>
  );
}
