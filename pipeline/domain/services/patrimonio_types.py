"""Value objects + helpers puros para ``PatrimonioCalculator`` (A6d.3.3 — ADR-100).

Módulo sem dependência de globals: cada função recebe explicitamente a config
de que precisa (:class:`MemberIdentity`, :class:`PatrimonioConfig`).

A hierarquia de arquivos:

- ``patrimonio_types.py`` — value objects + extractors triviais (este módulo)
- ``patrimonio_resolvers.py`` — resolvers de baseline em 4 formatos
- ``patrimonio_calculator.py`` — ``PatrimonioCalculator.calculate(inputs) -> dict``
"""

from __future__ import annotations

import calendar
import logging
import re
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Literal, Mapping

from pipeline.domain.services.conversao_me import ConversaoMeBrl
from pipeline.domain.services.money_parsing import valor_monetario_float

logger = logging.getLogger("mathoms.pipeline.patrimonio")

# Período sentinel de fatura sem data (propaga E0→E2→E3); nunca é ano-base.
_SENTINEL_PERIODO = "999999"

# Listas consolidadas (v1 + v2) varridas por ``_max_value_year`` e pelo eixo por membro.
CONSOLIDATED_LIST_KEYS = (
    "imoveis_consolidados",
    "bens_imoveis_consolidados",
    "investimentos_consolidados",
    "investimentos_financeiros_consolidados",
    "veiculos_consolidados",
    "dividas",
    "dividas_consolidadas",
)


# `float()` cru devolvia ``default`` para string pt-BR (`"243.285,37"` → 0,0) — a
# falha-espelho do ×100 (r5/M28): ali o dinheiro inflava, aqui desaparecia.
def safe_float(val: Any, default: float = 0.0) -> float:
    """Converte ``val`` para ``float``; retorna ``default`` se falhar."""
    return valor_monetario_float(val, default=default)


@dataclass(frozen=True)
class AnoReferenciaDivergenceWarning:
    """Ano-base dos itens (31/12) ≠ ano-chave do resumo (exercício) — ADR-274."""

    # Em artefato pós-Layer-2 não dispara; se disparar, a consolidação regrediu.
    value_year: str
    summary_year: str

    def format(self) -> str:
        return (
            f"ano_referencia divergente: itens em 31/12/{self.value_year} mas "
            f"resumo chaveado em {self.summary_year} (exercício). Resolvendo "
            f"valores por-item em {self.value_year} (self-heal, ADR-274)."
        )


# Aceita "YYYY" e legado "31_12_YYYY"; None para sentinel 999999 e chave
# ilegível. Comparar chaves SEM este parse é bug: max() lexicográfico faz
# "31_12_2024" vencer "2025" porque "3" > "2" (A40.l42).
def parse_ano_31_12(key: object) -> int | None:
    """Ano-base numa chave de ``valores_31_12``/``saldo_31_12`` (ADR-274)."""
    if _SENTINEL_PERIODO in str(key):
        return None
    match = re.search(r"(?:19|20)\d{2}", str(key))
    return int(match.group(0)) if match else None


def _years_in_vals(vals: object) -> set[int]:
    """Anos 31/12 numa dict ``valores_31_12``/``saldo_31_12`` (ADR-274)."""
    if not isinstance(vals, dict):
        return set()
    out: set[int] = set()
    for key in vals:
        ano = parse_ano_31_12(key)
        if ano is not None:
            out.add(ano)
    return out


def years_in_list(seq: object) -> set[int]:
    """Anos 31/12 numa lista consolidada de itens (ADR-274)."""
    out: set[int] = set()
    for item in seq or []:
        if isinstance(item, dict):
            out |= _years_in_vals(item.get("valores_31_12"))
            out |= _years_in_vals(item.get("saldo_31_12"))
    return out


def _max_value_year(baseline: dict) -> str | None:
    """Maior ano-base 31/12 entre os itens consolidados; ``None`` se nenhum."""
    years: set[int] = set()
    for list_key in CONSOLIDATED_LIST_KEYS:
        years |= years_in_list(baseline.get(list_key))
    return str(max(years)) if years else None


def resolve_value_year(baseline: dict, summary_year: str) -> str:
    """Ano-base de resolução por-item; warning tipado se divergir (ADR-274)."""
    # value_year = máximo dos itens; ausente → summary_year. Divergência
    # sinaliza consolidação keyed em exercício (pré-Layer-2) — warning ADR-097.
    value_year = _max_value_year(baseline) or summary_year
    if value_year != summary_year:
        warning = AnoReferenciaDivergenceWarning(value_year, summary_year)
        logger.warning(
            "patrimonio_ano_divergente: %s",
            warning.format(),
            extra={"value_year": value_year, "summary_year": summary_year},
        )
    return value_year


# =============================================================================
# Value objects
# =============================================================================


# `sem_dono` existe porque o domínio é ternário e `role_of` é binária: o `else`
# dela devolve `titular` para chave que não casa ninguém, afirmando posse que
# ninguém mediu. O enum sozinho NÃO trava a omissão do terceiro caso — não há
# mypy nem pyright em gate, e o mixin `str` mantém `PapelMembro.titular ==
# "titular"` verdadeiro, então um if/else binário segue calado. Quem trava é o
# teste de exaustividade sobre `set(PapelMembro)`, que o PR2 traz.
class PapelMembro(str, Enum):
    """Papel de uma posição — ternário ([[ADR-412]] §D2)."""

    titular = "titular"
    conjuge = "conjuge"
    sem_dono = "sem_dono"


@dataclass(frozen=True)
class MemberIdentity:
    """Identidade dos dois membros da família (titular + cônjuge).

    Substitui os globals ``_TITULAR_KEY``/``_CONJUGE_KEY``/``_TITULAR_NOME``/
    ``_CONJUGE_NOME``/``_KEY_INV_TITULAR``/``_KEY_INV_CONJUGE`` do script
    legado ``scripts/analyze_finances.py``.
    """

    titular_key: str
    conjuge_key: str
    titular_nome: str
    conjuge_nome: str

    # ADR-338: chaves de dict role-keyed (nunca derivadas do nome). O nome legal
    # vive só em VALORES (titular_nome/conjuge_nome); `titular_key`/`conjuge_key`
    # seguem como discriminadores internos de matching, nunca como chave emitida.
    @property
    def key_inv_titular(self) -> str:
        return "investimentos_titular"

    @property
    def key_inv_conjuge(self) -> str:
        return "investimentos_conjuge"

    @classmethod
    def from_family(cls, family: dict | None = None) -> "MemberIdentity":
        """Chaves e nomes de exibição a partir de ``family_members`` (DB, [[ADR-137]])."""
        fam = family or {}
        membros = fam.get("membros", {}) or {}
        if not isinstance(membros, dict):
            membros = {}
        titular_key = str(fam.get("titular", "david"))
        conjuge_key = next(
            (k for k, v in membros.items() if isinstance(v, dict) and v.get("papel") == "conjuge"),
            "",
        )
        return cls(
            titular_key=titular_key,
            conjuge_key=conjuge_key,
            titular_nome=membros.get(titular_key, {}).get("nome_curto", titular_key.title()),
            conjuge_nome=(
                membros.get(conjuge_key, {}).get("nome_curto", conjuge_key.title())
                if conjuge_key
                else ""
            ),
        )

    def role_of(self, member_key: str) -> str:
        return "conjuge" if self.conjuge_key and member_key == self.conjuge_key else "titular"

    def inv_key(self, member_key: str) -> str:
        return f"investimentos_{self.role_of(member_key)}"


@dataclass(frozen=True)
class PatrimonioConfig:
    """Config completa do :class:`PatrimonioCalculator`."""

    members: MemberIdentity

    # ADR-215 §1: mapping `property_id` → `classification` enum
    # (residencia_principal | uso_pessoal | locado | comercial | especulacao
    # | desconhecido). Vem do DB (`workspace_property_overrides`) via
    # `DBPropertyOverridesResolver` + `WorkspaceContext`. Empty dict ↔
    # workspace ainda não classificou nenhum imóvel — todos caem em cat_2.
    property_classification_overrides: dict[str, str] = field(default_factory=dict)

    # ADR-142 §Decisão (per-workspace via ADR-222): se `True`, `cat_2` (imóveis
    # de renda — somente classificações `locado` ou `comercial`) entra em
    # ``investivel_efetivo``; se `False`, fica fora (apenas cat_3+4+5+6 =
    # `investivel_financeiro`). ``uso_pessoal`` / ``especulacao`` /
    # ``desconhecido`` nunca entram, independente do toggle (Perini/Cerbasi).
    # Default ``True`` preserva retro-compat com `pipeline.json:14` legado.
    include_real_estate_in_if: bool = True


# Produtores carregam datas em larguras mistas ("YYYY-MM-DD", "YYYY-MM", "");
# comparar sem normalizar é bug de ordenação (mesma classe de A40.l42).
# Convenção: fim de período; "YYYY-MM" resolve para o último dia do mês.
def normalize_data_referencia(raw: object) -> tuple[str | None, str]:
    """Normaliza data de referência para ``(YYYY-MM-DD, precisao)`` (A40.l39)."""
    s = str(raw or "").strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
        return s, "dia"
    if re.fullmatch(r"\d{4}-\d{2}", s):
        ano, mes = int(s[:4]), int(s[5:7])
        return f"{s}-{calendar.monthrange(ano, mes)[1]:02d}", "mes"
    return None, "desconhecida"


@dataclass(frozen=True)
class CaixaDetalhe:
    """Linha de saldo em caixa ou moeda estrangeira (output legado)."""

    conta: str
    moeda: str
    saldo_original: float
    valor_brl: float
    tipo: str  # "caixa" | "moeda_estrangeira" | "moeda_estrangeira_irpf"
    # ADR-238 D5 (A33.l2): "extrato" | "informe_31_12" — informe vence extrato D+1.
    # ADR-238 §Emenda 2026-08-24 (A40.l63): + "baseline_irpf". A linha do
    # fallback ADR-245 herdava o default "extrato" e `build_posicao_31_12`
    # filtra por ele — ela entrava no card 31/12 com id `extrato:irpf_…` e
    # `data_referencia` nula, afirmando ser posição de extrato bancário.
    fonte: str = "extrato"
    # A40.l39 — fim de período do extrato vencedor (YYYY-MM-DD) + precisão
    # ("dia" | "mes" | "desconhecida"); linha de informe carrega 31/12/ano_base.
    data_referencia: str | None = None
    data_referencia_precisao: str = "desconhecida"
    # ADR-390 §Emenda 2026-08-24 (A40.l63) — obrigatório e keyword-only. Era
    # `| None = None` com o comentário "writer novo sempre preenche": prosa, não
    # tipo. O §Escopo 4 da lane sustentava o fechamento da classe em "o tipo não
    # deixa", e o tipo deixava — produtor novo publicava sem carimbo e o schema
    # validava, porque a ausência da chave também significa "artefato pré-390".
    # A tensão se resolve separando os lados: obrigatório na ESCRITA (aqui),
    # tolerante na LEITURA (`conversao` segue fora de `required` no schema).
    conversao: ConversaoMeBrl = field(kw_only=True)

    def to_dict(self) -> dict:
        return {
            "conta": self.conta,
            "moeda": self.moeda,
            "saldo_original": round(self.saldo_original, 2),
            "valor_brl": round(self.valor_brl, 2),
            "tipo": self.tipo,
            "fonte": self.fonte,
            "data_referencia": self.data_referencia,
            "data_referencia_precisao": self.data_referencia_precisao,
            "conversao": self.conversao.to_wire(),
        }


# Nenhuma conta some do caixa em silêncio: cada exclusão de domínio remanescente
# (poupança/PJ pendem de decisão de domínio; saldo desconhecido não é somável)
# deixa rastro estruturado no payload. Fatura é skip categórico: não é conta.
@dataclass(frozen=True)
class CaixaContaExcluida:
    """Conta E3 fora do caixa corrente, com razão tipada (ADR-376 §4 · ADR-097 D1)."""

    banco: str
    tipo_conta: str
    moeda: str
    motivo: str  # "poupanca" | "conta_pj" | "saldo_desconhecido"

    def format(self) -> str:
        return (
            f"conta {self.banco} ({self.tipo_conta}, {self.moeda}) "
            f"fora do caixa corrente: {self.motivo}"
        )

    def to_dict(self) -> dict:
        return {
            "banco": self.banco,
            "tipo_conta": self.tipo_conta,
            "moeda": self.moeda,
            "motivo": self.motivo,
        }


@dataclass(frozen=True)
class MarketValueResolution:
    """Resolução de valor de mercado para um imóvel (ADR-227 §D4)."""

    property_id: str
    valor_brl: Decimal
    source: Literal["mercado"]
    valuation_date: date
    staleness_days: int


@dataclass(frozen=True)
class RealEstateValuationContext:
    """Contexto pré-carregado (ADR-227 §D4); dict de market_values + debts evita I/O no domínio (ADR-111 stateless)."""

    market_values: Mapping[str, MarketValueResolution] = field(default_factory=dict)
    debts_by_property: Mapping[str, Decimal] = field(default_factory=dict)
    today: date = field(default_factory=date.today)


class IdentidadeIncoerenteError(RuntimeError):
    """Membros resolvidos com identidade diferente da que a config declara."""


@dataclass(frozen=True)
class MembrosResolvidos:
    """Titular e cônjuge já resolvidos, com as chaves de identidade que os produziram."""

    titular: Mapping[str, Any]
    conjuge: Mapping[str, Any]
    titular_key: str
    conjuge_key: str

    def as_tuple(self) -> tuple[dict, dict]:
        """Par ``(titular, conjuge)`` — forma que os consumidores legados leem."""
        return dict(self.titular), dict(self.conjuge)

    # Injeção obrigatória impede DOIS produtores; não impede que o único produtor
    # tenha rodado com a identidade errada ([[ADR-410]] D2).
    def afirma_coerencia_com(self, identity: "MemberIdentity") -> None:
        """Falha alto se o VO foi resolvido com chaves diferentes das da config."""
        esperado = (identity.titular_key, identity.conjuge_key)
        recebido = (self.titular_key, self.conjuge_key)
        if recebido != esperado:
            raise IdentidadeIncoerenteError(
                f"members resolvido para {recebido!r}, config declara {esperado!r}"
            )


@dataclass(frozen=True)
class PatrimonioInputs:
    """Inputs completos para ``PatrimonioCalculator.calculate``.

    O adapter carrega tudo via ``ArtifactStore`` + taxas.json + institutions.json
    e monta este value object. A calculadora opera pura sobre ele.
    """

    baseline: dict
    # `members` é obrigatório para que "dois produtores da mesma verdade" seja
    # impossível por construção, e não vigiado por gate ([[ADR-410]] D2): a
    # calculadora não tem resolver para chamar.
    members: MembrosResolvidos
    investimentos_atuais: dict | None = None
    caixa_total_brl: float = 0.0
    caixa_detalhes: list[CaixaDetalhe] = field(default_factory=list)
    valuation_context: RealEstateValuationContext | None = None

    @property
    def has_current_positions(self) -> bool:
        return (
            self.investimentos_atuais is not None
            and isinstance(self.investimentos_atuais, dict)
            and len(self.investimentos_atuais.get("dados", [])) > 0
        )


# =============================================================================
# Extractors triviais — pure value extraction with fallback keys
# =============================================================================


def imovel_valor(imovel: dict) -> float:
    """Valor de imóvel tentando chaves alternativas."""
    for key in ("valor_31_12_ano_base", "valor_irpf", "valor"):
        v = imovel.get(key)
        if v is not None:
            return safe_float(v)
    return 0.0


def imovel_property_id(imovel: dict) -> str | None:
    """Retorna `property_id` (ADR-215 P2) anexado ao imóvel pelo E1.5c, ou None."""
    pid = imovel.get("property_id")
    if isinstance(pid, str) and pid:
        return pid
    return None


def imovel_desc(imovel: dict) -> str:
    """Descrição de imóvel (lowercase) tentando múltiplas chaves.

    Tenta ``description``, ``descricao``, ``endereco`` e
    ``dados_completos.imovel`` — reproduz a lógica de ``_imovel_desc`` legacy.
    """
    desc = imovel.get("description") or imovel.get("descricao") or ""
    if not desc:
        desc = imovel.get("endereco") or ""
    if not desc:
        dc = imovel.get("dados_completos", {})
        if isinstance(dc, dict):
            desc = dc.get("imovel", "") or ""
    return desc.lower()


def veiculo_valor(veiculo: dict) -> float:
    """Valor de veículo tentando chaves alternativas."""
    for key in ("valor_31_12_ano_base", "valor_irpf", "valor"):
        v = veiculo.get(key)
        if v is not None:
            return safe_float(v)
    return 0.0


def investimento_valor(inv: Any) -> float:
    """Valor de investimento — aceita dict ou escalar.

    Um investimento pode ser ``{"valor_31_12_ano_base": 1000.0}`` ou um
    float puro (em formatos v1.5 consolidated que usam ``contas_bancarias``
    como escalar em vez de lista).
    """
    if isinstance(inv, dict):
        for key in ("valor_31_12_ano_base", "valor"):
            v = inv.get(key)
            if v is not None:
                return safe_float(v)
    return safe_float(inv)


def get_bens(member: dict) -> dict:
    """Retorna sub-dict ``bens`` (layout aninhado) ou o próprio membro (flat)."""
    if "bens" in member and isinstance(member["bens"], dict):
        return member["bens"]
    return member
