// Copy do estado de AUSÊNCIA do parecer, por código de 404 (ADR-366 §D6 · A40.l22).
//
// Uma copy por código porque as QUATRO AÇÕES são distintas — que é o teste do
// `RETAINED_BODY` (colapsar quando a ação é a mesma), não uma exceção a ele.
//
// `tier` NÃO é plano comercial: `_classify_llm_config` devolve "premium" ⟺ existe
// `LLMConfig` cuja `api_key_encrypted` decripta para texto não-vazio (BYOK,
// PRODUCT.md §4; pricing "Pendente" no §7). Logo a moldura destas frases é a
// CHAVE DE IA, nunca a compra: enquadrar por plano acusaria de downgrade quem
// perdeu a chave numa rotação de FERNET_KEY — caso que o `/config` já nomeia.
//
// Toda variante fecha com a MESMA frase de delimitação de dano, literal, que a
// retenção já usa: o cliente aprende um idioma só. Sem ela o leitor generaliza
// "o parecer falhou" para "os números estão errados", que é o dano real — e é
// ilimitado, porque vira dúvida retroativa sobre relatórios passados.

import type { ParecerAbsenceCode } from "@/lib/api";

/** Literal e única — assertada como string só no spec (COPY_GUIDELINES §2). */
export const DELIMITACAO_DE_DANO = "Os números das demais seções não mudam.";

/** `vazio` = nada aconteceu (card tracejado); `falha` = algo quebrou (Alert warning). */
export type ParecerAusenciaVariante = "vazio" | "falha";

export type ParecerAusenciaCta = "nenhum" | "chave_ia" | "reprocessar";

export interface ParecerAusenciaCopy {
  titulo: string;
  corpo: string;
  variante: ParecerAusenciaVariante;
  cta: ParecerAusenciaCta;
}

const AUSENCIA_COPY: Record<ParecerAbsenceCode, ParecerAusenciaCopy> = {
  // Presente ("ainda não tem"), nunca passado ("foi gerado sem"): este é o membro
  // FALLBACK do vocabulário — recebe código desconhecido e workspace/report
  // ausente. Mesmo princípio do `nao_registrado` da ADR-366 §D1: quem não sabe
  // não passa a afirmar. Sem CTA pelo mesmo motivo — não se manda agir sobre um
  // estado que pode ser outro.
  not_generated_yet: {
    titulo: "Parecer não disponível neste relatório",
    corpo: `Este relatório ainda não tem o parecer do planejador. ${DELIMITACAO_DE_DANO}`,
    variante: "vazio",
    cta: "nenhum",
  },
  // Descreve o que o parecer FAZ, nunca quem o escreve: "por um planejador"
  // afirmaria agente humano e contradiria o `FiduciaryDisclaimer` que roda na
  // mesma seção ("orientativo, não constitui recomendação personalizada").
  tier_gated: {
    titulo: "Parecer exige uma chave de IA ativa",
    corpo:
      "Este relatório foi gerado sem uma chave de IA ativa, então as etapas com IA " +
      "— inclusive o parecer — não rodaram. O parecer lê os seus números e aponta " +
      `pontos fortes, riscos e próximos passos. ${DELIMITACAO_DE_DANO}`,
    variante: "vazio",
    cta: "chave_ia",
  },
  generation_unavailable: {
    titulo: "Não conseguimos gerar o parecer deste relatório",
    corpo:
      "Tentamos gerar o parecer deste relatório e não conseguimos concluir. " +
      DELIMITACAO_DE_DANO,
    variante: "falha",
    cta: "reprocessar",
  },
  // A saída GRATUITA vem antes da cara: aqui existe row, logo o conteúdo foi
  // produzido — o que falhou foi servi-lo. `ReprocessarParecerLink` diz "usa sua
  // chave de IA novamente", que em BYOK é dinheiro do usuário no provedor.
  parecer_artifact_missing: {
    titulo: "Não conseguimos recuperar o parecer deste relatório",
    corpo:
      "O parecer foi gerado, mas não conseguimos carregá-lo agora. " +
      "Atualize a página — se continuar, gere o parecer novamente. " +
      DELIMITACAO_DE_DANO,
    variante: "falha",
    cta: "reprocessar",
  },
};

export function copyDaAusencia(code: ParecerAbsenceCode): ParecerAusenciaCopy {
  return AUSENCIA_COPY[code];
}
