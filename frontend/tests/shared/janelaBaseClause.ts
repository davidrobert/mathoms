/** A40.l3 (ADR-306 D1) — vocabulário do invariante de base temporal.
 *
 * Consts ÚNICAS, importadas pelo contract test (Vitest — roda em
 * `frontend-checks`, job em `all-green.needs`) **e** pelo spec de render
 * (Playwright, mesmo job).
 *
 * Por que compartilhadas e não uma cópia por runner: as duas cópias divergiram já
 * na primeira versão. A forma SINGULAR ("mês documentado") existia só no E2E — e
 * `janela_meses = 1` é o valor do substrato versionado
 * (`backend/tests/snapshots/dogfood_view_model.json`), ou seja, a asserção mais
 * forte estava no runner que **não** bloqueia merge. Divergência de guarda é
 * silenciosa por natureza: os dois testes passam, um deles mede menos.
 */

/** Cláusulas que declaram a BASE de um agregado.
 *
 * `No gráfico: N meses` **não entra**: é a contagem de barras RENDERIZADAS —
 * descreve o desenho, não a base do número citado. Aceitá-la deixava passar
 * texto do tipo "No gráfico: 12 meses. Receita média de R$ 42.667/mês.": o
 * desenho declarado, o agregado não. */
export const CLAUSULA_DE_BASE =
  /meses documentados|mês documentado|janela documentada|janela exibida|todo o período analisado/i;

/** Texto sujeito ao invariante: o que cita número agregado (monetário ou
 * percentual). Texto que só descreve o desenho ("No gráfico: 3 meses (25/10 a
 * 25/12).") não afirma agregado nenhum — não há base a declarar, e exigir
 * cláusula dele seria exigir rótulo de um número que não existe. */
export const CITA_AGREGADO = /R\$|\d(?:[.,]\d+)?\s?%/;
