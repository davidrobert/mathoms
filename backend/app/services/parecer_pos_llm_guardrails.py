"""Guardrails determinísticos pós-LLM do parecer (A28.l11 · ADR-292/294/295)."""

# Duas garantias aplicadas em ``_generate_with_llm`` ANTES de ``finalize_output``:
# (1) premissas do Monte Carlo em fallback (``premissas_economicas.status="parcial"``)
#     rebaixam ``confianca alta→media`` de itens ancorados em ``$.if_monte_carlo.*``
#     — rebaixar é a direção segura (ADR-294 "dropar > promover"); nunca bloqueia.
# (2) filtro 3-vias de ``campos_faltantes_pediria_se_iterasse``: path que resolve
#     não-nulo no E5 é espúrio (remove); path nulo com alias conhecido não-nulo é
#     path errado (remove + reanota — alimenta expansão do manifest); path
#     genuinamente ausente é sinal verdadeiro (mantém).
# Coerce/mutação pós-validação, nunca raise, nunca needs_review, zero custo LLM,
# zero reask. NÃO é red line/hard-block (co-design prompt-engineer 2026-07-03).

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Literal, Mapping, Optional

from backend.app.services.parecer_distiller import tokenize_path_part
from pipeline.llm.schemas.parecer_planejador import (
    CampoFaltante,
    ParecerPlanejadorOutput,
    PontoForte,
    Risco,
    Sugestao,
)

logger = logging.getLogger("mathoms.llm.parecer_planejador")

_IF_MONTE_CARLO_PREFIX = "$.if_monte_carlo"
_SUGESTAO_HORIZONS = ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas")
_MC_SECTION = "S7"
_MC_LEMMAS = (
    "monte carlo",
    "independência financeira",
    "independencia financeira",
    "probabilidade de sucesso",
    "probabilidade de atingir",
    "projeção de longo prazo",
    "projecao de longo prazo",
    "cone de",
)
_YEAR_IN_MOTIVO = re.compile(r"\b(20\d{2})\b")

# Path que o LLM pede errado → path canônico onde o dado vive no E5 (via 2 do
# filtro 3-vias). VAZIO desde o PE-3 (r7): a única entrada mapeava
# $.composicao_familiar.dependentes (registro civil) → $.irpf_kpis.dependentes
# (contagem fiscal do ano-base). São domínios e datas de referência distintos —
# tratar um pedido civil como "path errado" do fiscal É a fusão de domínios que
# o PE-3 diagnostica, e o parecer respondia com os dois lados sem reconciliar.
# O mecanismo da via 2 segue vivo para um alias que seja de fato o MESMO fato.
FIELD_PATH_ALIASES: dict[str, str] = {}

REASON_SPURIOUS = "field_request_spurious"
REASON_WRONG_PATH = "field_request_wrong_path"
# Path que resolve no E5 mas ficou fora do catálogo RENDERIZADO: sinaliza truncamento de
# contexto, não alucinação. AUDITA sem remover — ver ADR-206 §Emenda 2026-08-25.
REASON_OUT_OF_CATALOG = "field_request_out_of_catalog"
_REASONS_QUE_REMOVEM = frozenset({REASON_SPURIOUS, REASON_WRONG_PATH})

# Sentinelas de ausência do vocabulário real do E5 (A37.l4 · CTO-02). O boundary
# normaliza produtores novos para null, mas artefatos antigos ainda carregam
# "N/D" string em campo numérico — espelha pipeline/llm/value_formatter.
# O discriminador é a POSIÇÃO, não a palavra: sentinela ocupa o lugar do dado
# (`faixa_etaria="desconhecida"`); valor categórico É o dado (`categoria=
# "nao_identificado"` é balde real de despesa, e ficou FORA de propósito — incluí-lo
# faria o erro simétrico). Lista e medição: ADR-206 §Emenda 2026-08-25.
_ABSENCE_SENTINELS = frozenset(
    {"", "N/D", "nan", "desconhecida", "desconhecido", "indisponivel", "indisponível"}
)


FieldPathState = Literal["missing", "empty", "present"]

# Distingue "a chave não existe" de "a chave existe e não rende dado". O objeto
# sentinela não pode ser None nem "" — esses são valores legítimos de folha.
_ABSENT = object()


def _is_data(v: Any) -> bool:
    """Folha que conta como dado. ``0``/``False`` contam; coleção vazia, ``None``
    e sentinela de ausência ("N/D"/""/"nan") não."""
    if v is None or (isinstance(v, (list, dict)) and not v):
        return False
    return not (isinstance(v, str) and v.strip() in _ABSENCE_SENTINELS)


def _fanout(items: list, idxs_rest: list[str], rest: list[str]) -> Any:
    """Fan-out do ``[*]``. Coleção vazia devolve ``[]`` (o path EXISTE e não rende
    dado); coleção não-vazia cuja folha falta em TODOS os elementos devolve
    ``_ABSENT``. Motivos distintos, e ambos mantêm o pedido do planejador."""
    leaves: list[Any] = []
    for item in items:
        reached = _reach_indexed(item, idxs_rest, rest) if idxs_rest else _reach(item, rest)
        if reached is not _ABSENT:
            leaves.extend(reached)
    return leaves if leaves or not items else _ABSENT


def _index_one(current: Any, idx: str) -> Any:
    """``[n]`` posicional — ``_ABSENT`` quando o índice não existe."""
    try:
        return current[int(idx)]
    except (IndexError, KeyError, TypeError, ValueError):
        return _ABSENT


def _reach_indexed(current: Any, idxs: list[str], rest: list[str]) -> Any:
    """Aplica ``[n]`` posicional; ``[*]`` delega o fan-out sobre a coleção."""
    for pos, idx in enumerate(idxs):
        if idx == "*":
            fan = idxs[pos + 1 :]
            return _fanout(current, fan, rest) if isinstance(current, list) else _ABSENT
        current = _index_one(current, idx)
        if current is _ABSENT:
            return _ABSENT
    return _reach(current, rest)


def _reach(node: Any, parts: list[str]) -> Any:
    """``_ABSENT`` se algum ramo do path não existe; senão a lista de folhas
    alcançadas (uma, ou N quando o path atravessa ``[*]``)."""
    if not parts:
        return [node]
    base, idxs = tokenize_path_part(parts[0])
    if not isinstance(node, Mapping) or base not in node:
        return _ABSENT
    current = node[base]
    return _reach_indexed(current, idxs, parts[1:]) if idxs else _reach(current, parts[1:])


def classify_field_path(e5_data: Mapping[str, Any], path: str) -> FieldPathState:
    """3 estados: ``missing`` (nenhum ramo existe) · ``empty`` (existe e não rende dado —
    observação VÁLIDA do planejador) · ``present`` (ao menos um valor real)."""
    if not path.startswith("$."):
        return "missing"
    reached = _reach(e5_data, path[2:].split("."))
    if reached is _ABSENT:
        return "missing"
    return "present" if any(_is_data(v) for v in reached) else "empty"


# ----------------------------------------------------------------------
# (1) Confiança sob premissa fallback — camada pós-LLM (garantia)
# ----------------------------------------------------------------------


def _premissas_parciais(e5_data: Mapping[str, Any]) -> bool:
    premissas = e5_data.get("premissas_economicas")
    return isinstance(premissas, Mapping) and premissas.get("status") == "parcial"


def _prose_blob(item: Risco | Sugestao) -> str:
    parts = [item.titulo if isinstance(item, Risco) else item.acao]
    if isinstance(item, Risco):
        parts.extend([item.descricao, item.evidencia])
    else:
        caveat = item.impacto_estimado.caveat if item.impacto_estimado is not None else None
        parts.extend([item.impacto_qualitativo, caveat])
    return " ".join(p for p in parts if p).casefold()


def _has_mc_lemma(item: Risco | Sugestao) -> bool:
    blob = _prose_blob(item)
    return any(lemma in blob for lemma in _MC_LEMMAS)


def _anchored_on_monte_carlo(item: Risco | Sugestao) -> bool:
    return any(
        a.path is not None and a.path.startswith(_IF_MONTE_CARLO_PREFIX) for a in item.ancoras
    )


def _depends_on_monte_carlo(item: Risco | Sugestao) -> bool:
    """Âncora MC basta por si; o lemma ainda exige a seção (A40.l49 · [[ADR-438]])."""
    if _anchored_on_monte_carlo(item):
        return True
    return item.section_id == _MC_SECTION and _has_mc_lemma(item)


def _downgrade_risco(risco: Risco) -> Risco:
    return risco.model_copy(update={"confianca": "media"})


def _downgrade_sugestao(sug: Sugestao) -> Sugestao:
    # Espelha _ck_impacto_only_if_alta (ADR-294): model_copy não re-valida, então
    # o drop de impacto_estimado quando confianca != alta é explícito aqui.
    return sug.model_copy(update={"confianca": "media", "impacto_estimado": None})


def _downgrade_bucket(items: list, downgrade_fn) -> tuple[list, int]:
    out, count = [], 0
    for item in items:
        if item.confianca == "alta" and _depends_on_monte_carlo(item):
            out.append(downgrade_fn(item))
            count += 1
        else:
            out.append(item)
    return out, count


def _downgraded_buckets(output: ParecerPlanejadorOutput) -> tuple[dict[str, list], int]:
    update: dict[str, list] = {}
    total = 0
    update["riscos"], n = _downgrade_bucket(output.riscos, _downgrade_risco)
    total += n
    for horizon in _SUGESTAO_HORIZONS:
        update[horizon], n = _downgrade_bucket(getattr(output, horizon), _downgrade_sugestao)
        total += n
    return update, total


def downgrade_confianca_fallback(
    output: ParecerPlanejadorOutput, e5_data: Mapping[str, Any], workspace_id: str
) -> tuple[ParecerPlanejadorOutput, int]:
    """Rebaixa ``confianca alta→media`` de itens que dependem do Monte Carlo
    (S7 + âncora ``$.if_monte_carlo.*`` ou lemma na prosa) quando as premissas
    estão em fallback. Nunca bloqueia (A28.l11)."""
    if not _premissas_parciais(e5_data):
        return output, 0
    update, total = _downgraded_buckets(output)
    if not total:
        return output, 0
    logger.warning(
        "parecer_confianca_rebaixada_premissa_fallback",
        extra={"workspace_id": workspace_id, "count": total},
    )
    return output.model_copy(update=update), total


# ----------------------------------------------------------------------
# (2) Filtro 3-vias de campos_faltantes_pediria_se_iterasse
# ----------------------------------------------------------------------


def _years_in_motivo(motivo: str) -> set[int]:
    return {int(m) for m in _YEAR_IN_MOTIVO.findall(motivo)}


def _irpf_kpis(e5_data: Mapping[str, Any]) -> Mapping[str, Any]:
    block = e5_data.get("irpf_kpis")
    return block if isinstance(block, Mapping) else {}


def _status_for_year(e5_data: Mapping[str, Any], year: int) -> Optional[str]:
    irpf = _irpf_kpis(e5_data)
    por_ano = irpf.get("anos_completude_por_ano")
    if isinstance(por_ano, Mapping) and str(year) in por_ano:
        return str(por_ano[str(year)])
    default = irpf.get("ano_base_default", irpf.get("ano_base"))
    if default == year:
        status = irpf.get("ano_base_completude")
        return str(status) if status is not None else None
    return None


def _motivo_year_uncovered(campo: CampoFaltante, e5_data: Mapping[str, Any]) -> bool:
    """True se o motivo pede um ano sem cobertura completa no E5 (A40.l49 PR3)."""
    years = _years_in_motivo(campo.motivo)
    if not years:
        return False
    return any(_status_for_year(e5_data, year) != "completo" for year in years)


def _classify_campo(
    campo: CampoFaltante, e5_data: Mapping[str, Any], catalog_paths: frozenset[str]
) -> tuple[Optional[str], Optional[str]]:
    """``(reason, alias_path)`` — reason ``None`` = genuinamente ausente (mantém)."""
    if campo.field_path is None:
        return None, None  # path coercido (ADR-292) — motivo carrega o sinal, mantém
    if _motivo_year_uncovered(campo, e5_data):
        return None, None
    if classify_field_path(e5_data, campo.field_path) == "present":
        if campo.field_path in catalog_paths:
            return REASON_SPURIOUS, None
        return REASON_OUT_OF_CATALOG, None
    alias = FIELD_PATH_ALIASES.get(campo.field_path)
    if alias is not None and classify_field_path(e5_data, alias) == "present":
        return REASON_WRONG_PATH, alias
    return None, None


def _audit_entry(campo: CampoFaltante, reason: str, alias: Optional[str] = None) -> dict:
    """Entrada PII-safe p/ ``_meta.field_request_audit`` (path estrutural + motivo LLM)."""
    motivo = campo.motivo
    if alias:
        motivo = f"{campo.motivo} [reanotado: dado presente em {alias}]"
    entry: dict[str, Any] = {"field_path": campo.field_path, "motivo": motivo, "reason": reason}
    if alias:
        entry["alias_path"] = alias
    return entry


def _log_empty_field_path(
    campo: CampoFaltante, e5_data: Mapping[str, Any], workspace_id: str
) -> None:
    """``empty`` é pedido legítimo — telemetria só, sem entrada em ``field_request_audit``
    (promovê-lo a ``reason`` seria mudança de contrato; ver ADR-206)."""
    if campo.field_path is None:
        return
    if classify_field_path(e5_data, campo.field_path) != "empty":
        return
    logger.info(
        "field_request_empty_collection",
        extra={"workspace_id": workspace_id, "field_path": campo.field_path},
    )


def _partition_campos(
    campos: list[CampoFaltante],
    e5_data: Mapping[str, Any],
    workspace_id: str,
    catalog_paths: frozenset[str],
) -> tuple[list[CampoFaltante], list[dict]]:
    """Separa mantidos de auditados, emitindo a telemetria de cada decisão."""
    kept: list[CampoFaltante] = []
    audit: list[dict] = []
    for campo in campos:
        reason, alias = _classify_campo(campo, e5_data, catalog_paths)
        if reason is None:
            kept.append(campo)
            _log_empty_field_path(campo, e5_data, workspace_id)
            continue
        # Audita sem remover: removê-lo apagava do usuário a única pista de truncamento.
        if reason not in _REASONS_QUE_REMOVEM:
            kept.append(campo)
        audit.append(_audit_entry(campo, reason, alias))
        logger.warning(reason, extra={"workspace_id": workspace_id, "field_path": campo.field_path})
    return kept, audit


# `catalog_paths` obrigatório de propósito: com default, call-site novo herdaria em
# silêncio a pergunta ao universo errado. Passe o catálogo RENDERIZADO (o construído tem
# entries que o corte por bytes nunca mostrou ao modelo).
def filter_campos_faltantes(
    output: ParecerPlanejadorOutput,
    e5_data: Mapping[str, Any],
    workspace_id: str,
    *,
    catalog_paths: frozenset[str],
) -> tuple[ParecerPlanejadorOutput, list[dict]]:
    """Filtro 4-vias: remove espúrio/path errado, mantém ausente e fora-de-catálogo."""
    campos = output.campos_faltantes_pediria_se_iterasse
    if not campos:
        return output, []
    kept, audit = _partition_campos(campos, e5_data, workspace_id, catalog_paths)
    if not audit:
        return output, []
    return output.model_copy(update={"campos_faltantes_pediria_se_iterasse": kept}), audit


# ----------------------------------------------------------------------
# (3) Trajetória sem série — coerção pós-LLM (FP-2 D1-B)
# ----------------------------------------------------------------------

#: Espelha ``ParecerPlanejadorOutput.pontos_fortes`` (min_length=3 · ADR-202 §D5).
PONTOS_FORTES_MIN = 3
_DESCRICAO_CAP = 520  # espelha PontoForte.descricao

# Lemmas de VARIAÇÃO NO TEMPO, não de nível. Lista curta, medida sobre o parecer
# do r7: "trajetor" e "ritmo" saíram (2 falso-positivo / 0 verdadeiro — nomeiam
# projeção adiante e nível apurado); "tendenc" saiu por não ter ocorrência que
# permitisse medir e por cobrir prosa de mercado.
_TRAJETORIA_LEMMAS = (
    "acelera",
    "desacelera",
    "vem crescendo",
    "vem caindo",
    "vem melhorando",
    "vem piorando",
    "melhorou",
    "piorou",
)
# "pode acelerar a trajetória" projeta adiante — não afirma o passado (falso-positivo
# medido no risco S4 do r7). A janela cobre o sintagma, não a frase inteira.
_CONDICIONAL_ANTES = re.compile(
    r"(pode|podera|poderia|capaz de|permite|ajuda a|contribui para|para|a fim de)\s+\S{0,14}$"
)
_JANELA_CONDICIONAL = 42

_RESSALVA_TRAJETORIA = (
    "Ressalva: leitura do nível apurado na janela — o relatório não traz série "
    "histórica que sustente afirmação sobre evolução."
)


def ascii_fold(text: Any) -> str:
    decomposed = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _afirma_lemma(blob: str, lemma: str) -> bool:
    """Alguma ocorrência do lemma fora de sintagma condicional."""
    for match in re.finditer(re.escape(lemma), blob):
        janela = blob[max(0, match.start() - _JANELA_CONDICIONAL) : match.start()]
        if not _CONDICIONAL_ANTES.search(janela):
            return True
    return False


def _lemmas_de_trajetoria_afirmada(*textos: Any) -> list[str]:
    """Lemmas presentes em forma AFIRMATIVA (fora de sintagma condicional)."""
    blob = " ".join(ascii_fold(t) for t in textos)
    return [lemma for lemma in _TRAJETORIA_LEMMAS if _afirma_lemma(blob, lemma)]


def _com_ressalva(ponto: PontoForte, ressalva: str) -> PontoForte:
    """Reescreve ``descricao`` na forma ressalvada preservando tema e seção (D5)."""
    espaco = _DESCRICAO_CAP - len(ressalva) - 1
    base = ponto.descricao
    if len(base) > espaco:
        base = base[: espaco - 1].rstrip() + "…"
    return ponto.model_copy(update={"descricao": f"{base} {ressalva}"})


# Degrada, nunca substitui (D5): o piso de 3 é invariante de produto (ADR-202 §D5) e
# baixá-lo seria trocar o problema de lugar. Remove em ordem de índice enquanto o piso
# permitir; o excedente fica com a descrição ressalvada.
def aplicar_piso_pontos_fortes(
    pontos: list[PontoForte], alvos: list[int], ressalva: str, *, remover: bool = True
) -> tuple[list[PontoForte], int, int]:
    """``(pontos, removidos, ressalvados)`` respeitando ``PONTOS_FORTES_MIN``."""
    # `remover=False` ressalva sem deletar — chamador cujo árbitro é o próprio LLM (A40.l116).
    removiveis = max(0, len(pontos) - PONTOS_FORTES_MIN) if remover else 0
    a_remover = set(alvos[:removiveis])
    a_ressalvar = set(alvos[removiveis:])
    saida = [
        _com_ressalva(p, ressalva) if i in a_ressalvar else p
        for i, p in enumerate(pontos)
        if i not in a_remover
    ]
    return saida, len(a_remover), len(a_ressalvar)


def _alvos_trajetoria(pontos: list[PontoForte]) -> list[int]:
    return [
        i for i, p in enumerate(pontos) if _lemmas_de_trajetoria_afirmada(p.titulo, p.descricao)
    ]


def neutralize_trajetoria_sem_serie(
    output: ParecerPlanejadorOutput, workspace_id: str
) -> tuple[ParecerPlanejadorOutput, dict]:
    """Remove ponto forte que afirma trajetória; o diagnóstico geral só é medido."""
    pontos_in = list(output.pontos_fortes)
    diagnostico = _lemmas_de_trajetoria_afirmada(output.diagnostico_geral)
    pontos, removidos, ressalvados = aplicar_piso_pontos_fortes(
        pontos_in, _alvos_trajetoria(pontos_in), _RESSALVA_TRAJETORIA
    )
    telemetria = {
        "trajetoria_pontos_fortes_removidos": removidos,
        "trajetoria_pontos_fortes_ressalvados": ressalvados,
        "trajetoria_diagnostico_lemmas": diagnostico,
    }
    if not (removidos or ressalvados or diagnostico):
        return output, telemetria
    logger.warning(
        "parecer_trajetoria_sem_serie", extra={"workspace_id": workspace_id, **telemetria}
    )
    return output.model_copy(update={"pontos_fortes": pontos}), telemetria


def guardrails_summary(
    *,
    confianca_rebaixada: int,
    audit: list[dict],
    needs_review_triggered: bool = False,
    sugestoes_antagonicas: int = 0,
    extra: Optional[Mapping[str, Any]] = None,
) -> dict:
    """Telemetria dos guardrails. ``needs_review_triggered`` espelha evidencia/red-line
    (ADR-295) — o fallback do MC nunca promove needs_review (A28.l11 / A40.l49)."""
    summary = {
        "confianca_rebaixada": confianca_rebaixada,
        "field_requests_spurious": sum(1 for a in audit if a["reason"] == REASON_SPURIOUS),
        "field_requests_wrong_path": sum(1 for a in audit if a["reason"] == REASON_WRONG_PATH),
        "needs_review_triggered": needs_review_triggered,
        "sugestoes_antagonicas": sugestoes_antagonicas,
    }
    summary.update(extra or {})
    return summary


__all__ = [
    "FIELD_PATH_ALIASES",
    "FieldPathState",
    "PONTOS_FORTES_MIN",
    "REASON_SPURIOUS",
    "REASON_WRONG_PATH",
    "classify_field_path",
    "downgrade_confianca_fallback",
    "filter_campos_faltantes",
    "aplicar_piso_pontos_fortes",
    "ascii_fold",
    "guardrails_summary",
    "neutralize_trajetoria_sem_serie",
]
