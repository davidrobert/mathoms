/* Eleição da seção corrente, compartilhada pela faixa e pelo índice.
 *
 * O callback de `IntersectionObserver` recebe só as entradas que MUDARAM de
 * interseção naquele disparo. Escolher o topo dessa lista elege um vizinho
 * stale sempre que a seção corrente não mudou de razão — medido em A40.l104:
 * no mesmo scroll, a faixa dizia `S2` e o índice dizia `S8`.
 *
 * Os dois consomem estas funções para que respondam a mesma coisa; divergir
 * seria pior que qualquer uma das duas respostas isolada.
 */

/** Acumula a razão de interseção por id, zerando quem saiu de campo.
 *
 * `Number.MIN_VALUE` como piso de quem intersecta não é enfeite: com
 * `rootMargin` encolhendo o root a ~30% da viewport, uma seção alta cruza o
 * threshold 0 com `intersectionRatio` ≈ 0 — a razão é relativa ao TARGET, e
 * 270px de banda sobre 3000px de seção dá 0,09 no melhor caso e 0 no instante
 * da travessia. Sem o piso, `mostVisibleId` descartava justamente a seção que
 * acabara de entrar, e o índice ficava mudo. */
export function trackRatios(
  entries: readonly IntersectionObserverEntry[],
  ratios: Map<string, number>,
): void {
  for (const entry of entries) {
    const ratio = entry.isIntersecting
      ? Math.max(entry.intersectionRatio, Number.MIN_VALUE)
      : 0;
    ratios.set(entry.target.id, ratio);
  }
}

/** Id de maior razão acumulada; `null` enquanto nada intersecta. Empate resolve
 *  pela ordem de inserção, que é a ordem em que as seções foram observadas. */
export function mostVisibleId(ratios: ReadonlyMap<string, number>): string | null {
  let winner: string | null = null;
  let best = 0;
  for (const [id, ratio] of ratios) {
    if (ratio > best) {
      best = ratio;
      winner = id;
    }
  }
  return winner;
}

/** Mantém `target` visível rolando SÓ `box`, nunca os ancestrais.
 *
 * `scrollIntoView({block:"nearest"})` não serve: a faixa e o índice são
 * `position: sticky`, e o Chromium rola o DOCUMENTO até a posição de fluxo do
 * sticky. Medido em A40.l104 — com `scrollIntoView`, um `window.scrollTo(1500)`
 * voltava para 7px e o FAB "voltar ao topo" nunca aparecia. */
export function keepInView(
  box: HTMLElement,
  target: HTMLElement,
  axis: "x" | "y",
  margin = 24,
): void {
  const t = target.getBoundingClientRect();
  const b = box.getBoundingClientRect();
  const start = axis === "x" ? t.left - (b.left + margin) : t.top - (b.top + margin);
  const end = axis === "x" ? t.right - (b.right - margin) : t.bottom - (b.bottom - margin);
  const delta = start < 0 ? start : end > 0 ? end : 0;
  if (delta === 0) return;
  if (axis === "x") box.scrollLeft += delta;
  else box.scrollTop += delta;
}
