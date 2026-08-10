/** ADR-237 — formata probabilidade do Monte Carlo para exibição. */
// Guards `<1%`/`>99%` existem para não afirmar 0/100 sobre extremo.
//
// O arredondamento é meio-para-cima EXPLÍCITO e tem par no narrador Python
// (`projecao_if_narrator._fmt_probabilidade`), que publica o MESMO campo no
// MESMO relatório. Os dois declaravam paridade em docstring e nunca haviam sido
// comparados: medido no domínio real do estimador (`k/50000`, ADR-360),
// discordavam em 45 dos 50 001 desfechos, porque `round()` do Python é
// meio-para-PAR. Gate: `dev/check_probabilidade_parity.py` (pre-commit, roda em
// todo PR — o par vive nos dois stacks e nenhum filtro de path cobre os dois).
export function formatProbability(prob: number): string {
  if (prob <= 0) return "0%";
  if (prob >= 1) return "100%";
  if (prob < 0.01) return "<1%";
  if (prob > 0.99) return ">99%";
  return `${Math.floor(prob * 100 + 0.5)}%`;
}
