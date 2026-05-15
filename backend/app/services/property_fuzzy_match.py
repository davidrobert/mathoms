"""Fuzzy match de endereço do contribuinte vs descrição de imóvel (ADR-215 P4)."""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Final

from pipeline.domain.services.endereco_canonicalizer import normalize

# Threshold de pré-marcação (auto-sugere com badge). Acima disso a UI
# mostra como sugestão pré-selecionada; usuário ainda confirma (ADR-215).
THRESHOLD_PRE_SELECT: Final[int] = 80

# Threshold para auto-aplicar caso `override_source=fuzzy_match_accepted`
# seja escolhido pela UI sem revisão manual. ADR-215 exige confirmação;
# auto-aplica nunca acontece silenciosamente — esta constante serve como
# tier de confiança (UI pode mostrar destaque mais forte ≥92).
THRESHOLD_HIGH_CONFIDENCE: Final[int] = 92


def match_score(endereco_contribuinte: str, descricao_imovel: str) -> int:
    """Score 0-100 entre endereço normalizado e descrição normalizada do imóvel."""
    a = normalize(endereco_contribuinte or "")
    b = normalize(descricao_imovel or "")
    if not a or not b:
        return 0
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a or not tokens_b:
        return 0
    intersection_len = len(tokens_a & tokens_b)
    # token_set_ratio-like: usa intersection vs string normalizada para
    # tolerar tokens extras (ex: "apto 812" sobra na descrição mas não
    # no endereço fiscal).
    if intersection_len == 0:
        return 0
    intersection_str = " ".join(sorted(tokens_a & tokens_b))
    diff_a = " ".join(sorted(tokens_a - tokens_b))
    diff_b = " ".join(sorted(tokens_b - tokens_a))
    s1 = f"{intersection_str} {diff_a}".strip()
    s2 = f"{intersection_str} {diff_b}".strip()
    ratio_full = SequenceMatcher(None, s1, s2).ratio()
    # Boost quando há tokens raros casando (número da via tipicamente único).
    ratio_intersection = SequenceMatcher(None, intersection_str, intersection_str).ratio()
    score = max(ratio_full, ratio_intersection) * 100
    return int(round(score))


__all__ = [
    "match_score",
    "THRESHOLD_PRE_SELECT",
    "THRESHOLD_HIGH_CONFIDENCE",
]
