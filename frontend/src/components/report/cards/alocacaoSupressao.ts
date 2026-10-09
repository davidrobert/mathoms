import type { AlocacaoDerived } from "./alocacaoCardParts";

// `derived.motivo_supressao` é de máquina: `<slug>: <detalhe>`, causas unidas
// por "; " (`_compor_motivo` em alocacao_alvo_deviation.py). A frase de cada
// motivo é a mesma do narrador do E5N (alocacao_narrator.py): as duas pontas
// leem tests/fixtures/narrativas/alocacao_supressao_frases.json.
//
// Sem número no `nao_classificado`: o percentual do produtor é sobre a carteira
// financeira COM caixa, e os da tabela são sem caixa — o leitor compararia
// bases diferentes.
type CausaCobertura = {
  readonly slug: "cobertura_incompleta";
  readonly membros: readonly string[];
};

export type CausaSupressao =
  | CausaCobertura
  | { readonly slug: "nao_classificado" }
  | { readonly slug: "balde_negativo" }
  | { readonly slug: "valor_nao_apurado"; readonly itens: number | null }
  | { readonly slug: "desconhecida" };

const MEMBRO_DA_COBERTURA: Record<string, string> = {
  titular: "do titular",
  conjuge: "do cônjuge",
};
const MEMBRO_SEM_PAPEL = "de um membro da família";

/** `null` quando o produtor emitiu a indicação de aporte. */
export function motivoDaSupressao(
  derived: Pick<AlocacaoDerived, "motivo_supressao">,
): string | null {
  return derived.motivo_supressao?.trim() || null;
}

function juntarComE(partes: readonly string[]): string {
  if (partes.length <= 1) return partes.join("");
  return `${partes.slice(0, -1).join(", ")} e ${partes[partes.length - 1]}`;
}

function lerCausa(parte: string): CausaSupressao {
  const sep = parte.indexOf(":");
  const slug = (sep < 0 ? parte : parte.slice(0, sep)).trim();
  const detalhe = sep < 0 ? "" : parte.slice(sep + 1).trim();
  if (slug === "cobertura_incompleta") {
    const membros = detalhe
      .split(",")
      .map((m) => m.trim())
      .filter(Boolean);
    return { slug, membros };
  }
  if (slug === "valor_nao_apurado") {
    const n = /^(\d+)/.exec(detalhe);
    return { slug, itens: n ? Number(n[1]) : null };
  }
  if (slug === "nao_classificado" || slug === "balde_negativo") return { slug };
  return { slug: "desconhecida" };
}

/** Causas na ordem do produtor. */
export function lerCausasDaSupressao(motivo: string): CausaSupressao[] {
  return motivo
    .split(";")
    .map((p) => p.trim())
    .filter(Boolean)
    .map(lerCausa);
}

function membrosSemCobertura(causa: CausaCobertura): string {
  const rotulos = causa.membros.map(
    (m) => MEMBRO_DA_COBERTURA[m] ?? MEMBRO_SEM_PAPEL,
  );
  return juntarComE([
    ...new Set(rotulos.length > 0 ? rotulos : [MEMBRO_SEM_PAPEL]),
  ]);
}

function fraseDaCausa(causa: CausaSupressao): string {
  switch (causa.slug) {
    case "cobertura_incompleta":
      return `os investimentos ${membrosSemCobertura(causa)} não foram apurados`;
    case "nao_classificado":
      return "parte da carteira está sem classe definida";
    case "balde_negativo":
      return "há bem com valor negativo registrado no patrimônio";
    case "valor_nao_apurado":
      if (causa.itens === 1) return "há um bem sem valor apurado";
      return causa.itens
        ? `há ${causa.itens} bens sem valor apurado`
        : "há bem sem valor apurado";
    case "desconhecida":
      return "parte do patrimônio está sem valor confiável";
  }
}

function comMaiuscula(frase: string): string {
  return frase.charAt(0).toUpperCase() + frase.slice(1);
}

const SEM_INDICACAO = "Não indicamos a classe do próximo aporte";

/** Rodapé do card quando o produtor não emite a indicação de aporte. */
export function rodapeDaSupressao(causas: readonly CausaSupressao[]): string {
  const lidas: readonly CausaSupressao[] =
    causas.length > 0 ? causas : [{ slug: "desconhecida" }];
  const frases = [...new Set(lidas.map(fraseDaCausa))];
  if (frases.length === 1) return `${SEM_INDICACAO}: ${frases[0]}.`;
  return [
    `${SEM_INDICACAO}.`,
    ...frases.map((f) => `${comMaiuscula(f)}.`),
  ].join(" ");
}

/** Ressalva do KPI "Carteira total": só a cobertura tira valor da base. */
export function ressalvaDoTotal(
  causas: readonly CausaSupressao[],
): string | null {
  const cobertura = causas.find(
    (c): c is CausaCobertura => c.slug === "cobertura_incompleta",
  );
  if (!cobertura) return null;
  return `Este total não inclui os investimentos ${membrosSemCobertura(cobertura)}.`;
}
