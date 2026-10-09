/** ADR-439 D2/D5 — a nota da residência não apurada: o motivo, a direção do erro e a ação.
 *
 * Vive em `lib/` porque duas superfícies a usam — o relatório (`PatrimonioCategoriasCard`)
 * e o dashboard do `/plano` (`PieNotes`) — e duas redações para o mesmo fato derivam: o
 * relatório chegou a dizer `sem_valor` sem a direção do erro. Voz impessoal
 * (COPY_GUIDELINES §1.2): o workspace pode ser de uma pessoa ou de um casal, e "vocês"
 * erra no primeiro. Quando a falha é do produto, o produto é o sujeito ("não localizamos").
 */
import Link from "next/link";

import type { MotivoBaldeImovel } from "@/types/patrimonio-imovel";

export interface CtaResidencia {
  label: string;
  href: string;
}

export interface NotaResidencia {
  texto: string;
  cta: CtaResidencia;
}

const CONFIG_DA_RESIDENCIA = "/config?tab=members";

// "Indicar" quando não há marcação; "Atualizar" quando há uma e ela envelheceu. Nunca
// "Marcar": quem mora de aluguel não tem imóvel a marcar.
const INDICAR_RESIDENCIA: CtaResidencia = { label: "Indicar residência", href: CONFIG_DA_RESIDENCIA };
const ATUALIZAR_RESIDENCIA: CtaResidencia = {
  label: "Atualizar residência",
  href: CONFIG_DA_RESIDENCIA,
};

// ADR-444 D5: o override já existe, e sem `property_id` não haveria onde regravá-lo — o CTA
// só vem depois da condição de venda. Quem vendeu também cai aqui (ADR-439 §Correção 1), e o
// override não expira (D7): sem a condição, essa família não teria saída da nota.
const NAO_LOCALIZADA: NotaResidencia = {
  texto:
    "Residência não apurada: não localizamos na declaração o imóvel marcado; o valor dele pode estar em Outros imóveis. Se ele foi vendido ou transferido, a marcação ficou desatualizada",
  cta: ATUALIZAR_RESIDENCIA,
};

const NAO_DECLARADA: NotaResidencia = {
  texto:
    "Residência não apurada: falta indicar se é própria ou alugada; até lá, todos os imóveis contam em Outros imóveis",
  cta: INDICAR_RESIDENCIA,
};

/** Exaustivo de propósito — motivo novo no tipo quebra o build aqui. */
export const NOTA_RESIDENCIA_NAO_APURADA: Record<MotivoBaldeImovel, NotaResidencia> = {
  nao_localizada: NAO_LOCALIZADA,
  // As duas formas têm direções opostas e o front não as distingue: zero declarado é saída do
  // patrimônio no ano, e a casa atual cai no desconhecido (ADR-444 D2); valor não apurado
  // tira a casa da soma (ADR-431). A frase carrega os dois ramos, e o CTA é do da saída.
  sem_valor: {
    texto:
      "Residência não apurada: o imóvel marcado está sem valor em 31/12. Se ainda é próprio, ficou fora da soma, e o patrimônio real é maior. Se foi vendido ou transferido, a residência atual pode estar em Outros imóveis",
    cta: ATUALIZAR_RESIDENCIA,
  },
  nao_classificada: {
    texto:
      "Residência não apurada: falta indicar qual imóvel é a residência; até lá, todos os imóveis contam em Outros imóveis",
    cta: INDICAR_RESIDENCIA,
  },
  nao_declarada: NAO_DECLARADA,
  // Só o balde de geradores emite estes dois; na residência valem pelo significado.
  vinculo_perdido: NAO_LOCALIZADA,
  nao_classificados: NAO_DECLARADA,
};

// O CTA continua a frase da condição: em bloco próprio, valeria sem ela e pediria para
// refazer a marcação de quem só perdeu a identidade na leitura (ADR-444 D5).
export function NotaResidenciaNaoApurada({ motivo }: { motivo: MotivoBaldeImovel }) {
  const { texto, cta } = NOTA_RESIDENCIA_NAO_APURADA[motivo];
  return (
    <>
      {texto} ·{" "}
      <Link href={cta.href} className="text-[var(--brand-primary)] underline">
        {cta.label}
      </Link>
    </>
  );
}
