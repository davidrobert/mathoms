"""MemberAnalyzer — análise patrimonial por membro (Sessão A3c · Fase 8 foundation).

Extrai a fatia "patrimônio por membro" de ``scripts/e5_analyze.py:781``
(``analyze_patrimonio``) em um domain service puro. Escopo mínimo: cobre
apenas a decomposição por membro (imóveis residência vs investimento,
veículos, investimentos, contas bancárias). A consolidação cross-membro
(soma + caixa via E3 saldos + recálculo bruto) **continua no script legado**
até a Sessão A4+ que faz o `main_with_store` do E5.

Helpers extraídos:
- ``MemberAnalyzer.imovel_valor`` ⟵ ``_imovel_valor`` (e5_analyze.py:651)
- ``MemberAnalyzer.imovel_descricao`` ⟵ ``_imovel_desc`` (e5_analyze.py:660)
- ``MemberAnalyzer.veiculo_valor`` ⟵ ``_veiculo_valor`` (e5_analyze.py:676)
- ``MemberAnalyzer.investimento_valor`` ⟵ ``_investimento_valor`` (e5_analyze.py:685)
- ``MemberAnalyzer.bens_for`` ⟵ ``_get_bens`` (e5_analyze.py:644)
- ``MemberAnalyzer.analyze`` — orquestra os helpers, retorna
  :class:`MemberPatrimonio` tipado.

Paridade comprovada por testes; integração no ``main()`` do E5 fica para
sessão dedicada quando todo o E5 entrar no Caminho B.

Decisões de tipo:
- Valores monetários internos usam ``Decimal`` (precisão).
- O value object expõe ``to_legacy_floats() -> dict[str, float]`` para o
  shell que ainda fala em ``float`` (compatível com o output do legado).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable

# =============================================================================
# Helpers internos
# =============================================================================


def _safe_decimal(val: Any) -> Decimal:
    """Converte ``val`` para ``Decimal``, retornando 0 em caso de erro.

    Aceita strings com vírgula como separador decimal (formato BR).
    """
    if val is None:
        return Decimal(0)
    if isinstance(val, Decimal):
        return val
    if isinstance(val, (int, float)):
        try:
            return Decimal(str(val))
        except (ValueError, ArithmeticError):
            return Decimal(0)
    if isinstance(val, str):
        s = val.strip().replace("R$", "").strip()
        if not s:
            return Decimal(0)
        # BR: remove milhar (.) e troca decimal (,) → .
        if "," in s and s.count(",") == 1 and s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        try:
            return Decimal(s)
        except (ValueError, ArithmeticError):
            return Decimal(0)
    return Decimal(0)


# =============================================================================
# Value object
# =============================================================================


@dataclass(frozen=True)
class MemberPatrimonio:
    """Patrimônio decomposto de um único membro da família.

    Todos os valores em ``Decimal`` (precisão); use ``to_legacy_floats()``
    para serialização compatível com o output legado do E5.
    """

    member_key: str
    residencia: Decimal = Decimal(0)
    imoveis_investimento: Decimal = Decimal(0)
    veiculos: Decimal = Decimal(0)
    investimentos: Decimal = Decimal(0)
    contas_bancarias_extras: Decimal = Decimal(0)
    total_bens_irpf: Decimal = Decimal(0)
    total_dividas: Decimal = Decimal(0)

    @property
    def total_bens_calculado(self) -> Decimal:
        """Soma componentes — útil para sanity check vs ``total_bens_irpf``."""
        return (
            self.residencia
            + self.imoveis_investimento
            + self.veiculos
            + self.investimentos
            + self.contas_bancarias_extras
        )

    def to_legacy_floats(self) -> dict[str, float]:
        """Serializa em ``dict[str, float]`` compatível com o output do
        ``analyze_patrimonio`` legado (que sempre usa float)."""
        return {
            "member_key": self.member_key,  # type: ignore[dict-item]
            "residencia": float(self.residencia),
            "imoveis_investimento": float(self.imoveis_investimento),
            "veiculos": float(self.veiculos),
            "investimentos": float(self.investimentos),
            "contas_bancarias_extras": float(self.contas_bancarias_extras),
            "total_bens_irpf": float(self.total_bens_irpf),
            "total_dividas": float(self.total_dividas),
        }


# =============================================================================
# Service
# =============================================================================


class MemberAnalyzer:
    """Decompõe patrimônio individual a partir do dict de membro do baseline.

    Função pura — não toca disco, não acessa configs globais. Identifica o
    imóvel residencial via ``residencia_property_ids`` (set de UUIDs de
    `property_identity` classificados como `residencia_principal` no
    `workspace_property_overrides`; ADR-215 §1). Empty set → todos os
    imóveis caem em ``imoveis_investimento``.
    """

    def __init__(self) -> None:
        # Stateless. Helpers são static methods abaixo.
        pass

    # -- Helpers (paridade direta com privates de e5_analyze.py) --

    @staticmethod
    def bens_for(member: dict[str, Any]) -> dict[str, Any]:
        """Retorna sub-dict ``bens`` quando aninhado; senão usa o próprio
        membro (paridade com ``_get_bens``)."""
        bens = member.get("bens")
        if isinstance(bens, dict):
            return bens
        return member

    @staticmethod
    def imovel_valor(imovel: dict[str, Any]) -> Decimal:
        """Tenta ``valor_31_12_ano_base`` → ``valor_irpf`` → ``valor``."""
        for key in ("valor_31_12_ano_base", "valor_irpf", "valor"):
            v = imovel.get(key)
            if v is not None:
                return _safe_decimal(v)
        return Decimal(0)

    @staticmethod
    def imovel_descricao(imovel: dict[str, Any]) -> str:
        """``description`` → ``descricao`` → ``endereco`` → ``dados_completos.imovel``,
        normalizado para lowercase. Paridade com ``_imovel_desc``.
        """
        desc = imovel.get("description") or imovel.get("descricao") or ""
        if not desc:
            desc = imovel.get("endereco") or ""
        if not desc:
            dc = imovel.get("dados_completos")
            if isinstance(dc, dict):
                desc = dc.get("imovel", "") or ""
        return str(desc).lower()

    @staticmethod
    def veiculo_valor(veiculo: dict[str, Any]) -> Decimal:
        for key in ("valor_31_12_ano_base", "valor_irpf", "valor"):
            v = veiculo.get(key)
            if v is not None:
                return _safe_decimal(v)
        return Decimal(0)

    @staticmethod
    def investimento_valor(inv: Any) -> Decimal:
        """Aceita dict ``{valor_31_12_ano_base | valor: ...}`` ou escalar."""
        if isinstance(inv, dict):
            for key in ("valor_31_12_ano_base", "valor"):
                v = inv.get(key)
                if v is not None:
                    return _safe_decimal(v)
            return Decimal(0)
        return _safe_decimal(inv)

    # -- Análise --

    def analyze(
        self,
        member: dict[str, Any],
        *,
        member_key: str = "",
        residencia_property_ids: frozenset[str] = frozenset(),
    ) -> MemberPatrimonio:
        """Decompõe o patrimônio de um membro em componentes tipados (ADR-215 §1)."""
        bens = self.bens_for(member)
        residencia = Decimal(0)
        imoveis_inv = Decimal(0)
        for imovel in bens.get("imoveis", []) or []:
            if not isinstance(imovel, dict):
                continue
            valor = self.imovel_valor(imovel)
            pid = imovel.get("property_id")
            if isinstance(pid, str) and pid in residencia_property_ids:
                residencia += valor
            else:
                imoveis_inv += valor

        veiculos_total = Decimal(0)
        for veiculo in bens.get("veiculos", []) or []:
            if isinstance(veiculo, dict):
                veiculos_total += self.veiculo_valor(veiculo)

        investimentos_total = Decimal(0)
        for inv in bens.get("investimentos", []) or []:
            investimentos_total += self.investimento_valor(inv)

        # Contas bancárias podem ser list-of-dict (com ``valor``) ou escalar
        # único (raro, mas presente em baselines mais antigas).
        contas_extras = Decimal(0)
        contas = bens.get("contas_bancarias")
        if isinstance(contas, list):
            for c in contas:
                contas_extras += self.investimento_valor(c)
        elif contas is not None:
            contas_extras += _safe_decimal(contas)
        # Campos extras adicionais (``saldo_corretora``, ``moeda_estrangeira``,
        # ``outros``) — paridade com fallback IRPF de ``analyze_patrimonio``.
        for extra in ("saldo_corretora", "moeda_estrangeira", "outros"):
            v = bens.get(extra)
            if v is not None:
                contas_extras += _safe_decimal(v)

        total_bens = _safe_decimal(member.get("total_bens", 0))
        total_dividas = _safe_decimal(member.get("total_dividas", member.get("dividas", 0)))

        return MemberPatrimonio(
            member_key=member_key,
            residencia=residencia,
            imoveis_investimento=imoveis_inv,
            veiculos=veiculos_total,
            investimentos=investimentos_total,
            contas_bancarias_extras=contas_extras,
            total_bens_irpf=total_bens,
            total_dividas=total_dividas,
        )

    def aggregate(self, members: Iterable[MemberPatrimonio]) -> dict[str, Decimal]:
        """Agrega vários ``MemberPatrimonio`` somando componentes.

        Útil para o caller que precisa do patrimônio consolidado da família
        sem repetir a soma manual em cada chamada.
        """
        total = {
            "residencia": Decimal(0),
            "imoveis_investimento": Decimal(0),
            "veiculos": Decimal(0),
            "investimentos": Decimal(0),
            "contas_bancarias_extras": Decimal(0),
            "total_bens_irpf": Decimal(0),
            "total_dividas": Decimal(0),
        }
        for mp in members:
            total["residencia"] += mp.residencia
            total["imoveis_investimento"] += mp.imoveis_investimento
            total["veiculos"] += mp.veiculos
            total["investimentos"] += mp.investimentos
            total["contas_bancarias_extras"] += mp.contas_bancarias_extras
            total["total_bens_irpf"] += mp.total_bens_irpf
            total["total_dividas"] += mp.total_dividas
        return total
