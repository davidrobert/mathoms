"""StageSpec + STAGE_REGISTRY — contrato declarativo de stages (ADR-087).

Substitui o ``FROM_MAP`` manual em ``pipeline/orchestrator.py`` por um registro
declarativo. Cada stage declara o que lê e escreve; a ordem de execução é
explícita em ``FULL_ORDER`` e validada contra as dependências no startup.

Durante as Fases 1-8, os identificadores usam nomes legados (``"E2"``,
``"E3"``, ``"E5"``...). A Fase 9 aplica a **Opção A** (ADR-093):
migração completa para nomes descritivos (``"extract_statements"``,
``"reconcile_transactions"``...) via ``STAGE_RENAME_MAP``.

Exemplo:

    >>> FROM_MAP["E3"]
    ['E3', 'E4', 'E5', 'E5.N', 'E7-crossval', 'E7-review', 'E7-apply']
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StageSpec:
    """Especificação declarativa de um stage do pipeline.

    Attributes:
        name:   identificador do stage (nomes legados nas Fases 1-8).
        reads:  outros stages cujos artefatos este stage consome.
        writes: stages de artifact produzidos por este stage. Em geral é
                ``[name]`` (o próprio), mas ``apply_review`` escreve no
                artifact stage virtual ``analyze_finances_revised``.
        is_llm: True se o stage depende de chamada a LLM.
        tier:   ``"free"`` (executado em todos os workspaces) ou ``"premium"``.
    """

    name: str
    reads: tuple[str, ...] = field(default_factory=tuple)
    writes: tuple[str, ...] = field(default_factory=tuple)
    is_llm: bool = False
    tier: str = "free"


# =============================================================================
# STAGE_REGISTRY — nomes legados durante Fases 1-8
# =============================================================================
#
# ⚠️ NÃO use nomes descritivos (``extract_statements``, ``reconcile_transactions``)
# antes da Fase 9. O mapeamento 1-para-1 para os descritivos está em
# ``STAGE_RENAME_MAP`` como fonte de verdade — aplicado em bloco na Fase 9.
#
# Notas de design (preserva semântica da Fase 9):
#   - E0-unlock/E0-audit/E0-route: não produzem pipeline_artifacts. E0-route
#     move arquivos para data/ via StorageService — o vínculo com E2 é via
#     Document.stored_path, não via ArtifactStore. Writes=() é correto.
#   - E2, E2-faturas, E2-extratos, E2-llm: TRÊS artifact stages distintos
#     (``extract_invoices``/``extract_statements``/``extract_with_llm`` pós-9)
#     evitam colisão na UNIQUE constraint quando o mesmo documento é processado
#     por extrator determinístico + LLM fallback. E2 (legado) é a pasta
#     compartilhada em disco; ``E2-faturas`` e ``E2-extratos`` são os wrappers
#     executáveis. O orquestrador hoje só enfileira ``E2-faturas``, ``E2-extratos``
#     e ``E2-llm`` — ``E2`` só aparece em legado (_STAGE_TO_DIR) e como key de
#     compatibilidade no FROM_MAP de entrada (``run_from("E2")``).
#   - E7-apply lê ``E7-review``+``E5`` e produz ``E5-revised`` (o ``render_final_report``
#     lê desse artifact stage). ``E5-revised`` é um artifact stage virtual (não
#     executável) — ver VIRTUAL_ARTIFACT_STAGES.

STAGE_REGISTRY: dict[str, StageSpec] = {
    "E0-audit": StageSpec(
        "E0-audit",
    ),
    "E0-unlock": StageSpec("E0-unlock", tier="premium"),
    "E0-route": StageSpec("E0-route", tier="premium"),
    "E1": StageSpec("E1", writes=("E1",), is_llm=True, tier="premium"),
    "E1.5": StageSpec("E1.5", writes=("E1.5",), is_llm=True, tier="premium"),
    "E1.5c": StageSpec("E1.5c", reads=("E1.5",), writes=("E1.5c",)),
    "E2-faturas": StageSpec("E2-faturas", writes=("E2-faturas",)),
    "E2-extratos": StageSpec("E2-extratos", writes=("E2-extratos",)),
    "E2-llm": StageSpec("E2-llm", writes=("E2-llm",), is_llm=True, tier="premium"),
    "E3": StageSpec("E3", reads=("E2-extratos", "E2-faturas", "E2-llm"), writes=("E3",)),
    "E4": StageSpec("E4", reads=("E3",), writes=("E4",)),
    "E5": StageSpec("E5", reads=("E4", "E1.5c"), writes=("E5",)),
    "E5.N": StageSpec("E5.N", reads=("E5",), writes=("E5.N",)),
    "E7-crossval": StageSpec("E7-crossval", reads=("E5",), writes=("E7-crossval",)),
    "E7-review": StageSpec(
        "E7-review", reads=("E5",), writes=("E7-review",), is_llm=True, tier="premium"
    ),
    "E7-apply": StageSpec("E7-apply", reads=("E7-review", "E5"), writes=("E5-revised",)),
}


# Artifact stages válidos que NÃO são unidades de execução — apenas categorias
# de artefato escritas por outros stages. Hoje só existe ``E5-revised`` (saída
# de ``E7-apply``).
VIRTUAL_ARTIFACT_STAGES: frozenset[str] = frozenset({"E5-revised"})


# Sequência intencional de execução. NÃO é derivada automaticamente de
# ``reads``/``writes`` — é uma decisão do orquestrador. ``validate_full_order``
# apenas verifica consistência com as dependências declaradas.
FULL_ORDER: list[str] = [
    "E0-unlock",
    "E0-audit",
    "E0-route",
    "E1",
    "E1.5",
    "E1.5c",
    "E2-faturas",
    "E2-extratos",
    "E2-llm",
    "E3",
    "E4",
    "E5",
    "E5.N",
    "E7-crossval",
    "E7-review",
    "E7-apply",
]


# Sequência determinística (pula stages LLM). Derivada do ``STAGE_REGISTRY``.
DETERMINISTIC_ORDER: list[str] = [s for s in FULL_ORDER if not STAGE_REGISTRY[s].is_llm]


# =============================================================================
# Mapa canônico de rename (fonte de verdade para Fase 9 — ADR-093)
# =============================================================================

STAGE_RENAME_MAP: dict[str, str] = {
    "E0-audit": "audit_documents",
    "E0-unlock": "unlock_documents",
    "E0-route": "route_documents",
    "E1": "extract_members",
    "E1.5": "extract_baseline",
    "E1.5c": "consolidate_baseline",
    "E2-faturas": "extract_invoices",
    "E2-extratos": "extract_statements",
    "E2-llm": "extract_with_llm",
    "E3": "reconcile_transactions",
    "E4": "categorize_transactions",
    "E5": "analyze_finances",
    "E5.N": "generate_narratives",
    "E7-crossval": "validate_cross",
    "E7-review": "review_finances",
    "E7-apply": "apply_review",
    "E5-revised": "analyze_finances_revised",  # virtual artifact stage
}


# =============================================================================
# API
# =============================================================================


def build_from_map(order: list[str]) -> dict[str, list[str]]:
    """Constrói o índice "pular para stage X" a partir da sequência ``order``.

    Para cada stage em ``order``, retorna a sublista de stages a partir dele
    (inclusive). Usado pelo orquestrador para derivar ``FROM_MAP`` sem
    manutenção manual.

    Exemplos:

        >>> build_from_map(["a", "b", "c"])
        {'a': ['a', 'b', 'c'], 'b': ['b', 'c'], 'c': ['c']}
    """
    return {stage: order[i:] for i, stage in enumerate(order)}


def validate_full_order(order: list[str]) -> None:
    """Valida que ``order`` é consistente com as dependências declaradas.

    Para cada stage, todos os seus ``reads`` devem ser produzidos por algum
    stage que aparece **antes** dele na ordem (ou ser um ``VIRTUAL_ARTIFACT_STAGES``
    escrito por stage anterior).

    Lança:
        ValueError — stage em ``order`` não está no ``STAGE_REGISTRY``.
        AssertionError — dependência é consumida antes de ser produzida.
    """
    produced_by_prefix: set[str] = set()
    for i, stage in enumerate(order):
        if stage not in STAGE_REGISTRY:
            raise ValueError(f"Stage '{stage}' em order não está no STAGE_REGISTRY")
        spec = STAGE_REGISTRY[stage]
        for dep in spec.reads:
            if dep not in produced_by_prefix:
                raise AssertionError(
                    f"Dependência '{dep}' de '{stage}' deve ser produzida antes "
                    f"na ordem (posição atual de '{stage}': {i})"
                )
        produced_by_prefix.update(spec.writes)


def validate_artifact_stage(stage: str) -> None:
    """Valida que ``stage`` é um artifact stage aceitável.

    Aceitável significa:
        - ``stage in STAGE_REGISTRY`` (unidade executável), OU
        - ``stage in VIRTUAL_ARTIFACT_STAGES`` (produzido por outro stage).
    """
    if stage not in STAGE_REGISTRY and stage not in VIRTUAL_ARTIFACT_STAGES:
        raise ValueError(
            f"'{stage}' não é um artifact stage válido "
            f"(nem executável em STAGE_REGISTRY nem em VIRTUAL_ARTIFACT_STAGES)"
        )


# Valida consistência no import — falha rápido se alguém editar FULL_ORDER
# sem ajustar dependências.
validate_full_order(FULL_ORDER)


# =============================================================================
# Aliases legados para compatibilidade com orchestrator.FROM_MAP (por "E2", "E7")
# =============================================================================
#
# O orquestrador atual aceita ``run_from("E2")`` (sem sufixo) e ``run_from("E7")``
# (sem sufixo). Essas chaves não existem como stages executáveis — apenas como
# atalhos de "a partir daqui, inclui todos os subvariantes". Preservado em
# ``build_from_map_with_legacy_aliases`` para o orchestrator.
LEGACY_FROM_ALIASES: dict[str, str] = {
    "E0": "E0-unlock",  # "a partir de E0" = rodar todo E0-*
    "E2": "E2-faturas",  # "a partir de E2" = rodar todo E2-*
    "E7": "E7-crossval",  # "a partir de E7" = rodar todo E7-*
}
