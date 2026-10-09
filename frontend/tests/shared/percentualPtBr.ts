/** Percentual com PONTO decimal ("42.8%", "2.38 %") — em copy pt-BR o
 * separador é vírgula (COPY_GUIDELINES §4.6) e o formatador canônico é
 * `formatPercent` (`@/lib/format`).
 *
 * Use em asserção NEGATIVA sobre o `textContent` do componente, sempre ao lado
 * da positiva com a vírgula: sozinha, ela passa sobre um card que não renderizou.
 *
 * Não casa milhar pt-BR com casas ("1.234,5%": depois do ponto vem vírgula, não
 * `%`). Casa milhar inteiro ("1.234%"), que o relatório não tem. */
export const PERCENTUAL_COM_PONTO = /\d\.\d+\s?%/;
