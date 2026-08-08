// Copy do estado de AUSÊNCIA do parecer, por código de 404 (ADR-366 §D6 · A40.l22).
//
// Uma copy por código, ao contrário do `RETAINED_BODY` da retenção — que colapsa
// os 3 motivos numa frase de propósito, porque lá o cliente age igual em todos.
// Aqui não age: `tier_gated` não tem ação, `not_generated_yet` não tem ação, e os
// dois de falha pedem reprocessar. Colapsar afirmaria "não foi possível concluir"
// num estado em que o parecer FOI concluído (`parecer_artifact_missing` tem row).
//
// Toda variante delimita o escopo do dano na última frase. Sem isso o leitor
// generaliza "o parecer falhou" para "os números estão errados", que é o dano
// real — e é ilimitado, porque vira dúvida retroativa sobre relatórios passados.

import type { ParecerAbsenceCode } from "@/lib/api";

export interface ParecerAusenciaCopy {
  titulo: string;
  corpo: string;
  /** `true` ⇒ renderiza o link de reprocessar. Só onde o usuário PODE agir. */
  reprocessavel: boolean;
}

const AUSENCIA_COPY: Record<ParecerAbsenceCode, ParecerAusenciaCopy> = {
  not_generated_yet: {
    titulo: "Parecer não disponível neste relatório",
    corpo:
      "Este relatório foi gerado sem o parecer do planejador. " +
      "As demais seções não dependem dele.",
    reprocessavel: false,
  },
  // Fala do plano DO RUN, nunca do plano atual do cliente: quem subiu para
  // Premium depois continua sem parecer neste relatório, e "assine o Premium"
  // seria falso para ele. Sem CTA — não existe rota de upgrade no produto, e
  // link sem destino é a âncora morta que a A40.l7 existe para matar.
  tier_gated: {
    titulo: "Parecer não incluído no plano deste relatório",
    corpo:
      "Este relatório foi gerado no plano Free, que não inclui o parecer do planejador. " +
      "No Premium, o parecer traz a leitura dos seus números por um planejador. " +
      "As demais seções não dependem dele.",
    reprocessavel: false,
  },
  generation_unavailable: {
    titulo: "Parecer não foi concluído neste processamento",
    corpo:
      "Tentamos gerar o parecer para este relatório e não foi possível concluir. " +
      "As demais seções não foram afetadas.",
    reprocessavel: true,
  },
  // "Foi gerado, mas não conseguimos carregar" e não a copy de
  // `generation_unavailable`: aqui existe row de PlannerReview, logo a geração
  // concluiu. Dizer "não foi possível concluir" seria falso — e o custo de
  // reusar a string era exatamente essa falsidade.
  parecer_artifact_missing: {
    titulo: "Não conseguimos recuperar o parecer deste relatório",
    corpo:
      "O parecer foi gerado, mas não conseguimos carregá-lo agora. " +
      "As demais seções não foram afetadas.",
    reprocessavel: true,
  },
};

export function copyDaAusencia(code: ParecerAbsenceCode): ParecerAusenciaCopy {
  return AUSENCIA_COPY[code];
}
