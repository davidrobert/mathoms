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
    # Sem produtor desde 2026-08-11 (FP-010 · ADR-161 §Emenda): o kind fica no
    # vocabulário porque row histórica com ele precisa continuar legível — kind
    # sem produtor é inerte, kind removido é mudança de contrato.
    "seguros_insuficientes": "protecao",
    "concentracao_instituicao": "carteira",
    "lifestyle_creep": "comportamental",
    "renda_passiva_real_baixa": "alvo_if",
}

VALID_KINDS = frozenset(KIND_TO_CATEGORY.keys())

VALID_CATEGORIES = frozenset({"alvo_if", "carteira", "protecao", "comportamental", "endividamento"})

# Vocabulário de âncora: seções `enabled: true` de `config/report_layout.yaml`
# §estrategico.sections. Cópia à mão porque o domínio não faz I/O (ADR-089);
# o drift contra o YAML e contra o enum de `parecer_planejador.schema.json` é
# gateado em `tests/unit/pipeline/test_suggestion_rules.py`. S5/S6 são IDs
# queimados por design (ADR-168 removeu o modo USA que os ocupava) e nunca
# voltam — `section_id` órfão produz âncora morta no relatório e em /acao.
# Apêndices (APP_A..APP_E) ficam fora: vivem em §estrategico.appendices e não
# hospedam SuggestionCallout.
# Seção habilitada que NÃO é alvo de âncora. `S_PROTECAO` entrou no relatório em
# A40.l88 como render puro: o parecer segue sem ela em `parecer_planejador.schema.json`,
# e ampliar o enum da LLM sem renderer de callout criaria emissor sem leitor — a
# classe que aquela lane fechou. Tirar um id daqui exige adicioná-lo NOS DOIS lados
# no mesmo PR, com bump de PROMPT_VERSION.
SECOES_SEM_ANCORA = frozenset({"S_PROTECAO"})

VALID_SECTION_IDS = frozenset(
    {
        "S1",
        "S2",
        "S3",
        "S4",
        "S7",
        "S8",
        "S_IRPF_RENDA",
        "S_IRPF_OTIMIZACAO",
        "S9",
        "S10",
        "S_parecer",
        "plano_de_acao",
    }
)


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
        if self.section_id not in VALID_SECTION_IDS:
            raise ValueError(
                f"section_id inválido: {self.section_id!r}; aceitos: {sorted(VALID_SECTION_IDS)}"
            )
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
