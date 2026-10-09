/** Decimal com PONTO ("1.5 MB", "71.2 meses", "2.3s") — em copy pt-BR o
 * separador é vírgula (COPY_GUIDELINES §4.1) e o formatador canônico é
 * `formatNumber` (`@/lib/format`). O par do percentual é `percentualPtBr.ts`.
 *
 * Use em asserção NEGATIVA sobre o `textContent` do componente, sempre ao lado
 * da positiva com a vírgula: sozinha, ela passa sobre um componente que não
 * renderizou.
 *
 * Uma ou duas casas depois do ponto: com três, "1.023" é milhar pt-BR. */
export const DECIMAL_COM_PONTO = /\d\.\d{1,2}(?!\d)/;
