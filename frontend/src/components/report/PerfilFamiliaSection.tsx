"use client";

import { useEffect, useState } from "react";

import {
  listMembers,
  listMyWorkspaces,
  type FamilyMemberConfig,
} from "@/lib/api";
import { ReportCard } from "./ReportCard";
import { ReportSection } from "./ReportSection";
import { CpfField } from "./ui/CpfField";

interface PerfilEntry {
  // Onda R2 (PD-01): o narrador emite `left`/`right` (2 colunas, HTML de parágrafos).
  left?: string;
  right?: string;
}

interface MemberRow {
  id: string;
  name: string;
  role: string;
  cpfMasked: string | null;
}

interface RosterState {
  rows: MemberRow[];
  isOwner: boolean;
}

// Vocabulário de exibição do cadastro (`config/_AddMemberForm.tsx`). Role fora
// do mapa fica sem rótulo — nunca afirmar vínculo que o dado não sustenta
// (o card antigo rotulava dependente com CPF como "Titular").
const ROLE_LABELS: Record<string, string> = {
  titular: "Titular",
  conjuge: "Cônjuge",
  filho: "Filho(a)",
  dependente: "Dependente",
};

/** Quebra o HTML de parágrafos (`<p>…</p>`) do narrador em texto, sem
 *  dangerouslySetInnerHTML (precedente zero-HTML-injection do relatório). */
function parseParagraphs(html?: string): string[] {
  if (!html) return [];
  return html
    .split(/<\/p>/i)
    .map((chunk) => chunk.replace(/<[^>]*>/g, "").trim())
    .filter(Boolean);
}

// `cpf_masked` já vem pronto de `GET /config/members` (ADR-259 §4) — sem
// N+1 de fetch por membro. Membro sem CPF não entra: o dado documental do
// roster é o par nome civil → CPF; o nome sozinho já vive na narrativa.
async function resolveRoster(workspaceId: string): Promise<RosterState> {
  const [{ members }, { workspaces }] = await Promise.all([
    listMembers(workspaceId),
    listMyWorkspaces(),
  ]);
  const rows = members
    .filter((m): m is FamilyMemberConfig & { id: string } =>
      Boolean(m.id && m.cpf_masked),
    )
    .sort((a, b) => a.order - b.order)
    .map((m) => ({
      id: m.id,
      name: m.full_name,
      role: m.role,
      cpfMasked: m.cpf_masked ?? null,
    }));
  const isOwner =
    workspaces.find((w) => w.id === workspaceId)?.role === "owner";
  return { rows, isOwner };
}

function useRoster(workspaceId: string): RosterState | null {
  const [roster, setRoster] = useState<RosterState | null>(null);

  useEffect(() => {
    let active = true;
    resolveRoster(workspaceId)
      .then((state) => {
        if (active) setRoster(state);
      })
      .catch(() => {
        // Falha do fetch não pode quebrar o relatório: degrada para só-narrativa.
        if (active) setRoster({ rows: [], isOwner: false });
      });
    return () => {
      active = false;
    };
  }, [workspaceId]);

  return roster;
}

interface PerfilFamiliaSectionProps {
  readonly narrativas: Record<string, unknown> | undefined;
  readonly workspaceId: string;
  readonly familySurname?: string | null;
}

/** Bloco de identidade da família — seção do shell (`id="perfil"`, padrão V0).
 *
 * Funde o antigo par PerfilFamiliaCard + TitularesCard (ADR-259 §4) num card
 * único: faixa documental (nome civil → CPF mascarado, ordenada por `order`,
 * com o `role` do cadastro por linha) sobre a narrativa em 2 colunas do E5.N.
 * Hide-when-empty por metade: só roster, só narrativa, ou `null` quando ambos
 * faltam — a seção nunca deixa vazio fantasma no ritmo do relatório.
 */
function RosterRow({
  row,
  workspaceId,
  canReveal,
}: {
  row: MemberRow;
  workspaceId: string;
  canReveal: boolean;
}) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
      <dt className="text-sm text-[var(--surface-foreground)]">
        {row.name}
        {ROLE_LABELS[row.role] && (
          <span className="ml-2 text-xs text-[var(--surface-muted-foreground)]">
            {ROLE_LABELS[row.role]}
          </span>
        )}
      </dt>
      <dd className="text-sm">
        <CpfField
          workspaceId={workspaceId}
          memberId={row.id}
          memberName={row.name}
          cpfMasked={row.cpfMasked}
          canReveal={canReveal}
        />
      </dd>
    </div>
  );
}

function RosterList({
  roster,
  workspaceId,
  hasNarrativa,
}: {
  roster: RosterState;
  workspaceId: string;
  hasNarrativa: boolean;
}) {
  const divisor = hasNarrativa
    ? " mb-5 border-b border-[var(--surface-border)] pb-5"
    : "";
  return (
    <dl className={`flex flex-col gap-2${divisor}`}>
      {roster.rows.map((row) => (
        <RosterRow
          key={row.id}
          row={row}
          workspaceId={workspaceId}
          canReveal={roster.isOwner}
        />
      ))}
    </dl>
  );
}

function NarrativaColunas({ colunas }: { colunas: string[][] }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 sm:gap-8">
      {colunas.map((coluna, i) =>
        coluna.length > 0 ? (
          <div key={i} className="flex flex-col gap-3">
            {coluna.map((paragrafo, j) => (
              <p
                key={j}
                className="text-sm leading-relaxed text-[var(--surface-foreground)]"
              >
                {paragrafo}
              </p>
            ))}
          </div>
        ) : null,
      )}
    </div>
  );
}

export function PerfilFamiliaSection({
  narrativas,
  workspaceId,
  familySurname,
}: PerfilFamiliaSectionProps) {
  const roster = useRoster(workspaceId);
  const perfil = narrativas?.["perfil_familia"] as PerfilEntry | undefined;
  const colunas = [
    parseParagraphs(perfil?.left),
    parseParagraphs(perfil?.right),
  ];
  const hasNarrativa = colunas.some((c) => c.length > 0);
  const hasRoster = (roster?.rows.length ?? 0) > 0;
  if (!hasNarrativa && !hasRoster) return null;

  const surname = familySurname?.trim();
  return (
    <ReportSection id="perfil">
      <ReportCard
        variant="primary"
        title={surname ? `A Família ${surname}` : "A Família"}
      >
        {roster && hasRoster && (
          <RosterList
            roster={roster}
            workspaceId={workspaceId}
            hasNarrativa={hasNarrativa}
          />
        )}
        {hasNarrativa && <NarrativaColunas colunas={colunas} />}
      </ReportCard>
    </ReportSection>
  );
}
