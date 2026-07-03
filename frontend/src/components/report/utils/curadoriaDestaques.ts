/** Curadoria defensiva de destaques (A28.l10).
 *
 * A curadoria canônica acontece a montante no E5 (`pontos_fortes_analyzer` /
 * `build_alertas`); esta camada é o cinto de segurança da UI para payloads
 * antigos ou re-gerados antes do fix: suprime itens circulares de score e
 * deduplica a família de cobertura em meses (reserva ≈ colchão patrimonial).
 * Empty state honesto ("nenhum ponto…") é preferível a item vazio.
 */

export interface DestaqueItem {
  titulo?: string;
  descricao?: string;
  acao?: string;
  impacto?: string;
}

function normalize(text: string): string {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function itemText(item: DestaqueItem): string {
  return normalize(
    [item.titulo, item.descricao, item.acao, item.impacto]
      .filter(Boolean)
      .join(" "),
  );
}

/** Item circular: só restitui o próprio score ("Score financeiro: 7.2/10 (Bom)",
 * "Score Financeiro Positivo") — alerta que não alerta, ponto que não aponta. */
export function isCircularScoreItem(item: DestaqueItem): boolean {
  const text = itemText(item);
  if (!text.includes("score")) return false;
  return /\/\s*10|classificacao|positivo|\bbom\b|excelente/.test(text);
}

/** Chave semântica: colapsa redações diferentes da mesma tese (reserva de
 * emergência ≈ colchão patrimonial = cobertura em meses de despesas). */
export function semanticKey(item: DestaqueItem): string {
  const text = itemText(item);
  if (
    /reserva de emergencia|colchao patrimonial|patrimonio investivel|cobertura de \d+ meses|cobre \d+ meses/.test(
      text,
    )
  ) {
    return "cobertura-meses";
  }
  if (text.includes("score")) return "score";
  return normalize(item.titulo ?? item.acao ?? "").trim() || text;
}

/** Mantém a primeira ocorrência de cada chave semântica e descarta itens
 * circulares de score. Ordem original preservada. */
export function dedupeBySemanticKey<T extends DestaqueItem>(
  items: readonly T[],
): T[] {
  const seen = new Set<string>();
  const out: T[] = [];
  for (const item of items) {
    if (isCircularScoreItem(item)) continue;
    const key = semanticKey(item);
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(item);
  }
  return out;
}
