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

// O substantivo ensina a polaridade: "limite" é teto, "mínimo" é piso — e explica por que
// só o piso tem barra. "Meta" fica de fora porque colide com os Goals da família.
function textoDoComparador(c: Comparador): string {
  if (c.operador === ">=") return c.conforme ? "Mínimo atingido" : "Abaixo do mínimo";
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
