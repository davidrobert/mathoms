"""IRPFAnalyzer — KPIs derivados de declarações IRPF (ADR-157, ADR-189)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Iterable

from pipeline.llm.schemas.e16_irpf_full import (
    CodigoPagamentoDedutivel,
    CodigoRendimentoIsento,
    CodigoRendimentoTribExclusiva,
    IRPFFullOutput,
)


class PgblStatus(str, Enum):
    """ADR-189: diagnóstico tipificado da capacidade PGBL (4 estados)."""

    capacidade_disponivel = "capacidade_disponivel"
    modelo_simplificado = "modelo_simplificado"
    no_teto = "no_teto"
    sem_renda_tributavel = "sem_renda_tributavel"


@dataclass(frozen=True)
class PgblResumo:
    """ADR-189 §D2: aporte e teto dedutível no ano."""

    aportado_brl: Decimal
    teto_brl: Decimal


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

# Educação: teto fixo R$ 3.561,50 por pessoa (titular + cada dependente) —
# Instrução Normativa RFB 1.500/2014, valor congelado pela RFB. ADR-194 §D5
# anota o débito de migrar para fiscal_parameters table (ADR-135) quando RFB
# atualizar; lookup por ano-base sai de escopo nesta lane.
EDUCACAO_TETO_PER_PESSOA = Decimal("3561.50")

# Pensão alimentícia: 3 variantes RFB (judicial, acordo extrajudicial,
# escritura) consolidadas em 1 chave única no payload de saída — agregação
# no serializer (não no analyzer, que permanece fiel ao schema E1.6).
# ADR-194 §D4.
_PENSAO_ALIMENTICIA_CODIGOS = frozenset(
    {
        CodigoPagamentoDedutivel.pensao_alimenticia_judicial.value,
        CodigoPagamentoDedutivel.pensao_alimenticia_acordo_extrajudicial.value,
        CodigoPagamentoDedutivel.pensao_alimenticia_escritura.value,
    }
)


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

    def declarations_for_year(self, ano: int) -> list[IRPFFullOutput]:
        """Acesso público às declarações filtradas por ano-base (consumido por outros services)."""
        return list(self._by_year(ano))

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

    def pgbl_resumo(self, ano: int) -> PgblResumo:
        """ADR-189 §D2: aporte total + teto dedutível (12% × tributável das completas)."""
        decls = self._by_year(ano)
        aportado = _sum(_pgbl_aportado(d) for d in decls)
        teto = _sum(
            _renda_tributavel(d) * PGBL_TETO_PCT
            for d in decls
            if d.contribuinte.modelo.value != "simplificado"
        )
        return PgblResumo(aportado_brl=aportado, teto_brl=teto)

    def pgbl_status(self, ano: int) -> PgblStatus:
        """ADR-189: classifica o ano em um dos 4 estados de capacidade PGBL."""
        decls = self._by_year(ano)
        if decls and all(d.contribuinte.modelo.value == "simplificado" for d in decls):
            return PgblStatus.modelo_simplificado
        if self.rendimentos_tributaveis(ano) == Decimal("0"):
            return PgblStatus.sem_renda_tributavel
        if self.pgbl_capacidade_dedutivel(ano) > Decimal("0"):
            return PgblStatus.capacidade_disponivel
        return PgblStatus.no_teto

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

    def dependentes_count(self, ano: int) -> dict:
        """ADR-194 §D1: total + agregação por relação RFB (sparse)."""
        deps = self.dependentes_validos(ano)
        por_relacao: dict[str, int] = {}
        for d in deps:
            key = d.relacao.value
            por_relacao[key] = por_relacao.get(key, 0) + 1
        return {"count": len(deps), "por_relacao": por_relacao}

    def dedutiveis_aplicados(self, ano: int) -> dict:
        """ADR-194 §D2/D4/D5: 4 categorias sparse; PGBL excluído (ADR-189)."""
        pagamentos = self._pagamentos_no_ano(ano)
        educacao_teto = EDUCACAO_TETO_PER_PESSOA * (self.dependentes_count(ano)["count"] + 1)
        return _build_dedutiveis_payload(pagamentos, educacao_teto)

    def _pagamentos_no_ano(self, ano: int) -> list:
        return [p for d in self._by_year(ano) for p in d.pagamentos_efetuados]


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


def _sum_pagamentos_by_codes(pagamentos, codes: frozenset[str] | set[str]) -> dict:
    """ADR-194 §D2: agrega pagamentos por código RFB; teto_aplicado é `any(...)`."""
    filtrados = [p for p in pagamentos if p.codigo_rfb.value in codes]
    utilizado = _sum(p.valor_dedutivel_brl for p in filtrados)
    teto_aplicado = any(p.teto_aplicado for p in filtrados)
    return {"utilizado": utilizado, "teto_aplicado": teto_aplicado}


def _categoria_factual(utilizado: Decimal) -> dict | None:
    """Linha de categoria sem teto legal (saúde/pensão/INSS) — ADR-194 §D2."""
    if utilizado <= 0:
        return None
    return {"utilizado_brl": str(utilizado), "teto_brl": None, "teto_aplicado": False}


def _categoria_educacao(agg: dict, teto: Decimal) -> dict | None:
    """Linha de educação com teto agregado por pessoa — ADR-194 §D5."""
    utilizado = agg["utilizado"]
    if utilizado <= 0:
        return None
    teto_aplicado = agg["teto_aplicado"] or utilizado >= teto
    return {
        "utilizado_brl": str(utilizado),
        "teto_brl": str(teto),
        "teto_aplicado": teto_aplicado,
    }


_DEDUTIVEL_CODIGOS_FACTUAIS = {
    "saude": frozenset({CodigoPagamentoDedutivel.saude.value}),
    "pensao_alimenticia": _PENSAO_ALIMENTICIA_CODIGOS,
    "previdencia_oficial": frozenset({CodigoPagamentoDedutivel.previdencia_oficial.value}),
}
_DEDUTIVEL_CODIGOS_EDUCACAO = frozenset({CodigoPagamentoDedutivel.educacao.value})


def _build_dedutiveis_payload(pagamentos, educacao_teto: Decimal) -> dict:
    """ADR-194 §D3/D4: monta payload sparse das 4 categorias publicáveis."""
    out: dict[str, dict] = {}
    for key, codes in _DEDUTIVEL_CODIGOS_FACTUAIS.items():
        line = _categoria_factual(_sum_pagamentos_by_codes(pagamentos, codes)["utilizado"])
        if line is not None:
            out[key] = line
    edu = _categoria_educacao(
        _sum_pagamentos_by_codes(pagamentos, _DEDUTIVEL_CODIGOS_EDUCACAO),
        educacao_teto,
    )
    if edu is not None:
        out["educacao"] = edu
    return _reorder_dedutiveis(out)


def _reorder_dedutiveis(payload: dict) -> dict:
    """ADR-194 §D8: ordem fixa saude→educacao→pensao→previdencia."""
    ordem = ("saude", "educacao", "pensao_alimenticia", "previdencia_oficial")
    return {k: payload[k] for k in ordem if k in payload}


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


# ADR-238 D5: ``FiscalAnalyzer`` é o novo nome canônico do IRPFAnalyzer
# pós-A17. Mantemos ``IRPFAnalyzer`` como alias por 1 sprint (cutover A18)
# para callers existentes; novos call-sites devem usar ``FiscalAnalyzer``.
# Quando o ``FiscalSource`` adapter cobrir 100% dos consumers em L2-L4, o
# alias é removido.
FiscalAnalyzer = IRPFAnalyzer


__all__ = [
    "IRPFAnalyzer",
    "FiscalAnalyzer",
    "RendaSplit",
    "AliquotaPair",
    "PGBL_TETO_PCT",
    "PgblStatus",
    "PgblResumo",
    "EDUCACAO_TETO_PER_PESSOA",
]
