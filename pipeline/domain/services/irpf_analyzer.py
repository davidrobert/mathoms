"""IRPFAnalyzer — KPIs derivados de declarações IRPF (ADR-157)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from pipeline.llm.schemas.e16_irpf_full import (
    CodigoPagamentoDedutivel,
    CodigoRendimentoIsento,
    CodigoRendimentoTribExclusiva,
    IRPFFullOutput,
)

# Mapa de buckets para split trabalho×capital (Perini).
# Códigos isentos de capital: lucros (09), poupança/rendimentos (12).
# Códigos exclusiva de capital: JCP (10), aplicações (12), ganho de capital (06).
_CAPITAL_ISENTO = frozenset({CodigoRendimentoIsento.lucros_dividendos.value, "12"})
_CAPITAL_EXCLUSIVA = frozenset(
    {
        CodigoRendimentoTribExclusiva.jcp.value,
        CodigoRendimentoTribExclusiva.rendimentos_aplicacoes_financeiras.value,
        CodigoRendimentoTribExclusiva.ganho_capital.value,
    }
)
# Códigos exclusiva de trabalho: 13º (11) — entram no bucket trabalho.
_TRABALHO_EXCLUSIVA = frozenset({CodigoRendimentoTribExclusiva.decimo_terceiro.value})

# Pensão alimentícia paga (sai do bolso, fora do tributável)
_PENSAO_PAGA_CODIGOS = frozenset(
    {
        CodigoPagamentoDedutivel.pensao_alimenticia_judicial.value,
        CodigoPagamentoDedutivel.pensao_alimenticia_acordo_extrajudicial.value,
        CodigoPagamentoDedutivel.pensao_alimenticia_escritura.value,
    }
)

PGBL_TETO_PCT = Decimal("0.12")


@dataclass(frozen=True)
class RendaSplit:
    """Decomposição renda do trabalho × capital (Perini)."""

    trabalho_brl: Decimal
    capital_brl: Decimal

    @property
    def total_brl(self) -> Decimal:
        return self.trabalho_brl + self.capital_brl


@dataclass(frozen=True)
class AliquotaPair:
    """Duas alíquotas distintas — comparáveis a tabela RFB e a Cerbasi."""

    sobre_tributavel_pct: Decimal
    sobre_total_pct: Decimal


def _payload_to_model(d: dict) -> IRPFFullOutput:
    """Converte payload JSON (com Decimal-as-string) de volta para Pydantic."""
    return IRPFFullOutput.model_validate(d)


def _sum(values: Iterable[Decimal]) -> Decimal:
    total = Decimal("0")
    for v in values:
        total += v
    return total


class IRPFAnalyzer:
    """Queries puras sobre declarações IRPF (sem I/O — recebe lista de outputs)."""

    def __init__(self, declarations: list[IRPFFullOutput]):
        self._decls = declarations

    @classmethod
    def from_payloads(cls, payloads: list[dict]) -> "IRPFAnalyzer":
        return cls([_payload_to_model(p) for p in payloads])

    def _by_year(self, ano: int) -> list[IRPFFullOutput]:
        return [d for d in self._decls if d.contribuinte.ano_base == ano]

    def anos_base_disponiveis(self) -> list[int]:
        return sorted({d.contribuinte.ano_base for d in self._decls})

    def renda_anual_familiar(self, ano: int) -> Decimal:
        """Soma rendimentos brutos da família (titular + cônjuge) no ano-base."""
        decls = self._by_year(ano)
        return _sum(_renda_total(d) for d in decls)

    def rendimentos_tributaveis(self, ano: int) -> Decimal:
        """Apenas rendimentos tributáveis (PJ + PF + exterior) — base RFB."""
        decls = self._by_year(ano)
        return _sum(_renda_tributavel(d) for d in decls)

    def ir_pago_total(self, ano: int) -> Decimal:
        return _sum(d.imposto_apurado.ir_pago_brl for d in self._by_year(ano))

    def contrib_previdenciaria_total(self, ano: int) -> Decimal:
        decls = self._by_year(ano)
        return _sum(_contrib_previdenciaria(d) for d in decls)

    def pensao_alimenticia_paga(self, ano: int) -> Decimal:
        decls = self._by_year(ano)
        return _sum(_pensao_paga(d) for d in decls)

    def renda_liquida_familiar(self, ano: int) -> Decimal:
        bruta = self.renda_anual_familiar(ano)
        ir = self.ir_pago_total(ano)
        prev = self.contrib_previdenciaria_total(ano)
        pensao = self.pensao_alimenticia_paga(ano)
        return bruta - ir - prev - pensao

    def aliquotas(self, ano: int) -> AliquotaPair:
        tributavel = self.rendimentos_tributaveis(ano)
        total = self.renda_anual_familiar(ano)
        ir = self.ir_pago_total(ano)
        sobre_trib = (ir / tributavel * 100) if tributavel > 0 else Decimal("0")
        sobre_total = (ir / total * 100) if total > 0 else Decimal("0")
        return AliquotaPair(sobre_trib, sobre_total)

    def pgbl_capacidade_dedutivel(self, ano: int) -> Decimal:
        """Capacidade PGBL não usada (zero se modelo simplificado — G0)."""
        decls = self._by_year(ano)
        capacidade = Decimal("0")
        for d in decls:
            if d.contribuinte.modelo.value == "simplificado":
                continue
            tributavel = _renda_tributavel(d)
            ja_aportado = _pgbl_aportado(d)
            capacidade += (tributavel * PGBL_TETO_PCT) - ja_aportado
        return max(capacidade, Decimal("0"))

    def split_trabalho_vs_capital(self, ano: int) -> RendaSplit:
        """Trabalho = PJ + 13º exclusiva; Capital = aluguéis PF + isentos 09/12 + exclusiva 06/10/12 + exterior."""
        decls = self._by_year(ano)
        trabalho = _sum(_bucket_trabalho(d) for d in decls)
        capital = _sum(_bucket_capital(d) for d in decls)
        return RendaSplit(trabalho, capital)

    def evolucao_renda_anos(self) -> dict[int, Decimal]:
        return {ano: self.renda_anual_familiar(ano) for ano in self.anos_base_disponiveis()}

    def dependentes_validos(self, ano: int) -> list:
        decls = self._by_year(ano)
        out = []
        for d in decls:
            out.extend(d.dependentes)
        return out


# =============================================================================
# Helpers (módulo-level — pure functions, sem estado)
# =============================================================================


def _renda_tributavel(d: IRPFFullOutput) -> Decimal:
    pj = _sum(fp.rendimentos_tributaveis_brl for fp in d.rendimentos_pj)
    pf = _sum(fp.valor_brl for fp in d.rendimentos_pf)
    ext = _sum(fp.valor_brl for fp in d.rendimentos_exterior)
    return pj + pf + ext


def _renda_isenta(d: IRPFFullOutput) -> Decimal:
    return _sum(r.valor_brl for r in d.rendimentos_isentos)


def _renda_exclusiva(d: IRPFFullOutput) -> Decimal:
    return _sum(r.valor_brl for r in d.rendimentos_tributacao_exclusiva)


# Anti-13º duplo: 13º vive APENAS em rendimentos_tributacao_exclusiva no agregado;
# `decimo_terceiro_bruto_brl` da FontePagadoraPJ é informativo. Somar tributáveis
# + isentos + exclusiva sem incluir o decimo_terceiro_bruto da PJ evita duplicação.
def _renda_total(d: IRPFFullOutput) -> Decimal:
    """Total bruto: tributável + isentos + exclusiva (anti-13º duplo)."""
    return _renda_tributavel(d) + _renda_isenta(d) + _renda_exclusiva(d)


def _contrib_previdenciaria(d: IRPFFullOutput) -> Decimal:
    return _sum(fp.contrib_previdenciaria_brl for fp in d.rendimentos_pj)


def _pensao_paga(d: IRPFFullOutput) -> Decimal:
    return _sum(
        p.valor_dedutivel_brl
        for p in d.pagamentos_efetuados
        if p.codigo_rfb.value in _PENSAO_PAGA_CODIGOS
    )


def _pgbl_aportado(d: IRPFFullOutput) -> Decimal:
    return _sum(
        p.valor_dedutivel_brl
        for p in d.pagamentos_efetuados
        if p.codigo_rfb.value == CodigoPagamentoDedutivel.pgbl.value
    )


def _alugueis_pf(d: IRPFFullOutput) -> Decimal:
    # rendimentos_pf é o bucket canônico de aluguel recebido (PF→PF carnê-leão)
    # — schema docstring de FontePagadoraPF e prompt e16. Perini classifica
    # aluguel como capital imobiliário (AUVP idem); manter em trabalho era
    # artefato de implementação inicial. Re-classificação documentada na
    # ADR-NNN da lane A8.3 TRS real.
    return _sum(fp.valor_brl for fp in d.rendimentos_pf)


def _bucket_trabalho(d: IRPFFullOutput) -> Decimal:
    pj = _sum(fp.rendimentos_tributaveis_brl for fp in d.rendimentos_pj)
    decimo_terceiro = _sum(
        r.valor_brl
        for r in d.rendimentos_tributacao_exclusiva
        if r.codigo_rfb.value in _TRABALHO_EXCLUSIVA
    )
    return pj + decimo_terceiro


def _bucket_capital(d: IRPFFullOutput) -> Decimal:
    isentos = _sum(
        r.valor_brl for r in d.rendimentos_isentos if r.codigo_rfb.value in _CAPITAL_ISENTO
    )
    exclusiva = _sum(
        r.valor_brl
        for r in d.rendimentos_tributacao_exclusiva
        if r.codigo_rfb.value in _CAPITAL_EXCLUSIVA
    )
    exterior = _sum(fp.valor_brl for fp in d.rendimentos_exterior)
    return isentos + exclusiva + exterior + _alugueis_pf(d)


__all__ = ["IRPFAnalyzer", "RendaSplit", "AliquotaPair", "PGBL_TETO_PCT"]
