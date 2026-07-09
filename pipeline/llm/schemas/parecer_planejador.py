"""Output schema Pydantic do parecer planejador — espelha JSON Schema (ADR-202/207/209)."""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, BeforeValidator, Field, field_validator, model_validator
from pydantic.json_schema import SkipJsonSchema

logger = logging.getLogger("mathoms.llm.parecer_planejador")


def _normalize_confianca(v):
    """Boundary do LLM (ADR-202 §D6): aceita 'média'/'Alta'/'BAIXA' coercendo para forma canônica lowercase ASCII. Prod 2026-05-18 run 98e60bef: LLM emitia 'média' (PT natural) e 4 retries falhavam contra Literal['alta','media','baixa']. Inconsistência histórica com Severidade=['Crítica','Alta','Média','Baixa'] (com acento+caps) viesa o LLM a usar 'média' aqui também."""
    if not isinstance(v, str):
        return v
    no_accent = unicodedata.normalize("NFKD", v).encode("ASCII", "ignore").decode()
    return no_accent.lower()


# Enums fechados (espelham o JSON Schema $defs).
Severidade = Literal["Crítica", "Alta", "Média", "Baixa"]
Prioridade = Literal["P0", "P1", "P2"]
Confianca = Annotated[Literal["alta", "media", "baixa"], BeforeValidator(_normalize_confianca)]
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


def _jsonpath_drift_category(v: str) -> str:
    """Categoria PII-safe do path inválido. NUNCA retorna o valor — um filtro como
    ``$.ativos[?(@.descricao=~'.*Exemplo.*')]`` carrega nome próprio (LGPD)."""
    if "[?" in v or "?(" in v:
        return "filter"
    if "=~" in v:
        return "regex_match"
    if ".." in v:
        return "recursive_descent"
    return "other"


def _coerce_jsonpath_or_none(v):
    """Boundary do LLM (ADR-292): ``evidencia_path``/``field_path`` fora do subset
    suportado vira ``None`` em vez de hard-fail de schema. Mata o reask storm —
    claude-sonnet-4-6 emite filtros JSONPath (``[?(...)]``, ``=~``) que o
    verificador não resolve (ver ``_JSONPATH_RE`` em planner_drill_down). Mesmo
    padrão de ``_normalize_confianca``: coerção no boundary > ``pattern=`` que
    disparava 4 reasks por geração (incidente parecer 2026-06-16, ~243s/needs_review).
    Path coercido vira ``missing_path`` no verificador (não-fatal em ``warn``)."""
    if not isinstance(v, str) or (len(v) <= 255 and _JSONPATH_RE.match(v)):
        return v
    logger.warning(
        "parecer_evidencia_path_coerced", extra={"category": _jsonpath_drift_category(v)}
    )
    return None


# Aplicado em field_path (CampoFaltante) + Ancora.path.
EvidenciaPath = Annotated[Optional[str], BeforeValidator(_coerce_jsonpath_or_none)]


def _coerce_rotulo_or_none(v):
    """Boundary do LLM (ADR-296): ``rótulo`` fora da FORMA (não-identifier ASCII ou
    > 64 chars) vira ``None`` — nunca reask. A PERTINÊNCIA (``rótulo == root do path``)
    é do verificador, não do schema: o conjunto válido é o catálogo daquela geração,
    não um ``Literal`` estático (root novo no E5 → falso-drop sistemático). Mesmo
    padrão de ``_coerce_jsonpath_or_none``. NUNCA loga o valor (pode carregar prosa)."""
    if not isinstance(v, str) or (len(v) <= 64 and v.isidentifier()):
        return v
    logger.warning("parecer_rotulo_coerced", extra={"len": len(v)})
    return None


# Aplicado em Ancora.rotulo — root da seção dona do path (1º segmento do JSONPath).
Rotulo = Annotated[Optional[str], BeforeValidator(_coerce_rotulo_or_none)]


class Ancora(BaseModel):
    """Citação determinística (ADR-296): LLM emite ``path``+``rotulo`` copiados da MESMA
    linha do catálogo; ``valor_renderizado`` é escrito pelo finalize (não pelo LLM) —
    ``value_mismatch`` por transcrição vira impossível por construção."""

    path: EvidenciaPath = None
    rotulo: Rotulo = None
    valor_renderizado: Optional[str] = None  # escrito pelo finalize, não pelo LLM


# Fim de frase para truncação graciosa — terminador seguido de espaço ou fim.
_SENTENCE_END_RE = re.compile(r"[.!?](?=\s|$)")


def _cut_at_sentence(text: str, cap: int) -> str:
    """Trunca ``text`` em ≤ ``cap`` no último fim de frase; fallback: limite de
    palavra; último recurso: corte duro em ``cap``. Sem reticências (poluiria o
    renderer). Invariante: todos os caps de prosa são >> ``min_length`` do campo,
    logo o corte nunca viola o piso (ADR-294)."""
    head = text[:cap]
    ends = [m.end() for m in _SENTENCE_END_RE.finditer(head)]
    if ends:
        return head[: ends[-1]].rstrip()
    space = head.rfind(" ")
    return (head[:space] if space > 0 else head).rstrip()


def _truncate_prose_at_cap(cap: int):
    """Boundary do LLM (ADR-294): prosa acima do teto é truncada no fim de frase
    em vez de hard-fail → reask. Mata o reask storm de comprimento (incidente
    5@5.com 2026-06-17: ``diagnostico_geral`` 699 chars contra cap stale 500 →
    4 reasks/233s/needs_review). O teto-guia do prompt (~15% abaixo do cap)
    continua sendo a 1ª linha; o schema vira boundary defensivo, não gatilho de
    reask. Como ``BeforeValidator``, roda ANTES do ``field_validator`` de sigilo/
    ticker — a checagem de §13 vê o texto já truncado."""

    def _coerce(v):
        if not isinstance(v, str) or len(v) <= cap:
            return v
        logger.warning("parecer_prose_truncated", extra={"original_len": len(v), "cap": cap})
        return _cut_at_sentence(v, cap)

    return _coerce


def _prose(min_length: int, cap: int):
    """Prosa obrigatória do LLM: truncação no boundary + constraints de tamanho."""
    return Annotated[
        str,
        BeforeValidator(_truncate_prose_at_cap(cap)),
        Field(min_length=min_length, max_length=cap),
    ]


def _prose_opt(cap: int):
    """Prosa opcional do LLM (default ``None``) com truncação no boundary."""
    return Annotated[Optional[str], BeforeValidator(_truncate_prose_at_cap(cap))]


def _check_no_ticker_no_sigilo(text: str) -> str:
    """Valida body textual: sem ticker, sem termos sigilo §13."""
    if _TICKER_RE.search(text):
        raise ValueError("contém ticker brasileiro proibido (ADR-202 §D4)")
    lowered = text.lower()
    for term in _FORBIDDEN_TERMS:
        if term.lower() in lowered:
            raise ValueError(f"contém termo sigilo §13 proibido: {term!r} (ADR-207)")
    return text


#: Hard cap de riscos (ADR-202 §D5) — UX anti-overwhelm deliberado (Cerbasi).
_RISCOS_CAP = 12
_SEVERIDADE_RANK = {"Crítica": 0, "Alta": 1, "Média": 2, "Baixa": 3}


def _severidade_rank(item) -> int:
    """Rank de severidade tolerante a dict cru (Instructor) e a instância Risco."""
    raw = item.get("severidade") if isinstance(item, dict) else getattr(item, "severidade", None)
    return _SEVERIDADE_RANK.get(raw, 4)


class Metadata(BaseModel):
    """Cabeçalho de auditoria do parecer (orchestrator preenche)."""

    persona_hash: str = Field(..., pattern=_SHA256_RE.pattern)
    manifest_version: str = Field(..., pattern=_VERSION_RE.pattern)
    model_id: str = Field(..., min_length=1)
    tier_at_generation: Literal["free", "premium"]
    generated_at: str = Field(..., description="ISO 8601 UTC com offset")


class PontoForte(BaseModel):
    titulo: _prose(3, 120)
    descricao: _prose(1, 520)
    ancora_metodologica: AncoraMetodologica
    tema_canonico: Optional[TemaCanonico] = None
    section_id: Optional[SectionId] = None

    @field_validator("descricao")
    @classmethod
    def _ck_body(cls, v: str) -> str:
        return _check_no_ticker_no_sigilo(v)


class Risco(BaseModel):
    severidade: Severidade
    titulo: _prose(3, 140)
    descricao: _prose(1, 650)
    ancora_metodologica: AncoraMetodologica
    tema_canonico: TemaCanonico
    evidencia: _prose_opt(390) = None
    ancoras: list[Ancora] = Field(default_factory=list, max_length=3)
    section_id: SectionId
    confianca: Optional[Confianca] = None

    @field_validator("descricao")
    @classmethod
    def _ck_body(cls, v: str) -> str:
        return _check_no_ticker_no_sigilo(v)


class ImpactoEstimado(BaseModel):
    # WHY float (ADR-090, co-design data-engineer 2026-07-07 · A33.l1): output do
    # LLM via Instructor é float; orchestrator converte para cents antes de
    # persistir Suggestion.amount_brl_cents — sem acúmulo float. Decimal aqui
    # reabriria risco de reask storm (ADR-292/294) sem eval; reavaliar quando o
    # schema churnar por outro motivo. Exceção nominal no gate
    # dev/check_float_money.py --scan-schemas (LLM_SCHEMAS_FLOAT_ALLOWLIST).
    valor_estimado_brl: float = Field(
        ..., description="Positivo = ganho; negativo = perda evitada."
    )
    unidade: UnidadeImpacto
    caveat: _prose(10, 300)
    # ADR-220: tipagem do impacto. Ausência aceita (compat) → renderer trata
    # como "outro". Para sugestão de tema IF (regra 25× Perini), manifest check
    # exige >=1 sugestão com tipo='patrimonio_alvo' (dev/check_parecer_manifest_in_sync.py).
    tipo: Optional[ImpactoTipo] = None


class Sugestao(BaseModel):
    prioridade: Prioridade
    acao: _prose(10, 340)
    impacto_qualitativo: _prose(10, 420)
    ancora_metodologica: AncoraMetodologica
    tema_canonico: TemaCanonico
    confianca: Confianca
    section_id: SectionId
    suggestion_dedup_key: str = Field(..., pattern=_SHA256_RE.pattern)
    impacto_estimado: Optional[ImpactoEstimado] = None
    ancoras: list[Ancora] = Field(default_factory=list, max_length=3)
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
        """ADR-294 (emenda ADR-202 §D6): impacto_estimado exige confianca='alta'.
        Coerce (drop) em vez de raise — raise virava reask storm (incidente 5@5.com
        2026-06-17). Dropar > promover confianca: promover mentiria sobre a confiança
        que o modelo atribuiu e ADR-208 usa 'alta' como gate de feature paga."""
        if self.impacto_estimado is not None and self.confianca != "alta":
            logger.warning(
                "parecer_impacto_dropped_low_confianca", extra={"confianca": self.confianca}
            )
            self.impacto_estimado = None
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
    titulo: _prose(3, 120)
    conteudo: _prose(20, 780)
    ancoras_metodologicas: list[AncoraMetodologica] = Field(..., min_length=1, max_length=4)

    @field_validator("conteudo")
    @classmethod
    def _ck_body(cls, v: str) -> str:
        return _check_no_ticker_no_sigilo(v)


class CampoFaltante(BaseModel):
    # ADR-292: coerce inválido → None (era ``str`` com ``pattern=``). A regra 3 do
    # prompt instrui o modelo a registrar paths NÃO-whitelistados aqui — i.e.
    # exatamente os que falham o regex. Hard-fail viraria reask; ``motivo`` carrega
    # o sinal mesmo com path None.
    field_path: EvidenciaPath = None
    motivo: str = Field(..., min_length=5, max_length=200)


class ParecerPlanejadorOutput(BaseModel):
    """Output canônico do stage ``review_finances_holistic`` (ADR-199/202)."""

    # ADR-296: bump major — evidencia_path:str → ancoras:[{path,rotulo,valor_renderizado}].
    # Pareceres v1 persistidos não migram (content_json imutável, ADR-204); renderer
    # faz dispatch por version.
    version: str = Field("2.0", pattern=_VERSION_RE.pattern)
    metadata: Metadata
    diagnostico_geral: _prose(50, 750)
    pontos_fortes: list[PontoForte] = Field(..., min_length=3, max_length=6)
    riscos: list[Risco] = Field(..., max_length=_RISCOS_CAP)
    sugestoes_execucao: list[Sugestao] = Field(..., max_length=5)
    sugestoes_taticas: list[Sugestao] = Field(..., max_length=5)
    sugestoes_estrategicas: list[Sugestao] = Field(..., max_length=5)
    metricas: list[Metrica] = Field(..., max_length=10)
    notas_metodologicas: list[NotaMetodologica] = Field(..., max_length=5)
    campos_faltantes_pediria_se_iterasse: Optional[list[CampoFaltante]] = Field(
        default=None, max_length=20
    )
    # A33.l7 — riscos dropados no boundary (>cap 12). ``SkipJsonSchema`` esconde
    # do contrato enviado ao LLM; ``exclude=True`` mantém fora do content_json
    # persistido (schema canônico com additionalProperties:false intacto).
    # Consumido pelo orchestrator → métrica ``mathoms.llm.parecer.riscos_truncados``.
    riscos_truncados: SkipJsonSchema[int] = Field(default=0, exclude=True)

    @field_validator("diagnostico_geral")
    @classmethod
    def _ck_diagnostico(cls, v: str) -> str:
        return _check_no_ticker_no_sigilo(v)

    @model_validator(mode="before")
    @classmethod
    def _truncate_riscos_at_cap(cls, data):
        """Boundary do LLM (padrão ADR-294, A33.l7): >12 riscos trunca mantendo os
        mais severos (sort estável) em vez de hard-fail → reask. O drop alimenta
        ``riscos_truncados`` — telemetria que calibra o cap ("aprovado como está,
        telemetria mede", PLAN-llm-prompts-hardening §Não-objetivos)."""
        if not isinstance(data, dict):
            return data
        riscos = data.get("riscos")
        if not isinstance(riscos, list) or len(riscos) <= _RISCOS_CAP:
            return data
        logger.warning(
            "parecer_riscos_truncados",
            extra={"original_len": len(riscos), "cap": _RISCOS_CAP},
        )
        kept = sorted(riscos, key=_severidade_rank)[:_RISCOS_CAP]
        return {**data, "riscos": kept, "riscos_truncados": len(riscos) - _RISCOS_CAP}

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
    "Ancora",
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
