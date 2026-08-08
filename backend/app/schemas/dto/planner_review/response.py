"""Response DTOs do aggregate ``PlannerReview`` (ADR-199 + ADR-208 §gating)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Enums user-facing alinhados com pipeline.llm.schemas.parecer_planejador.
# Reexpostos aqui para evitar dep do frontend em módulo pipeline (boundary
# CLAUDE.md: `pipeline/**` permanece backend-side; DTOs HTTP têm shape próprio).
Severidade = Literal["Crítica", "Alta", "Média", "Baixa"]
Prioridade = Literal["P0", "P1", "P2"]
Confianca = Literal["alta", "media", "baixa"]
TemaCanonico = Literal[
    "Proteção",
    "Alocação",
    "Renda passiva",
    "Liquidez",
    "Custo tributário",
    "Saúde de balanço",
    "Diagnóstico de dados",
    "Equilíbrio presente-futuro",
    "Convergência metodológica",
]
FrequenciaRevisao = Literal["mensal", "trimestral", "semestral", "anual"]
SectionId = Literal[
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
]
UnidadeImpacto = Literal["ano", "mes"]
Tier = Literal["free", "premium"]


class PontoForteDTO(BaseModel):
    """Ponto forte user-facing — `ancora_metodologica` removida (sigilo §13 · ADR-207)."""

    model_config = ConfigDict(extra="forbid")

    titulo: str
    descricao: str
    tema_canonico: Optional[TemaCanonico] = None
    section_id: Optional[SectionId] = None


class AncoraDTO(BaseModel):
    """Âncora de citação determinística (ADR-296) — chip D2-puro; `valor_renderizado` é o R$ resolvido do `path` pelo finalize. v1 usa `evidencia_path` (dispatch por `version`)."""

    model_config = ConfigDict(extra="forbid")

    path: Optional[str] = None
    rotulo: Optional[str] = None
    valor_renderizado: Optional[str] = None


class RiscoDTO(BaseModel):
    """Risco user-facing — sem ancora metodológica (sigilo §13)."""

    model_config = ConfigDict(extra="forbid")

    severidade: Severidade
    titulo: str
    descricao: str
    tema_canonico: TemaCanonico
    evidencia: Optional[str] = None
    evidencia_path: Optional[str] = None  # v1 (ADR-296: renderer dispatch por version)
    ancoras: list[AncoraDTO] = Field(default_factory=list)
    section_id: SectionId
    confianca: Optional[Confianca] = None


class ImpactoEstimadoDTO(BaseModel):
    """Impacto estimado (LLM emite só com confianca='alta' — ADR-202 §D6)."""

    model_config = ConfigDict(extra="forbid")

    # Decimal no wire (ADR-090) — Pydantic serializa como string. Frontend
    # converte via Number() na renderização via <MonetaryValue/> (mesma
    # convenção de Suggestion.amount_brl).
    valor_estimado_brl: Decimal
    unidade: UnidadeImpacto
    caveat: str


class SugestaoDTO(BaseModel):
    """Sugestão user-facing — `suggestion_dedup_key` exposto p/ promover->/acao."""

    model_config = ConfigDict(extra="forbid")

    prioridade: Prioridade
    acao: str
    impacto_qualitativo: str
    tema_canonico: TemaCanonico
    confianca: Confianca
    section_id: SectionId
    suggestion_dedup_key: str
    impacto_estimado: Optional[ImpactoEstimadoDTO] = None
    evidencia_path: Optional[str] = None  # v1 (ADR-296: renderer dispatch por version)
    ancoras: list[AncoraDTO] = Field(default_factory=list)


class MetricaDTO(BaseModel):
    """Métrica observável — sem ancora user-facing."""

    model_config = ConfigDict(extra="forbid")

    nome: str
    valor_atual: str
    target: str
    frequencia_revisao: FrequenciaRevisao
    section_id: SectionId
    tema_canonico: Optional[TemaCanonico] = None


class NotaMetodologicaDTO(BaseModel):
    """Nota metodológica — preserva `tema_canonico` (vez de ancora; ADR-207)."""

    model_config = ConfigDict(extra="forbid")

    titulo: str
    conteudo: str
    temas_canonicos: list[TemaCanonico] = Field(default_factory=list)


class GatedCounts(BaseModel):
    """Detalhe por bucket de quantos itens foram cortados pelo tier filter (UI teaser)."""

    model_config = ConfigDict(extra="forbid")

    pontos_fortes: int = 0
    riscos: int = 0
    sugestoes_execucao: int = 0
    sugestoes_taticas: int = 0
    sugestoes_estrategicas: int = 0
    metricas: int = 0
    notas_metodologicas: int = 0


class ParecerContentMeta(BaseModel):
    """Meta de runtime do parecer — auditoria + funil de conversão (ADR-208)."""

    model_config = ConfigDict(extra="forbid")

    tier_at_generation: Tier
    persona_hash: str
    manifest_version: str
    schema_version: str
    model_id: str
    generated_at: str
    gated_counts: GatedCounts = Field(default_factory=GatedCounts)


class ParecerPlanejadorContent(BaseModel):
    """Shape user-facing do parecer pós-tier filter (DTO da resposta HTTP)."""

    model_config = ConfigDict(extra="forbid")

    version: str = "1.0"
    diagnostico_geral: str
    pontos_fortes: list[PontoForteDTO] = Field(default_factory=list)
    riscos: list[RiscoDTO] = Field(default_factory=list)
    sugestoes_execucao: list[SugestaoDTO] = Field(default_factory=list)
    sugestoes_taticas: list[SugestaoDTO] = Field(default_factory=list)
    sugestoes_estrategicas: list[SugestaoDTO] = Field(default_factory=list)
    metricas: list[MetricaDTO] = Field(default_factory=list)
    notas_metodologicas: list[NotaMetodologicaDTO] = Field(default_factory=list)
    meta: ParecerContentMeta


# A ADR-366 §D6 enumerava TRÊS códigos e omitia `parecer_artifact_missing`, que o
# router já produzia. Fechar o vocabulário nos 3 escritos faria o snapshot mentir
# sobre o 4º — correção registrada na emenda de 2026-08-07 da própria ADR.
class PlannerReviewAbsenceDetail(BaseModel):
    """Corpo do 404 — por que não há parecer a servir (ADR-366 §D6)."""

    model_config = ConfigDict(extra="forbid")

    code: Literal[
        "report_not_found",
        "not_generated_yet",
        "generation_unavailable",
        "parecer_artifact_missing",
        "tier_gated",
    ]
    message: str


class PlannerReviewAbsence(BaseModel):
    """Envelope do 404 — o FastAPI aninha o `detail` da ``HTTPException``."""

    model_config = ConfigDict(extra="forbid")

    detail: PlannerReviewAbsenceDetail


class RetentionDetail(BaseModel):
    """Retenção por qualidade — classe FECHADA de motivo (ADR-366 §D3)."""

    model_config = ConfigDict(extra="forbid")

    # Nunca `error_detail` cru: o valor real é vocabulário de operador
    # ("evidencia unverified (severidade alta): risco:3") e, no ramo de sigilo,
    # carrega o próprio termo §13.
    reason: Literal[
        "parecer.citacao_nao_confirmada",
        "parecer.sigilo",
        "parecer.conselho_vedado",
    ]
    items_dropped_count: int = 0


class PlannerReviewResponse(BaseModel):
    """Resposta do endpoint ``GET .../planner-review`` — metadados + conteúdo tipado."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workspace_id: str
    pipeline_run_id: str
    status: str
    persona_hash: str
    manifest_version: str
    schema_version: str
    model_id: str
    tier_at_generation: Tier
    items_shown_count: int
    items_gated_count: int
    cost_usd_cents: int
    created_at: datetime
    published_at: Optional[datetime] = None
    superseded_at: Optional[datetime] = None
    supersedes_id: Optional[str] = None
    superseded_by_id: Optional[str] = None
    immutable_hash: Optional[str] = None

    # Desfecho da geração — eixo ORTOGONAL a `status` (ADR-366 §D1). Discriminante
    # que o cliente consome direto; nunca re-derivado de contador no frontend.
    outcome: Literal["entregue", "entregue_com_retencao", "retido", "nao_registrado"] = (
        "nao_registrado"
    )
    retention: Optional[RetentionDetail] = None
    # Conteúdo tipado (Ato 5). Após `apply_tier_filter`, free traz subset
    # com `meta.gated_counts.<bucket>` > 0 indicando teaser.
    # `None` ⟺ `outcome == "retido"`: o artifact do desfecho retido é o placeholder
    # de `empty_needs_review_output` (3 pontos fortes intitulados "placeholder" +
    # "Inspecione _meta.error_detail"). Sanitizar seria whitelist eterna; `null` é
    # porta fechada e torna a invariante enforçada por tipo (ADR-366 §D5).
    content: Optional[ParecerPlanejadorContent] = None

    @model_validator(mode="after")
    def _outcome_matches_payload(self) -> "PlannerReviewResponse":
        """Correlação desfecho ↔ payload — fail-fast no boundary (ADR-366 §D5)."""
        if (self.outcome == "retido") != (self.content is None):
            raise ValueError(f"outcome={self.outcome!r} incompatível com content presente/ausente")
        if self.retention is None and self.outcome in ("entregue_com_retencao", "retido"):
            raise ValueError(f"outcome={self.outcome!r} exige `retention`")
        return self
