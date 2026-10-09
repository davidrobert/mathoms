/**
 * Tradução de erros técnicos do pipeline para mensagens user-facing (ADR-068).
 *
 * Ao invés de mostrar stack traces ou nomes de etapas no topo, identificamos
 * padrões comuns e oferecemos uma mensagem que fala do **impacto** para o
 * usuário e do **próximo passo** sugerido. O texto técnico continua disponível
 * via "Ver detalhes do erro".
 */

import { phaseOfStage, getPhase } from "./pipelinePhases";

export interface UserFacingError {
  /** Resumo de uma linha, foco no impacto. */
  headline: string;
  /** Próximo passo sugerido. Pode ser null. */
  hint: string | null;
}

/**
 * Marcador que o sanitizador do backend põe em todo erro de banco redigido (ADR-441 D2).
 * Contrato com `DATABASE_VALUES_OMITTED` em `pipeline/observability/failure_text.py`.
 */
export const DATABASE_VALUES_OMITTED = "valores do banco omitidos";

interface ErrorPattern {
  match: RegExp;
  /** Stages a que o pattern se aplica (vazio = qualquer). */
  stages?: readonly string[];
  build: (stage: string | null) => UserFacingError;
}

const PATTERNS: readonly ErrorPattern[] = [
  {
    // PDF protegido: aceita password/senha/encrypted e formas
    // específicas envolvendo "locked" no contexto de arquivo/PDF.
    // NÃO casa com "database is locked" (SQLite), "account locked",
    // "mutex locked" etc. — esses são problemas técnicos diferentes
    // e a UX de "cadastre senha no Cofre" não ajuda o usuário lá.
    match: /password|senha|protegid[oa]|encrypted|pdf[^.]{0,40}locked|locked[^.]{0,40}pdf|file is locked/i,
    build: () => ({
      headline:
        "Algum PDF está protegido por senha e não conseguimos abri-lo.",
      hint:
        "Cadastre a senha do documento na aba Cofre e tente reprocessar.",
    }),
  },
  {
    match: /timeout|timed out|deadline/i,
    build: (stage) => timeoutError(stage),
  },
  {
    match: /api[_ ]?key|unauthor|401|403|invalid.*key/i,
    build: () => ({
      headline:
        "A chave de API configurada para a IA não está autorizada.",
      hint: "Verifique a chave em Configuração → IA e teste a conexão.",
    }),
  },
  {
    match: /rate[_ ]?limit|429|too many requests/i,
    build: () => ({
      headline: "Atingimos o limite de chamadas à IA neste momento.",
      hint: "Aguarde alguns minutos e reprocesse.",
    }),
  },
  {
    match: /no documents|nenhum documento|empty/i,
    stages: ["E0-route"],
    build: () => ({
      headline:
        "Nenhum documento pronto foi encontrado para processar.",
      hint: "Envie documentos pela aba Documentos antes de gerar o relatório.",
    }),
  },
  {
    match: /schema|validation|invalid.*format/i,
    build: () => ({
      headline:
        "Encontramos um documento em formato inesperado e não conseguimos lê-lo.",
      hint:
        "Veja os detalhes técnicos abaixo para identificar o arquivo problemático.",
    }),
  },
];

function timeoutError(stage: string | null): UserFacingError {
  return {
    headline: `O processamento de ${getPhase(stage ?? "").title.toLowerCase()} demorou mais que o esperado.`,
    hint: "Tente reprocessar — geralmente resolve em uma nova execução.",
  };
}

/** Fallback genérico, baseado na fase. */
function genericError(failedStage: string | null | undefined): UserFacingError {
  const phaseId = failedStage ? phaseOfStage(failedStage) : null;
  const phaseTitle = phaseId
    ? getPhase(phaseId).title.toLowerCase()
    : "processar seus documentos";

  return {
    headline: `Não conseguimos completar a etapa de ${phaseTitle}.`,
    hint: "Tente reprocessar — se o erro persistir, veja os detalhes técnicos.",
  };
}

/**
 * Erro de banco redigido traz nome de tabela e coluna (`api_key_encrypted`,
 * `schema_version`, `deadline_at`) que casariam os padrões por acidente: decide
 * antes deles. O único rótulo que vira headline próprio é o de timeout.
 */
function redactedDatabaseError(
  text: string,
  failedStage: string | null | undefined,
): UserFacingError {
  return /statement timeout/i.test(text)
    ? timeoutError(failedStage ?? null)
    : genericError(failedStage);
}

/**
 * Gera mensagem user-facing a partir do texto de erro e da etapa que falhou.
 * Fallback: mensagem genérica com nome amigável da fase.
 */
export function buildUserFacingError(
  errorText: string | null | undefined,
  failedStage: string | null | undefined,
): UserFacingError {
  const text = errorText ?? "";
  if (text.includes(DATABASE_VALUES_OMITTED)) {
    return redactedDatabaseError(text, failedStage);
  }
  for (const pattern of PATTERNS) {
    if (pattern.stages && failedStage && !pattern.stages.includes(failedStage)) {
      continue;
    }
    if (pattern.match.test(text)) {
      return pattern.build(failedStage ?? null);
    }
  }
  return genericError(failedStage);
}
