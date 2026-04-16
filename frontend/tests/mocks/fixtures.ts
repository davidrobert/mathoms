/**
 * MSW fixtures — F6.5 (sub-fase 6.5A.2)
 *
 * Dataset estático "happy path" para handlers default. Tests específicos
 * preferem usar `factories/` (data builders type-safe) ao invés destas
 * fixtures, porque factories permitem overrides parciais e nomes únicos.
 *
 * REGRA LGPD/PII (ADR-063, task 6.5D.7):
 * - CPFs aqui são SEMPRE 000.000.000-00 (placeholder), nunca CPFs gerados
 *   "parecidos com reais". Tests que precisam de CPF válido usam o gerador
 *   determinístico mod-11 em `tests/utils/cpf.ts` (criado em 6.5D.7).
 * - Nomes/emails são fictícios (usar @test.com, sem nomes reais conhecidos).
 * - Valores monetários são redondos e óbvios para facilitar leitura.
 */
import type {
  CategoryConfig,
  DashboardResponse,
  DocumentResponse,
  FamilyMemberConfig,
  LLMConfigResponse,
  NotificationItem,
  PipelineRunResponse,
  ReportResponse,
  TransactionItem,
  UserResponse,
  VaultPasswordResponse,
} from "@/lib/api";

const NOW = "2026-04-15T12:00:00Z";

const user: UserResponse = {
  id: "user-1",
  email: "founder@test.com",
  full_name: "Founder Teste",
  is_active: true,
};

const reports: ReportResponse[] = [
  {
    id: "report-1",
    workspace_id: "ws-1",
    title: "Relatório Família Teste — Abr/2026",
    period: "2026-04",
    size_bytes: 524_288,
    score: 82,
    patrimonio_liquido: 950_000,
    created_at: NOW,
    has_analysis_data: true,
  },
];

const documents: DocumentResponse[] = [
  {
    id: "doc-1",
    workspace_id: "ws-1",
    original_name: "extrato_c6_202604.pdf",
    stored_path: "ws-1/uploads/doc-1.pdf",
    doc_type: "bank_statement",
    bank_code: "c6bank",
    period: "2026-04",
    status: "ready",
    classification_meta: null,
    file_size_bytes: 102_400,
    content_type: "application/pdf",
    error_message: null,
    uploaded_at: NOW,
  },
];

const vaultPasswords: VaultPasswordResponse[] = [
  { id: "vault-1", label: "C6 Bank", created_at: NOW },
];

const pipelineRun: PipelineRunResponse = {
  id: "run-1",
  workspace_id: "ws-1",
  status: "completed",
  current_stage: null,
  failed_at_stage: null,
  paused_at_stage: null,
  tier_at_run: "free",
  total_documents: 1,
  incremental: false,
  celery_task_id: "celery-task-1",
  started_at: NOW,
  completed_at: NOW,
  stage_logs: [
    {
      id: "log-1",
      stage: "E0",
      status: "completed",
      output_summary: { processed: 1 },
      errors: null,
      duration_ms: 1200,
      started_at: NOW,
      completed_at: NOW,
    },
  ],
};

const members: FamilyMemberConfig[] = [
  {
    id: "member-1",
    key: "founder",
    full_name: "Founder Teste",
    short_name: "Founder",
    cpf: "000.000.000-00", // placeholder — gerador real em 6.5D.7
    birth_date: "1985-03-10",
    role: "responsavel",
    order: 1,
    extra: null,
    accounts: [
      {
        id: "acc-1",
        institution_code: "c6bank",
        account_type: "corrente",
        agency: "0001",
        account_number: "12345-6",
      },
    ],
  },
];

const categories: CategoryConfig[] = [
  {
    id: "cat-1",
    code: "alimentacao",
    name: "Alimentação",
    category_type: "expense",
    monthly_cap: 2000,
    order: 1,
    keywords: ["mercado", "padaria", "ifood"],
  },
  {
    id: "cat-2",
    code: "salario",
    name: "Salário",
    category_type: "income",
    monthly_cap: null,
    order: 1,
    keywords: ["pagto folha", "salario"],
  },
];

const transactions: TransactionItem[] = [
  {
    data: "2026-04-05",
    descricao: "Mercado XYZ",
    valor: -250.5,
    banco: "C6 Bank",
    categoria: "alimentacao",
    origem: "extrato",
    tipo_conta: "corrente",
    titular: "Founder",
    moeda: "BRL",
    transaction_hash: "h-1",
    is_overridden: false,
  },
  {
    data: "2026-04-01",
    descricao: "Pagto Folha",
    valor: 12_500,
    banco: "C6 Bank",
    categoria: "salario",
    origem: "extrato",
    tipo_conta: "corrente",
    titular: "Founder",
    moeda: "BRL",
    transaction_hash: "h-2",
    is_overridden: false,
  },
];

const dashboard: DashboardResponse = {
  kpis: [
    { label: "Receitas", value: "R$ 12.500,00", raw_value: 12_500, delta: 500, delta_percent: 0.04 },
    { label: "Despesas", value: "R$ 8.400,00", raw_value: -8_400, delta: -120, delta_percent: -0.014 },
    { label: "Saldo", value: "R$ 4.100,00", raw_value: 4_100, delta: 380, delta_percent: 0.1 },
    { label: "Score", value: "78", raw_value: 78, delta: null, delta_percent: null },
  ],
  charts: [],
  alerts: [],
  data_freshness: NOW,
  periodo: "2026-04",
};

const notifications: NotificationItem[] = [
  {
    id: "notif-1",
    severity: "info",
    title: "Pipeline concluído",
    message: "Sua análise de Abr/2026 está pronta.",
    source: "pipeline",
    is_read: false,
    created_at: NOW,
  },
];

const llmConfig: LLMConfigResponse = {
  id: "llm-1",
  provider: "anthropic",
  model_name: "claude-opus-4-6",
  max_tokens: 4096,
  temperature: 0.0,
  created_at: NOW,
  updated_at: NOW,
};

export const fixtures = {
  user,
  reports,
  documents,
  vaultPasswords,
  pipelineRun,
  members,
  categories,
  transactions,
  dashboard,
  notifications,
  llmConfig,
};
