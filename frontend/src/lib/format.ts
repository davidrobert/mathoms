import type { DocumentStatus, DocumentType, PipelineStageStatus, PipelineRunStatus } from "./api";

// ─── Number Formatting ───

const BRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const USD = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
const PCT_ABS = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const COMPACT_BRL = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  notation: "compact",
  maximumFractionDigits: 1,
});

export function formatCurrency(value: number, currency: "BRL" | "USD" = "BRL"): string {
  return currency === "USD" ? USD.format(value) : BRL.format(value);
}

// ADR-209: pct fields são absolutos (44.7 = 44,7%). Formatters NÃO multiplicam.
export function formatPercent(value: number, decimals = 1): string {
  if (decimals !== 1) {
    return `${new Intl.NumberFormat("pt-BR", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value)}%`;
  }
  return `${PCT_ABS.format(value)}%`;
}

export function formatDelta(
  value: number,
  opts?: { percent?: number; currency?: "BRL" | "USD"; invert?: boolean }
): string {
  const formatted = formatCurrency(value, opts?.currency);
  let result = value >= 0 ? `+${formatted}` : formatted;
  if (opts?.percent != null) {
    const pctSign = opts.percent >= 0 ? "+" : "";
    result += ` (${pctSign}${formatPercent(opts.percent)})`;
  }
  return result;
}

export function formatCompact(value: number): string {
  return COMPACT_BRL.format(value);
}

export function formatNumber(value: number, decimals = 0): string {
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

// ─── Byte / Duration Formatting ───

export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
}

// ─── Date Formatting ───

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatDateShort(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR");
}

const MONTH_SHORT = new Intl.DateTimeFormat("pt-BR", { month: "short" });
const MONTH_LONG = new Intl.DateTimeFormat("pt-BR", { month: "long" });

const MONTH_SHORT_PT = [
  "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
  "Jul", "Ago", "Set", "Out", "Nov", "Dez",
];

/** Valor BRL completo com centavos — útil em tooltip quando exibição é compact. */
export function formatFullBRL(value: number): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

const MONTH_SHORT_PT_LOWER = [
  "jan", "fev", "mar", "abr", "mai", "jun",
  "jul", "ago", "set", "out", "nov", "dez",
];

/** v2.F.3b — período no cover do relatório.
 *
 * "2023-01 a 2026-04" → "jan 2023 — abr 2026" (em-dash U+2014).
 * Single-period "2026-04" → "abr 2026". Falha graciosamente: retorna o
 * input cru se o formato não casar.
 */
export function formatPeriodCoverPtBR(periodo: string | null | undefined): string {
  if (!periodo) return "—";
  const fmt = (p: string): string | null => {
    const [y, m] = p.trim().split("-");
    const mi = parseInt(m, 10);
    if (!y || isNaN(mi) || mi < 1 || mi > 12) return null;
    return `${MONTH_SHORT_PT_LOWER[mi - 1]} ${y}`;
  };
  const parts = periodo.split(" a ");
  if (parts.length === 2) {
    const a = fmt(parts[0]);
    const b = fmt(parts[1]);
    if (a && b) return `${a} — ${b}`;
  }
  if (parts.length === 1) {
    const a = fmt(parts[0]);
    if (a) return a;
  }
  return periodo;
}

/** "2023-01 a 2026-04" → "Jan 2023 → Abr 2026". Retorna input se não reconhecer. */
export function formatPeriodRange(periodo: string | null | undefined): string {
  if (!periodo) return "—";
  const parts = String(periodo).split(" a ");
  const fmt = (p: string) => {
    const [y, m] = p.trim().split("-");
    const mi = parseInt(m, 10);
    if (!y || isNaN(mi) || mi < 1 || mi > 12) return null;
    return `${MONTH_SHORT_PT[mi - 1]} ${y}`;
  };
  if (parts.length === 2) {
    const a = fmt(parts[0]);
    const b = fmt(parts[1]);
    if (a && b) return `${a} → ${b}`;
  }
  if (parts.length === 1) {
    const a = fmt(parts[0]);
    if (a) return a;
  }
  return String(periodo);
}

/** ISO → "há 2 min", "há 3h", "há 2 d", "em 5 min". */
export function formatRelativeTime(iso: string): string {
  const now = Date.now();
  const then = new Date(iso).getTime();
  if (isNaN(then)) return "—";
  const diffSec = Math.round((now - then) / 1000);
  const abs = Math.abs(diffSec);
  const past = diffSec >= 0;
  const prefix = past ? "há " : "em ";
  if (abs < 60) return past ? "agora" : "em instantes";
  if (abs < 3600) return `${prefix}${Math.floor(abs / 60)} min`;
  if (abs < 86400) return `${prefix}${Math.floor(abs / 3600)}h`;
  if (abs < 86400 * 30) return `${prefix}${Math.floor(abs / 86400)} d`;
  if (abs < 86400 * 365) return `${prefix}${Math.floor(abs / (86400 * 30))} meses`;
  return `${prefix}${Math.floor(abs / (86400 * 365))} anos`;
}

export function formatPeriod(yyyymm: string | number): string {
  const s = String(yyyymm);
  if (s.length < 6) return s;
  const year = s.slice(0, 4);
  const month = parseInt(s.slice(4, 6), 10);
  if (isNaN(month) || month < 1 || month > 12) return s;
  const d = new Date(Number(year), month - 1, 1);
  return `${MONTH_SHORT.format(d)}/${year}`;
}

export function formatMonth(date: Date | string): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return `${MONTH_LONG.format(d)}/${d.getFullYear()}`;
}

export function formatRange(start: string | number, end: string | number): string {
  return `${formatPeriod(start)}–${formatPeriod(end)}`;
}

export function formatDocPeriod(raw: string | null | undefined): string {
  if (!raw) return "—";
  if (raw === "999999") return "Indeterminado";
  if (raw.includes("_")) {
    const [start, end] = raw.split("_");
    if (start === end) return formatPeriod(start);
    return formatRange(start, end);
  }
  return formatPeriod(raw);
}

// ─── Status Labels & Variants (semantic, no hardcoded Tailwind classes) ───

export type StatusVariant = "success" | "warning" | "error" | "info" | "neutral" | "premium" | "muted";

interface StatusLabel {
  label: string;
  variant: StatusVariant;
}

const DOC_STATUS_MAP: Record<DocumentStatus, StatusLabel> = {
  uploaded:        { label: "Enviado",          variant: "neutral" },
  unlocking:       { label: "Desbloqueando",    variant: "warning" },
  classifying:     { label: "Classificando",    variant: "info" },
  ready:           { label: "Pronto",           variant: "success" },
  needs_password:  { label: "Precisa de senha", variant: "warning" },
  processing:      { label: "Processando",      variant: "info" },
  processed:       { label: "Processado",       variant: "success" },
  error:           { label: "Erro",             variant: "error" },
};

export function docStatusLabel(status: DocumentStatus): StatusLabel {
  return DOC_STATUS_MAP[status] ?? { label: status, variant: "neutral" };
}

/**
 * Estado efetivo do documento — derivado de status + pipeline_e2_extract_ok + needs_review + doc_type.
 *
 * Sequência: Recebido → Aguarda senha → Não classificado / Revisar → Pronto → Extraído / Sem extrato.
 * "Não classificado" (muted) sinaliza doc_type=other — pipeline jamais aceita até reclassificação manual.
 * "Revisar" (warning) sinaliza tipo conhecido com baixa confiança — pipeline pode rodar após validação.
 */
export function docEffectiveStatus(doc: {
  status: DocumentStatus;
  pipeline_e2_extract_ok?: boolean | null;
  needs_review?: boolean | null;
  doc_type?: DocumentType | null;
}): StatusLabel {
  const { status, pipeline_e2_extract_ok, needs_review, doc_type } = doc;

  if (status === "error") {
    return { label: "Erro", variant: "error" };
  }
  if (status === "needs_password") {
    return { label: "Aguarda senha", variant: "warning" };
  }
  if (status === "uploaded" || status === "unlocking" || status === "classifying") {
    return { label: "Recebido", variant: "neutral" };
  }
  if (status === "processing") {
    return { label: "Analisando", variant: "info" };
  }
  if (status === "ready") {
    if (needs_review && doc_type === "other") return { label: "Não classificado", variant: "muted" };
    if (needs_review) return { label: "Revisar", variant: "warning" };
    return { label: "Pronto", variant: "info" };
  }
  if (status === "processed") {
    if (pipeline_e2_extract_ok) return { label: "Extraído", variant: "success" };
    if (needs_review && doc_type === "other") return { label: "Não classificado", variant: "muted" };
    if (needs_review) return { label: "Revisar", variant: "warning" };
    // pipeline_e2_extract_ok===false: pipeline rodou sem extrato; null: N/A (IRPF, members JSON).
    if (pipeline_e2_extract_ok === false) return { label: "Sem extrato", variant: "neutral" };
    return { label: "Processado", variant: "success" };
  }
  return { label: status, variant: "neutral" };
}

/** Classificação concluída: pode ir ao pipeline / relatório (antes ou depois de um run). */
export function isDocumentClassifiedOk(status: DocumentStatus): boolean {
  return status === "ready" || status === "processed";
}

const DOC_TYPE_MAP: Record<DocumentType, string> = {
  bank_statement: "Extrato",
  credit_card_bill: "Fatura",
  investment_report: "Investimentos",
  irpf: "IRPF",
  informe_rendimentos_anuais: "Informe de rendimentos",
  comprovante_bem: "Comprovante de bem",
  e1_members_json: "Membros (JSON)",
  e1_5_baseline_json: "Baseline (JSON)",
  other: "Outro",
};

export {
  E0_DOC_TYPE_MAP,
  docSubtypeLabel,
  documentDisplayLabel,
} from "./documentTypeLabels";

export function docTypeLabel(type: DocumentType | null): string {
  return type ? DOC_TYPE_MAP[type] ?? type : "—";
}

const BANK_NAMES: Record<string, string> = {
  itau: "Itaú",
  bradesco: "Bradesco",
  santander: "Santander",
  c6bank: "C6 Bank",
  btgpactual: "BTG Pactual",
  rico: "Rico",
  picpay: "PicPay",
  wise: "Wise",
  bankofamerica: "Bank of America",
  quintoandar: "QuintoAndar",
  binance: "Binance",
  caixa: "Caixa Econômica Federal",
  nubank: "Nubank",
  inter: "Inter",
  stone: "Stone",
  receitafederal: "Receita Federal",
};

export function bankLabel(code: string | null): string {
  if (!code) return "—";
  return BANK_NAMES[code.toLowerCase()] ?? code;
}

/** Rótulo de instituição (banco, corretora, Receita, QuintoAndar, etc.) — alias de ``bankLabel``. */
export function institutionLabel(code: string | null): string {
  return bankLabel(code);
}

/** Extensão amigável para exibição (PDF, CSV, …). */
export function fileFormatLabel(contentType: string | null | undefined, originalName: string): string {
  const ext = originalName.includes(".") ? originalName.split(".").pop()?.toLowerCase() ?? "" : "";
  const map: Record<string, string> = {
    pdf: "PDF",
    csv: "CSV",
    xls: "XLS",
    xlsx: "XLSX",
    json: "JSON",
    jpg: "JPEG",
    jpeg: "JPEG",
    png: "PNG",
  };
  if (ext && map[ext]) return map[ext];
  if (contentType?.includes("pdf")) return "PDF";
  if (contentType?.includes("csv")) return "CSV";
  if (contentType?.includes("spreadsheet") || contentType?.includes("excel")) return "XLSX";
  if (contentType?.includes("json")) return "JSON";
  if (contentType?.includes("image/jpeg") || contentType?.includes("jpg")) return "JPEG";
  if (contentType?.includes("png")) return "PNG";
  if (ext) return ext.toUpperCase();
  return "—";
}

/** Resumo curto para a lista: data da última análise + qualidade da leitura do extrato. */
export function pipelineE2TouchLabel(
  lastRunAt: string | null | undefined,
  e2Ok: boolean | null | undefined,
): string {
  if (!lastRunAt) return "—";
  const when = formatDateShort(lastRunAt);
  if (e2Ok === true) return `${when} · leitura estruturada do extrato`;
  if (e2Ok === false) return `${when} · leitura automática incompleta`;
  return when;
}

/** Texto do tooltip (sem jargão técnico de pipeline/estágios). */
export function pipelineTouchTooltipExplanation(
  e2Ok: boolean | null | undefined,
): string {
  if (e2Ok === true) {
    return (
      "O sistema organizou os lançamentos deste arquivo de forma estruturada para usar na consolidação " +
      "e no relatório."
    );
  }
  if (e2Ok === false) {
    return (
      "O arquivo entrou na análise, mas a leitura automática do extrato não foi completa " +
      "(por exemplo: layout do banco ainda não suportado, PDF só com imagem ou formato não tratado). " +
      "Parte das informações pode vir de outras fontes no relatório."
    );
  }
  return "Não foi possível verificar automaticamente o nível de detalhe extraído deste arquivo.";
}

const RUN_STATUS_MAP: Record<PipelineRunStatus, StatusLabel> = {
  pending:         { label: "Pendente",       variant: "neutral" },
  running:         { label: "Em execução",    variant: "info" },
  completed:       { label: "Concluído",      variant: "success" },
  partial_failure: { label: "Parcial",        variant: "warning" },
  failed:          { label: "Falhou",         variant: "error" },
  cancelled:       { label: "Cancelado",      variant: "muted" },
  needs_review:    { label: "Aguardando revisão", variant: "warning" },
  resuming:        { label: "Retomando",      variant: "info" },
};

export function runStatusLabel(status: PipelineRunStatus): StatusLabel {
  return RUN_STATUS_MAP[status] ?? { label: status, variant: "neutral" };
}

interface StageStatusLabel {
  label: string;
  variant: StatusVariant;
  icon: string;
}

const STAGE_STATUS_MAP: Record<PipelineStageStatus, StageStatusLabel> = {
  pending:           { label: "Pendente",           variant: "neutral",  icon: "○" },
  running:           { label: "Executando",         variant: "info",     icon: "◉" },
  completed:         { label: "Concluído",          variant: "success",  icon: "✓" },
  failed:            { label: "Falhou",             variant: "error",    icon: "✗" },
  skipped:           { label: "Ignorado",           variant: "muted",    icon: "⊘" },
  skipped_free_tier: { label: "Premium",            variant: "muted",    icon: "⊘" },
  needs_review:      { label: "Aguardando revisão", variant: "warning",  icon: "⚠" },
};

export function stageStatusLabel(status: PipelineStageStatus): StageStatusLabel {
  return STAGE_STATUS_MAP[status] ?? { label: status, variant: "neutral", icon: "?" };
}

export { STAGE_DISPLAY_NAMES, stageName } from "./stage-names";

export function formatElapsed(startedAt: string): string {
  const ms = Date.now() - new Date(startedAt).getTime();
  if (ms < 0) return "0s";
  if (ms < 10_000) return "< 10s";
  if (ms < 60_000) return `${Math.floor(ms / 1000)}s`;
  const mins = Math.floor(ms / 60_000);
  const secs = Math.floor((ms % 60_000) / 1000);
  return `${mins}min ${secs.toString().padStart(2, "0")}s`;
}
