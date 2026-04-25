/**
 * Frontend test data factories — F6.5 (sub-fase 6.5F.7)
 *
 * Por que factories e não fixtures fixas?
 * - Overrides parciais sem repetir o objeto inteiro
 * - Counters incrementais → IDs/emails únicos por test (evita race em paralelo)
 * - Type-safe: refletem 1:1 os types de `lib/api.ts` — TS quebra se backend muda
 *   mas factory não atualiza
 * - Default sane (LGPD-safe): nada PII real
 *
 * Padrão de uso:
 *   const u = makeUser({ email: "x@test.com" });
 *   const m = makeMember({ key: "spouse", role: "conjuge" });
 *
 * Reset entre tests: chamar `resetCounters()` em beforeEach se a ordem de IDs
 * importar (raro). Defaults com IDs sequenciais bastam para 95% dos casos.
 */
import type {
  BankAccountConfig,
  CategoryConfig,
  DashboardKPI,
  DashboardResponse,
  DocumentResponse,
  DocumentStatus,
  DocumentType,
  FamilyMemberConfig,
  LLMConfigResponse,
  NotificationItem,
  PipelineRunResponse,
  PipelineRunStatus,
  PipelineStageLog,
  PipelineStageStatus,
  ReportResponse,
  TransactionItem,
  UserResponse,
  VaultPasswordResponse,
} from "@/lib/api";

// ─── Counters (escopo de processo de teste) ───
const counters = {
  user: 0,
  workspace: 0,
  member: 0,
  account: 0,
  category: 0,
  document: 0,
  report: 0,
  run: 0,
  stage: 0,
  vault: 0,
  notification: 0,
  transaction: 0,
};

export function resetCounters() {
  for (const k of Object.keys(counters) as Array<keyof typeof counters>) {
    counters[k] = 0;
  }
}

const isoNow = () => new Date("2026-04-15T12:00:00Z").toISOString();
const next = (k: keyof typeof counters) => ++counters[k];

// ─── User ───

export function makeUser(overrides: Partial<UserResponse> = {}): UserResponse {
  const n = next("user");
  return {
    id: `user-${n}`,
    email: `user${n}@test.com`,
    full_name: `Test User ${n}`,
    is_active: true,
    is_developer: false,
    ...overrides,
  };
}

// ─── Bank Account + Family Member ───

export function makeBankAccount(
  overrides: Partial<BankAccountConfig> = {},
): BankAccountConfig {
  const n = next("account");
  return {
    id: `acc-${n}`,
    institution_code: "c6bank",
    account_type: "corrente",
    agency: "0001",
    account_number: `12345-${n}`,
    ...overrides,
  };
}

export function makeMember(
  overrides: Partial<FamilyMemberConfig> = {},
): FamilyMemberConfig {
  const n = next("member");
  return {
    id: `member-${n}`,
    key: `member_${n}`,
    full_name: `Member ${n}`,
    short_name: `M${n}`,
    cpf: "000.000.000-00", // placeholder — gerador real em 6.5D.7
    birth_date: "1990-01-01",
    role: "responsavel",
    order: n,
    extra: null,
    accounts: [makeBankAccount()],
    ...overrides,
  };
}

// ─── Category ───

export function makeCategory(
  overrides: Partial<CategoryConfig> = {},
): CategoryConfig {
  const n = next("category");
  return {
    id: `cat-${n}`,
    code: `cat_${n}`,
    name: `Categoria ${n}`,
    category_type: "expense",
    monthly_cap: 1000,
    order: n,
    keywords: [`palavra${n}`],
    ...overrides,
  };
}

// ─── Document ───

export function makeDocument(
  overrides: Partial<DocumentResponse> = {},
): DocumentResponse {
  const n = next("document");
  return {
    id: `doc-${n}`,
    workspace_id: "ws-test",
    original_name: `extrato_${n}.pdf`,
    stored_path: `ws-test/uploads/doc-${n}.pdf`,
    doc_type: "bank_statement" satisfies DocumentType,
    bank_code: "c6bank",
    period: "2026-04",
    status: "ready" satisfies DocumentStatus,
    classification_meta: null,
    file_size_bytes: 100_000,
    content_type: "application/pdf",
    error_message: null,
    uploaded_at: isoNow(),
    pipeline_last_run_at: null,
    pipeline_e2_extract_ok: null,
    ...overrides,
  };
}

// ─── Vault Password ───

export function makeVaultPassword(
  overrides: Partial<VaultPasswordResponse> = {},
): VaultPasswordResponse {
  const n = next("vault");
  return {
    id: `vault-${n}`,
    label: `Senha ${n}`,
    created_at: isoNow(),
    ...overrides,
  };
}

// ─── Pipeline Run + Stage Log ───

export function makeStageLog(
  overrides: Partial<PipelineStageLog> = {},
): PipelineStageLog {
  const n = next("stage");
  return {
    id: `log-${n}`,
    stage: `E${n}`,
    status: "completed" satisfies PipelineStageStatus,
    output_summary: { processed: 1 },
    errors: null,
    duration_ms: 1000,
    started_at: isoNow(),
    completed_at: isoNow(),
    ...overrides,
  };
}

export function makeRun(
  overrides: Partial<PipelineRunResponse> = {},
): PipelineRunResponse {
  const n = next("run");
  return {
    id: `run-${n}`,
    workspace_id: "ws-test",
    status: "completed" satisfies PipelineRunStatus,
    current_stage: null,
    failed_at_stage: null,
    paused_at_stage: null,
    tier_at_run: "free",
    total_documents: 1,
    incremental: false,
    celery_task_id: `celery-${n}`,
    started_at: isoNow(),
    completed_at: isoNow(),
    stage_logs: [makeStageLog()],
    report_id: null,
    ...overrides,
  };
}

// ─── Report ───

export function makeReport(
  overrides: Partial<ReportResponse> = {},
): ReportResponse {
  const n = next("report");
  return {
    id: `report-${n}`,
    workspace_id: "ws-test",
    title: `Relatório ${n}`,
    period: "2026-04",
    size_bytes: 500_000,
    score: null,
    patrimonio_liquido: null,
    created_at: isoNow(),
    pipeline_run_id: null,
    source_document_count: 0,
    source_document_ids: [],
    has_analysis_data: true,
    ...overrides,
  };
}

// ─── Transaction ───

export function makeTransaction(
  overrides: Partial<TransactionItem> = {},
): TransactionItem {
  const n = next("transaction");
  return {
    data: "2026-04-05",
    descricao: `Transação ${n}`,
    valor: -100,
    banco: "C6 Bank",
    categoria: "alimentacao",
    origem: "extrato",
    tipo_conta: "corrente",
    titular: "Founder",
    moeda: "BRL",
    transaction_hash: `h-${n}`,
    is_overridden: false,
    ...overrides,
  };
}

// ─── Notification ───

export function makeNotification(
  overrides: Partial<NotificationItem> = {},
): NotificationItem {
  const n = next("notification");
  return {
    id: `notif-${n}`,
    severity: "info",
    title: `Notificação ${n}`,
    message: "Mensagem de teste",
    source: "pipeline",
    is_read: false,
    created_at: isoNow(),
    ...overrides,
  };
}

// ─── Dashboard ───

export function makeKPI(overrides: Partial<DashboardKPI> = {}): DashboardKPI {
  return {
    label: "KPI",
    value: "R$ 0,00",
    raw_value: 0,
    delta: null,
    delta_percent: null,
    ...overrides,
  };
}

export function makeDashboard(
  overrides: Partial<DashboardResponse> = {},
): DashboardResponse {
  return {
    kpis: [makeKPI({ label: "Saldo", value: "R$ 4.100,00", raw_value: 4100 })],
    charts: [],
    alerts: [],
    data_freshness: isoNow(),
    periodo: "2026-04",
    ...overrides,
  };
}

// ─── LLM Config ───

export function makeLLMConfig(
  overrides: Partial<LLMConfigResponse> = {},
): LLMConfigResponse {
  return {
    id: "llm-1",
    provider: "anthropic",
    model_name: "claude-opus-4-6",
    max_tokens: 4096,
    temperature: 0.0,
    created_at: isoNow(),
    updated_at: isoNow(),
    ...overrides,
  };
}
