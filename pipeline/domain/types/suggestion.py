"""Tipos puros do gerador de Suggestion (Direção E · Onda 5 · ADR-153 / ADR-161).

Esses dataclasses vivem em ``pipeline/domain/types/`` para serem
importáveis por ``pipeline/domain/services/suggestion_generator.py``
sem trazer SQLAlchemy/FastAPI via transitivos do backend.

Backend converte para ``backend.app.models.suggestion.Suggestion`` no
use case :func:`backend.app.application.suggestions.regenerate_for_report`.

ADR-161 (Onda 8): adicionadas 6 regras canônicas (Cerbasi/AUVP completo)
e campo ``category`` para agrupamento semântico (cross-kind).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Optional

Severity = Literal["info", "warning", "danger"]
Origin = Literal["deterministic", "llm"]

# Categorias semânticas (ADR-161 §dedup): agrupam kinds por causa-raiz.
# Permitem dedup cross-kind no futuro (ex.: TRS + aporte_abaixo_meta são
# ambos `alvo_if`). Por ora, apenas tagueia para UI agrupar/filtrar.
Category = Literal[
    "alvo_if",  # TRS, renda passiva real, aporte vs meta IF
    "carteira",  # alocação, concentração por instituição
    "protecao",  # reserva emergência, seguros
    "comportamental",  # taxa poupança, lifestyle creep
    "endividamento",  # dívidas perigosas
]

# Mapeamento canônico kind → category (ADR-161 §dedup).
# FP-003: `dolarizacao_atrasada` removida — USA modo deletado em ADR-168.
KIND_TO_CATEGORY: dict[str, Category] = {
    # v1 (ADR-153)
    "trs_desalinhada": "alvo_if",
    "reserva_insuficiente": "protecao",
    "alocacao_fora_alvo": "carteira",
    "aporte_abaixo_meta": "alvo_if",
    # v2 (ADR-161 — Cerbasi/AUVP completos)
    "endividamento_perigoso": "endividamento",
    "taxa_poupanca_caindo": "comportamental",
    "seguros_insuficientes": "protecao",
    "concentracao_instituicao": "carteira",
    "lifestyle_creep": "comportamental",
    "renda_passiva_real_baixa": "alvo_if",
}

VALID_KINDS = frozenset(KIND_TO_CATEGORY.keys())

VALID_CATEGORIES = frozenset({"alvo_if", "carteira", "protecao", "comportamental", "endividamento"})


@dataclass(frozen=True)
class SuggestionDraft:
    """Sugestão proposta antes de persistência. Imutável."""

    section_id: str
    kind: str
    severity: Severity
    title: str
    rationale: str
    dedup_key: str
    amount_brl: Optional[Decimal] = None
    origin: Origin = "deterministic"
    category: Optional[Category] = None

    def __post_init__(self) -> None:
        if self.kind not in VALID_KINDS:
            raise ValueError(f"kind inválido: {self.kind!r}; aceitos: {sorted(VALID_KINDS)}")
        if self.severity not in ("info", "warning", "danger"):
            raise ValueError(f"severity inválida: {self.severity!r}")
        if self.origin not in ("deterministic", "llm"):
            raise ValueError(f"origin inválida: {self.origin!r}")
        if not self.section_id or not self.title or not self.rationale:
            raise ValueError("section_id/title/rationale são obrigatórios e não-vazios")
        if not self.dedup_key or len(self.dedup_key) < 8:
            raise ValueError("dedup_key precisa ≥ 8 chars")
        if self.category is not None and self.category not in VALID_CATEGORIES:
            raise ValueError(
                f"category inválida: {self.category!r}; aceitos: {sorted(VALID_CATEGORIES)}"
            )
        # Auto-derivação: se category não passada, infere do kind.
        if self.category is None:
            inferred = KIND_TO_CATEGORY.get(self.kind)
            if inferred is not None:
                # frozen=True bloqueia setattr direto; uso __dict__.
                object.__setattr__(self, "category", inferred)
