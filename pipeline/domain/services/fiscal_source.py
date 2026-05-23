"""FiscalSource — adapter polimórfico sobre IRPFFullOutput + Informes anuais (ADR-238 D5)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Iterable, Optional

from pipeline.llm.schemas.e16_irpf_full import IRPFFullOutput

# Codes RFB declaração `pagamentos_efetuados` para PGBL (oficial / patrocinador).
_PGBL_CODIGOS_DEDUCAO = frozenset({"36"})  # CodigoPagamentoDedutivel.pgbl


def _to_decimal(v) -> Decimal:
    """Coerção minimalista; aceita Decimal/int/str. None → 0."""
    if v is None:
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


@dataclass(frozen=True)
class InformePrevidenciaSummary:
    """Visão sumarizada de informe PGBL/VGBL para consumo pelo analyzer."""

    plano_tipo: str  # "pgbl" | "vgbl"
    fonte_pagadora_cnpj: str
    ano_base: int
    contribuicoes_anuais: Decimal
    saldo_31_12: Decimal


_PJ_RETENCOES_FIELDS = (
    "irrf_anual",
    "csll_anual",
    "pis_anual",
    "cofins_anual",
    "inss_anual",
    "iss_anual",
)


def _build_pj_summary(informe: dict) -> Optional["InformeFinanceiroPJSummary"]:
    if informe.get("tipo_informe") != "financeiro_pj":
        return None
    payload = informe.get("financeiro_pj") or {}
    regime = payload.get("regime_tributario")
    if not regime:
        return None
    retencoes = sum(_to_decimal(payload.get(f, "0")) for f in _PJ_RETENCOES_FIELDS)
    return InformeFinanceiroPJSummary(
        regime_tributario=regime,
        cnpj_pagador=payload.get("cnpj_pagador", ""),
        cnpj_beneficiario=payload.get("cnpj_beneficiario", ""),
        ano_base=int(informe.get("ano_base", 0)),
        receita_bruta_anual=_to_decimal(payload.get("receita_bruta_anual")),
        retencoes_totais_anuais=retencoes,
    )


@dataclass(frozen=True)
class InformeFinanceiroPJSummary:
    """Visão sumarizada de informe Financeiro PJ — A17 L2 P3 (ADR-238 D5 · ADR-236 cascata)."""

    regime_tributario: str  # "simples_nacional" | "lucro_presumido"
    cnpj_pagador: str
    cnpj_beneficiario: str
    ano_base: int
    receita_bruta_anual: Decimal
    retencoes_totais_anuais: Decimal  # IRRF + CSLL + PIS + COFINS + INSS + ISS


@dataclass(frozen=True)
class FiscalDivergencia:
    """Divergência efêmera entre informe e declaração — gerada em E5, não persiste (LGPD)."""

    ano_base: int
    fonte_pagadora_cnpj: str
    informe_valor: Decimal
    irpf_valor: Decimal
    campo: str  # "pgbl_contribuicoes" | "saldo_31_12" | ...


@dataclass(frozen=True)
class FiscalSource:
    """Fonte fiscal consolidada (IRPF + informes) com precedência D4: declaração vence (ADR-238 D5)."""

    irpf: Optional[IRPFFullOutput] = None
    informes: tuple[dict, ...] = field(default_factory=tuple)

    @classmethod
    def from_irpf_full(cls, irpf: IRPFFullOutput | None) -> "FiscalSource":
        return cls(irpf=irpf, informes=())

    @classmethod
    def from_informes(cls, informes: Iterable[dict] | None) -> "FiscalSource":
        return cls(irpf=None, informes=tuple(informes or ()))

    @classmethod
    def from_both(
        cls, irpf: IRPFFullOutput | None, informes: Iterable[dict] | None
    ) -> "FiscalSource":
        return cls(irpf=irpf, informes=tuple(informes or ()))

    def has_pgbl_data(self) -> bool:
        """True quando há dado de PGBL em qualquer fonte (declaração ou informe)."""
        if self._irpf_pgbl_total() > 0:
            return True
        return any(self._informe_is_pgbl(i) for i in self.informes)

    def pgbl_contribuicoes_total(self) -> Decimal:
        """Total PGBL agregando IRPF + informes não-overlap; VGBL filtrado (ADR-238 D8)."""
        # Declaração vence: começa do IRPF e adiciona apenas informes cujo
        # (ano_base, fonte_cnpj) NÃO está no IRPF.
        cobertos_irpf = self._irpf_cnpjs_por_ano()
        total = self._irpf_pgbl_total()
        for informe in self.informes:
            if not self._informe_is_pgbl(informe):
                continue  # VGBL nunca conta
            ano = informe.get("ano_base")
            cnpj = informe.get("fonte_pagadora_cnpj")
            if (ano, cnpj) in cobertos_irpf:
                continue  # declaração vence
            payload = informe.get("previdencia") or {}
            total += _to_decimal(payload.get("contribuicoes_anuais"))
        return total

    def financeiro_pj_summaries(self) -> list[InformeFinanceiroPJSummary]:
        """Lista de informes financeiro_pj sumarizados (ADR-236 cascata: alimenta receita_pj quando E4 ausente)."""
        return [s for s in (_build_pj_summary(i) for i in self.informes) if s is not None]

    def previdencia_summaries(self) -> list[InformePrevidenciaSummary]:
        """Lista de informes previdência sumarizados (PGBL + VGBL — VGBL filtra no consumer)."""
        out: list[InformePrevidenciaSummary] = []
        for informe in self.informes:
            if informe.get("tipo_informe") != "previdencia_privada":
                continue
            payload = informe.get("previdencia") or {}
            plano = payload.get("plano_tipo")
            if not plano:
                continue
            out.append(
                InformePrevidenciaSummary(
                    plano_tipo=plano,
                    fonte_pagadora_cnpj=informe.get("fonte_pagadora_cnpj", ""),
                    ano_base=int(informe.get("ano_base", 0)),
                    contribuicoes_anuais=_to_decimal(payload.get("contribuicoes_anuais")),
                    saldo_31_12=_to_decimal(payload.get("saldo_31_12")),
                )
            )
        return out

    def _diff_pgbl_informe(
        self, informe: dict, irpf_por_chave: dict[tuple[int, str], Decimal]
    ) -> FiscalDivergencia | None:
        """Compara 1 informe vs declaração; retorna FiscalDivergencia ou None."""
        if not self._informe_is_pgbl(informe):
            return None
        ano = int(informe.get("ano_base", 0))
        cnpj = informe.get("fonte_pagadora_cnpj", "")
        irpf_valor = irpf_por_chave.get((ano, cnpj))
        if irpf_valor is None:
            return None
        payload = informe.get("previdencia") or {}
        informe_valor = _to_decimal(payload.get("contribuicoes_anuais"))
        if abs(informe_valor - irpf_valor) < Decimal("1.00"):
            return None
        return FiscalDivergencia(ano, cnpj, informe_valor, irpf_valor, "pgbl_contribuicoes")

    def divergencias_pgbl(self) -> list[FiscalDivergencia]:
        """Divergências PGBL informe vs declaração (LGPD: warning efêmero em E5, não persistir)."""
        if self.irpf is None or not self.informes:
            return []
        irpf_por_chave = self._irpf_pgbl_por_cnpj_ano()
        return [
            d
            for d in (self._diff_pgbl_informe(i, irpf_por_chave) for i in self.informes)
            if d is not None
        ]

    # ---- internals ----

    @staticmethod
    def _informe_is_pgbl(informe: dict) -> bool:
        if informe.get("tipo_informe") != "previdencia_privada":
            return False
        payload = informe.get("previdencia") or {}
        return payload.get("plano_tipo") == "pgbl"

    def _irpf_pgbl_total(self) -> Decimal:
        if self.irpf is None:
            return Decimal("0")
        total = Decimal("0")
        for pag in self.irpf.pagamentos_efetuados or []:
            codigo = getattr(pag.codigo, "value", pag.codigo) if hasattr(pag, "codigo") else None
            if codigo in _PGBL_CODIGOS_DEDUCAO:
                total += _to_decimal(getattr(pag, "valor_pago", 0))
        return total

    def _irpf_cnpjs_por_ano(self) -> set[tuple[int, str]]:
        """Set de ``(ano_base, cnpj)`` cobertos pela declaração — para dedupe D4."""
        if self.irpf is None:
            return set()
        ano = self._irpf_ano_base()
        if ano is None:
            return set()
        cnpjs: set[tuple[int, str]] = set()
        for pag in self.irpf.pagamentos_efetuados or []:
            codigo = getattr(pag.codigo, "value", pag.codigo) if hasattr(pag, "codigo") else None
            if codigo not in _PGBL_CODIGOS_DEDUCAO:
                continue
            cnpj = getattr(pag, "cnpj_beneficiario", None) or getattr(pag, "cnpj", None) or ""
            if cnpj:
                cnpjs.add((ano, cnpj))
        return cnpjs

    def _irpf_pgbl_por_cnpj_ano(self) -> dict[tuple[int, str], Decimal]:
        """Mapping ``(ano, cnpj) → soma_PGBL_declaracao`` para diff."""
        if self.irpf is None:
            return {}
        ano = self._irpf_ano_base()
        if ano is None:
            return {}
        out: dict[tuple[int, str], Decimal] = {}
        for pag in self.irpf.pagamentos_efetuados or []:
            codigo = getattr(pag.codigo, "value", pag.codigo) if hasattr(pag, "codigo") else None
            if codigo not in _PGBL_CODIGOS_DEDUCAO:
                continue
            cnpj = getattr(pag, "cnpj_beneficiario", None) or getattr(pag, "cnpj", None) or ""
            if not cnpj:
                continue
            chave = (ano, cnpj)
            out[chave] = out.get(chave, Decimal("0")) + _to_decimal(getattr(pag, "valor_pago", 0))
        return out

    def _irpf_ano_base(self) -> int | None:
        if self.irpf is None:
            return None
        contrib = getattr(self.irpf, "contribuinte", None)
        if contrib is None:
            return None
        ano = getattr(contrib, "ano_base", None)
        return int(ano) if ano is not None else None
