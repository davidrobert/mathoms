/** Copy do diálogo destrutivo do pipeline (ADR-417 D4).
 *
 * Interromper um run que EXECUTA e descartar um que está PAUSADO são atos
 * diferentes, e o texto único descrevia só o primeiro: "será interrompido ao
 * final da etapa em execução" — numa pausa não há etapa executando.
 */
import type { PipelineRunResponse } from "@/lib/api";

export type CancelCopy = {
  title: string;
  description: string;
  confirmLabel: string;
};

const INTERROMPER: CancelCopy = {
  title: "Cancelar execução atual?",
  description:
    "O pipeline será interrompido ao final da etapa em execução. Etapas já concluídas serão mantidas.",
  confirmLabel: "Cancelar execução",
};

function conferencias(pendingCount: number): string {
  if (pendingCount === 1)
    return "A conferência pendente deixa de ser necessária.";
  if (pendingCount > 1)
    return `As ${pendingCount} conferências pendentes deixam de ser necessárias.`;
  return "A conferência pendente deixa de ser necessária.";
}

/** Os três fatos que o usuário tem na cabeça, na ordem em que os pensa: o que já
 *  foi feito se perde? · meu relatório atual cai? · e agora? Mesma régua de
 *  `ReviewActions::consequenceText`. Não promete retomar de onde parou — isso
 *  dependeria de `_resolve_base_run` aceitar run `cancelled`, que não foi medido. */
function descartar(
  pendingCount: number,
  hasRelatorioAnterior: boolean,
): CancelCopy {
  const cauda = hasRelatorioAnterior
    ? "O que já foi processado fica guardado — nada é apagado — e seu relatório atual continua valendo. Você pode processar de novo quando quiser."
    : "O que já foi processado fica guardado, mas nenhum relatório foi gerado ainda — você vai precisar processar de novo.";
  return {
    title: "Descartar este processamento?",
    description: `${conferencias(pendingCount)} ${cauda}`,
    confirmLabel: "Descartar",
  };
}

/** `runs` entra inteiro porque "existe relatório para cair de volta?" é fato do
 *  histórico, não da tela — e é a pergunta que mais pesa na decisão de descartar. */
export function cancelCopyFor(
  run: PipelineRunResponse | null,
  opts: { pendingCount: number; runs: PipelineRunResponse[] },
): CancelCopy {
  if (run?.status !== "needs_review") return INTERROMPER;
  return descartar(
    opts.pendingCount,
    opts.runs.some((r) => Boolean(r.report_id)),
  );
}
