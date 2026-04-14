import type { DocumentStatus, DocumentType, PipelineStageStatus, PipelineRunStatus } from "./api";

// ─── Number Formatting ───

const BRL = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const USD = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
const PCT = new Intl.NumberFormat("pt-BR", { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 });
const COMPACT_BRL = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  notation: "compact",
  maximumFractionDigits: 1,
});

export function formatCurrency(value: number, currency: "BRL" | "USD" = "BRL"): string {
  return currency === "USD" ? USD.format(value) : BRL.format(value);
}

export function formatPercent(value: number, decimals = 1): string {
  if (decimals !== 1) {
    return new Intl.NumberFormat("pt-BR", {
      style: "percent",
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value);
  }
  return PCT.format(value);
}

export function formatDelta(
  value: number,
  opts?: { percent?: number; currency?: "BRL" | "USD"; invert?: boolean }
): string {
  const sign = value >= 0 ? "+" : "";
  const formatted = formatCurrency(value, opts?.currency);
  const prefix = sign + (value >= 0 ? "" : "");
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
  if (!ms) return "—";
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

const DOC_TYPE_MAP: Record<DocumentType, string> = {
  bank_statement: "Extrato",
  credit_card_bill: "Fatura",
  investment_report: "Investimentos",
  irpf: "IRPF",
  e1_members_json: "Membros (JSON)",
  e1_5_baseline_json: "Baseline (JSON)",
  other: "Outro",
};

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
  nubank: "Nubank",
  inter: "Inter",
};

export function bankLabel(code: string | null): string {
  if (!code) return "—";
  return BANK_NAMES[code.toLowerCase()] ?? code;
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

export const STAGE_DISPLAY_NAMES: Record<string, string> = {
  "E0-audit": "Auditoria",
  "E0-route": "Roteamento",
  "E0-unlock": "Desbloqueio",
  "E1.5c": "Consolidar Baseline",
  "E2": "Extração",
  "E2-extratos": "Extratos",
  "E2-faturas": "Faturas",
  "E3": "Reconciliação",
  "E4": "Categorização",
  "E5": "Análise",
  "E5.N": "Narrativas",
  "E6": "Relatório",
  "E7-crossval": "Cross-validation",
};

export function stageName(stage: string): string {
  return STAGE_DISPLAY_NAMES[stage] ?? stage;
}

export function formatElapsed(startedAt: string): string {
  const ms = Date.now() - new Date(startedAt).getTime();
  if (ms < 0) return "0s";
  if (ms < 10_000) return "< 10s";
  if (ms < 60_000) return `${Math.floor(ms / 1000)}s`;
  const mins = Math.floor(ms / 60_000);
  const secs = Math.floor((ms % 60_000) / 1000);
  return `${mins}min ${secs.toString().padStart(2, "0")}s`;
}
