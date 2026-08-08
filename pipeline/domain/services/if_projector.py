"""IFProjector — projeção determinística de IF (A5a/F8 · ADR-237).

O cone Monte Carlo em torno desta projeção vive em ``if_monte_carlo``.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import date

_TODAY_FALLBACK = date(2026, 4, 19)


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val.replace(".", "").replace(",", "."))
        except ValueError:
            return 0.0
    return 0.0


def _safe_int(val) -> int | None:
    """``None`` preservado — ausência de prazo declarado não é zero (ADR-369 D2)."""
    if isinstance(val, bool) or val is None:
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _calculate_age(dob: date, reference_date: date) -> int:
    """Idade em anos (calendar-accurate) — paridade com ``calculate_edad``."""
    age = reference_date.year - dob.year
    if (reference_date.month, reference_date.day) < (dob.month, dob.day):
        age -= 1
    return age


def _round_opt(val: float | None, ndigits: int) -> float | None:
    """``round`` que preserva ausência em vez de arredondar ``None``."""
    return None if val is None else round(val, ndigits)


# =============================================================================
# Config
# =============================================================================


@dataclass(frozen=True)
class IFProjectorConfig:
    """Parâmetros da projeção IF (R9/ISP).

    Sources no legado:
    - ``if_meta`` ← ``goals.json::independencia_financeira.if_meta``
      (fallback: regex em ``life_plan_goals.md``).
    - ``if_trs_pct`` ← ``goals.json::independencia_financeira.trs_pct``
      (fallback: regex em ``life_plan_goals.md``).
    - ``taxa_retirada_segura_pct`` ← ``goals.json::independencia_financeira.taxa_retirada_segura_pct`` (default 4%).
    - ``retorno_real_anual_pct`` ← ``goals.json::independencia_financeira.retorno_real_anual_pct`` (default 6%).
    - ``aporte_mensal`` ← ``goals.json::aportes.meta_aporte_mensal``.
    - ``titular_dob`` / ``conjuge_dob`` ← ``family_members.json::membros[...].data_nascimento``.
    - ``reference_date`` ← ``datetime.now().date()`` no legado (injetável para testes).
    - ``titular_key`` ← ``family_members.json::titular`` (default ``"david"``).
    - ``conjuge_key`` ← membro com ``papel == "conjuge"`` em ``family_members.json`` (vazio se não houver).
    """

    if_meta: float
    if_trs_pct: float
    titular_dob: date
    taxa_retirada_segura_pct: float = 4.0
    retorno_real_anual_pct: float = 6.0
    aporte_mensal: float = 0.0
    conjuge_dob: date | None = None
    reference_date: date = _TODAY_FALLBACK
    titular_key: str = "david"
    conjuge_key: str = ""
    # A40.l28 (ADR-369 D2) — o prazo DECLARADO pela família (`goals.
    # independencia_financeira.horizonte_anos`), qualificado aqui porque o
    # projetor também resolve um prazo REALISTA a partir do aporte. São os dois
    # lados da tesoura: compromisso vs. capacidade. `prazo_declarado_pendente`
    # marca Goal semeado no onboarding — ninguém declarou nada.
    prazo_declarado_anos: int | None = None
    prazo_declarado_em: str | None = None
    prazo_declarado_pendente: bool = False

    @classmethod
    def from_configs(
        cls,
        *,
        goals: dict | None = None,
        titular_dob: date,
        conjuge_dob: date | None = None,
        reference_date: date | None = None,
        titular_key: str = "david",
        conjuge_key: str = "",
    ) -> "IFProjectorConfig":
        """Constrói a config a partir do dict ``goals.json``.

        ``if_meta`` / ``if_trs_pct`` devem estar presentes ou em
        ``independencia_financeira``; do contrário levanta ``ValueError``
        (paridade com ``extract_if_target_from_life_plan`` / ``extract_if_trs``).
        """
        goals_cfg = (goals or {}).get("independencia_financeira", {}) or {}
        aportes_cfg = (goals or {}).get("aportes", {}) or {}

        if_meta = goals_cfg.get("if_meta")
        if if_meta is None:
            raise ValueError("IF meta não encontrada em goals.independencia_financeira.if_meta")
        if_trs = goals_cfg.get("trs_pct")
        if if_trs is None:
            raise ValueError("TRS não encontrado em goals.independencia_financeira.trs_pct")

        return cls(
            if_meta=_safe_float(if_meta),
            if_trs_pct=_safe_float(if_trs),
            titular_dob=titular_dob,
            taxa_retirada_segura_pct=_safe_float(goals_cfg.get("taxa_retirada_segura_pct", 4.0)),
            retorno_real_anual_pct=_safe_float(goals_cfg.get("retorno_real_anual_pct", 6.0)),
            aporte_mensal=_safe_float(aportes_cfg.get("meta_aporte_mensal", 0)),
            conjuge_dob=conjuge_dob,
            reference_date=reference_date or _TODAY_FALLBACK,
            titular_key=titular_key,
            conjuge_key=conjuge_key,
            prazo_declarado_anos=_safe_int(goals_cfg.get("horizonte_anos")),
            prazo_declarado_em=goals_cfg.get("declarado_em"),
            prazo_declarado_pendente=bool(goals_cfg.get("is_template", False)),
        )


# =============================================================================
# Helpers puros — extratores de life_plan_goals.md
# =============================================================================


def extract_if_meta_from_text(content: str) -> float | None:
    """Regex para ``**R$ ...`` em ``life_plan_goals.md``."""
    m = re.search(r"\*\*R\$\s*([\d.,]+)", content)
    if m:
        return _safe_float(m.group(1))
    return None


def extract_if_trs_from_text(content: str) -> float | None:
    """Regex para ``TRS ... ##%`` em ``life_plan_goals.md``."""
    m = re.search(r"TRS.*?(\d+(?:[.,]\d+)?)\s*%", content, re.IGNORECASE)
    if m:
        return _safe_float(m.group(1))
    return None


def extract_renda_passiva_from_text(content: str) -> float:
    """Regex para ``Renda passiva atual: R$ ...`` em ``life_plan_goals.md``."""
    m = re.search(
        r"Renda passiva atual:\s*R\$\s*([\d.,]+)",
        content,
        re.IGNORECASE,
    )
    if m:
        return _safe_float(m.group(1))
    return 0.0


# =============================================================================
# Result
# =============================================================================


# Não afirma "infinito": premissas nulas só põem o caso fora do ramo fechado.
MOTIVO_PRAZO_INDEFINIDO = (
    "prazo até a IF não projetável com as premissas atuais (aporte mensal e/ou retorno real nulos)"
)


@dataclass(frozen=True)
class IFProjection:
    """Saída de ``IFProjector.project``. Compatível com o output de
    ``analyze_goals`` do legado via :meth:`to_legacy_dict`.
    """

    # `prazo_anos_realista is None` = ausência medida; idade/ano projetados
    # acompanham em None (nunca aritmética sobre sentinela — era 999 → 1040).
    if_meta: float
    if_trs: float
    if_trs_monthly_value: float
    if_pct: float
    if_gap: float
    prazo_anos_realista: float | None
    idade_titular_if: int | None
    ano_if: int | None
    renda_passiva_estimada_4pct: float
    # FP-009 — retorno real esperado %a.a. (== `retorno_real_anual_pct`).
    # Consumido por `rule_endividamento_perigoso` (carry-trade trigger).
    retorno_esperado_pct_aa: float = 6.0
    idade_conjuge_if: int | None = None
    motivo_prazo_indefinido: str | None = None
    # Separa "não há cônjuge datado" (chave ausente) de "há cônjuge, mas o
    # prazo não foi projetado" (chave presente com valor `null`).
    tem_conjuge_datado: bool = False
    titular_key: str = "david"
    conjuge_key: str = ""

    def to_legacy_dict(self) -> dict:
        # Chaves sempre presentes; `null` sem prazo projetado (distinga por `is None`).
        out: dict = {
            "if_meta": round(self.if_meta, 2),
            "if_trs": round(self.if_trs, 2),
            "if_trs_monthly_value": round(self.if_trs_monthly_value, 2),
            "if_pct": round(self.if_pct, 2),
            "if_gap": round(self.if_gap, 2),
            "prazo_anos_realista": _round_opt(self.prazo_anos_realista, 1),
            # ADR-338: chave role-keyed (era idade_<nome>_if + alias morto "david_idade_if").
            "idade_titular_if": self.idade_titular_if,
            "ano_if": self.ano_if,
            "motivo_prazo_indefinido": self.motivo_prazo_indefinido,
            "renda_passiva_estimada_4pct": round(self.renda_passiva_estimada_4pct, 2),
            # FP-009: alinhamento com retorno ponderado da carteira fica para FP-004.
            "retorno_esperado_pct_aa": round(self.retorno_esperado_pct_aa, 2),
        }
        if self.conjuge_key and self.tem_conjuge_datado:
            out["idade_conjuge_if"] = self.idade_conjuge_if
        return out


# =============================================================================
# Service
# =============================================================================


def _project_horizon(
    cfg: IFProjectorConfig, prazo_anos: float | None
) -> tuple[int | None, int | None, int | None]:
    """(idade_titular, idade_conjuge, ano) na IF; tudo ``None`` sem prazo."""
    # Ausência propaga em vez de virar aritmética: era `idade + 999` → 1040.
    if prazo_anos is None:
        return None, None, None
    anos = int(prazo_anos)
    idade_conjuge = (
        None
        if cfg.conjuge_dob is None
        else _calculate_age(cfg.conjuge_dob, cfg.reference_date) + anos
    )
    return (
        _calculate_age(cfg.titular_dob, cfg.reference_date) + anos,
        idade_conjuge,
        cfg.reference_date.year + anos,
    )


class IFProjector:
    """Projeta prazo e progresso para atingir Independência Financeira.

    Função pura — recebe ``investivel`` (R$) e retorna :class:`IFProjection`.
    Cálculo do prazo realista usa math de juros compostos sobre PV+PMT:

        FV = PV · (1+r)^n + PMT · ((1+r)^n − 1) / r

    Resolvendo para n:

        n = log((FV + PMT/r) / (PV + PMT/r)) / log(1+r)

    Quando ``aporte_mensal == 0`` ou ``retorno_real_anual_pct == 0`` e
    ``investivel < if_meta``, o ramo fechado acima não se aplica e
    ``prazo_anos_realista`` é ``None`` — junto com ``idade_titular_if`` /
    ``idade_conjuge_if`` / ``ano_if``. Era a sentinela ``999`` do legado, que
    somada à idade produzia "IF aos 1040 anos" no payload E5 e virava âncora
    citável do parecer.
    """

    def __init__(self, config: IFProjectorConfig) -> None:
        self._config = config

    def project(self, investivel: float) -> IFProjection:
        cfg = self._config
        if_trs_monthly = (cfg.if_trs_pct / 100.0) / 12.0
        if_trs_value = cfg.if_meta * if_trs_monthly

        if_pct = (investivel / cfg.if_meta * 100) if cfg.if_meta > 0 else 0.0
        if_gap = cfg.if_meta - investivel

        # Taxa mensal equivalente da anual composta.
        retorno_anual = cfg.retorno_real_anual_pct / 100.0
        r = (1 + retorno_anual) ** (1 / 12) - 1 if retorno_anual > 0 else 0.0

        prazo_anos = self._solve_prazo(
            investivel=investivel,
            if_meta=cfg.if_meta,
            r=r,
            aporte_mensal=cfg.aporte_mensal,
        )

        idade_titular_if, idade_conjuge_if, ano_if = _project_horizon(cfg, prazo_anos)

        taxa = cfg.taxa_retirada_segura_pct / 100.0
        renda_passiva_current = investivel * taxa / 12

        return IFProjection(
            if_meta=cfg.if_meta,
            if_trs=cfg.if_trs_pct,
            if_trs_monthly_value=if_trs_value,
            if_pct=if_pct,
            if_gap=if_gap,
            prazo_anos_realista=prazo_anos,
            idade_titular_if=idade_titular_if,
            idade_conjuge_if=idade_conjuge_if,
            ano_if=ano_if,
            renda_passiva_estimada_4pct=renda_passiva_current,
            retorno_esperado_pct_aa=cfg.retorno_real_anual_pct,
            motivo_prazo_indefinido=None if prazo_anos is not None else MOTIVO_PRAZO_INDEFINIDO,
            tem_conjuge_datado=cfg.conjuge_dob is not None,
            titular_key=cfg.titular_key,
            conjuge_key=cfg.conjuge_key,
        )

    @staticmethod
    def _solve_prazo(
        *,
        investivel: float,
        if_meta: float,
        r: float,
        aporte_mensal: float,
    ) -> float | None:
        """Resolve n (meses) em PV*(1+r)^n + PMT*((1+r)^n - 1)/r = FV."""
        # `None` fora do ramo fechado (r <= 0 ou aporte <= 0) — era a sentinela
        # 999.0, que vazava somada à idade do titular. O chamador não inventa prazo.
        if investivel >= if_meta:
            return 0.0
        if r > 0 and aporte_mensal > 0:
            numerator = if_meta + aporte_mensal / r
            denominator = investivel + aporte_mensal / r
            if denominator > 0 and numerator / denominator > 0:
                n_meses = math.log(numerator / denominator) / math.log(1 + r)
                return max(0.0, n_meses / 12)
        return None
