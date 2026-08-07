"""Citação verificada E5→E6 — guardrail 3 camadas do evidencia_path (ADR-279 §E · F4)."""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterator, Optional, Sequence

from pipeline.llm.prompts.parecer_planejador import PROMPT_VERSION
from pipeline.llm.schemas.parecer_planejador import Ancora, ParecerPlanejadorOutput
from pipeline.llm.tools.planner_drill_down import PlannerDrillDown

logger = logging.getLogger("mathoms.llm.parecer_planejador")

# Entra no composite de compute_cache_key — bump invalida caches pré-F4.
# "2" (ADR-292): coerção de evidencia_path inválido → None.
# "3" (ADR-296): contrato ancoras[{path,rotulo,valor_renderizado}]; value_mismatch
# (transcrição de número) substituído por pairing_mismatch (rotulo ↔ root do path).
# "4" (ADR-304): number_in_prose vira violação hard per-item (KR1 A27 — enforcement,
# não prompt); cache pré-enforcement pode conter R$ na prosa.
# "5" (ADR-304 §Emenda 2026-08-03): reversão — number_in_prose volta a telemetria.
# Bump OBRIGATÓRIO: o cache sob ev4 guarda outputs já MUTILADOS (itens dropados pelo
# enforcement) e o hit não repopula evidencia_summary, então serviria a mutilação com
# items_dropped ausente do output_summary — o fix seria "verificado" pelo artefato do bug.
# "6" (ADR-366 §D7): a CAUSA daquele defeito — o hit não repopular — só agora foi
# tocada. O cache passa a guardar envelope {output, evidencia_summary, entries}, e o
# shape antigo não é legível; o bump é o que garante que nenhum hit o alcance.
EVIDENCIA_VERIFICATION_VERSION = "6"

# Inventário de campos de prosa inspecionados — estratificador do summary (A40.l30).
# 1 (implícito, sem a chave): riscos[].descricao/.evidencia + sugestoes_*[].acao — os
# 3 campos que a ADR-304 §"evidência inflada" (b) nomeia contra os 8+ da R22.
# 2: os 9 campos das duas classes (ver _iter_anchorable_items/_iter_prose_only_items).
#
# É chave PRÓPRIA, e não bump de EVIDENCIA_VERIFICATION_VERSION, por decisão do
# co-design `prompt-engineer` 2026-08-07: o bump invalida o cache do envelope
# (ADR-366 §D7) ⇒ força geração nova ⇒ viola a restrição "US$ 0" da lane. Um cache
# hit serve summary antigo, então TODO leitor trata ausência como `unknown` — nunca
# como 0. Comparar janela instrumentada com janela pré-instrumento produziria delta
# de drift falso: é a mesma classe de erro (piso lido como medida) que a lane fecha.
PROSE_INVENTORY_VERSION = 2

_EVIDENCIA_MODE_ENV = "MATHOMS_PARECER_EVIDENCIA_MODE"
_VALID_MODES = ("warn", "strict")

_SUGESTAO_HORIZONS = ("sugestoes_execucao", "sugestoes_taticas", "sugestoes_estrategicas")

# Ancorada em R$ — percentuais, anos, datas e multiplicadores sem R$ ficam fora.
_MONEY_RE = re.compile(
    r"R\$\s*(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?(?:\s*(milh(?:[õo]es|[ãa]o)|mil|mi)\b)?"
)

# Faixa monetária na prosa ("R$ 250-300 mil") — telemetria de number_in_prose
# (ADR-296: prosa não deve conter R$; deve ser 0).
_RANGE_RE = re.compile(r"R\$\s*[\d.,]+\s*(?:-|–|\ba\b|\baté\b)\s*(?:R\$\s*)?[\d.,]+")

# Valor monetário SEM prefixo R$ ("720 mil reais", "720.000 reais", "3 milhões de
# reais") — o LLM pode driblar o R$ (KR1, A27); mesmos grupos de _MONEY_RE para reuso
# de _token_from_match (integer, decimals, mult).
_REAIS_RE = re.compile(
    r"(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?"
    r"(?:\s*(milh(?:[õo]es|[ãa]o)|mil|mi))?\s*(?:de\s+)?reais\b",
    re.IGNORECASE,
)

# Moeda estrangeira na prosa (A40.l30 item 7 — defeito (c) da ADR-304 §"evidência
# inflada"). NÃO é detector de transcrição, é de FABRICAÇÃO: medido em 2026-08-07, o
# exec context não contém nenhum US$ (`FormatHint` não tem `usd`, `_format_brl` é a
# única saída monetária, e `$.narrativas` não é projetado no manifest). Logo US$ na
# prosa não foi copiado de lugar nenhum. Contador SEPARADO de money_tokens_total:
# folhar moedas num número só é o defeito de unidade da ADR-358 §3. Consequência
# assumida: o catálogo é BRL-only por construção (`_entry_for` → format_value(v,"brl")),
# então valor USD não tem rota de âncora — telemetria, nunca gate (ver §Handoff).
_USD_RE = re.compile(
    r"(?:US\$|USD)\s*(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?"
    r"(?:\s*(milh(?:[õo]es|[ãa]o)|mil|mi)\b)?"
)
_DOLARES_RE = re.compile(
    r"(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?"
    r"(?:\s*(milh(?:[õo]es|[ãa]o)|mil|mi))?\s*(?:de\s+)?d[óo]lares\b",
    re.IGNORECASE,
)

# ADR-296: pairing_mismatch substitui value_mismatch (este zerado por construção —
# prosa não tem R$). Ordem preservada p/ telemetria; value_mismatch fica no histórico.
# number_in_prose é pureza monetária da prosa — nem cobertura nem correção de citação;
# fora de coverage/correctness_failed E fora de _HARD_LAYERS (ADR-304 §Emenda
# 2026-08-03: budget monitorado, não invariante ==0). Fica aqui porque dict.fromkeys
# garante a chave em 0 mesmo em run limpo — tirar daqui emudece a telemetria.
_LAYERS = ("missing_path", "whitelist_miss", "resolve_null", "pairing_mismatch", "number_in_prose")
# ADR-292/A26.l6: cobertura (item sem âncora verificável) ≠ correção (âncora que
# resolve errado / rotulo incoerente). Mesma partição que o gate do eval.
_COVERAGE_LAYER = "missing_path"
_CORRECTNESS_LAYERS = ("whitelist_miss", "resolve_null", "pairing_mismatch")
_REASON_TO_LAYER = {
    "path_not_whitelisted": "whitelist_miss",
    "value_null": "resolve_null",
    "value_absent": "resolve_null",
}


@dataclass(frozen=True)
class MoneyToken:
    """Token monetário extraído da prosa — sempre em cents int (ADR-090)."""

    # RESÍDUO SEM CONSUMIDOR (era `value_mismatch`, ADR-296): nenhum call-site lê `cents`
    # nem `half_step_cents` — `verify_evidencia` só usa `len(money_tokens)`. Não existe
    # comparador prosa ↔ `ancoras[].valor_renderizado` em lugar nenhum do repo; é por isso
    # que `number_in_prose` detecta PRESENÇA e não divergência, e é essa ausência que
    # sustenta a reversão da ADR-304 §Emenda 2026-08-03. Mantido (não deletado) porque a
    # lane do comparador real precisa dos dois campos.
    cents: int
    # Semântica PROJETADA (nunca exercida): 0 = valor exato na prosa; >0 = a prosa
    # arredondou ("3 milhões"), então o match seria o intervalo [cents-h, cents+h).
    half_step_cents: int


@dataclass(frozen=True)
class NumberInProseWarning:
    """Prosa de item com valor monetário digitado (ADR-304) — PII-safe: só contagem."""

    item_type: str
    item_index: int
    token_count: int

    def format(self) -> str:
        return (
            f"valor monetário digitado na prosa de {self.item_type}[{self.item_index}] "
            f"({self.token_count} token(s)) — esperado ancoras[].valor_renderizado "
            f"(ADR-296/ADR-304)"
        )


# Recebe dicts já serializados, não `DroppedItem`: o enforcement consome esta
# verificação, e importá-lo aqui inverteria a dependência.
def _retention_block(dropped_items, retention_trigger: Optional[dict]) -> dict:
    """Retenção por qualidade no summary — contagem, tupla estrutural e gatilho."""
    return {
        # ADR-295: itens removidos pelo enforcement per-item no strict (auditável).
        "items_dropped": len(dropped_items),
        # ADR-366 §D3: a tupla estrutural que se perdia — `_parse_hard_violations`
        # descartava a camada e `_check_evidencia` colapsava tudo em `len()`.
        "dropped_items": list(dropped_items),
        # Item que reteve o parecer INTEIRO — diagnóstico, nunca contagem.
        "retention_trigger": retention_trigger,
    }


@dataclass
class EvidenciaVerification:
    """Agregado + detalhe por-path da verificação (telemetria F4)."""

    verified: int = 0
    failed: int = 0
    failures_by_layer: dict[str, int] = field(default_factory=lambda: dict.fromkeys(_LAYERS, 0))
    entries: list[dict] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)  # "tipo:índice:camada"
    # UNIDADES DIFERENTES, não confundir ao ler budget (ADR-358 §3 — régua errada):
    # money_tokens_total conta TOKENS monetários; failures_by_layer["number_in_prose"]
    # conta ITENS ofensores. O eval expõe o primeiro sob o nome do segundo.
    # ancoras_total é a densidade de citação (piso anti-sub-citação, ADR-296).
    money_tokens_total: int = 0
    range_in_scalar_count: int = 0
    ancoras_total: int = 0
    # DENOMINADOR (A40.l30 item 1). Sem ele, "densidade" conflacia *menos âncoras por
    # item* com *menos itens* — é o que impedia decompor o 9→5 medido pela A40.l16.
    # Conta só itens da classe ANCORÁVEL (têm contrato `ancoras` no schema); prosa da
    # classe B entra em money_tokens_total e NÃO no denominador, senão "âncoras por
    # item" divide por itens que não podem ter âncora.
    itens_total: int = 0
    # Item com `ancoras: []` — hoje contribui 0 em ancoras_total e não gera entry
    # (fail-open que explica `evidencia_failed: 0` nos 19 runs). Aqui ele é CONTADO.
    itens_sem_ancora: int = 0
    # Moeda estrangeira e métricas: telemetria em chave própria, FORA de
    # money_tokens_total (ADR-358 §3 — não folhar unidades diferentes num número só).
    money_tokens_usd: int = 0
    # `metricas[].valor_atual`/`target` são "string formatada" POR CONTRATO e contêm
    # R$ legitimamente hoje — incluí-los na pureza de prosa produziria falso-positivo
    # em massa. Medido aqui como *before* executável para a RV2-01 do
    # PLAN-pipeline-review-r2, que dá `Metrica.ancoras` e sobrescreve `valor_atual`
    # pelo valor stampado do E5. NENHUM gate lê esta chave.
    metricas_money_tokens: int = 0
    # ADR-304: sinal auditável por item ofensor (padrão ADR-097 D1).
    number_in_prose_warnings: list[NumberInProseWarning] = field(default_factory=list)

    @property
    def coverage_failed(self) -> int:
        """Citações sem path verificável (missing_path) — gap de cobertura."""
        return self.failures_by_layer.get(_COVERAGE_LAYER, 0)

    @property
    def correctness_failed(self) -> int:
        """Citações que resolvem ERRADO — é o que o gate strict (l2) bloqueia."""
        return sum(self.failures_by_layer.get(k, 0) for k in _CORRECTNESS_LAYERS)

    def by_section(self) -> dict[str, dict[str, int]]:
        """Outcomes por item_type (risco/sugestões) — qual seção perde citação."""
        out: dict[str, dict[str, int]] = {}
        for entry in self.entries:
            section = out.setdefault(entry["item_type"], {})
            section[entry["outcome"]] = section.get(entry["outcome"], 0) + 1
        return out

    def summary(
        self,
        *,
        needs_review_triggered: bool,
        dropped_items: Sequence[dict] = (),
        retention_trigger: Optional[dict] = None,
    ) -> dict:
        return {
            **self._verification_block(),
            **_retention_block(dropped_items, retention_trigger),
            "prompt_version": PROMPT_VERSION,
            "needs_review_triggered": needs_review_triggered,
        }

    def _verification_block(self) -> dict:
        """Agregados da verificação de citação — sem nada de enforcement."""
        return {
            "evidencia_verified": self.verified,
            "evidencia_failed": self.failed,
            "coverage_failed": self.coverage_failed,
            "correctness_failed": self.correctness_failed,
            "failures_by_layer": dict(self.failures_by_layer),
            "by_section": self.by_section(),
            "money_tokens_total": self.money_tokens_total,
            "range_in_scalar_count": self.range_in_scalar_count,
            "ancoras_total": self.ancoras_total,
            "itens_total": self.itens_total,
            "itens_sem_ancora": self.itens_sem_ancora,
            "money_tokens_usd": self.money_tokens_usd,
            "metricas_money_tokens": self.metricas_money_tokens,
            "prose_inventory_version": PROSE_INVENTORY_VERSION,
        }


def resolve_evidencia_mode(manifest_mode: str) -> str:
    """Modo efetivo: env override > manifest > 'warn' (default fail-open)."""
    env_mode = os.environ.get(_EVIDENCIA_MODE_ENV, "").strip().lower()
    mode = env_mode or (manifest_mode or "warn").strip().lower()
    return mode if mode in _VALID_MODES else "warn"


def log_evidencia_kpi(verification: "EvidenciaVerification", workspace_id: str) -> None:
    """KPI de citação por geração (A26.l6) — cobertura vs. correção, PII-free, gate-auditável."""
    logger.info(
        "parecer_evidencia_kpi",
        extra={
            "workspace_id": workspace_id,
            "verified": verification.verified,
            "coverage_failed": verification.coverage_failed,
            "correctness_failed": verification.correctness_failed,
        },
    )


def verify_evidencia(
    *, output: ParecerPlanejadorOutput, drill: PlannerDrillDown
) -> EvidenciaVerification:
    """Cross-check por âncora sobre riscos + sugestões; ``drill`` é instância dedicada."""
    result = EvidenciaVerification()
    for item_type, index, prose_fields, ancoras in _iter_anchorable_items(output):
        _record_prose(result, item_type=item_type, index=index, prose_fields=prose_fields)
        result.itens_total += 1
        result.ancoras_total += len(ancoras)
        if not ancoras:
            result.itens_sem_ancora += 1
        for ancora in ancoras:
            layer = _check_anchor(drill, ancora)
            _record(result, item_type=item_type, index=index, path=ancora.path, layer=layer)
    for item_type, index, prose_fields in _iter_prose_only_items(output):
        _record_prose(result, item_type=item_type, index=index, prose_fields=prose_fields)
    result.metricas_money_tokens = _count_metricas_money(output)
    return result


def _record_prose(
    result: EvidenciaVerification,
    *,
    item_type: str,
    index: int,
    prose_fields: list[Optional[str]],
) -> None:
    """Pureza monetária de um item (ADR-296: prosa NÃO deve conter R$)."""
    money_tokens = _extract_money_tokens(prose_fields)
    result.money_tokens_total += len(money_tokens)
    result.money_tokens_usd += len(_extract_usd_tokens(prose_fields))
    result.range_in_scalar_count += _count_ranges(prose_fields)
    if money_tokens:
        # Entra em `violations` para auditoria, mas a camada está FORA de
        # _HARD_LAYERS: o enforcement strict a ignora (ADR-304 §Emenda 2026-08-03).
        _record_number_in_prose(
            result, item_type=item_type, index=index, token_count=len(money_tokens)
        )


# Classe ANCORÁVEL — o schema dá `ancoras` a estes itens, logo são o denominador
# legítimo de "âncoras por item". 6 dos 9 campos do inventário v2.
def _iter_anchorable_items(
    output: ParecerPlanejadorOutput,
) -> Iterator[tuple[str, int, list[Optional[str]], list[Ancora]]]:
    """(item_type, índice, campos de prosa, âncoras) por item com contrato de âncora."""
    for i, risco in enumerate(output.riscos):
        yield "risco", i, [risco.titulo, risco.descricao, risco.evidencia], risco.ancoras
    for horizon in _SUGESTAO_HORIZONS:
        for i, sug in enumerate(getattr(output, horizon)):
            yield horizon, i, _sugestao_prose(sug), sug.ancoras


def _sugestao_prose(sug) -> list[Optional[str]]:
    """`impacto_qualitativo` é nomeado na R22 e nunca foi inspecionado; `caveat` é
    prosa user-visible que entra pelo mesmo item."""
    caveat = sug.impacto_estimado.caveat if sug.impacto_estimado is not None else None
    return [sug.acao, sug.impacto_qualitativo, caveat]


# Classe PROSA-SEM-ÂNCORA — R22 nomeia `diagnostico_geral`, `descricao`, `conteudo` e
# `notas_metodologicas[]`, mas o schema não lhes dá `ancoras`. Entram na pureza
# monetária e ficam FORA do denominador: dividir por item que não pode ancorar
# produziria densidade estruturalmente inatingível.
# `campos_faltantes_pediria_se_iterasse[].motivo` fica fora por outro critério —
# não é renderizado ao usuário (`rg 'campos_faltantes' frontend/src` = 0 hits; vira
# `ReviewReason`). O critério de fronteira do inventário é **prosa renderizada ao
# usuário**, não "nomeado na R22" — sem regra explícita o próximo agente re-litiga.
def _iter_prose_only_items(
    output: ParecerPlanejadorOutput,
) -> Iterator[tuple[str, int, list[Optional[str]]]]:
    """(item_type, índice, campos de prosa) por item user-visible sem contrato de âncora."""
    yield "diagnostico_geral", 0, [output.diagnostico_geral]
    for i, ponto in enumerate(output.pontos_fortes):
        yield "ponto_forte", i, [ponto.titulo, ponto.descricao]
    for i, nota in enumerate(output.notas_metodologicas):
        yield "nota_metodologica", i, [nota.titulo, nota.conteudo]


def _count_metricas_money(output: ParecerPlanejadorOutput) -> int:
    """Tokens monetários em `metricas[]` — telemetria isolada (ver campo no agregado)."""
    fields = [f for m in output.metricas for f in (m.nome, m.valor_atual, m.target)]
    return len(_extract_money_tokens(fields)) + len(_extract_usd_tokens(fields))


def _check_anchor(drill: PlannerDrillDown, ancora: Ancora) -> Optional[str]:
    """None = verificado; senão a camada que falhou (ADR-296)."""
    if ancora.path is None:
        return "missing_path"  # path coercido (ADR-292) — cobertura, fail-open
    tool_result = drill.get_e5_jsonpath(ancora.path)
    if not tool_result.found:
        return _REASON_TO_LAYER.get(tool_result.reason or "", "resolve_null")
    # Cross-check determinístico: rotulo deve casar a seção dona do path (1º segmento).
    if ancora.rotulo != ancora.path[2:].split(".", 1)[0]:
        return "pairing_mismatch"
    return None


def _record(
    result: EvidenciaVerification,
    *,
    item_type: str,
    index: int,
    path: Optional[str],
    layer: Optional[str],
) -> None:
    outcome = layer or "verified"
    result.entries.append(
        {"item_type": item_type, "item_index": index, "path": path, "outcome": outcome}
    )
    if layer is None:
        result.verified += 1
        return
    result.failed += 1
    result.failures_by_layer[layer] += 1
    result.violations.append(f"{item_type}:{index}:{layer}")
    # NUNCA logar o valor — só camada + path (PII/byte-identidade).
    logger.warning(
        "parecer_evidencia_violation",
        extra={"layer": layer, "path": path, "item": f"{item_type}[{index}]"},
    )


def _record_number_in_prose(
    result: EvidenciaVerification, *, item_type: str, index: int, token_count: int
) -> None:
    """Pureza monetária da prosa — budget monitorado (ADR-296 §Re-eval), não hard."""
    # Camada separada dos contadores de âncora (`verified`/`failed` seguem contando só
    # citações) e incrementa por ITEM ofensor, não por token — ver §UNIDADES acima.
    warning = NumberInProseWarning(item_type=item_type, item_index=index, token_count=token_count)
    result.number_in_prose_warnings.append(warning)
    result.failures_by_layer["number_in_prose"] += 1
    result.violations.append(f"{item_type}:{index}:number_in_prose")
    result.entries.append(
        {"item_type": item_type, "item_index": index, "path": None, "outcome": "number_in_prose"}
    )
    # NUNCA logar o valor — só contagem + item (PII).
    logger.warning("parecer_number_in_prose_violation", extra={"detail": warning.format()})


# ----------------------------------------------------------------------
# Extração de tokens monetários da prosa
# ----------------------------------------------------------------------


def _extract_money_tokens(prose_fields: list[Optional[str]]) -> list[MoneyToken]:
    return _tokens_for(prose_fields, (_MONEY_RE, _REAIS_RE))


def _extract_usd_tokens(prose_fields: list[Optional[str]]) -> list[MoneyToken]:
    return _tokens_for(prose_fields, (_USD_RE, _DOLARES_RE))


def _tokens_for(
    prose_fields: list[Optional[str]], patterns: tuple[re.Pattern, ...]
) -> list[MoneyToken]:
    tokens: list[MoneyToken] = []
    for text in prose_fields:
        if text:
            tokens.extend(_dedupe_by_span(text, patterns))
    return tokens


def _dedupe_by_span(text: str, patterns: tuple[re.Pattern, ...]) -> list[MoneyToken]:
    """Um valor monetário = UM token. "R$ 720 mil reais" casa `_MONEY_RE` (0,10) E
    `_REAIS_RE` (3,16) — spans sobrepostos, 2 tokens para 1 valor. É o defeito (a) da
    ADR-304 §"evidência inflada" ("conta matches, não valores distintos"), e sem o
    dedupe ampliar o inventário de 3→9 campos re-baselinaria um número simultaneamente
    piso (poucos campos) e inflado (match duplo) — ninguém poderia interpretá-lo.
    Vence o match que começa antes; empate no início, o mais longo (o com prefixo R$,
    cujo `_token_from_match` lê o multiplicador correto)."""
    matches = sorted(
        (m for pattern in patterns for m in pattern.finditer(text)),
        key=lambda m: (m.start(), -m.end()),
    )
    kept: list[re.Match] = []
    covered_end = -1
    for match in matches:
        if match.start() < covered_end:
            continue
        kept.append(match)
        covered_end = match.end()
    return [_token_from_match(m) for m in kept]


def _count_ranges(prose_fields: list[Optional[str]]) -> int:
    """Faixas R$ X–Y na prosa de item cujo campo-fonte não é faixa legítima."""
    return sum(len(_RANGE_RE.findall(text)) for text in prose_fields if text)


def _token_from_match(m: re.Match) -> MoneyToken:
    integer, decimals, mult = m.group(1), m.group(2), m.group(3)
    base = Decimal(integer.replace(".", ""))
    if decimals:
        base += Decimal(decimals) / (Decimal(10) ** len(decimals))
    if not mult:
        return MoneyToken(cents=_to_cents(base), half_step_cents=0)
    factor = Decimal(1_000) if mult == "mil" else Decimal(1_000_000)
    half_step = factor / (Decimal(10) ** len(decimals or "")) / 2
    return MoneyToken(cents=_to_cents(base * factor), half_step_cents=_to_cents(half_step))


def _to_cents(value: Decimal) -> int:
    return int((value * 100).to_integral_value(rounding=ROUND_HALF_UP))


__all__ = [
    "EVIDENCIA_VERIFICATION_VERSION",
    "PROSE_INVENTORY_VERSION",
    "EvidenciaVerification",
    "MoneyToken",
    "NumberInProseWarning",
    "log_evidencia_kpi",
    "resolve_evidencia_mode",
    "verify_evidencia",
]
