"""Regra "informe 31/12 vence extrato D+1" — A17 L3 P3/P5 (ADR-238 D5, co-design 2026-07-07).

Informe é fonte fiscal certificada do snapshot 31/12: quando a mesma conta
aparece no extrato da virada de ano (dez/ano-base ou jan/ano-base+1), o
saldo do informe **sempre vence**. Tolerância assimétrica só decide se a
divergência gera warning: ``diff <= max(R$ 1,00; 0,01% do saldo)`` → adota
informe em silêncio; acima → adota informe + warning tipado (efêmero — o
diff com valores NÃO é persistido; payload carrega apenas booleans, padrão
``divergencias_pgbl()`` do PR #406 / LGPD).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass, replace
from dataclasses import field as dataclass_field
from decimal import Decimal

from pipeline.domain.services.patrimonio_types import CaixaDetalhe

#: Tipos de saldo de informe elegíveis para override de caixa — CDB/LCI/fundos
#: não são caixa e nunca substituem conta-corrente.
_TIPOS_CAIXA_INFORME = ("conta_corrente", "conta_exterior")

_TOLERANCIA_ABS = Decimal("1.00")
_TOLERANCIA_PCT = Decimal("0.0001")  # 0,01% do saldo do informe


@dataclass(frozen=True)
class InformeExtratoDivergencia:
    """Divergência informe 31/12 × extrato D+1 acima da tolerância (ADR-097 D1)."""

    instituicao: str
    moeda: str
    diff_brl: Decimal
    ano_base: int

    def format(self) -> str:
        return (
            f"saldo do informe 31/12/{self.ano_base} diverge do extrato da virada de ano "
            f"em R$ {self.diff_brl:,.2f} ({self.instituicao}, {self.moeda}); adotado o "
            f"informe como fonte fiscal; revise se houve movimentação na virada de ano."
        )


@dataclass(frozen=True)
class ExtratoPosicao:
    """Posição de caixa derivada de extrato E3 + metadados de matching."""

    detalhe: CaixaDetalhe
    banco: str
    period_end: str  # "YYYY-MM-DD" | "YYYY-MM" | ""


@dataclass(frozen=True)
class OverrideResult:
    """Posições pós-override + ajuste no total + divergências (efêmeras)."""

    detalhes: list[CaixaDetalhe]
    ajuste_total_brl: Decimal
    divergencias: list[InformeExtratoDivergencia]


def apply_informe_override(
    posicoes: list[ExtratoPosicao], informe_entries: list[dict]
) -> OverrideResult:
    """Aplica "informe vence extrato D+1"; muta entries in-place com marcas booleans (LGPD)."""
    acc = _OverrideAccumulator()
    for pos in posicoes:
        entry = _find_matching_informe(pos, informe_entries, acc.matched_ids)
        acc.consume(pos, entry)
    return OverrideResult(
        detalhes=acc.detalhes,
        ajuste_total_brl=acc.ajuste,
        divergencias=acc.divergencias,
    )


@dataclass
class _OverrideAccumulator:
    """Estado do loop de override — separa iteração de acumulação."""

    detalhes: list[CaixaDetalhe] = dataclass_field(default_factory=list)
    ajuste: Decimal = Decimal("0")
    divergencias: list[InformeExtratoDivergencia] = dataclass_field(default_factory=list)
    matched_ids: set[int] = dataclass_field(default_factory=set)

    def consume(self, pos: ExtratoPosicao, entry: dict | None) -> None:
        if entry is None:
            self.detalhes.append(pos.detalhe)
            return
        self.matched_ids.add(id(entry))
        novo, delta, div = _override_posicao(pos, entry)
        self.detalhes.append(novo)
        self.ajuste += delta
        if div is not None:
            self.divergencias.append(div)


def _find_matching_informe(
    pos: ExtratoPosicao, informe_entries: list[dict], matched_ids: set[int]
) -> dict | None:
    """1º informe elegível (tipo caixa, saldo_brl presente, moeda + banco + janela D+1)."""
    for entry in informe_entries:
        if id(entry) in matched_ids or not _is_elegivel(entry):
            continue
        if entry.get("moeda", "BRL") != pos.detalhe.moeda:
            continue
        if not _banco_match(pos.banco, entry):
            continue
        if not _period_in_janela_d1(pos.period_end, int(entry.get("ano_base", 0))):
            continue
        return entry
    return None


def _is_elegivel(entry: dict) -> bool:
    return entry.get("tipo") in _TIPOS_CAIXA_INFORME and entry.get("saldo_brl") is not None


def _banco_match(banco: str, entry: dict) -> bool:
    """Token do catálogo (`wise`, `c6bank`, `itau`) contido na descrição normalizada."""
    token = _norm_ascii(banco.strip())
    if not token:
        return False
    descricao = _norm_ascii(str(entry.get("descricao") or ""))
    return token in descricao or token in descricao.replace(" ", "")


def _norm_ascii(s: str) -> str:
    """Acento-insensitive: catálogo usa códigos ASCII, descrições têm acentos."""
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


def _period_in_janela_d1(period_end: str, ano_base: int) -> bool:
    """Extrato termina em dez/ano-base ou jan/ano-base+1 (a virada D+1 do ADR-238 D5)."""
    if not period_end or not ano_base:
        return False
    prefix = period_end[:7]
    return prefix in (f"{ano_base}-12", f"{ano_base + 1}-01")


def _override_posicao(
    pos: ExtratoPosicao, entry: dict
) -> tuple[CaixaDetalhe, Decimal, InformeExtratoDivergencia | None]:
    """Substitui valor do extrato pelo do informe; marca entry in-place (booleans)."""
    informe_brl = Decimal(str(entry["saldo_brl"]))
    extrato_brl = Decimal(str(pos.detalhe.valor_brl))
    diff = abs(informe_brl - extrato_brl)
    relevante = diff > max(_TOLERANCIA_ABS, informe_brl.copy_abs() * _TOLERANCIA_PCT)
    entry["informe_venceu_extrato"] = True
    entry["divergencia_relevante"] = relevante
    novo = replace(
        pos.detalhe,
        saldo_original=float(Decimal(str(entry.get("saldo_original") or "0"))),
        valor_brl=float(informe_brl),
        fonte="informe_31_12",
    )
    divergencia = _build_divergencia(pos, entry, diff) if relevante else None
    return novo, informe_brl - extrato_brl, divergencia


def _build_divergencia(
    pos: ExtratoPosicao, entry: dict, diff: Decimal
) -> InformeExtratoDivergencia:
    return InformeExtratoDivergencia(
        instituicao=pos.detalhe.conta,
        moeda=pos.detalhe.moeda,
        diff_brl=diff,
        ano_base=int(entry.get("ano_base", 0)),
    )
