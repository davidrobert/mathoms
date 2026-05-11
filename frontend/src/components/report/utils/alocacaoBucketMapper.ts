/**
 * Agrega `investimentos.tabela_classes` (10 buckets canônicos ADR-193)
 * em 4 buckets do alvo v1 + computa desvio em pp por classe.
 *
 * Fase A é client-side (v1 não tem `derived.desvio_por_classe`); v2 AUVP
 * (ADR-141) move o cálculo para o backend e este util será removido.
 *
 * Decisões de mapeamento (validadas com financial-planner 2026-05-11):
 *   - Caixa fora do denominador (reserva ≠ investimento).
 *   - Cripto, Outros → "fora do alvo" (alvo=0).
 *   - Previdência → Renda Fixa; Fundos → Ações; Internacional → USD.
 *   - v2 AUVP segrega cada aproximação.
 */

export type AlvoBucketId = "renda_fixa" | "acoes" | "imoveis_reits" | "liquidez_usd";

export type SeverityLevel = "alinhado" | "atencao" | "rebalancear" | "neutro";
export type BadgeSeverity = "alinhado" | "atencao" | "rebalancear" | "sem_alvo";

export interface ClasseAtivoRow {
  categoria: string;
  valor: number;
  pct: number;
}

export interface AlocacaoAlvoV1 {
  renda_fixa_pct?: number | null;
  acoes_pct?: number | null;
  imoveis_reits_pct?: number | null;
  liquidez_usd_pct?: number | null;
}

export interface BucketRow {
  id: AlvoBucketId | "caixa" | "fora_alvo";
  label: string;
  valor: number;
  atual_pct: number;
  alvo_pct: number | null;
  desvio_pp: number | null;
  severity: SeverityLevel;
  subItems?: string[];
}

export interface AlocacaoSummary {
  total: number;
  total_investivel: number;
  reserva_caixa_valor: number;
  buckets: BucketRow[];
  max_abs_desvio_pp: number;
  badge: { severity: BadgeSeverity; label: string };
  hasAlvo: boolean;
  nextAporteBucket: AlvoBucketId | null;
}

const ALVO_LABELS: Record<AlvoBucketId, string> = {
  renda_fixa: "Renda Fixa",
  acoes: "Ações",
  imoveis_reits: "Imóveis / FIIs",
  liquidez_usd: "USD / Internacional",
};

const FORA_DO_ALVO: ReadonlySet<string> = new Set(["Cripto", "Outros"]);

function severityFor(absDesvio: number): SeverityLevel {
  if (absDesvio <= 2) return "alinhado";
  if (absDesvio <= 5) return "atencao";
  return "rebalancear";
}

function mapToBucket(
  categoria: string,
): AlvoBucketId | "caixa" | "fora_alvo" | null {
  if (categoria === "Caixa") return "caixa";
  if (FORA_DO_ALVO.has(categoria)) return "fora_alvo";
  if (categoria === "Renda Fixa" || categoria === "Previdência") return "renda_fixa";
  if (categoria === "Ações BR" || categoria === "Fundos") return "acoes";
  if (categoria === "FIIs" || categoria === "Imóveis Investimento") return "imoveis_reits";
  if (categoria === "Internacional") return "liquidez_usd";
  return null;
}

interface Accumulator {
  valor: number;
  contribuintes: Set<string>;
}

interface Aggregated {
  buckets: Record<AlvoBucketId, Accumulator>;
  caixa: number;
  fora: Accumulator;
}

function emptyAcc(): Accumulator {
  return { valor: 0, contribuintes: new Set() };
}

function emptyAggregated(): Aggregated {
  return {
    buckets: {
      renda_fixa: emptyAcc(),
      acoes: emptyAcc(),
      imoveis_reits: emptyAcc(),
      liquidez_usd: emptyAcc(),
    },
    caixa: 0,
    fora: emptyAcc(),
  };
}

function ingestRow(agg: Aggregated, row: ClasseAtivoRow): void {
  const valor = row.valor ?? 0;
  if (valor <= 0) return;
  const target = mapToBucket(row.categoria);
  if (target === null) return;
  if (target === "caixa") {
    agg.caixa += valor;
    return;
  }
  if (target === "fora_alvo") {
    agg.fora.valor += valor;
    agg.fora.contribuintes.add(row.categoria);
    return;
  }
  agg.buckets[target].valor += valor;
  agg.buckets[target].contribuintes.add(row.categoria);
}

function accumulate(rows: readonly ClasseAtivoRow[]): Aggregated {
  const agg = emptyAggregated();
  for (const r of rows) ingestRow(agg, r);
  return agg;
}

function extractAlvoValues(
  alvo: AlocacaoAlvoV1 | undefined,
): Record<AlvoBucketId, number | null> {
  const pick = (v: number | null | undefined): number | null =>
    typeof v === "number" ? v : null;
  return {
    renda_fixa: pick(alvo?.renda_fixa_pct),
    acoes: pick(alvo?.acoes_pct),
    imoveis_reits: pick(alvo?.imoveis_reits_pct),
    liquidez_usd: pick(alvo?.liquidez_usd_pct),
  };
}

function buildAlvoBucketRow(
  id: AlvoBucketId,
  acc: Accumulator,
  alvoPct: number | null,
  investivel: number,
): BucketRow {
  const atualPct = investivel > 0 ? (acc.valor / investivel) * 100 : 0;
  const desvio = alvoPct === null ? null : atualPct - alvoPct;
  return {
    id,
    label: ALVO_LABELS[id],
    valor: acc.valor,
    atual_pct: atualPct,
    alvo_pct: alvoPct,
    desvio_pp: desvio,
    severity: desvio === null ? "neutro" : severityFor(Math.abs(desvio)),
    subItems: Array.from(acc.contribuintes),
  };
}

function buildAlvoBucketRows(
  agg: Aggregated,
  alvoValues: Record<AlvoBucketId, number | null>,
  investivel: number,
): BucketRow[] {
  const rows = (Object.keys(agg.buckets) as AlvoBucketId[]).map((id) =>
    buildAlvoBucketRow(id, agg.buckets[id], alvoValues[id], investivel),
  );
  rows.sort((a, b) => {
    const da = a.desvio_pp === null ? -Infinity : Math.abs(a.desvio_pp);
    const db = b.desvio_pp === null ? -Infinity : Math.abs(b.desvio_pp);
    return db - da;
  });
  return rows;
}

function buildForaRow(
  fora: Accumulator,
  investivel: number,
  hasAlvo: boolean,
): BucketRow {
  const atualPct = investivel > 0 ? (fora.valor / investivel) * 100 : 0;
  return {
    id: "fora_alvo",
    label: "Fora do alvo",
    valor: fora.valor,
    atual_pct: atualPct,
    alvo_pct: hasAlvo ? 0 : null,
    desvio_pp: hasAlvo ? atualPct : null,
    severity: hasAlvo ? severityFor(Math.abs(atualPct)) : "neutro",
    subItems: Array.from(fora.contribuintes),
  };
}

function buildCaixaRow(caixa: number, total: number): BucketRow {
  const atualPct = total > 0 ? (caixa / total) * 100 : 0;
  return {
    id: "caixa",
    label: "Reserva (Caixa)",
    valor: caixa,
    atual_pct: atualPct,
    alvo_pct: null,
    desvio_pp: null,
    severity: "neutro",
    subItems: ["Caixa"],
  };
}

function computeBadge(
  hasAlvo: boolean,
  buckets: readonly BucketRow[],
): AlocacaoSummary["badge"] {
  if (!hasAlvo) return { severity: "sem_alvo", label: "Sem alvo definido" };
  const counts = {
    rebalancear: buckets.filter((r) => r.severity === "rebalancear").length,
    atencao: buckets.filter((r) => r.severity === "atencao").length,
  };
  if (counts.rebalancear > 0) {
    return {
      severity: "rebalancear",
      label: pluralLabel("Rebalancear", counts.rebalancear),
    };
  }
  if (counts.atencao > 0) {
    return { severity: "atencao", label: pluralLabel("Atenção", counts.atencao) };
  }
  return { severity: "alinhado", label: "Carteira alinhada" };
}

function pluralLabel(prefix: string, n: number): string {
  return n === 1 ? `${prefix}: 1 classe` : `${prefix}: ${n} classes`;
}

function pickNextAporte(rows: readonly BucketRow[]): AlvoBucketId | null {
  const subalocados = rows.filter(
    (r): r is BucketRow & { desvio_pp: number; id: AlvoBucketId } =>
      r.desvio_pp !== null &&
      r.desvio_pp < 0 &&
      r.id !== "caixa" &&
      r.id !== "fora_alvo",
  );
  if (subalocados.length === 0) return null;
  return subalocados.reduce((min, cur) => (cur.desvio_pp < min.desvio_pp ? cur : min))
    .id;
}

function hasAnyAlvo(values: Record<AlvoBucketId, number | null>): boolean {
  return Object.values(values).some((v) => v !== null);
}

function resolveTotal(rows: readonly ClasseAtivoRow[], total: number): number {
  if (total > 0) return total;
  return rows.reduce((s, r) => s + (r.valor ?? 0), 0);
}

function collectExtras(
  agg: Aggregated,
  investivel: number,
  safeTotal: number,
  hasAlvo: boolean,
): BucketRow[] {
  const out: BucketRow[] = [];
  if (agg.fora.valor > 0) out.push(buildForaRow(agg.fora, investivel, hasAlvo));
  if (agg.caixa > 0) out.push(buildCaixaRow(agg.caixa, safeTotal));
  return out;
}

function maxAbsDesvio(buckets: readonly BucketRow[]): number {
  return buckets.reduce(
    (m, r) => (r.desvio_pp === null ? m : Math.max(m, Math.abs(r.desvio_pp))),
    0,
  );
}

function summaryFrom(
  agg: Aggregated,
  alvoRows: BucketRow[],
  hasAlvo: boolean,
  safeTotal: number,
  investivel: number,
): AlocacaoSummary {
  const buckets = [...alvoRows, ...collectExtras(agg, investivel, safeTotal, hasAlvo)];
  return {
    total: safeTotal,
    total_investivel: investivel,
    reserva_caixa_valor: agg.caixa,
    buckets,
    max_abs_desvio_pp: maxAbsDesvio(buckets),
    badge: computeBadge(hasAlvo, buckets),
    hasAlvo,
    nextAporteBucket: pickNextAporte(alvoRows),
  };
}

export function aggregateAlocacao(
  rows: readonly ClasseAtivoRow[] | undefined,
  alvo: AlocacaoAlvoV1 | undefined,
  total: number,
): AlocacaoSummary {
  const safeRows = rows ?? [];
  const safeTotal = resolveTotal(safeRows, total);
  const agg = accumulate(safeRows);
  const investivel = Math.max(0, safeTotal - agg.caixa);
  const alvoValues = extractAlvoValues(alvo);
  const hasAlvo = hasAnyAlvo(alvoValues);
  const alvoRows = buildAlvoBucketRows(agg, alvoValues, investivel);
  return summaryFrom(agg, alvoRows, hasAlvo, safeTotal, investivel);
}

export function bucketLabel(id: AlvoBucketId): string {
  return ALVO_LABELS[id];
}
