import { PCT, type AlocacaoDerived } from "./alocacaoCardParts";

// `derived.motivo_supressao` é de máquina: `<slug>: <detalhe>`, causas unidas
// por "; " (`_compor_motivo` em alocacao_alvo_deviation.py). As frases estão em
// paridade literal com o narrador do E5N (alocacao_narrator.py), travada por
// tests/test_alocacao_supressao_copy_parity.py.
const MEMBRO_DA_COBERTURA: Record<string, string> = {
  titular: "do titular",
  conjuge: "do cônjuge",
};

const CAUSA_POR_SLUG: Record<string, string> = {
  balde_negativo: "há bem com valor negativo no patrimônio",
  valor_nao_apurado: "há bem sem valor apurado no patrimônio",
};

const CAUSA_DESCONHECIDA = "parte do patrimônio está sem dado confiável";

function juntarComE(partes: readonly string[]): string {
  if (partes.length <= 1) return partes.join("");
  return `${partes.slice(0, -1).join(", ")} e ${partes[partes.length - 1]}`;
}

function causaCobertura(detalhe: string): string {
  const membros = detalhe
    .split(",")
    .map((m) => m.trim())
    .filter(Boolean)
    .map((m) => MEMBRO_DA_COBERTURA[m] ?? "de um membro da família");
  if (membros.length === 0) return CAUSA_DESCONHECIDA;
  return `os investimentos ${juntarComE([...new Set(membros)])} não foram apurados`;
}

function causaNaoClassificado(detalhe: string): string {
  const pct = /^(\d+(?:\.\d+)?)%/.exec(detalhe.trim());
  if (!pct) return "parte da carteira está sem classe definida";
  return `${PCT.format(Number(pct[1]))}% da carteira está sem classe definida`;
}

function causaDe(parte: string): string {
  const sep = parte.indexOf(":");
  const slug = (sep < 0 ? parte : parte.slice(0, sep)).trim();
  const detalhe = sep < 0 ? "" : parte.slice(sep + 1);
  if (slug === "cobertura_incompleta") return causaCobertura(detalhe);
  if (slug === "nao_classificado") return causaNaoClassificado(detalhe);
  return CAUSA_POR_SLUG[slug] ?? CAUSA_DESCONHECIDA;
}

/** `null` quando o produtor emitiu a indicação de aporte. */
export function motivoDaSupressao(derived: Pick<AlocacaoDerived, "motivo_supressao">): string | null {
  return derived.motivo_supressao?.trim() || null;
}

/** Causas legíveis de `motivo_supressao`, na ordem do produtor e sem repetição. */
export function causasDaSupressao(motivo: string): string[] {
  const causas = motivo
    .split(";")
    .map((p) => p.trim())
    .filter(Boolean)
    .map(causaDe);
  return [...new Set(causas)];
}

/** Rodapé do card quando o produtor não emite a indicação de aporte. */
export function rodapeDaSupressao(motivo: string): string {
  const causas = causasDaSupressao(motivo);
  const porque = causas.length > 0 ? juntarComE(causas) : CAUSA_DESCONHECIDA;
  return `Próximo aporte não indicado: ${porque}.`;
}
