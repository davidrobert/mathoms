"""Oráculo de saldo do colapso ([[A40.l2]] · 4º P0 da verificação) — puro, sem I/O.

**Por que um oráculo próprio.** A prova que o enforce planejava usar — "os warnings de
continuidade de saldo não mudaram" — é verde **por construção, em duas camadas**:

1. ``e3_reconciler_adapter`` passa ``statements`` (lista **pré-colapso**) ao
   ``SaldoContinuityValidator``, e o comentário inline declara isso intencional
   ("sempre sobre os statements originais (pré-merge) para preservar fidelidade
   temporal"). A população certa nem chega ao validator.
2. ``reconciliation_validators`` compara ``closing_balance(n)`` vs
   ``opening_balance(n+1)`` — **metadado puro**, independente da lista de transações.
   Remover row não move esse número nem em princípio.

Não se conserta mudando a população: a fidelidade pré-merge é intencional. Conserta-se
medindo outra coisa — o **resíduo** ``closing − (opening + Σ tx)`` por statement, antes
e depois do colapso, e comparando a **DIREÇÃO**.

**A direção é o critério, não a magnitude.** Se as rows removidas são duplicatas
espúrias, o resíduo tem de se aproximar de zero: o saldo declarado pelo banco não muda,
e tirar lançamento que nunca existiu faz a conta fechar melhor. Resíduo que **se afasta**
é evidência de que a row removida era real. Medido em 2026-08-05, foi exatamente esse
eixo que reprovou as 140 remoções intra-proveniência (3/3 grupos pioraram, cada delta
igual ao cents removido daquele grupo).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class SaldoResidual:
    """Resíduo de um statement: ``closing − (opening + Σ tx)``, em cents."""

    source: str
    antes: int
    depois: int

    @property
    def mudou(self) -> bool:
        return self.antes != self.depois

    @property
    def melhorou(self) -> bool:
        """Aproximou-se de zero — o que uma remoção de duplicata espúria deve fazer."""
        return abs(self.depois) < abs(self.antes)

    @property
    def piorou(self) -> bool:
        return abs(self.depois) > abs(self.antes)


@dataclass(frozen=True)
class SaldoOracleReport:
    """Veredito PII-free — contagens e cents agregados, nunca linha individual."""

    mensuraveis: int = 0
    fechavam_em_zero: int = 0
    inalterados: int = 0
    melhoraram: int = 0
    pioraram: int = 0
    cents_piora: int = 0
    fontes_que_pioraram: tuple[str, ...] = field(default_factory=tuple)

    @property
    def observados(self) -> int:
        """Statements mensuráveis que o colapso de fato TOCOU."""
        return self.mensuraveis - self.inalterados

    @property
    def aprovado(self) -> bool:
        """Direção autoriza E o oráculo observou alguma remoção."""
        # `pioraram == 0` sozinho aprova por VACUIDADE quando nenhuma row removida caiu
        # em statement com saldo declarado nos dois lados — que é o caso comum, porque a
        # perna LLM tipicamente não traz saldo. Aprovar sem observar é o mesmo
        # falso-verde que este oráculo existe para substituir.
        return self.pioraram == 0 and self.observados > 0

    @property
    def vacuo(self) -> bool:
        """Nenhuma remoção caiu em statement mensurável — o oráculo não viu nada."""
        return self.observados == 0

    def as_details(self) -> dict:
        return {
            "mensuraveis": self.mensuraveis,
            "fechavam_em_zero": self.fechavam_em_zero,
            "inalterados": self.inalterados,
            "melhoraram": self.melhoraram,
            "pioraram": self.pioraram,
            "cents_piora": self.cents_piora,
            "observados": self.observados,
            "vacuo": self.vacuo,
            "aprovado": self.aprovado,
        }


def _cents(money) -> int | None:
    if money is None:
        return None
    return int((Decimal(str(money.amount)) * 100).to_integral_value())


def _residual(stmt) -> int | None:
    """``closing − (opening + Σ tx)`` em cents; ``None`` se falta saldo declarado."""
    abertura, fechamento = _cents(stmt.opening_balance), _cents(stmt.closing_balance)
    if abertura is None or fechamento is None:
        return None
    movimento = sum(_cents(tx.amount) or 0 for tx in stmt.transactions)
    return fechamento - (abertura + movimento)


def _by_source(statements) -> dict[str, int]:
    """``{source_document: resíduo}`` — só statements com saldo declarado nos dois lados."""
    out: dict[str, int] = {}
    for stmt in statements:
        residual = _residual(stmt)
        if residual is not None and stmt.source_document:
            out[stmt.source_document] = residual
    return out


def residuals(antes, depois) -> tuple[SaldoResidual, ...]:
    """Pareia por ``source_document`` — statement sem par nos dois lados é ignorado."""
    a, d = _by_source(antes), _by_source(depois)
    return tuple(
        SaldoResidual(source=src, antes=a[src], depois=d[src])
        for src in sorted(a.keys() & d.keys())
    )


def saldo_oracle(antes, depois) -> SaldoOracleReport:
    """Compara o resíduo de saldo antes/depois do colapso, pela DIREÇÃO."""
    linhas = residuals(antes, depois)
    pioraram = [r for r in linhas if r.piorou]
    return SaldoOracleReport(
        mensuraveis=len(linhas),
        fechavam_em_zero=sum(1 for r in linhas if r.antes == 0),
        inalterados=sum(1 for r in linhas if not r.mudou),
        melhoraram=sum(1 for r in linhas if r.melhorou),
        pioraram=len(pioraram),
        cents_piora=sum(abs(r.depois) - abs(r.antes) for r in pioraram),
        fontes_que_pioraram=tuple(r.source for r in pioraram),
    )


def fmt_saldo_oracle(report: SaldoOracleReport) -> list[str]:
    """Bloco PII-safe para o relatório do harness."""
    if not report.mensuraveis:
        return ["## Oráculo de saldo", "", "- nenhum statement com saldo declarado nos dois lados."]
    alerta = "  ⚠️ **DIREÇÃO CONTRÁRIA**" if report.pioraram else ""
    vacuo = "  ⚠️ **VÁCUO** — nenhuma remoção caiu em statement mensurável" if report.vacuo else ""
    return [
        "## Oráculo de saldo (resíduo `closing − (opening + Σ tx)`)",
        "",
        f"- mensuráveis: **{report.mensuraveis}** "
        f"(fechavam em zero: {report.fechavam_em_zero} · inalterados: {report.inalterados})",
        f"- **observados** (mensuráveis que o colapso tocou): **{report.observados}**{vacuo}",
        f"- melhoraram: **{report.melhoraram}** · pioraram: **{report.pioraram}**{alerta}",
        f"- cents de piora: **{report.cents_piora}**",
        f"- `aprovado={str(report.aprovado).lower()}` — a **direção** é o critério: resíduo "
        "que se afasta de zero é evidência de que a row removida era real",
    ]
