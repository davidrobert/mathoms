/**
 * Helpers compartilhados de cor semântica e label do Score Financeiro.
 * Thresholds: < 40% do max → loss, < 60% → alert, ≥ 60% → gain.
 */

export function getScoreColorVar(valor: number, max: number): string {
  if (valor < max * 0.4) return "var(--semantic-loss)";
  if (valor < max * 0.6) return "var(--semantic-alert)";
  return "var(--semantic-gain)";
}

export function getScoreLabel(valor: number, max: number): string {
  if (valor < max * 0.4) return "Atenção";
  if (valor < max * 0.6) return "Bom";
  return "Ótimo";
}
