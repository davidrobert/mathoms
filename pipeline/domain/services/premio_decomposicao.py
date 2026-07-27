"""Decomposição do prêmio de seguro por cobertura (KPI G) — ADR-352.

Extraído de ``protecao_analyzer`` (A19 L1 P1, ADR-240) para manter o analyzer
sob 500 linhas. Rateia o ``premio_total_brl`` de cada apólice pelas categorias
das coberturas (bottom-up), com invariante ``Σ premio_decomposicao == premio_total``
cent-exato; apólice sem cobertura precificada cai em bem-dominante ou
``nao_identificado`` (nunca fabrica ``auto``).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal


def _to_decimal(v) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def premio_total_anual(apolices_vigentes: list[dict]) -> Decimal:
    return sum((_to_decimal(a.get("premio_total_brl")) for a in apolices_vigentes), Decimal("0"))


def _categoriza_apolice(apolice: dict) -> str:
    """Classifica apólice em {auto, residencial, vida, saude, ap} pelo bem dominante."""
    tipos = {b.get("tipo") for b in (apolice.get("bens_segurados") or [])}
    if "imovel" in tipos and "veiculo" not in tipos:
        return "residencial"
    if "veiculo" in tipos:
        return "auto"
    if "pessoa" in tipos:
        return _classifica_pessoa(apolice)
    return "auto"  # fallback


def coberturas_pessoa(apolice: dict):
    """Itera as coberturas dos bens tipo 'pessoa' da apólice (compartilhado com KPIs de flag)."""
    for bem in apolice.get("bens_segurados") or []:
        if bem.get("tipo") == "pessoa":
            yield from bem.get("coberturas") or []


def _classifica_pessoa(apolice: dict) -> str:
    """Sub-classificação V2 (vida/saude/ap) pelo tipo da 1ª cobertura."""
    for cov in coberturas_pessoa(apolice):
        t = cov.get("tipo")
        if t in ("vida", "saude", "acidentes"):
            return "ap" if t == "acidentes" else t
    return "vida"


# ADR-352: categoria de uma cobertura pelo tipo do bem que a contém.
_BEM_CATEGORIA = {"veiculo": "auto", "imovel": "residencial"}
_PESSOA_COBERTURA_CATEGORIA = {"vida": "vida", "saude": "saude", "acidentes": "ap"}


def _categoria_cobertura(bem_tipo: str, cobertura: dict) -> str:
    if bem_tipo in _BEM_CATEGORIA:
        return _BEM_CATEGORIA[bem_tipo]
    return _PESSOA_COBERTURA_CATEGORIA.get(cobertura.get("tipo"), "vida")


def _pesos_por_categoria(apolice: dict) -> dict[str, Decimal]:
    """Σ premio_brl das coberturas, agrupado por categoria (peso do rateio)."""
    pesos: dict[str, Decimal] = {}
    for bem in apolice.get("bens_segurados") or []:
        tipo = bem.get("tipo") or ""
        for cov in bem.get("coberturas") or []:
            cat = _categoria_cobertura(tipo, cov)
            pesos[cat] = pesos.get(cat, Decimal("0")) + _to_decimal(cov.get("premio_brl"))
    return {k: v for k, v in pesos.items() if v > 0}


def _rateia_premio(premio_total: Decimal, pesos: dict[str, Decimal]) -> dict[str, Decimal]:
    """Aloca premio_total proporcional aos pesos, cent-exato (maior-resto) — ADR-352 D2."""
    total_peso = sum(pesos.values(), Decimal("0"))
    cents = int((premio_total * 100).to_integral_value(rounding=ROUND_HALF_UP))
    ideal = {k: cents * v / total_peso for k, v in pesos.items()}
    base = {k: int(x) for k, x in ideal.items()}  # floor (x >= 0)
    resto = cents - sum(base.values())
    for k in sorted(ideal, key=lambda k: ideal[k] - int(ideal[k]), reverse=True)[:resto]:
        base[k] += 1
    return {k: Decimal(c) / 100 for k, c in base.items()}


def _categoria_apolice_fallback(apolice: dict) -> str:
    """Sem cobertura precificada: bem dominante, ou 'nao_identificado' (nunca fabrica 'auto')."""
    if apolice.get("bens_segurados"):
        return _categoriza_apolice(apolice)
    return "nao_identificado"


def _decompoe_apolice(apolice: dict) -> dict[str, Decimal]:
    """Prêmio de 1 apólice repartido por categoria; Σ == premio_total_brl (ADR-352)."""
    premio_total = _to_decimal(apolice.get("premio_total_brl"))
    pesos = _pesos_por_categoria(apolice)
    if pesos:
        return _rateia_premio(premio_total, pesos)
    return {_categoria_apolice_fallback(apolice): premio_total}


def premio_decomposicao(apolices_vigentes: list[dict]) -> dict[str, Decimal]:
    decomp: dict[str, Decimal] = {}
    for a in apolices_vigentes:
        for cat, valor in _decompoe_apolice(a).items():
            decomp[cat] = decomp.get(cat, Decimal("0")) + valor
    return decomp
