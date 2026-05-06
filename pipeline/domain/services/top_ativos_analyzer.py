"""TopAtivosAnalyzer — ranking dos N maiores ativos individuais (companion de A5b InvestimentosClassesAnalyzer; lê o mesmo ``bens_por_membro``; inclui ``investimentos[]`` + ``imoveis[]`` não-residência; exclui escalares ``criptos``/``contas_bancarias``)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

from pipeline.domain.services.investimentos_classes_analyzer import (
    InvestimentosClassesConfig,
)


def _safe_money(val) -> Decimal:
    if val is None:
        return Decimal("0")
    if isinstance(val, Decimal):
        return val
    if isinstance(val, (int, float)):
        return Decimal(str(val))
    if isinstance(val, str):
        try:
            return Decimal(val.replace(",", "."))
        except (ValueError, ArithmeticError):
            return Decimal("0")
    return Decimal("0")


@dataclass(frozen=True)
class TopAtivosConfig:
    classes_config: InvestimentosClassesConfig
    limit: int = 15

    @classmethod
    def from_configs(
        cls,
        *,
        scoring: dict | None = None,
        residencia_keyword: str = "",
        limit: int = 15,
    ) -> "TopAtivosConfig":
        return cls(
            classes_config=InvestimentosClassesConfig.from_configs(
                scoring=scoring, residencia_keyword=residencia_keyword
            ),
            limit=limit,
        )


@dataclass(frozen=True)
class TopAtivo:
    posicao: int
    nome: str
    classe: str
    membro: str
    instituicao: str
    valor: Decimal
    pct_carteira: float  # percentage 0-100, peso na carteira
    tipo_origem: str

    def to_dict(self) -> dict:
        return {
            "posicao": self.posicao,
            "nome": self.nome,
            "classe": self.classe,
            "membro": self.membro,
            "instituicao": self.instituicao,
            "valor": float(round(self.valor, 2)),
            "pct_carteira": round(self.pct_carteira, 2),
            "tipo_origem": self.tipo_origem,
        }


@dataclass(frozen=True)
class TopAtivosResult:
    top_ativos: tuple[TopAtivo, ...]
    total_carteira: Decimal

    def to_legacy_dict(self) -> dict:
        return {"top_ativos": [a.to_dict() for a in self.top_ativos]}


@dataclass(frozen=True)
class _Candidate:
    nome: str
    classe: str
    membro: str
    instituicao: str
    valor: Decimal
    tipo_origem: str


class TopAtivosAnalyzer:
    """Ranking dos N maiores ativos individuais por valor."""

    def __init__(self, config: TopAtivosConfig | None = None) -> None:
        self._config = config or TopAtivosConfig.from_configs()

    def analyze(
        self,
        bens_por_membro: list[tuple[str, Mapping[str, Any]]] | None,
    ) -> TopAtivosResult:
        candidates = self._collect_candidates(bens_por_membro or [])
        candidates.sort(key=lambda c: c.valor, reverse=True)
        total = sum((c.valor for c in candidates), start=Decimal("0"))
        result = self._build_result(candidates, total)
        return TopAtivosResult(top_ativos=result, total_carteira=total)

    def _collect_candidates(
        self,
        bens_por_membro: list[tuple[str, Mapping[str, Any]]],
    ) -> list[_Candidate]:
        out: list[_Candidate] = []
        for entry in bens_por_membro:
            if not isinstance(entry, tuple) or len(entry) != 2:
                continue
            member, bens = entry
            if not isinstance(bens, Mapping):
                continue
            out.extend(self._collect_investimentos(member, bens))
            out.extend(self._collect_imoveis(member, bens))
        return out

    def _build_result(self, candidates: list[_Candidate], total: Decimal) -> tuple[TopAtivo, ...]:
        top_n = candidates[: self._config.limit]
        out: list[TopAtivo] = []
        for i, c in enumerate(top_n, start=1):
            pct = float(c.valor / total) * 100 if total > 0 else 0.0
            out.append(
                TopAtivo(
                    posicao=i,
                    nome=c.nome,
                    classe=c.classe,
                    membro=c.membro,
                    instituicao=c.instituicao,
                    valor=c.valor,
                    pct_carteira=pct,
                    tipo_origem=c.tipo_origem,
                )
            )
        return tuple(out)

    def _collect_investimentos(self, member: str, bens: Mapping[str, Any]) -> list[_Candidate]:
        out: list[_Candidate] = []
        for inv in bens.get("investimentos", []) or []:
            if not isinstance(inv, Mapping):
                continue
            cand = self._build_inv_candidate(member, inv)
            if cand is not None:
                out.append(cand)
        return out

    def _build_inv_candidate(self, member: str, inv: Mapping[str, Any]) -> _Candidate | None:
        valor = _safe_money(inv.get("valor", inv.get("valor_31_12_ano_base", 0)))
        if valor <= 0:
            return None
        tipo = str(inv.get("tipo") or "").strip()
        instituicao_raw = str(inv.get("instituicao") or "").strip()
        instituicao = instituicao_raw.capitalize() if instituicao_raw else ""
        nome = str(inv.get("nome") or "").strip() or self._fallback_nome(tipo, instituicao)
        return _Candidate(
            nome=nome,
            classe=self._classify_tipo(tipo),
            membro=member,
            instituicao=instituicao,
            valor=valor,
            tipo_origem="investimento",
        )

    def _collect_imoveis(self, member: str, bens: Mapping[str, Any]) -> list[_Candidate]:
        out: list[_Candidate] = []
        kw = self._config.classes_config.residencia_keyword
        for imovel in bens.get("imoveis", []) or []:
            if not isinstance(imovel, Mapping):
                continue
            cand = self._build_imovel_candidate(member, imovel, kw)
            if cand is not None:
                out.append(cand)
        return out

    def _build_imovel_candidate(
        self, member: str, imovel: Mapping[str, Any], residencia_kw: str
    ) -> _Candidate | None:
        valor = _safe_money(
            imovel.get("valor_31_12_ano_base") or imovel.get("valor_irpf") or imovel.get("valor", 0)
        )
        if valor <= 0:
            return None
        if residencia_kw and residencia_kw in self._imovel_desc(imovel):
            return None
        return _Candidate(
            nome=self._imovel_nome(imovel),
            classe="Imóveis Investimento",
            membro=member,
            instituicao="",
            valor=valor,
            tipo_origem="imovel",
        )

    def _classify_tipo(self, tipo: str) -> str:
        tipo_lower = tipo.lower()
        for classe in ("Ações", "Renda Fixa", "Cripto", "Contas Bancárias"):
            keywords = self._config.classes_config.keywords_por_classe.get(classe, ())
            if any(kw in tipo_lower for kw in keywords):
                return classe
        return "Outros"

    @staticmethod
    def _fallback_nome(tipo: str, instituicao: str) -> str:
        if not tipo:
            return instituicao or "Investimento"
        if instituicao:
            return f"{tipo} ({instituicao})"
        return tipo

    @staticmethod
    def _imovel_desc(imovel: Mapping[str, Any]) -> str:
        desc = imovel.get("description") or imovel.get("descricao") or ""
        if not desc:
            desc = imovel.get("endereco") or ""
        if not desc:
            dc = imovel.get("dados_completos")
            if isinstance(dc, Mapping):
                desc = dc.get("imovel", "") or ""
        return str(desc).lower()

    @staticmethod
    def _imovel_nome(imovel: Mapping[str, Any]) -> str:
        for key in ("description", "descricao", "endereco"):
            v = imovel.get(key)
            if v:
                return str(v).strip()
        dc = imovel.get("dados_completos")
        if isinstance(dc, Mapping):
            v = dc.get("imovel")
            if v:
                return str(v).strip()
        return "Imóvel investimento"
