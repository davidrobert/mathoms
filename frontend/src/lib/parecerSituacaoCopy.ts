// A40.l92 — a situação de cada métrica do parecer é decidida no BACKEND; aqui só se escolhe
// a palavra.
//
// A coluna era "Trilha": `clamp(atual / alvo)` re-derivado por regex sobre a string
// renderizada. A regex comia o glifo do operador, e a barra de um TETO enchia conforme a
// métrica piorava — `taxa_endividamento` 45% contra `≤ 20%` desenhava trilha cheia, a
// gramática de "meta atingida" sobre uma violação de 25pp.
//
// Co-design (product-designer + financial-planner): progresso contra teto não existe nas
// três metodologias — abaixo do teto "menor" não é "melhor" —, então o teto ganha só status
// e o piso mantém a barra como codificação secundária. O status afirma SÓ o comparador:
// "Dentro do limite" não quer dizer "dívida saudável". Despesas não identificadas fala da
// leitura do relatório, não da família, e mostra o tier do produtor na tríade da ADR-353.

import type { Comparador, Metrica, NivelConfianca } from "@/lib/api/planner-review";

/** `atencao` em âmbar, nunca vermelho: severidade é do canal de risco, não do comparador. */
export type TomDaSituacao = "conforme" | "atencao";

export interface SituacaoDaMetrica {
  texto: string;
  tom: TomDaSituacao;
  /** Barra só quando o backend publica progresso — o que acontece só no piso. */
  progressoPct: number | null;
}

const NIVEL: Record<NivelConfianca, SituacaoDaMetrica> = {
  alta: { texto: "Cobertura alta", tom: "conforme", progressoPct: null },
  parcial: { texto: "Cobertura parcial", tom: "atencao", progressoPct: null },
  insuficiente: { texto: "Cobertura insuficiente", tom: "atencao", progressoPct: null },
};

// O substantivo ensina a polaridade: "limite" é teto, "alvo" é piso. "Alvo" nomeia a coluna
// vizinha, não a natureza do limiar — por isso é verdadeiro nos três pisos, inclusive o da
// reserva, que é o alvo do PERFIL (6/12/18 meses) e não um mínimo: "abaixo do mínimo"
// contradizia o canal de risco, cujo mínimo é outro número. "Meta" fica de fora porque
// colide com os Goals da família; "acima do alvo" num teto leria como elogio a violação.
function textoDoComparador(c: Comparador): string {
  if (c.operador === ">=") return c.conforme ? "Alvo atingido" : "Abaixo do alvo";
  return c.conforme ? "Dentro do limite" : "Acima do limite";
}

/** `null` = sem comparação publicada: órfã, observado ausente ou parecer anterior ao campo. */
export function situacaoDaMetrica(m: Metrica): SituacaoDaMetrica | null {
  if (m.nivel_confianca) return NIVEL[m.nivel_confianca];
  if (!m.comparador) return null;
  return {
    texto: textoDoComparador(m.comparador),
    tom: m.comparador.conforme ? "conforme" : "atencao",
    progressoPct: m.comparador.progresso_pct,
  };
}
