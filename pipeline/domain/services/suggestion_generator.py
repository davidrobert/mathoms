"""SuggestionGenerator — gerador determinístico de sugestões (Direção E · Onda 5 · ADR-153).

Função pura: dado o snapshot E5 (dict com 24+ chaves top-level produzido
por :func:`pipeline.domain.services.e5_serialization.build_e5_output`),
aplica 5 regras canônicas e retorna lista de :class:`SuggestionDraft`
ranqueada (severidade desc → valor desc) e truncada em
:data:`SUGGESTION_CAP`.

**Sem I/O.** Persistência (FK report, dedup vs Descartadas, transação)
é responsabilidade do use case
:func:`backend.app.application.suggestions.regenerate_for_report`.

Boundary do pipeline (ADR-101 / `dev/check_pipeline_boundaries.py`):
não importa ``backend.*``. ``SuggestionDraft`` é dataclass puro em
:mod:`pipeline.domain.types.suggestion` — backend mapeia no use case.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from pipeline.domain.types.suggestion import SuggestionDraft

# =============================================================================
# Constantes públicas (referenciadas no backend)
# =============================================================================

SUGGESTION_CAP: int = 6
"""Cap por re-geração — designer fixou 3-6 sugestões/relatório."""

DISMISS_RESPECT_WINDOW_DAYS: int = 90
"""Janela de respeito a Descartadas — re-aparecem após este prazo."""

# =============================================================================
# Configuração (thresholds — refinar com financial-planner se evidência pedir)
# =============================================================================


@dataclass(frozen=True)
class SuggestionGeneratorConfig:
    """Thresholds configuráveis por workspace/perfil futuro."""

    # Reserva de emergência: alvo em meses de despesa (Cerbasi/AUVP padrão).
    reserva_target_meses: int = 6

    # TRS: alvo conservador (Bruno Perini = 4%); flagga se efetiva >15% acima.
    trs_target_pct: float = 4.0
    trs_drift_tolerance_pct: float = 0.15  # 15%

    # Alocação: tolerância em pontos percentuais antes de flag.
    alocacao_drift_pp: float = 10.0

    # Aporte: % da meta abaixo do qual sinaliza (média 3 meses).
    aporte_min_pct_meta: float = 0.7

    # Dolarização: cobertura mínima vs meta em pp.
    dolar_drift_pp: float = 15.0


# =============================================================================
# Generator
# =============================================================================


class SuggestionGenerator:
    """Aplica regras canônicas v1 sobre o snapshot E5."""

    def __init__(self, config: SuggestionGeneratorConfig | None = None) -> None:
        self._config = config or SuggestionGeneratorConfig()

    def generate(self, snapshot: dict[str, Any]) -> list[SuggestionDraft]:
        drafts: list[SuggestionDraft] = []
        for rule in (
            _rule_trs_desalinhada,
            _rule_reserva_insuficiente,
            _rule_alocacao_fora_alvo,
            _rule_aporte_abaixo_meta,
            _rule_dolarizacao_atrasada,
        ):
            try:
                draft = rule(snapshot, self._config)
            except (KeyError, TypeError, ValueError):
                # Regras são defensivas — snapshot incompleto ⇒ skip silencioso.
                draft = None
            if draft is not None:
                drafts.append(draft)
        drafts.sort(key=_rank_key, reverse=True)
        return drafts[:SUGGESTION_CAP]


# =============================================================================
# Ranking
# =============================================================================

_SEVERITY_RANK = {"danger": 3, "warning": 2, "info": 1}


def _rank_key(draft: SuggestionDraft) -> tuple[int, int]:
    sev = _SEVERITY_RANK.get(draft.severity, 0)
    amount = int(draft.amount_brl * 100) if draft.amount_brl is not None else 0
    return (sev, amount)


# =============================================================================
# Regras
# =============================================================================


def _rule_trs_desalinhada(
    snapshot: dict[str, Any], cfg: SuggestionGeneratorConfig
) -> SuggestionDraft | None:
    goals = _as_dict(snapshot.get("goals"))
    if not goals:
        return None
    trs_atual = _as_float(goals.get("taxa_retirada_efetiva_pct"))
    target = cfg.trs_target_pct
    if trs_atual is None:
        return None
    threshold = target * (1 + cfg.trs_drift_tolerance_pct)
    if trs_atual <= threshold:
        return None
    sugestao_trs = round(target, 1)
    title = f"Reduzir taxa de retirada para {sugestao_trs:.1f}% ao ano"
    rationale = (
        f"Taxa de retirada efetiva está em {trs_atual:.1f}% — "
        f"acima do alvo conservador de {sugestao_trs:.1f}% (Perini/AUVP). "
        f"Ajustar para sustentar a renda no longo prazo sem corroer principal."
    )
    return SuggestionDraft(
        section_id="S7",
        kind="trs_desalinhada",
        origin="deterministic",
        severity="warning",
        title=title,
        rationale=rationale,
        amount_brl=None,
        dedup_key=_dedup_key(
            "trs_desalinhada",
            bucket=_pct_bucket(trs_atual, step=0.5),
        ),
    )


def _rule_reserva_insuficiente(
    snapshot: dict[str, Any], cfg: SuggestionGeneratorConfig
) -> SuggestionDraft | None:
    reserva = _as_dict(snapshot.get("reserva_emergencia"))
    if not reserva:
        return None
    meses = _as_float(reserva.get("meses_cobertura"))
    if meses is None or meses >= cfg.reserva_target_meses:
        return None
    gap_brl = _as_decimal(reserva.get("gap_brl"))
    fluxo = _as_dict(snapshot.get("fluxo_caixa"))
    aporte_mensal = _as_decimal(fluxo.get("aporte_meta_mensal")) or _as_decimal(
        fluxo.get("aporte_medio_3m")
    )
    title = f"Reforçar reserva de emergência até {cfg.reserva_target_meses} meses"
    rationale = _build_reserva_rationale(meses, cfg.reserva_target_meses, gap_brl, aporte_mensal)
    severity = "danger" if meses < 3 else "warning"
    return SuggestionDraft(
        section_id="S2",
        kind="reserva_insuficiente",
        origin="deterministic",
        severity=severity,
        title=title,
        rationale=rationale,
        amount_brl=gap_brl,
        dedup_key=_dedup_key("reserva_insuficiente", bucket=_meses_bucket(meses)),
    )


def _build_reserva_rationale(
    meses_atual: float,
    meses_alvo: int,
    gap_brl: Decimal | None,
    aporte_mensal: Decimal | None,
) -> str:
    """Onda 10 #5 — rationale enriquecido com gap + ETA do aporte mensal."""
    base = (
        f"Sua reserva atual cobre {meses_atual:.1f} meses de custo essencial, "
        f"abaixo do alvo de {meses_alvo} meses (Perini/Cerbasi)."
    )
    if gap_brl is None or gap_brl <= 0:
        return base + " Reforçar protege o plano contra choque de renda."
    parts = [base, f"Faltam **{_format_brl(gap_brl)}**."]
    parts.append(_reserva_aporte_clause(gap_brl, aporte_mensal))
    return " ".join(p for p in parts if p)


def _reserva_aporte_clause(gap_brl: Decimal, aporte_mensal: Decimal | None) -> str:
    """ETA + CTA quando o aporte está disponível; texto curto caso contrário."""
    if aporte_mensal is None or aporte_mensal <= 0:
        return "Reforçar protege o plano contra choque de renda."
    meses = max(int((gap_brl / aporte_mensal).to_integral_value()), 1)
    aporte_brl = _format_brl(aporte_mensal)
    return (
        f"Aportando {aporte_brl}/mês, completa em ~{meses} meses. "
        f"**Próximo passo:** elevar aporte mensal para reserva ou direcionar "
        f"o próximo aporte de {aporte_brl} integralmente para Tesouro Selic / "
        "CDB liquidez diária."
    )


def _rule_alocacao_fora_alvo(
    snapshot: dict[str, Any], cfg: SuggestionGeneratorConfig
) -> SuggestionDraft | None:
    investimentos = _as_dict(snapshot.get("investimentos"))
    if not investimentos:
        return None
    desvios = _as_list(investimentos.get("desvios_alvo"))
    pior = _pick_worst_desvio(desvios)
    if pior is None:
        return None
    desvio_pp = _as_float(pior.get("desvio_pp"))
    if desvio_pp is None or abs(desvio_pp) <= cfg.alocacao_drift_pp:
        return None
    classe = str(pior.get("classe", "alocação"))
    direcao = "reduzir" if desvio_pp > 0 else "aumentar"
    title = f"Rebalancear alocação: {direcao} {classe} ({desvio_pp:+.0f}pp)"
    fluxo = _as_dict(snapshot.get("fluxo_caixa"))
    proximo_aporte = _as_decimal(fluxo.get("aporte_meta_mensal")) or _as_decimal(
        fluxo.get("aporte_medio_3m")
    )
    rationale = _build_alocacao_rationale(
        classe,
        desvio_pp,
        direcao,
        _as_float(pior.get("atual_pct")),
        _as_float(pior.get("alvo_pct")),
        proximo_aporte,
        desvios,
        cfg.alocacao_drift_pp,
    )
    return SuggestionDraft(
        section_id="S3",
        kind="alocacao_fora_alvo",
        origin="deterministic",
        severity="info",
        title=title,
        rationale=rationale,
        amount_brl=None,
        dedup_key=_dedup_key(
            "alocacao_fora_alvo",
            bucket=f"{classe}|{_pct_bucket(desvio_pp, step=2.5)}",
        ),
    )


def _pick_worst_desvio(desvios: list[Any]) -> dict[str, Any] | None:
    """Maior |desvio_pp| da lista; None se vazio."""
    if not desvios:
        return None
    pior = max(desvios, key=lambda d: abs(_as_float(_as_dict(d).get("desvio_pp")) or 0.0))
    return _as_dict(pior) or None


def _build_alocacao_rationale(
    classe: str,
    desvio_pp: float,
    direcao: str,
    atual_pct: float | None,
    alvo_pct: float | None,
    proximo_aporte: Decimal | None,
    desvios: list[Any],
    drift_pp: float,
) -> str:
    """Onda 10 #5 — head + drift + CTA + tabela markdown (cada parte opcional)."""
    head = _alocacao_head(classe, desvio_pp, direcao, atual_pct, alvo_pct)
    drift = f"Drift acima da tolerância ({drift_pp:.0f}pp)."
    cta = _alocacao_cta(classe, proximo_aporte)
    table = _format_alocacao_table(desvios)
    return "\n\n".join(p for p in (head, drift, cta, table) if p)


def _alocacao_cta(classe: str, proximo_aporte: Decimal | None) -> str:
    """CTA "Próximo aporte" — vazio quando o aporte mensal não está disponível."""
    if proximo_aporte is None or proximo_aporte <= 0:
        return ""
    return (
        f"**Próximo passo:** o próximo aporte de {_format_brl(proximo_aporte)} "
        f"pode ir integralmente para **{classe}** e iniciar o rebalanceamento."
    )


def _alocacao_head(
    classe: str,
    desvio_pp: float,
    direcao: str,
    atual_pct: float | None,
    alvo_pct: float | None,
) -> str:
    """Frase cabeçalho — anexa atual/alvo se disponível."""
    head = f"Classe **{classe}** está {abs(desvio_pp):.1f}pp {direcao}da do alvo"
    if atual_pct is not None and alvo_pct is not None:
        return head + f" (atual {atual_pct:.1f}% vs alvo {alvo_pct:.1f}%)."
    return head + "."


def _format_alocacao_table(desvios: list[Any]) -> str:
    """Tabela markdown atual/alvo/Δ — só se >=2 entradas com pcts."""
    rows: list[str] = []
    for entry in desvios:
        d = _as_dict(entry)
        atual = _as_float(d.get("atual_pct"))
        alvo = _as_float(d.get("alvo_pct"))
        desvio = _as_float(d.get("desvio_pp"))
        if atual is None or alvo is None or desvio is None:
            continue
        classe = str(d.get("classe", "—"))
        rows.append(f"| {classe} | {atual:.1f}% | {alvo:.1f}% | {desvio:+.1f}pp |")
    if len(rows) < 2:
        return ""
    header = "| Classe | Atual | Alvo | Δ |\n| --- | --- | --- | --- |"
    return "**Distribuição atual vs alvo:**\n\n" + header + "\n" + "\n".join(rows)


def _format_brl(value: Decimal) -> str:
    """Decimal monetário em formato BR (R$ 1.234,56) sem depender de locale."""
    quantized = value.quantize(Decimal("0.01"))
    formatted = f"{quantized:,.2f}"
    swapped = formatted.replace(",", "_TMP_").replace(".", ",").replace("_TMP_", ".")
    return f"R$ {swapped}"


def _rule_aporte_abaixo_meta(
    snapshot: dict[str, Any], cfg: SuggestionGeneratorConfig
) -> SuggestionDraft | None:
    fluxo = _as_dict(snapshot.get("fluxo_caixa"))
    if not fluxo:
        return None
    aporte_medio = _as_decimal(fluxo.get("aporte_medio_3m"))
    aporte_meta = _as_decimal(fluxo.get("aporte_meta_mensal"))
    if aporte_medio is None or aporte_meta is None or aporte_meta <= 0:
        return None
    pct = float(aporte_medio / aporte_meta)
    if pct >= cfg.aporte_min_pct_meta:
        return None
    gap = aporte_meta - aporte_medio
    title = "Retomar disciplina de aporte mensal"
    rationale = (
        f"Aporte médio dos últimos 3 meses está em {pct * 100:.0f}% da meta — "
        f"abaixo do limiar de {cfg.aporte_min_pct_meta * 100:.0f}%. "
        f"Sem disciplina, o ano-IF projetado escorrega."
    )
    return SuggestionDraft(
        section_id="S2",
        kind="aporte_abaixo_meta",
        origin="deterministic",
        severity="warning",
        title=title,
        rationale=rationale,
        amount_brl=gap if gap > 0 else None,
        dedup_key=_dedup_key(
            "aporte_abaixo_meta",
            bucket=_brl_bucket(gap, step=Decimal("1000")),
        ),
    )


def _rule_dolarizacao_atrasada(
    snapshot: dict[str, Any], cfg: SuggestionGeneratorConfig
) -> SuggestionDraft | None:
    dolar = _as_dict(
        snapshot.get("dolarizacao") or snapshot.get("usa", {}).get("dolarizacao")
        if isinstance(snapshot.get("usa"), dict)
        else snapshot.get("dolarizacao")
    )
    if not dolar:
        return None
    cobertura = _as_float(dolar.get("cobertura_pct"))
    meta = _as_float(dolar.get("meta_pct"))
    if cobertura is None or meta is None:
        return None
    drift = meta - cobertura
    if drift <= cfg.dolar_drift_pp:
        return None
    title = f"Acelerar conversão para USD (gap {drift:.0f}pp)"
    rationale = (
        f"Cobertura USD em {cobertura:.0f}% — meta é {meta:.0f}%. "
        f"Drift de {drift:.0f}pp acima da tolerância ({cfg.dolar_drift_pp:.0f}pp). "
        f"Acelerar aportes em USD reduz risco cambial do plano de mudança."
    )
    return SuggestionDraft(
        section_id="U1",
        kind="dolarizacao_atrasada",
        origin="deterministic",
        severity="info",
        title=title,
        rationale=rationale,
        amount_brl=None,
        dedup_key=_dedup_key(
            "dolarizacao_atrasada",
            bucket=_pct_bucket(drift, step=5.0),
        ),
    )


# =============================================================================
# Helpers de coerção (snapshot é Record<string, unknown> — defensivo)
# =============================================================================


def _as_dict(v: Any) -> dict[str, Any]:
    return v if isinstance(v, dict) else {}


def _as_list(v: Any) -> list[Any]:
    return v if isinstance(v, list) else []


def _as_float(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v.replace(",", "."))
        except ValueError:
            return None
    return None


def _as_decimal(v: Any) -> Decimal | None:
    f = _as_float(v)
    if f is None:
        return None
    return Decimal(str(f)).quantize(Decimal("0.01"))


# =============================================================================
# Dedup buckets (toleram ruído sem perder gatilhos)
# =============================================================================


def _pct_bucket(pct: float, *, step: float) -> str:
    bucket = round(pct / step) * step
    return f"pct{bucket:.1f}"


def _meses_bucket(meses: float) -> str:
    if meses < 1:
        return "meses-lt1"
    if meses < 3:
        return "meses-1to3"
    if meses < 6:
        return "meses-3to6"
    return "meses-ge6"


def _brl_bucket(value: Decimal | None, *, step: Decimal) -> str:
    if value is None:
        return "brl-none"
    bucket = (value / step).quantize(Decimal("1")) * step
    return f"brl{bucket}"


def _dedup_key(kind: str, *, bucket: str) -> str:
    """Hash determinístico kind|bucket → 32 hex (estável entre runs).

    O ``workspace_id`` é parte da chave única no DB
    ``UNIQUE (workspace_id, dedup_key, status)`` — não precisa entrar
    aqui, e isso permite testes determinísticos sem workspace.
    """
    raw = f"{kind}|{bucket}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]
