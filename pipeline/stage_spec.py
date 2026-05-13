"""StageSpec + STAGE_REGISTRY — contrato declarativo de stages (ADR-087).

Substitui o ``FROM_MAP`` manual em ``pipeline/orchestrator.py`` por um registro
declarativo. Cada stage declara o que lê e escreve; a ordem de execução é
explícita em ``FULL_ORDER`` e validada contra as dependências no startup.

**F9.2 (2026-04-25):** ``STAGE_REGISTRY``/``FULL_ORDER``/``DETERMINISTIC_ORDER``
agora usam nomes descritivos (``"reconcile_transactions"``, ``"analyze_finances"``…)
como keys. ``STAGE_RENAME_MAP`` permanece como compat reverso (legacy → descriptive).
Use ``resolve_stage_name(name)`` para normalizar input externo (HTTP, CLI, DB)
para o nome descritivo canônico. Hardening final dos nomes legados: F9.6.

Exemplo:

    >>> FROM_MAP["reconcile_transactions"][0]
    'reconcile_transactions'
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
# Mapa canônico de rename (legacy → descriptive — ADR-093)
# =============================================================================
#
# Em F9.2+ STAGE_REGISTRY usa keys descritivas. STAGE_RENAME_MAP permanece
# como dicionário de compat reverso para CLI alias (e_reset.py --from E3),
# inputs HTTP legados, e leitura de rows DB ainda no formato antigo
# (resolvido em F9.3 via Alembic).

STAGE_RENAME_MAP: dict[str, str] = {
    "E0-audit": "audit_documents",
    "E0-unlock": "unlock_documents",
    "E0-route": "route_documents",
    "E1": "extract_members",
    "E1.5": "extract_baseline",
    "E1.5c": "consolidate_baseline",
    "E1.6": "extract_irpf_full",  # ADR-157 — alias mantido por simetria com E1.5/E1.5c
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
    # ADR-199 — parecer planejador (Ato 4). Alias legado mantido para HTTP/CLI
    # mesmo que o stage seja "novo" e não tenha equivalente pré-F9.2 — preserva
    # invariância STAGE_RENAME_MAP.values() == set(STAGE_REGISTRY) ∪ VIRTUAL.
    "E6-parecer": "review_finances_holistic",
}

LEGACY_TO_DESCRIPTIVE: dict[str, str] = STAGE_RENAME_MAP
DESCRIPTIVE_TO_LEGACY: dict[str, str] = {v: k for k, v in STAGE_RENAME_MAP.items()}


def resolve_stage_name(name: str) -> str:
    """Normaliza nome de stage para descritivo canônico.

    Aceita legacy (``"E3"``) ou descritivo (``"reconcile_transactions"``)
    e retorna sempre o descritivo. Strings desconhecidas passam through.
    Use em qualquer boundary que receba input externo (HTTP, CLI, DB).
    """
    return STAGE_RENAME_MAP.get(name, name)


def to_legacy_stage_name(name: str) -> str:
    """Inverso de ``resolve_stage_name`` — retorna nome legado se descritivo é conhecido.

    Usado por adaptadores que ainda gravam DB rows no formato legado durante
    a janela F9.2 → F9.3.
    """
    return DESCRIPTIVE_TO_LEGACY.get(name, name)


# =============================================================================
# STAGE_REGISTRY — keys descritivas (F9.2+, ADR-093)
# =============================================================================
#
# Notas de design:
#   - unlock_documents/audit_documents/route_documents: não produzem
#     pipeline_artifacts. route_documents move arquivos para data/ via
#     StorageService — o vínculo com extract_* é via Document.stored_path,
#     não via ArtifactStore. Writes=() é correto.
#   - extract_invoices, extract_statements, extract_with_llm: TRÊS artifact
#     stages distintos evitam colisão na UNIQUE constraint quando o mesmo
#     documento é processado por extrator determinístico + LLM fallback.
#     O orquestrador enfileira os três; "E2" (sem sufixo) é apenas alias
#     de FROM_MAP em LEGACY_FROM_ALIASES.
#   - apply_review lê review_finances + analyze_finances e produz
#     analyze_finances_revised (artifact stage virtual — ver
#     VIRTUAL_ARTIFACT_STAGES).

STAGE_REGISTRY: dict[str, StageSpec] = {
    "audit_documents": StageSpec("audit_documents"),
    "unlock_documents": StageSpec("unlock_documents", tier="premium"),
    "route_documents": StageSpec("route_documents", tier="premium"),
    "extract_members": StageSpec(
        "extract_members", writes=("extract_members",), is_llm=True, tier="premium"
    ),
    "extract_baseline": StageSpec(
        "extract_baseline", writes=("extract_baseline",), is_llm=True, tier="premium"
    ),
    "consolidate_baseline": StageSpec(
        "consolidate_baseline", reads=("extract_baseline",), writes=("consolidate_baseline",)
    ),
    # ADR-157: stage paralelo a `extract_baseline` que captura todo conteúdo
    # financeiro do IRPF. `reads=()` por design — `analyze_finances` faz try-read
    # opcional para sobreviver workspaces sem IRPF (G2 sign-off).
    "extract_irpf_full": StageSpec(
        "extract_irpf_full", writes=("extract_irpf_full",), is_llm=True, tier="premium"
    ),
    "extract_invoices": StageSpec("extract_invoices", writes=("extract_invoices",)),
    "extract_statements": StageSpec("extract_statements", writes=("extract_statements",)),
    "extract_with_llm": StageSpec(
        "extract_with_llm", writes=("extract_with_llm",), is_llm=True, tier="premium"
    ),
    "reconcile_transactions": StageSpec(
        "reconcile_transactions",
        reads=("extract_statements", "extract_invoices", "extract_with_llm"),
        writes=("reconcile_transactions",),
    ),
    "categorize_transactions": StageSpec(
        "categorize_transactions",
        reads=("reconcile_transactions",),
        writes=("categorize_transactions",),
    ),
    "analyze_finances": StageSpec(
        "analyze_finances",
        reads=("categorize_transactions", "consolidate_baseline"),
        writes=("analyze_finances",),
    ),
    "generate_narratives": StageSpec(
        "generate_narratives", reads=("analyze_finances",), writes=("generate_narratives",)
    ),
    "validate_cross": StageSpec(
        "validate_cross", reads=("analyze_finances",), writes=("validate_cross",)
    ),
    "review_finances": StageSpec(
        "review_finances",
        reads=("analyze_finances",),
        writes=("review_finances",),
        is_llm=True,
        tier="premium",
    ),
    "apply_review": StageSpec(
        "apply_review",
        reads=("review_finances", "analyze_finances"),
        writes=("analyze_finances_revised",),
    ),
    # ADR-199 (Ato 4): parecer planejador supersede review_finances.
    # Coexiste durante migração; review_finances é removido em sprint+1 pós-cutover.
    "review_finances_holistic": StageSpec(
        "review_finances_holistic",
        reads=("analyze_finances",),
        writes=("review_finances_holistic",),
        is_llm=True,
        tier="premium",
    ),
}


# Artifact stages válidos que NÃO são unidades de execução — apenas categorias
# de artefato escritas por outros stages. Hoje só existe
# ``analyze_finances_revised`` (saída de ``apply_review``).
VIRTUAL_ARTIFACT_STAGES: frozenset[str] = frozenset({"analyze_finances_revised"})


# Sequência intencional de execução. NÃO é derivada automaticamente de
# ``reads``/``writes`` — é uma decisão do orquestrador. ``validate_full_order``
# apenas verifica consistência com as dependências declaradas.
FULL_ORDER: list[str] = [
    "unlock_documents",
    "audit_documents",
    "route_documents",
    "extract_members",
    "extract_baseline",
    "consolidate_baseline",
    "extract_irpf_full",  # ADR-157 — agrupado com docs de ano-base (junto de E1.5)
    "extract_invoices",
    "extract_statements",
    "extract_with_llm",
    "reconcile_transactions",
    "categorize_transactions",
    "analyze_finances",
    "generate_narratives",
    "validate_cross",
    "review_finances",
    "apply_review",
    # ADR-199 — parecer roda após apply_review (consome E5 mas é não-bloqueante
    # do plano de ação determinístico; emite Suggestion(origin=llm) paralelas).
    "review_finances_holistic",
]


# Sequência determinística (pula stages LLM). Derivada do ``STAGE_REGISTRY``.
DETERMINISTIC_ORDER: list[str] = [s for s in FULL_ORDER if not STAGE_REGISTRY[s].is_llm]


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
    "E0": "unlock_documents",  # "a partir de E0" = rodar todo E0-*
    "E2": "extract_invoices",  # "a partir de E2" = rodar todo E2-*
    "E7": "validate_cross",  # "a partir de E7" = rodar todo E7-*
}
