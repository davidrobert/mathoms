"""EndividamentoAnalyzer — análise de dívidas (Sessão A5b · Fase 8).

Extrai ``analyze_endividamento`` (e5_analyze.py:1602) em domain service puro.
Consolida dívidas por membro a partir do baseline e computa proporção sobre
o patrimônio bruto.

Função pura. Depende de ``_resolve_members`` (A5b vai reexpor) e
``MemberAnalyzer`` (A3c) para extração de totais por membro — aqui
recebemos os membros já resolvidos como lista de dicts para manter o service
desacoplado da lógica de resolução (que vive no orquestrador E5).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Callable, Mapping

from pipeline.domain.services.member_key_matcher import (
    matches_member_exclusively,
    matches_member_key,
)
from pipeline.domain.services.money_parsing import valor_monetario_float
from pipeline.observability.view_model_pii import redact_cartorial


def _safe_float(val) -> float:
    # O strip incondicional de `.` inflava valor ISO em 100× (r5/M28).
    return valor_monetario_float(val)


# =============================================================================
# Result
# =============================================================================


# Campos cujo valor obriga declaração de fonte no item — e vice-versa
# (bijeção; gate em ``tests/test_endividamento_fontes_bijecao.py``).
_CAMPOS_COM_FONTE = (
    "saldo_devedor",
    "parcela_mensal",
    "taxa_juros_aa",
    "desembolso_mensal_observado_brl",
)


@dataclass(frozen=True)
class DividaItem:
    # Ausência é None, nunca sentinela ("N/D"/0.0) — contrato tipado no schema E5
    # e guardrail do parecer tratam null como dado faltante (A37.l4 · DE-07).
    descricao: str
    saldo_devedor: float
    # ADR-401: a origem do saldo é `baseline_irpf` (estoque de 31/12) ou
    # `declarado` (usuário). Nenhum outro campo do item tem fonte hoje.
    fonte_saldo: str = "baseline_irpf"
    membro: str | None = None
    divida_id: str | None = None
    tipo: str | None = None
    saldo_ano_referencia: int | None = None
    parcela_mensal: float | None = None
    # Percentual absoluto AO ANO. O sufixo `_aa` é load-bearing: sem ele o
    # classificador monetário-por-default lê 12.5 como R$ 0,12 no snapshot.
    taxa_juros_aa: float | None = None

    def to_dict(self) -> dict:
        item = {
            "divida_id": self.divida_id,
            # A40.l6 redige PII cartorial; o rótulo já nasce de vocabulário
            # fechado (ADR-401 D4), então aqui é cinto-e-suspensório, não a
            # garantia — a peneira de `_CODIGO_CANONICO` é que fecha a porta.
            "descricao": redact_cartorial(self.descricao),
            "membro": self.membro,
            "tipo": self.tipo,
            "saldo_devedor": round(self.saldo_devedor, 2),
            "saldo_ano_referencia": self.saldo_ano_referencia,
            "parcela_mensal": round(self.parcela_mensal, 2)
            if self.parcela_mensal is not None
            else None,
            "taxa_juros_aa": self.taxa_juros_aa,
        }
        item["fontes"] = self._fontes(item)
        return item

    def _fontes(self, item: dict) -> dict:
        """Derivada do próprio item — bijeção por construção, não por disciplina."""
        origens = {
            "saldo_devedor": self.fonte_saldo,
            "parcela_mensal": "declarado",
            "taxa_juros_aa": "declarado",
            "desembolso_mensal_observado_brl": "observado_e4",
        }
        return {c: origens[c] for c in _CAMPOS_COM_FONTE if item.get(c) is not None}


@dataclass(frozen=True)
class EndividamentoAnalysis:
    total_dividas: float
    percentual_patrimonio: float
    dividas: tuple[DividaItem, ...]
    detalhe: str

    def to_legacy_dict(self) -> dict:
        return {
            "total_dividas": round(self.total_dividas, 2),
            "percentual_patrimonio": round(self.percentual_patrimonio, 2),
            "dividas": [d.to_dict() for d in self.dividas],
            "detalhe": self.detalhe,
        }


# Rótulos de exibição por tipo do baseline (ADR-301). A totalidade contra o
# enum do schema é gate — tipo novo sem rótulo não passa silenciosamente.
TIPO_LABEL: dict[str, str] = {
    "financiamento_imobiliario": "Financiamento imobiliário",
    "financiamento_veiculo": "Financiamento de veículo",
    "consignado": "Empréstimo consignado",
    "emprestimo_pessoal": "Empréstimo pessoal",
    "cheque_especial": "Cheque especial",
    "cartao_credito": "Cartão de crédito",
    "credito_rotativo": "Crédito rotativo",
    "outros": "Outras dívidas",
}
_DESC_SEM_TIPO = "Dívida (origem: declaração patrimonial)"

# Forma de código canônico do `institution_catalog` (ADR-137): `itau`, `c6bank`.
# `descricao` é artefato exportado no PDF (ADR-129), então o único dado externo
# que entra nela passa por esta peneira — resolver que devolva razão social por
# extenso ("Banco X S.A. — Ag 1234") é rejeitado e o rótulo cai no ordinal.
_CODIGO_CANONICO = re.compile(r"^[a-z0-9_]{2,32}$")

# Linha de `baseline["dividas"][]` (ADR-301). Alias nomeado em vez de
# `dict[str, Any]` cru: diz o que o dict é, e o schema já é o contrato.
DividaRow = Mapping[str, Any]


# Ler o objeto por ano com `safe_float` devolve 0.0 e some com a dívida — é o
# defeito vivo de `patrimonio_resolvers._total_dividas_for`, medido em 2026-08-19.
# Devolve `Decimal` — ADR-090: dinheiro é float só no wire, nunca no cálculo.
def _resolve_saldo(dv: DividaRow, ano_ref: str | None) -> Decimal:
    """``saldo_31_12`` é objeto por ano no schema (ADR-301); escalar é forma legada."""
    saldo = dv.get("saldo_31_12", 0)
    if not isinstance(saldo, dict):
        return _dec(saldo)
    if ano_ref and ano_ref in saldo:
        return _dec(saldo[ano_ref])
    anos = sorted(k for k in saldo if str(k).isdigit())
    return _dec(saldo[anos[-1]]) if anos else Decimal(0)


def _dec(valor: Any) -> Decimal:
    return Decimal(str(_safe_float(valor)))


def _ano_de(dv: DividaRow, ano_ref: str | None) -> int | None:
    for candidato in (dv.get("ano_referencia"), ano_ref):
        try:
            ano = int(candidato)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue
        if 2000 <= ano <= 2100:
            return ano
    saldo = dv.get("saldo_31_12")
    anos = sorted(k for k in saldo if str(k).isdigit()) if isinstance(saldo, dict) else []
    return int(anos[-1]) if anos else None


def _str_ou_none(valor: Any) -> str | None:
    return valor if isinstance(valor, str) and valor.strip() else None


# Match por token (`matches_member_key`, #1550), nunca substring: `ana` casava
# dentro de `mariana` e a dívida trocava de dono em silêncio (classe RV6-14).
def _detalhe(items: list[DividaItem]) -> str:
    return "; ".join(d.descricao for d in items) if items else "Sem dívidas identificadas"


def _item_de(dv: DividaRow, rotulo: str, ano_ref: str | None, identity: Any) -> DividaItem | None:
    """``None`` quando o saldo não é positivo — dívida quitada não é linha."""
    saldo = _resolve_saldo(dv, ano_ref)
    if saldo <= 0:
        return None
    tipo = dv.get("tipo")
    return DividaItem(
        descricao=rotulo,
        saldo_devedor=float(saldo),  # boundary do DTO: wire é JSON number (ADR-090)
        membro=_membro_de(dv, identity),
        divida_id=_str_ou_none(dv.get("divida_id")),
        tipo=tipo if tipo in TIPO_LABEL else None,
        saldo_ano_referencia=_ano_de(dv, ano_ref),
    )


def _membro_de(dv: DividaRow, identity: Any) -> str | None:
    """Nome de EXIBIÇÃO do dono; ``None`` quando conjunta ou não resolvida."""
    if identity is None:
        return None
    prop = str(dv.get("proprietario", "") or "").lower()
    if not prop:
        return None
    conjuge_key = getattr(identity, "conjuge_key", "")
    titular_key = getattr(identity, "titular_key", "")
    if conjuge_key and matches_member_exclusively(conjuge_key, titular_key, prop):
        return getattr(identity, "conjuge_nome", None) or None
    if conjuge_key and matches_member_key(conjuge_key, prop):
        return None  # conjunta: nem titular nem cônjuge sozinho é o dono
    if titular_key and matches_member_key(titular_key, prop):
        return getattr(identity, "titular_nome", None) or None
    return None


# =============================================================================
# Service
# =============================================================================


# O item publicado é uma DÍVIDA (contrato), não "um membro que tem dívida": a
# fonte é `baseline["dividas"][]`, itemizado desde a ADR-301. Antes da ADR-401 o
# analyzer ignorava esse array e fabricava um item por membro a partir de
# `member_data["total_dividas"]` — daí a `descricao` inventada.
# `resolve_credor_code` é opcional e mapeia `credor` para código canônico do
# `institution_catalog`; sem ele a desambiguação cai no ordinal, que é sempre
# correto e só menos informativo.
class EndividamentoAnalyzer:
    """Analisa estrutura de dívidas da família."""

    def __init__(
        self,
        resolve_credor_code: Callable[[str], str | None] | None = None,
    ) -> None:
        self._resolve_credor_code = resolve_credor_code

    def analyze(
        self,
        patrimonio: Mapping[str, Any],
        members: list[dict[str, Any]],
        *,
        dividas_baseline: list[DividaRow] | None = None,
        ano_ref: str | None = None,
        identity: Any = None,
    ) -> EndividamentoAnalysis:
        bruto = _safe_float(patrimonio.get("bruto", 0))
        dividas_total = _safe_float(patrimonio.get("dividas", 0))
        items = self._itemize(dividas_baseline, ano_ref, identity) or self._fallback_por_membro(
            members
        )
        return EndividamentoAnalysis(
            total_dividas=dividas_total,
            percentual_patrimonio=(dividas_total / bruto * 100) if bruto > 0 else 0.0,
            dividas=tuple(items),
            detalhe=_detalhe(items),
        )

    def _itemize(
        self,
        dividas: list[DividaRow] | None,
        ano_ref: str | None,
        identity: Any,
    ) -> list[DividaItem]:
        validas = [d for d in (dividas or []) if isinstance(d, dict)]
        rotulos = self._rotulos(validas) if validas else []
        items = [_item_de(dv, rotulos[idx], ano_ref, identity) for idx, dv in enumerate(validas)]
        return [i for i in items if i is not None]

    def _rotulos(self, dividas: list[DividaRow]) -> list[str]:
        """Rótulo por item, desambiguado só quando o tipo se repete."""
        por_tipo: dict[str | None, list[int]] = {}
        for idx, dv in enumerate(dividas):
            tipo = dv.get("tipo") if dv.get("tipo") in TIPO_LABEL else None
            por_tipo.setdefault(tipo, []).append(idx)
        rotulos = [""] * len(dividas)
        for tipo, idxs in por_tipo.items():
            base = TIPO_LABEL.get(tipo, _DESC_SEM_TIPO) if tipo else _DESC_SEM_TIPO
            for ordinal, idx in enumerate(idxs, start=1):
                sufixo = self._sufixo(dividas[idx], ordinal) if len(idxs) > 1 else ""
                rotulos[idx] = f"{base}{sufixo}"
        return rotulos

    def _sufixo(self, dv: DividaRow, ordinal: int) -> str:
        codigo = self._codigo_credor(dv.get("credor"))
        return f" — {codigo}" if codigo else f" #{ordinal}"

    def _codigo_credor(self, credor: Any) -> str | None:
        if not self._resolve_credor_code or not isinstance(credor, str) or not credor.strip():
            return None
        codigo = self._resolve_credor_code(credor)
        if not isinstance(codigo, str) or not _CODIGO_CANONICO.match(codigo):
            return None
        return codigo

    @staticmethod
    def _fallback_por_membro(members: list[dict[str, Any]] | None) -> list[DividaItem]:
        """Baseline sem itemização: 1 item por membro, sem inventar tipo nem credor."""
        items = []
        for entry in members or []:
            if not isinstance(entry, dict):
                continue
            member_data = entry.get("data") or {}
            valor = _safe_float(member_data.get("total_dividas", member_data.get("dividas", 0)))
            if valor > 0:
                items.append(
                    DividaItem(
                        descricao=_DESC_SEM_TIPO,
                        saldo_devedor=valor,
                        membro=entry.get("nome") or None,
                    )
                )
        return items
