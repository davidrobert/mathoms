"""Finalização do parecer pós-LLM (ADR-202/204/207)."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Mapping, Optional

from backend.app.services.parecer_citation_catalog import ancora_format_hint
from backend.app.services.parecer_section_route import resolve_destino
from pipeline.llm.schemas.parecer_planejador import (
    Ancora,
    Metadata,
    Metrica,
    ParecerPlanejadorOutput,
    PontoForte,
    Risco,
    Sugestao,
)
from pipeline.llm.tools.planner_drill_down import PlannerDrillDown
from pipeline.llm.value_formatter import _coerce_number, format_value

# Termos sigilo §13 — camada 2 de defesa (persona é 1, UI é 3 — ADR-207).
_FORBIDDEN_TERMS = (
    "Perini",
    "Bruno Perini",
    "Cerbasi",
    "Gustavo Cerbasi",
    "Raul Sena",
    "AUVP",
    "Viver de Renda",
    "Equilíbrio Financeiro",
    "Casais Inteligentes",
    "A Única Verdade Possível",
    "Diagrama do Cerrado",
    "Anderson Investimentos",
)

_FORBIDDEN_LOWER = tuple(t.lower() for t in _FORBIDDEN_TERMS)


def compute_suggestion_dedup_key(*, workspace_id: str, ancora: str, acao: str) -> str:
    """sha256 hex (64) determinístico — mesma (ws, ancora, ação normalizada) → mesma key."""
    acao_norm = re.sub(r"\s+", " ", acao.strip().lower())[:100]
    composite = f"{workspace_id}|{ancora}|{acao_norm}"
    return hashlib.sha256(composite.encode("utf-8")).hexdigest()


def compute_suggestion_thesis_key(
    *,
    workspace_id: str,
    tema_canonico: Optional[str],
    section_id: Optional[str],
    ancora: Optional[str],
) -> Optional[str]:
    """Identidade semântica da tese (ADR-290 B1) — estável entre runs, independe de redação/valor. Campo-fonte ausente → None (linha fica fora do supersede)."""
    if not (tema_canonico and section_id and ancora):
        return None
    composite = f"{workspace_id}|{tema_canonico}|{section_id}|{ancora}"
    return hashlib.sha256(composite.encode("utf-8")).hexdigest()


def severity_from_prioridade(prio: str) -> str:
    """Mapping ADR-153: P0→danger, P1→warning, P2→info."""
    return {"P0": "danger", "P1": "warning", "P2": "info"}.get(prio, "info")


def _scan_field(field_name: str, text: str | None, violations: list[str]) -> None:
    """Append a violations cada termo proibido encontrado."""
    if not text:
        return
    lowered = text.lower()
    for term, term_lower in zip(_FORBIDDEN_TERMS, _FORBIDDEN_LOWER):
        if term_lower in lowered:
            violations.append(f"{field_name}: termo {term!r}")


def _scan_riscos(output: ParecerPlanejadorOutput, v: list[str]) -> None:
    for i, r in enumerate(output.riscos):
        _scan_field(f"riscos[{i}].descricao", r.descricao, v)
        _scan_field(f"riscos[{i}].titulo", r.titulo, v)
        _scan_field(f"riscos[{i}].evidencia", r.evidencia, v)


def _scan_sugestoes(output: ParecerPlanejadorOutput, v: list[str]) -> None:
    for horizon in ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas"):
        for i, s in enumerate(getattr(output, horizon)):
            _scan_field(f"{horizon}[{i}].acao", s.acao, v)
            _scan_field(f"{horizon}[{i}].impacto_qualitativo", s.impacto_qualitativo, v)


def validate_anti_sigilo(output: ParecerPlanejadorOutput) -> list[str]:
    """Retorna lista de violações sigilo §13 sobre o output completo."""
    violations: list[str] = []
    _scan_field("diagnostico_geral", output.diagnostico_geral, violations)
    for i, p in enumerate(output.pontos_fortes):
        _scan_field(f"pontos_fortes[{i}].descricao", p.descricao, violations)
    _scan_riscos(output, violations)
    _scan_sugestoes(output, violations)
    for i, n in enumerate(output.notas_metodologicas):
        _scan_field(f"notas_metodologicas[{i}].conteudo", n.conteudo, violations)
        _scan_field(f"notas_metodologicas[{i}].titulo", n.titulo, violations)
    return violations


def _fix_dedup_keys(sugs: list[Sugestao], workspace_id: str) -> list[Sugestao]:
    """Recalcula suggestion_dedup_key determinístico para lista de sugestões."""
    out: list[Sugestao] = []
    for s in sugs:
        key = compute_suggestion_dedup_key(
            workspace_id=workspace_id, ancora=s.ancora_metodologica, acao=s.acao
        )
        out.append(s.model_copy(update={"suggestion_dedup_key": key}))
    return out


# ADR-290 F3 — cap de geração. Prompt (regra 13) é best-effort; invariante
# de produto é garantido aqui, deterministicamente, antes do persist.
GENERATION_CAP_PER_HORIZON = 3


def _truncation_rank(s: Sugestao) -> tuple[int, int]:
    """(P0 primeiro, |impacto| desc) — P0 sem valor nunca é cortado por R$ alto
    de prioridade menor (proteção fiduciária; count(P0) ≤ 2 cabe no cap)."""
    cents = (
        abs(int(round(s.impacto_estimado.valor_estimado_brl * 100)))
        if s.impacto_estimado is not None
        else -1
    )
    return (1 if s.prioridade == "P0" else 0, cents)


def _truncate_horizon(sugs: list[Sugestao]) -> list[Sugestao]:
    """Mantém as GENERATION_CAP_PER_HORIZON de maior rank, na ordem original."""
    if len(sugs) <= GENERATION_CAP_PER_HORIZON:
        return list(sugs)
    ranked = sorted(sugs, key=_truncation_rank, reverse=True)
    keep = {id(s) for s in ranked[:GENERATION_CAP_PER_HORIZON]}
    return [s for s in sugs if id(s) in keep]


def _finalize_horizon(sugs: list[Sugestao], workspace_id: str) -> list[Sugestao]:
    return _fix_dedup_keys(_truncate_horizon(sugs), workspace_id)


def _capped_horizons(
    output: ParecerPlanejadorOutput, workspace_id: str
) -> dict[str, list[Sugestao]]:
    return {
        h: _finalize_horizon(getattr(output, h), workspace_id)
        for h in ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas")
    }


def _stamped_metadata(
    output: ParecerPlanejadorOutput,
    *,
    persona_hash: str,
    manifest_version: str,
    model_id: str,
    tier: str,
) -> Metadata:
    return output.metadata.model_copy(
        update={
            "persona_hash": persona_hash,
            "manifest_version": manifest_version,
            "model_id": model_id,
            "tier_at_generation": tier,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )


def _resolve_ancora(ancora: Ancora, drill: PlannerDrillDown, labels: Mapping) -> Ancora:
    """Resolve path→valor_renderizado e carimba label do mapa (ADR-296 · A40.l49)."""
    updates: dict = {}
    mapped = labels.get(ancora.path) if ancora.path else None
    if mapped is not None:
        updates["label"] = mapped.label
    if ancora.path is None:
        return ancora.model_copy(update=updates) if updates else ancora
    result = drill.get_e5_jsonpath(ancora.path)
    if result.found:
        updates["valor_renderizado"] = format_value(result.value, ancora_format_hint(ancora.path))
    return ancora.model_copy(update=updates) if updates else ancora


def _stamp_item(
    item: Risco | Sugestao, drill: PlannerDrillDown, labels: Mapping
) -> Risco | Sugestao:
    if not item.ancoras:
        return item
    stamped = [_resolve_ancora(a, drill, labels) for a in item.ancoras]
    return item.model_copy(update={"ancoras": stamped})


def stamp_ancora_values(
    output: ParecerPlanejadorOutput, drill: PlannerDrillDown
) -> ParecerPlanejadorOutput:
    """ADR-296: grava o snapshot valor_renderizado de cada âncora (LLM não autora o número)."""
    from backend.app.services.parecer_manifest import load_manifest

    labels = load_manifest().citation_labels
    update: dict = {"riscos": [_stamp_item(r, drill, labels) for r in output.riscos]}
    for horizon in ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas"):
        update[horizon] = [_stamp_item(s, drill, labels) for s in getattr(output, horizon)]
    return output.model_copy(update=update)


# Unidade do catálogo → (hint do formatter, fator para a escala de exibição). Fechado
# de propósito: unidade nova sem entrada aqui renderizaria pelo ramo errado e ninguém
# veria. A paridade com o catálogo é gateada em teste, no molde do `_BASE_POR_DENOMINADOR`.
# `ratio_0_1` existe porque `protecao_custo_premio` guarda razão 0–1: é aqui que ela vira
# ponto percentual, e é a única conversão de escala do estampador.
_UNIDADE_RENDER: Mapping[str, tuple[str, float]] = {
    "pct": ("pct", 1.0),
    "pct_aa": ("pct", 1.0),
    "meses": ("meses", 1.0),
    "ano": ("int", 1.0),
    "ratio_0_1": ("pct", 100.0),
}

# O hint `meses` do formatter compartilhado arredonda para inteiro
# (`value_formatter._format_unit`), mas `cobertura_meses` é produzido com 1 casa
# (`reserva_emergencia_calculator`). Sobre um alvo inteiro isso publica
# "6 meses ≥ 6 meses" para uma cobertura de 5,6 — **violação renderizada como
# conformidade**, que é a primeira linha do que a [[ADR-399]] existe para impedir.
# A casa decimal fica só nesta rota; o formatter compartilhado não muda, porque os
# outros consumidores dele comparam contra nada.
_CASA_DECIMAL_SIGNIFICATIVA = {"meses"}


def _render_meses(numero: float) -> str:
    return f"{numero:.1f}".replace(".", ",") + " meses"


# `<=`/`>=` viram os glifos que a família lê; `<`/`>` passam.
_OPERADOR_GLIFO = {"<=": "≤", ">=": "≥", "<": "<", ">": ">"}


# A escala roda sobre o número COERCIDO, não sobre o tipo que veio do payload: o
# observado de `protecao_custo_premio` chega como a string "0.005686", e um guard por
# `isinstance(float)` deixaria o fator sem aplicar — publicando 0,0% no lugar de 0,6%,
# que é exatamente o erro de 100× que a renomeação da chave existe para fechar.
def _render_valor(valor, unidade: str) -> Optional[str]:
    render = _UNIDADE_RENDER.get(unidade)
    if render is None or valor is None:
        return None
    hint, fator = render
    numero = _coerce_number(valor)
    if unidade in _CASA_DECIMAL_SIGNIFICATIVA:
        return _render_meses(numero) if numero is not None else None
    if fator != 1.0:
        return format_value(numero * fator, hint) if numero is not None else None
    return format_value(valor, hint)


def _render_target(alvo: Mapping) -> Optional[str]:
    """Alvo publicável exige procedência E limiar E operador — a conjunção é o ponto.
    `procedencia` sozinha não renderiza; `limiar` sozinho é número sem fonte, que é o
    defeito que a [[ADR-399]] fecha."""
    if not (alvo.get("procedencia") and alvo.get("limiar") is not None and alvo.get("operador")):
        return None
    valor = _render_valor(alvo["limiar"], alvo.get("unidade", ""))
    if valor is None:
        return None
    return f"{_OPERADOR_GLIFO.get(alvo['operador'], alvo['operador'])} {valor}"


# Rótulo de último recurso quando o payload é de era anterior ao `rotulo` (#1770) ou não
# publica `kpi_targets`. A chave não é bonita, mas **identifica** — linha sem nome é pior
# que linha com nome técnico: a tabela sai anônima e o leitor não sabe o que observar.
_SEM_OBSERVADO = "valor observado não disponível neste run"


def _rotulo_de(alvo: Mapping, chave: str) -> str:
    return alvo.get("rotulo") or chave.replace("_", " ").capitalize()


def _sem_entrada_no_catalogo(metrica: Metrica) -> Metrica:
    """E5 anterior ao #1591 não publica `kpi_targets`: não se inventa número, mas a
    linha precisa de identidade — 67 artefatos do dogfood caem aqui."""
    return metrica.model_copy(
        update={
            "nome": _rotulo_de({}, metrica.metrica_key),
            "target_motivo": "alvo não resolvido para este KPI",
        }
    )


# Comparador exige os DOIS lados. Publicar alvo prescritivo ao lado de um observado vazio
# é o comparador com um lado fabricado pela ausência — a mesma classe de defeito que a
# [[ADR-399]] fecha, pela outra ponta.
def _par(alvo: Mapping, valor: Optional[str]) -> dict:
    if valor is None:
        return {"target": None, "target_motivo": alvo.get("motivo") or _SEM_OBSERVADO}
    return {"target": _render_target(alvo), "target_motivo": alvo.get("motivo")}


def _stamp_metrica(metrica: Metrica, drill: PlannerDrillDown, alvos: Mapping) -> Metrica:
    alvo = alvos.get(metrica.metrica_key)
    if not isinstance(alvo, Mapping):
        return _sem_entrada_no_catalogo(metrica)
    # `.get()` em TODO campo: `rotulo` nasceu no #1770 e `kpi_targets` existe desde o
    # #1591 — há uma janela de E5 persistidos sem ele. Indexar com `[]` derrubava o stage
    # com KeyError, DEPOIS de pagar a chamada LLM e ANTES de `_write_cache`, então cada
    # retry pagava de novo. Regenerar só o parecer sobre E5 do run base (ADR-291) é a
    # operação normal, não o caso raro.
    observado = drill.get_e5_jsonpath(alvo.get("observado_path") or "")
    valor = _render_valor(observado.value, alvo.get("unidade") or "") if observado.found else None
    return metrica.model_copy(
        update={
            "nome": _rotulo_de(alvo, metrica.metrica_key),
            "valor_atual": valor,
            **_par(alvo, valor),
        }
    )


def _destino(item, e5_data: Optional[Mapping] = None) -> str:
    paths = [a.path for a in getattr(item, "ancoras", None) or []]
    secao, _passo = resolve_destino(
        tema_canonico=getattr(item, "tema_canonico", None),
        ancora_paths=paths,
        metrica_key=getattr(item, "metrica_key", None),
        e5_data=e5_data,
    )
    return secao


def stamp_section_ids(
    output: ParecerPlanejadorOutput, e5_data: Optional[Mapping] = None
) -> ParecerPlanejadorOutput:
    """A40.l117: o destino de leitura é derivado, não escolhido pela prosa."""
    # Roda ANTES dos guardrails pós-LLM — o guard de Monte Carlo lê `section_id`, e lê-lo
    # antes do carimbo era ler a escolha do modelo. O campo já saiu do contrato enviado a
    # ele (``SkipJsonSchema``): aqui não há sobrescrita de autoria, há preenchimento.
    campos = ("riscos", "pontos_fortes", "metricas", *_SUGESTAO_HORIZONS_FINAL)
    return output.model_copy(update={c: _carimba(getattr(output, c), e5_data) for c in campos})


def _carimba(itens: list, e5_data: Optional[Mapping] = None) -> list:
    return [i.model_copy(update={"section_id": _destino(i, e5_data)}) for i in itens]


def stamp_metrica_targets(
    output: ParecerPlanejadorOutput, drill: PlannerDrillDown, alvos: Mapping
) -> ParecerPlanejadorOutput:
    """[[ADR-399]] D1: nome, valor observado e alvo saem do catálogo, não do modelo."""
    # O LLM já não pode emiti-los (``SkipJsonSchema``); aqui eles são escritos. Alvo de
    # KPI órfão fica ``None`` e o motivo vai junto — o item perde o comparador e
    # continua publicado como observacional.
    return output.model_copy(
        update={"metricas": [_stamp_metrica(m, drill, alvos) for m in output.metricas]}
    )


def finalize_output(
    *,
    output: ParecerPlanejadorOutput,
    workspace_id: str,
    tier: str,
    model_id: str,
    persona_hash: str,
    manifest_version: str,
) -> ParecerPlanejadorOutput:
    """Sobrescreve metadata + cap de geração (ADR-290 F3) + dedup_keys determinísticos."""
    metadata = _stamped_metadata(
        output,
        persona_hash=persona_hash,
        manifest_version=manifest_version,
        model_id=model_id,
        tier=tier,
    )
    return output.model_copy(
        update={"metadata": metadata, **_capped_horizons(output, workspace_id)}
    )


_SUGESTAO_HORIZONS_FINAL = ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas")

_PLACEHOLDER_PONTO = PontoForte(
    titulo="placeholder",
    descricao="needs_review placeholder",
    ancora_metodologica="convergencia",
)


def empty_needs_review_output(
    *, persona_hash: str, manifest_version: str, model_id: str, tier: str
) -> ParecerPlanejadorOutput:
    """Placeholder needs_review — não é salvo nem publicado, só serializado pro caller."""
    metadata = Metadata(
        persona_hash=persona_hash,
        manifest_version=manifest_version,
        model_id=model_id,
        tier_at_generation=tier,  # type: ignore[arg-type]
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    return ParecerPlanejadorOutput(
        version="1.0",
        metadata=metadata,
        diagnostico_geral=(
            "Geração interrompida — parecer marcado para revisão. "
            "Inspecione _meta.error_detail para diagnóstico."
        ),
        pontos_fortes=[_PLACEHOLDER_PONTO] * 3,
        riscos=[],
        sugestoes_execucao=[],
        sugestoes_taticas=[],
        sugestoes_estrategicas=[],
        metricas=[],
        notas_metodologicas=[],
    )
