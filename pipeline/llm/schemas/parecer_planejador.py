"""Output schema Pydantic do parecer planejador — espelha JSON Schema (ADR-202/207/209)."""

from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# Enums fechados (espelham o JSON Schema $defs).
Severidade = Literal["Crítica", "Alta", "Média", "Baixa"]
Prioridade = Literal["P0", "P1", "P2"]
Confianca = Literal["alta", "media", "baixa"]
AncoraMetodologica = Literal["perini", "cerbasi", "auvp", "convergencia"]
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
# ADR-220: tipagem semântica do impacto. Evita confundir fluxo anual (R$/ano)
# com patrimônio-alvo (R$ estoque pela regra 25× IF).
ImpactoTipo = Literal[
    "patrimonio_alvo",
    "fluxo_anual",
    "economia_anual_irpf",
    "gap_protecao",
    "outro",
]
# ADR-220: categoria editorial da sugestão, ortogonal a tema_canonico
# (tema é metodologia; categoria é natureza do impacto).
CategoriaSugestao = ImpactoTipo

# Regex anti-ticker (ADR-202 §D4) — body textual user-facing nunca cita ticker BR.
_TICKER_RE = re.compile(r"[A-Z]{4}\d{1,2}|[A-Z]{4}11")
# Regex sigilo §13 — sufixo de defesa (validador Python; persona é 1ª linha; UI é 3ª).
_FORBIDDEN_TERMS = (
    "Perini",
    "Bruno Perini",
    "Cerbasi",
    "Gustavo Cerbasi",
    "Raul Sena",
    "AUVP",
    "Viver de Renda",
    "Equilíbrio Financeiro",
)

# Path JSONPath subset — alinhado a pipeline.llm.tools.planner_drill_down.
# Rejeita `$..*` (recursive descent), filtros, operadores.
_JSONPATH_RE = re.compile(r"^\$\.[A-Za-z_][A-Za-z_0-9\[\]*]*(\.[A-Za-z_][A-Za-z_0-9\[\]*]*)*$")
# sha256 hex (64 chars) — persona_hash / dedup_key / immutable_hash.
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
# Manifest/schema version semver (relaxado: x.y ou x.y.z).
_VERSION_RE = re.compile(r"^[0-9]+\.[0-9]+(\.[0-9]+)?$")


def _check_no_ticker_no_sigilo(text: str) -> str:
    """Valida body textual: sem ticker, sem termos sigilo §13."""
    if _TICKER_RE.search(text):
        raise ValueError("contém ticker brasileiro proibido (ADR-202 §D4)")
    lowered = text.lower()
    for term in _FORBIDDEN_TERMS:
        if term.lower() in lowered:
            raise ValueError(f"contém termo sigilo §13 proibido: {term!r} (ADR-207)")
    return text


class Metadata(BaseModel):
    """Cabeçalho de auditoria do parecer (orchestrator preenche)."""

    persona_hash: str = Field(..., pattern=_SHA256_RE.pattern)
    manifest_version: str = Field(..., pattern=_VERSION_RE.pattern)
    model_id: str = Field(..., min_length=1)
    tier_at_generation: Literal["free", "premium"]
    generated_at: str = Field(..., description="ISO 8601 UTC com offset")


class PontoForte(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=120)
    descricao: str = Field(..., min_length=1, max_length=400)
    ancora_metodologica: AncoraMetodologica
    tema_canonico: Optional[TemaCanonico] = None
    section_id: Optional[SectionId] = None

    @field_validator("descricao")
    @classmethod
    def _ck_body(cls, v: str) -> str:
        return _check_no_ticker_no_sigilo(v)


class Risco(BaseModel):
    severidade: Severidade
    titulo: str = Field(..., min_length=3, max_length=140)
    descricao: str = Field(..., min_length=1, max_length=500)
    ancora_metodologica: AncoraMetodologica
    tema_canonico: TemaCanonico
    evidencia: Optional[str] = Field(None, max_length=300)
    evidencia_path: Optional[str] = Field(None, pattern=_JSONPATH_RE.pattern)
    section_id: SectionId
    confianca: Optional[Confianca] = None

    @field_validator("descricao")
    @classmethod
    def _ck_body(cls, v: str) -> str:
        return _check_no_ticker_no_sigilo(v)


class ImpactoEstimado(BaseModel):
    # WHY float (ADR-090): output do LLM via Instructor é float;
    # orchestrator converte para cents antes de persistir Suggestion.amount_brl_cents.
    valor_estimado_brl: float = Field(  # rate from LLM output (ADR-090: cents on persist)
        ..., description="Positivo = ganho; negativo = perda evitada."
    )
    unidade: UnidadeImpacto
    caveat: str = Field(..., min_length=10, max_length=240)
    # ADR-220: tipagem do impacto. Ausência aceita (compat) → renderer trata
    # como "outro". Para sugestão de tema IF (regra 25× Perini), manifest check
    # exige >=1 sugestão com tipo='patrimonio_alvo' (dev/check_parecer_manifest_in_sync.py).
    tipo: Optional[ImpactoTipo] = None


class Sugestao(BaseModel):
    prioridade: Prioridade
    acao: str = Field(..., min_length=10, max_length=280)
    impacto_qualitativo: str = Field(..., min_length=10, max_length=320)
    ancora_metodologica: AncoraMetodologica
    tema_canonico: TemaCanonico
    confianca: Confianca
    section_id: SectionId
    suggestion_dedup_key: str = Field(..., pattern=_SHA256_RE.pattern)
    impacto_estimado: Optional[ImpactoEstimado] = None
    evidencia_path: Optional[str] = Field(None, pattern=_JSONPATH_RE.pattern)
    # ADR-220: categoria editorial da sugestão (natureza do impacto). Opcional;
    # quando presente, renderer agrupa sugestões irmãs e exibe label semântico.
    # Pode diferir de impacto_estimado.tipo (sugestão pode ter "categoria=if"
    # mas impacto tipado como "fluxo_anual" — irmã traz patrimonio_alvo).
    categoria_sugestao: Optional[CategoriaSugestao] = None

    @field_validator("acao", "impacto_qualitativo")
    @classmethod
    def _ck_body(cls, v: str) -> str:
        return _check_no_ticker_no_sigilo(v)

    @model_validator(mode="after")
    def _ck_impacto_only_if_alta(self) -> "Sugestao":
        if self.impacto_estimado is not None and self.confianca != "alta":
            raise ValueError("impacto_estimado só permitido com confianca='alta' (ADR-202 §D6)")
        return self


class Metrica(BaseModel):
    nome: str = Field(..., min_length=3, max_length=80)
    valor_atual: str = Field(..., min_length=1, max_length=60)
    target: str = Field(..., min_length=1, max_length=60)
    frequencia_revisao: FrequenciaRevisao
    section_id: SectionId
    ancora_metodologica: Optional[AncoraMetodologica] = None
    tema_canonico: Optional[TemaCanonico] = None


class NotaMetodologica(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=120)
    conteudo: str = Field(..., min_length=20, max_length=600)
    ancoras_metodologicas: list[AncoraMetodologica] = Field(..., min_length=1, max_length=4)

    @field_validator("conteudo")
    @classmethod
    def _ck_body(cls, v: str) -> str:
        return _check_no_ticker_no_sigilo(v)


class CampoFaltante(BaseModel):
    field_path: str = Field(..., pattern=_JSONPATH_RE.pattern)
    motivo: str = Field(..., min_length=5, max_length=200)


class ParecerPlanejadorOutput(BaseModel):
    """Output canônico do stage ``review_finances_holistic`` (ADR-199/202)."""

    version: str = Field("1.0", pattern=_VERSION_RE.pattern)
    metadata: Metadata
    diagnostico_geral: str = Field(..., min_length=50, max_length=500)
    pontos_fortes: list[PontoForte] = Field(..., min_length=3, max_length=6)
    riscos: list[Risco] = Field(..., max_length=12)
    sugestoes_execucao: list[Sugestao] = Field(..., max_length=5)
    sugestoes_taticas: list[Sugestao] = Field(..., max_length=5)
    sugestoes_estrategicas: list[Sugestao] = Field(..., max_length=5)
    metricas: list[Metrica] = Field(..., max_length=10)
    notas_metodologicas: list[NotaMetodologica] = Field(..., max_length=5)
    campos_faltantes_pediria_se_iterasse: Optional[list[CampoFaltante]] = Field(
        default=None, max_length=20
    )

    @field_validator("diagnostico_geral")
    @classmethod
    def _ck_diagnostico(cls, v: str) -> str:
        return _check_no_ticker_no_sigilo(v)

    @model_validator(mode="after")
    def _ck_p0_cap(self) -> "ParecerPlanejadorOutput":
        """count(P0) ≤ 2 no agregado dos 3 horizontes (ADR-202 §D3)."""
        all_sug = self.sugestoes_execucao + self.sugestoes_taticas + self.sugestoes_estrategicas
        p0_count = sum(1 for s in all_sug if s.prioridade == "P0")
        if p0_count > 2:
            raise ValueError(f"count(P0)={p0_count} excede o cap 2 no agregado (ADR-202 §D3)")
        return self

    def find_impacto_tipagem_violations(self) -> list[str]:
        """ADR-220 soft check: sugestões IF/renda passiva exigem tipagem patrimonio_alvo."""
        all_sug = self.sugestoes_execucao + self.sugestoes_taticas + self.sugestoes_estrategicas
        if_themed = [s for s in all_sug if s.tema_canonico == "Renda passiva"]
        if not if_themed:
            return []
        has_alvo = any(
            s.impacto_estimado is not None and s.impacto_estimado.tipo == "patrimonio_alvo"
            for s in if_themed
        )
        if has_alvo:
            return []
        return [
            "ADR-220: tema_canonico='Renda passiva' sem irmã marcada "
            "impacto_estimado.tipo='patrimonio_alvo' (regra 25× IF)."
        ]


# LLM emite o schema com ``metadata`` placeholder (orchestrator preenche os
# campos auditáveis após chamar). Para tornar a validação realista durante
# Instructor parsing, o schema completo é o mesmo — o LLM aceita preencher
# qualquer valor; orchestrator sobrescreve antes da persistência. Alternativa
# de "dois schemas" (LLM-out + persisted) foi rejeitada — fricção sem ganho.


__all__ = [
    "AncoraMetodologica",
    "CampoFaltante",
    "CategoriaSugestao",
    "Confianca",
    "FrequenciaRevisao",
    "ImpactoEstimado",
    "ImpactoTipo",
    "Metadata",
    "Metrica",
    "NotaMetodologica",
    "ParecerPlanejadorOutput",
    "PontoForte",
    "Prioridade",
    "Risco",
    "SectionId",
    "Severidade",
    "Sugestao",
    "TemaCanonico",
    "UnidadeImpacto",
]
