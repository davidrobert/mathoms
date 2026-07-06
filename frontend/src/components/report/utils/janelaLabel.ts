/** A28.l9 — humaniza o rótulo de janela de mensalização (ADR-306 D2).
 *
 * O E5 rotula todo bloco mensalizado com `janela` (`12m` | `full` |
 * `irpf[_<ano>]`) + `janela_meses`. Consumidores UI anexam este texto via
 * `InfoTooltip` ao lado do label — nunca duas mensalizações sem rótulo.
 * Retorna `null` para payload antigo sem rótulo (tooltip é omitido).
 */
export function formatJanelaTooltip(
  janela: string | undefined,
  janelaMeses: number | undefined,
): string | null {
  if (!janela) return null;
  if (janela === "12m") {
    const meses = janelaMeses && janelaMeses > 0 ? janelaMeses : 12;
    return `Média mensal calculada sobre os últimos ${meses} meses documentados.`;
  }
  if (janela === "full") {
    const sufixo = janelaMeses && janelaMeses > 0 ? ` (${janelaMeses} meses)` : "";
    return `Média mensal calculada sobre todo o período analisado${sufixo}.`;
  }
  if (janela.startsWith("irpf")) {
    const ano = janela.split("_")[1];
    return `Valor mensalizado do ano-base IRPF${ano ? ` ${ano}` : ""} (12 meses).`;
  }
  return `Média mensal calculada sobre a janela "${janela}".`;
}
