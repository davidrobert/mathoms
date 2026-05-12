import { ReportCard } from "../ReportCard";
import { MonetaryValue } from "../MonetaryValue";
import type { CardVariant } from "@/generated/report-layout";
import {
  parseDecimalString,
  type DedutivelCategoria,
  type DedutivelLinha,
  type PgblStatus,
} from "@/types/irpf";

interface IrpfDedutiveisAplicadosCardProps {
  dedutiveis: Partial<Record<DedutivelCategoria, DedutivelLinha>>;
  anoBase: number;
  /** ADR-194 §6.4 + ADR-198 — subtítulo, variante e chip variam por regime. */
  pgblStatus: PgblStatus;
  /** Variante default opcional; resolvida internamente por subutilização. */
  variantOverride?: CardVariant;
}

function resolveSubtitle(pgblStatus: PgblStatus, anoBase: number): string {
  const eligibleOnly =
    pgblStatus === "modelo_simplificado" || pgblStatus === "sem_renda_tributavel";
  const lead = eligibleOnly
    ? "Pagamentos elegíveis a dedução"
    : "Valores deduzidos do imposto";
  return `${lead} · ${anoBase}`;
}

const CATEGORIA_LABEL: Record<DedutivelCategoria, string> = {
  saude: "Saúde",
  educacao: "Educação",
  pensao_alimenticia: "Pensão alimentícia",
  previdencia_oficial: "Previdência oficial (INSS)",
};

const CATEGORIA_ORDEM: readonly DedutivelCategoria[] = [
  "saude",
  "educacao",
  "pensao_alimenticia",
  "previdencia_oficial",
];

function hasSubutilizacao(linha: DedutivelLinha): boolean {
  if (linha.teto_brl === null) return false;
  if (linha.teto_aplicado) return false;
  const utilizado = parseDecimalString(linha.utilizado_brl) ?? 0;
  const teto = parseDecimalString(linha.teto_brl) ?? 0;
  return utilizado < teto;
}

function semEfeitoFiscal(pgblStatus: PgblStatus): boolean {
  return (
    pgblStatus === "modelo_simplificado" ||
    pgblStatus === "sem_renda_tributavel"
  );
}

function resolveVariant(
  linhas: Array<[DedutivelCategoria, DedutivelLinha]>,
  pgblStatus: PgblStatus,
  override?: CardVariant,
): CardVariant {
  if (override) return override;
  if (semEfeitoFiscal(pgblStatus)) return "neutral";
  return linhas.some(([, l]) => hasSubutilizacao(l)) ? "info" : "neutral";
}

function buildLinhas(
  dedutiveis: Partial<Record<DedutivelCategoria, DedutivelLinha>>,
): Array<[DedutivelCategoria, DedutivelLinha]> {
  const out: Array<[DedutivelCategoria, DedutivelLinha]> = [];
  for (const key of CATEGORIA_ORDEM) {
    const linha = dedutiveis[key];
    if (!linha) continue;
    const utilizado = parseDecimalString(linha.utilizado_brl) ?? 0;
    if (utilizado > 0) out.push([key, linha]);
  }
  return out;
}

/** ADR-194 §6.2 + §6.4 + ADR-198 — Dedutíveis Aplicados por Categoria (factual, não-prescritivo).
 *
 * Lista vertical com barra de progresso para Educação (única categoria com teto
 * fixo nesta iteração). Variante condicional `info`/`neutral` resolvida por
 * presença de subutilização. Subtítulo condicional ao regime (§6.4):
 * simplificado/sem renda tributável usam "Pagamentos elegíveis a dedução";
 * completa usa "Valores deduzidos do imposto". Chip "Espaço de R$ X" também
 * é condicional ao regime (ADR-198): em simplificado/sem renda tributável
 * vira "Sem efeito neste regime" (neutral), sem implicar gap acionável.
 * Copy literal congelada por G0 em 2026-05-12. */
export function IrpfDedutiveisAplicadosCard({
  dedutiveis,
  anoBase,
  pgblStatus,
  variantOverride,
}: IrpfDedutiveisAplicadosCardProps) {
  const linhas = buildLinhas(dedutiveis);
  const variant = resolveVariant(linhas, pgblStatus, variantOverride);
  const subtitle = resolveSubtitle(pgblStatus, anoBase);

  return (
    <ReportCard
      variant={variant}
      size="full"
      title="Dedutíveis Aplicados por Categoria"
    >
      <div className="space-y-4">
        <p className="text-xs uppercase tracking-wide text-[var(--surface-muted-foreground)]">
          {subtitle}
        </p>

        <dl
          className="divide-y divide-[var(--surface-border)]"
          aria-label={`Dedutíveis aplicados em ${anoBase}`}
        >
          {linhas.map(([key, linha]) => (
            <DedutivelLinhaRow
              key={key}
              categoria={key}
              linha={linha}
              pgblStatus={pgblStatus}
            />
          ))}
        </dl>

        <p className="text-xs italic leading-relaxed text-[var(--surface-muted-foreground)]">
          Valores extraídos diretamente da declaração entregue à Receita. O
          &quot;limite RFB&quot; reflete o teto legal vigente em {anoBase} para
          a categoria; <strong>não é recomendação</strong> de incluir despesas
          adicionais — comprovantes precisam atender às regras de
          dedutibilidade (origem, vínculo com dependente, exclusividade do
          exercício).
        </p>
      </div>
    </ReportCard>
  );
}

function DedutivelLinhaRow({
  categoria,
  linha,
  pgblStatus,
}: {
  categoria: DedutivelCategoria;
  linha: DedutivelLinha;
  pgblStatus: PgblStatus;
}) {
  const utilizado = parseDecimalString(linha.utilizado_brl) ?? 0;
  const teto = linha.teto_brl !== null ? parseDecimalString(linha.teto_brl) ?? 0 : null;
  const label = CATEGORIA_LABEL[categoria];

  return (
    <div className="grid grid-cols-1 gap-2 py-3 md:grid-cols-[200px_1fr_auto] md:items-center">
      <dt className="font-medium text-[var(--surface-foreground)]">{label}</dt>
      <dd className="flex items-center gap-3">
        <span className="font-mono text-base font-semibold tabular-nums">
          <MonetaryValue value={utilizado} />
        </span>
        <DedutivelProgressBar
          categoria={categoria}
          utilizado={utilizado}
          teto={teto}
        />
      </dd>
      <DedutivelStatusChip
        linha={linha}
        utilizado={utilizado}
        teto={teto}
        pgblStatus={pgblStatus}
      />
    </div>
  );
}

function DedutivelProgressBar({
  categoria,
  utilizado,
  teto,
}: {
  categoria: DedutivelCategoria;
  utilizado: number;
  teto: number | null;
}) {
  if (teto === null || teto <= 0) return null;
  const pct = Math.min(100, Math.round((utilizado / teto) * 100));
  return (
    <div className="hidden flex-1 md:block">
      <progress
        value={utilizado}
        max={teto}
        className="h-2 w-full"
        aria-label={`${CATEGORIA_LABEL[categoria]}: ${pct}% do teto aplicado`}
      />
    </div>
  );
}

function DedutivelStatusChip({
  linha,
  utilizado,
  teto,
  pgblStatus,
}: {
  linha: DedutivelLinha;
  utilizado: number;
  teto: number | null;
  pgblStatus: PgblStatus;
}) {
  if (teto === null) {
    return (
      <span className="rounded-full bg-[var(--surface-muted)] px-3 py-1 text-xs font-medium text-[var(--surface-muted-foreground)]">
        Sem teto legal
      </span>
    );
  }
  if (linha.teto_aplicado || utilizado >= teto) {
    return (
      <span className="rounded-full bg-[var(--surface-muted)] px-3 py-1 text-xs font-medium text-[var(--surface-muted-foreground)]">
        No teto
      </span>
    );
  }
  // ADR-198 — em simplificado/sem renda tributável, "Espaço de R$ X"
  // implica gap acionável de IR que não existe nesse regime.
  if (semEfeitoFiscal(pgblStatus)) {
    return (
      <span className="rounded-full bg-[var(--surface-muted)] px-3 py-1 text-xs font-medium text-[var(--surface-muted-foreground)]">
        Sem efeito neste regime
      </span>
    );
  }
  const espaco = teto - utilizado;
  return (
    <span className="rounded-full border border-[var(--brand-info)] px-3 py-1 text-xs font-medium text-[var(--brand-info)]">
      Espaço de <MonetaryValue value={espaco} />
    </span>
  );
}
