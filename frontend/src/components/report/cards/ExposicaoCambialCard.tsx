"use client";

import { useState } from "react";

import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import { LastroDeclareDropdown } from "./LastroDeclareDropdown";
import { useExposicaoCambialV2 } from "@/hooks/useExposicaoCambialV2";
import type {
  ExposicaoCambialAtivo,
  LastroMoeda,
  LastroSource,
  MatchKind,
} from "@/lib/api/exposicaoCambial";
import type { ExposicaoCambialData } from "@/types/report-analysis";

interface ExposicaoCambialCardProps {
  /** V1 data (E5 payload) — usado como instant render enquanto V2 carrega. */
  data: ExposicaoCambialData | undefined;
  /** Quando presente, dispara fetch V2 + override UI (ADR-224 PR-E). */
  workspaceId?: string | null;
}

const TIER_LABEL: Record<string, string> = {
  verde: "adequado",
  amarelo: "abaixo do recomendado",
  vermelho: "sub-alocado",
  empty: "sem exposição",
};

const TIER_BADGE_CLASS: Record<string, string> = {
  verde: "bg-[var(--semantic-success)]/15 text-[var(--semantic-success)]",
  amarelo: "bg-[var(--semantic-warning)]/15 text-[var(--semantic-warning)]",
  vermelho: "bg-[var(--semantic-danger)]/15 text-[var(--semantic-danger)]",
  empty: "bg-[var(--surface-muted)] text-[var(--surface-muted-foreground)]",
};

const LASTRO_SOURCE_LABEL: Record<LastroSource, string> = {
  override: "você declarou",
  catalog: "catálogo Mathoms",
  fallback_classe: "lastro não declarado",
};

const LASTRO_SOURCE_CLASS: Record<LastroSource, string> = {
  override: "bg-[var(--brand-accent)]/15 text-[var(--brand-accent)]",
  catalog: "bg-[var(--surface-muted)] text-[var(--surface-muted-foreground)]",
  fallback_classe: "bg-[var(--semantic-warning)]/15 text-[var(--semantic-warning)]",
};

/** Bloco G + ADR-224 PR-E — Card "Exposição Cambial" com fetch V2 + declare lastro inline.
 *
 * Renderiza patrimônio com lastro em moeda estrangeira (caixa USD/EUR + ativos com lastro
 * USD via asset_catalog). Threshold (financial-planner): verde ≥10% · amarelo 5-10% ·
 * vermelho <5%. Denominador: `investivel_financeiro` (Cerbasi/AUVP).
 *
 * Quando `workspaceId` presente, fetch V2 via `useExposicaoCambialV2` substitui o
 * payload V1 (E5) e expõe botão "Declarar lastro" inline por ativo.
 */
export function ExposicaoCambialCard({ data, workspaceId }: ExposicaoCambialCardProps) {
  const v2 = useExposicaoCambialV2(workspaceId ?? null);

  // V2 carregou → usa V2; ainda carregando ou sem workspaceId → fallback V1 (instant render).
  if (workspaceId && v2.data) {
    return <ExposicaoCambialCardV2 v2={v2} />;
  }
  if (!data) return null;
  return <ExposicaoCambialCardV1 data={data} />;
}

function ExposicaoCambialCardV1({ data }: { data: ExposicaoCambialData }) {
  const tier = data.tier;
  const badgeText =
    tier === "empty"
      ? "0% sem exposição"
      : `${data.pct_investivel_financeiro.toFixed(1)}% · ${TIER_LABEL[tier] ?? tier}`;
  return (
    <ReportCard variant="feature" title="Exposição Cambial">
      <div className="space-y-4">
        <CardHeader badgeText={badgeText} tier={tier} />
        {tier === "empty" ? (
          <EmptyExposicaoMessage />
        ) : (
          <>
            <TotalDisplay totalBrl={data.total_brl} />
            <PorMoedaTableV1 rows={data.por_moeda} />
          </>
        )}
        <Footnote />
      </div>
    </ReportCard>
  );
}

function ExposicaoCambialCardV2({
  v2,
}: {
  v2: ReturnType<typeof useExposicaoCambialV2>;
}) {
  const tier = v2.data?.tier ?? "empty";
  const pct = v2.data?.pct_investivel_financeiro ?? 0;
  const badgeText =
    tier === "empty" ? "0% sem exposição" : `${pct.toFixed(1)}% · ${TIER_LABEL[tier] ?? tier}`;
  return (
    <ReportCard variant="feature" title="Exposição Cambial">
      <div className="space-y-4">
        <CardHeader badgeText={badgeText} tier={tier} />
        {tier === "empty" ? (
          <EmptyExposicaoMessage />
        ) : (
          <>
            <TotalDisplay totalBrl={parseFloat(v2.data?.total_brl ?? "0")} />
            <PorMoedaTableV2 rows={v2.data?.por_moeda ?? []} />
            <AtivosContribuintes
              ativos={v2.data?.ativos_contribuintes ?? []}
              onDeclare={(m, k, l) =>
                v2.declare({ match_kind: m, asset_match_key: k, lastro_moeda: l })
              }
            />
          </>
        )}
        <Footnote />
      </div>
    </ReportCard>
  );
}

function CardHeader({ badgeText, tier }: { badgeText: string; tier: string }) {
  return (
    <header className="flex items-start justify-between gap-4">
      <p className="text-sm text-[var(--surface-muted-foreground)]">
        Patrimônio protegido contra desvalorização do real.
      </p>
      <span
        className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${
          TIER_BADGE_CLASS[tier] ?? TIER_BADGE_CLASS.empty
        }`}
      >
        {badgeText}
      </span>
    </header>
  );
}

function EmptyExposicaoMessage() {
  return (
    <p className="text-sm text-[var(--surface-muted-foreground)]">
      Seu patrimônio está 100% denominado em real. Diversificação cambial reduz risco de
      perda de poder de compra em cenários de desvalorização do real.
    </p>
  );
}

function TotalDisplay({ totalBrl }: { totalBrl: number }) {
  return (
    <div>
      <div className="font-mono text-3xl font-bold tabular-nums">
        <MonetaryValue value={totalBrl} />
      </div>
      <div className="text-sm text-[var(--surface-muted-foreground)]">
        do patrimônio investível financeiro
      </div>
    </div>
  );
}

function PorMoedaTableV1({
  rows,
}: {
  rows: ExposicaoCambialData["por_moeda"];
}) {
  if (rows.length === 0) return null;
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-[var(--surface-border)] text-left">
          <th scope="col" className="pb-2 font-display font-semibold">Moeda</th>
          <th scope="col" className="pb-2 text-right font-display font-semibold">Equiv. BRL</th>
          <th scope="col" className="pb-2 text-right font-display font-semibold">%</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr
            key={row.moeda}
            className="border-b border-[var(--surface-border)]/40 last:border-0"
          >
            <td className="py-2">{row.moeda}</td>
            <td className="py-2 text-right">
              <MonetaryValue value={row.valor_brl} />
            </td>
            <td className="py-2 text-right font-mono tabular-nums text-[var(--surface-muted-foreground)]">
              {row.pct_total_cambial.toFixed(1)}%
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function PorMoedaTableV2({
  rows,
}: {
  rows: Array<{ moeda: string; valor_brl: string; share_pct: number }>;
}) {
  if (rows.length === 0) return null;
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="border-b border-[var(--surface-border)] text-left">
          <th scope="col" className="pb-2 font-display font-semibold">Moeda</th>
          <th scope="col" className="pb-2 text-right font-display font-semibold">Equiv. BRL</th>
          <th scope="col" className="pb-2 text-right font-display font-semibold">%</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr
            key={row.moeda}
            className="border-b border-[var(--surface-border)]/40 last:border-0"
          >
            <td className="py-2">{row.moeda}</td>
            <td className="py-2 text-right">
              <MonetaryValue value={parseFloat(row.valor_brl)} />
            </td>
            <td className="py-2 text-right font-mono tabular-nums text-[var(--surface-muted-foreground)]">
              {row.share_pct.toFixed(1)}%
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function AtivosContribuintes({
  ativos,
  onDeclare,
}: {
  ativos: ExposicaoCambialAtivo[];
  onDeclare: (kind: MatchKind, key: string, lastro: LastroMoeda) => Promise<unknown>;
}) {
  const [editingKey, setEditingKey] = useState<string | null>(null);
  if (ativos.length === 0) return null;
  return (
    <section aria-label="Ativos que compõem a exposição cambial">
      <h3 className="mb-2 font-display text-sm font-semibold">Ativos contribuintes</h3>
      <ul className="space-y-2">
        {ativos.map((ativo) => (
          <li
            key={`${ativo.tipo}:${ativo.nome}`}
            className="rounded border border-[var(--surface-border)]/40 p-2"
          >
            <AtivoRow
              ativo={ativo}
              isEditing={editingKey === ativo.nome}
              onStartEdit={() => setEditingKey(ativo.nome)}
              onCancel={() => setEditingKey(null)}
              onDeclare={async (lastro) => {
                await onDeclare(_inferMatchKind(ativo), ativo.nome, lastro);
                setEditingKey(null);
              }}
            />
          </li>
        ))}
      </ul>
    </section>
  );
}

function AtivoRow({
  ativo,
  isEditing,
  onStartEdit,
  onCancel,
  onDeclare,
}: {
  ativo: ExposicaoCambialAtivo;
  isEditing: boolean;
  onStartEdit: () => void;
  onCancel: () => void;
  onDeclare: (lastro: LastroMoeda) => Promise<void>;
}) {
  if (isEditing) {
    return (
      <LastroDeclareDropdown
        ativoNome={ativo.nome}
        matchKind={_inferMatchKind(ativo)}
        assetMatchKey={ativo.nome}
        currentLastro={ativo.moeda as LastroMoeda}
        onDeclare={onDeclare}
        onCancel={onCancel}
      />
    );
  }
  return (
    <div className="flex items-center justify-between gap-2 text-sm">
      <div className="min-w-0 flex-1">
        <div className="truncate font-medium">{ativo.nome}</div>
        <div className="flex items-center gap-2 text-xs">
          <span
            className={`rounded-full px-1.5 py-0.5 ${LASTRO_SOURCE_CLASS[ativo.lastro_source]}`}
          >
            {LASTRO_SOURCE_LABEL[ativo.lastro_source]}
          </span>
          <span className="font-mono text-[var(--surface-muted-foreground)]">
            {ativo.moeda}
          </span>
        </div>
      </div>
      <div className="text-right">
        <div className="font-mono tabular-nums">
          <MonetaryValue value={parseFloat(ativo.valor_brl)} />
        </div>
        <button
          type="button"
          className="text-xs text-[var(--brand-primary)] hover:underline"
          onClick={onStartEdit}
        >
          Declarar lastro
        </button>
      </div>
    </div>
  );
}

function _inferMatchKind(ativo: ExposicaoCambialAtivo): MatchKind {
  // Heurística: nomes curtos ALL-CAPS são tickers; CNPJ tem 14 dígitos; resto é descrição.
  const nome = ativo.nome.trim();
  if (/^[A-Z0-9]{4,6}$/.test(nome)) return "ticker";
  if (/^\d{14}$/.test(nome.replace(/\D/g, ""))) return "cnpj";
  return "description";
}

function Footnote() {
  return (
    <p className="text-xs text-[var(--surface-muted-foreground)]">
      Considera caixa em moeda forte (USD, EUR) + ativos com lastro econômico não-BRL.
      Sugestão de alocação contracíclica: ≥10% em moeda forte como proteção de poder de
      compra.
    </p>
  );
}
