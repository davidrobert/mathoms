/** A40.l3 (ADR-306 D1) — cláusulas de base temporal aceitas em texto derivado.
 *
 * Const ÚNICA, importada pelo contract test (Vitest — roda em `frontend-checks`,
 * job em `all-green.needs`) **e** pelo spec de render (Playwright, mesmo job).
 *
 * Por que compartilhada e não uma cópia por runner: as duas cópias divergiram já
 * na primeira versão. A forma SINGULAR ("mês documentado") existia só no E2E — e
 * `janela_meses = 1` é o valor do substrato versionado
 * (`backend/tests/snapshots/dogfood_view_model.json`), ou seja, a asserção mais
 * forte estava no runner que **não** bloqueia merge. Divergência de guarda é
 * silenciosa por natureza: os dois testes passam, um deles mede menos.
 */
export const CLAUSULA_DE_BASE =
  /meses documentados|mês documentado|janela exibida|todo o período analisado|No gráfico:/i;
