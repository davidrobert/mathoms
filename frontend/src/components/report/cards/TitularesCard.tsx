"use client";

import { useEffect, useState } from "react";

import { listMembers, listMyWorkspaces, type FamilyMemberConfig } from "@/lib/api";
import { ReportCard } from "../ReportCard";
import { CpfField } from "../ui/CpfField";

interface MemberRow {
  id: string;
  name: string;
  cpfMasked: string | null;
}

async function resolveIsOwner(workspaceId: string): Promise<boolean> {
  const { workspaces } = await listMyWorkspaces();
  return workspaces.find((w) => w.id === workspaceId)?.role === "owner";
}

async function resolveMemberRows(workspaceId: string): Promise<MemberRow[]> {
  // `cpf_masked` já vem pronto de `GET /config/members` (ADR-259 §4) — sem
  // N+1 de fetch por membro.
  const { members } = await listMembers(workspaceId);
  const withCpf = members.filter(
    (m): m is FamilyMemberConfig & { id: string } => Boolean(m.id && m.cpf_masked),
  );
  return withCpf.map((m) => ({ id: m.id, name: m.full_name, cpfMasked: m.cpf_masked ?? null }));
}

/** ADR-259 §4 — identificação dos titulares no topo do relatório: nome +
 * CPF mascarado (reveal owner-only via `CpfField`). Renderiza nada se não
 * houver membro com CPF cadastrado ou se a busca falhar — a seção nunca
 * quebra o relatório. */
export function TitularesCard({ workspaceId }: { readonly workspaceId: string }) {
  const [rows, setRows] = useState<MemberRow[] | null>(null);
  const [isOwner, setIsOwner] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([resolveMemberRows(workspaceId), resolveIsOwner(workspaceId)])
      .then(([memberRows, owner]) => {
        if (!active) return;
        setRows(memberRows);
        setIsOwner(owner);
      })
      .catch(() => {
        if (active) setRows([]);
      });
    return () => {
      active = false;
    };
  }, [workspaceId]);

  if (!rows || rows.length === 0) return null;

  return (
    <ReportCard variant="neutral" title="Titulares">
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {rows.map((row) => (
          <div key={row.id} style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
            <span>{row.name}</span>
            <CpfField
              workspaceId={workspaceId}
              memberId={row.id}
              memberName={row.name}
              cpfMasked={row.cpfMasked}
              canReveal={isOwner}
            />
          </div>
        ))}
      </div>
    </ReportCard>
  );
}
