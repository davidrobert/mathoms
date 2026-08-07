/** A40.l22 — a frase do contador de itens retidos do parecer.
 *
 * Vive em `lib/` porque duas superfícies a usam — o relatório (`S_parecer` +
 * banner) e a operacional (`/pipeline`) — e elas **não** coabitam a tela: um
 * produtor único evita a deriva de duas redações para o mesmo fato, que é o
 * modo de falha da copy duplicada.
 *
 * "itens do parecer", não "riscos": `items_dropped_count` é escalar do parecer
 * inteiro, e o enforcement remove risco **ou** sugestão
 * (`backend/app/services/parecer_strict_enforcement.py::_SUGESTAO_HORIZONS`).
 * Atribuí-lo ao bucket em cuja caption ele mora afirmaria "N riscos retidos"
 * num parecer que perdeu uma sugestão — a classe de mentira que a lane fecha.
 *
 * "retido", nunca "não publicado": COPY_GUIDELINES §2.2 `@2026-08-06` bane o
 * segundo por colidir com o estado `Publicado` da ADR-204, e exige o objeto
 * junto ("retenção" solta colide com retenção de IRRF, já user-facing).
 */
export function frasePecasRetidas(count: number): string {
  const objeto = count === 1 ? "item do parecer" : "itens do parecer";
  const flexao = count === 1 ? "retido" : "retidos";
  return `${count} ${objeto} ${flexao} na conferência`;
}
