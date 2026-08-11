import { LAYOUT } from "@/generated/report-layout";

/** Seções renderizadas pelo shell fora de `layout.sections` (padrão Sumário
 * Executivo). Títulos aqui alimentam nav/TOC quando o YAML só tem o anchor. */
export const SHELL_SECTION_TITLES = {
  V0: "O que mudou",
  perfil: "Perfil da Família",
} as const satisfies Record<string, string>;

/** Ids que o shell renderiza — `ReportSection` os aceita além dos do YAML. */
export type ShellSectionId = keyof typeof SHELL_SECTION_TITLES;

/** Mapa section_id → title do LAYOUT, sem prefixo de apêndice. */
// É o título que as duas superfícies de índice (TopNav e ToC) consomem, via
// `shortLabel`. `sectionHeading` compõe o `<h2>` a partir daqui.
export function buildTitleMap(): Record<string, string> {
  const map: Record<string, string> = { ...SHELL_SECTION_TITLES };
  for (const s of LAYOUT.estrategico.sections) map[s.id] = s.title;
  for (const a of LAYOUT.estrategico.appendices ?? []) map[a.id] = a.title;
  return map;
}

/** section_id → letra do apêndice, declarada em `navigation`. */
// A numeração é literal no YAML e não recomputada (ADR-167): APP_D segue "D"
// mesmo quando APP_C some por hide-when-empty.
function appendixNums(): Record<string, string> {
  const out: Record<string, string> = {};
  for (const group of LAYOUT.navigation?.estrategico ?? []) {
    for (const link of group.links) {
      if (link.is_appendix && link.num) out[link.section_id] = link.num;
    }
  }
  return out;
}

/** Título do `<h2>` da seção — fonte única é o LAYOUT (ADR-076). */
// Existe porque cada seção hardcodava o próprio heading enquanto o índice lia
// o YAML: 6 seções divergiam, e o leitor via o ToC dizer uma coisa e o heading
// outra no mesmo scroll (A40.l7 §Insumos item 2). Derivar mata a classe — não
// há mais onde digitar um título divergente.
export function sectionHeading(id: string): string {
  const title = buildTitleMap()[id] ?? id;
  const num = appendixNums()[id];
  return num ? `Apêndice ${num} — ${title}` : title;
}
