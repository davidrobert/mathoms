"""TopAtivosAnalyzer — ranking dos N maiores ativos individuais (companion de A5b InvestimentosClassesAnalyzer; lê o mesmo ``bens_por_membro``; inclui ``investimentos[]`` + ``imoveis[]`` não-residência; exclui escalares ``criptos``/``contas_bancarias``)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

from pipeline.domain.services.asset_classifier import AssetAuthority, classify_asset_outcome
from pipeline.domain.services.imovel_na_carteira import (
    CLASSES_SEM_PESO,
    classe_do_imovel_na_carteira,
)
from pipeline.domain.services.investimentos_classes_analyzer import (
    InvestimentosClassesConfig,
)
from pipeline.domain.services.patrimonio_imovel_classifier import (
    CLASSIFICATION_DESCONHECIDO,
    classificacao_do_imovel,
)
from pipeline.domain.services.patrimonio_types import imovel_property_id, imovel_valor


def _valor_declarado_do_imovel(imovel: Mapping[str, Any]) -> Decimal:
    """O mesmo valor que o patrimônio soma ([[ADR-431]]): não apurado fica de fora."""
    return _safe_money(imovel_valor(dict(imovel)))


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
        property_classification_overrides: Mapping[str, str] | None = None,
        limit: int = 15,
    ) -> "TopAtivosConfig":
        return cls(
            classes_config=InvestimentosClassesConfig.from_configs(
                scoring=scoring,
                property_classification_overrides=property_classification_overrides,
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
    # percentage 0-100, peso na carteira; `None` = sem peso ([[ADR-444]] D4).
    pct_carteira: float | None
    tipo_origem: str
    # Quem decidiu a `classe` ([[ADR-400]]) — inclusive `origem`, para imóvel,
    # cuja classe vem da proveniência e não de degrau algum.
    autoridade: str | None = None
    # Uso do imóvel (override da família); só em imóvel — o produtor de prosa a lê.
    classificacao_imovel: str | None = None

    def to_dict(self) -> dict:
        pct = round(self.pct_carteira, 2) if self.pct_carteira is not None else None
        d = {
            "posicao": self.posicao,
            "nome": self.nome,
            "classe": self.classe,
            "membro": self.membro,
            "instituicao": self.instituicao,
            "valor": float(round(self.valor, 2)),
            "pct_carteira": pct,
            "tipo_origem": self.tipo_origem,
            "autoridade": self.autoridade,
        }
        if self.tipo_origem == "imovel":
            d["classificacao_imovel"] = self.classificacao_imovel
        return d


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
    property_id: str | None = None
    autoridade: str | None = None
    classificacao_imovel: str | None = None


# Defaults de ignorância de `_classify_investimento` (`consolidate_baseline.py:732`):
# "não sei classificar", não tipo de produto. Como rótulo seriam o "Investimento
# pelado" que a [[ADR-337]] proíbe. Latente até a [[ADR-410]] D1 — o resolver
# descartava `tipo`, então `classe` vencia por ausência e ninguém viu.
_TIPOS_SEM_INFORMACAO = frozenset({"investimento", "investimentos", "outros"})


class TopAtivosAnalyzer:
    """Ranking dos N maiores ativos individuais por valor."""

    def __init__(self, config: TopAtivosConfig | None = None) -> None:
        self._config = config or TopAtivosConfig.from_configs()

    def analyze(
        self,
        bens_por_membro: list[tuple[str, Mapping[str, Any]]] | None,
        *,
        residencia_no_desconhecido: bool = False,
    ) -> TopAtivosResult:
        candidates = self._collect_candidates(bens_por_membro or [], residencia_no_desconhecido)
        candidates = _dedup_by_property_id(candidates)
        candidates.sort(key=lambda c: c.valor, reverse=True)
        # [[ADR-444]] D4: o item sem peso fica na posição por valor e fora da base dos demais.
        total = sum((c.valor for c in candidates if c.classe not in CLASSES_SEM_PESO), Decimal("0"))
        result = self._build_result(candidates, total)
        return TopAtivosResult(top_ativos=result, total_carteira=total)

    def _collect_candidates(
        self,
        bens_por_membro: list[tuple[str, Mapping[str, Any]]],
        residencia_no_desconhecido: bool,
    ) -> list[_Candidate]:
        out: list[_Candidate] = []
        for entry in bens_por_membro:
            if not isinstance(entry, tuple) or len(entry) != 2:
                continue
            member, bens = entry
            if not isinstance(bens, Mapping):
                continue
            out.extend(self._collect_investimentos(member, bens))
            out.extend(self._collect_imoveis(member, bens, residencia_no_desconhecido))
        return out

    def _build_result(self, candidates: list[_Candidate], total: Decimal) -> tuple[TopAtivo, ...]:
        top_n = candidates[: self._config.limit]
        out: list[TopAtivo] = []
        for i, c in enumerate(top_n, start=1):
            pct = _pct_na_carteira(c, total)
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
                    autoridade=c.autoridade,
                    classificacao_imovel=c.classificacao_imovel,
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
        descricao = str(inv.get("descricao") or inv.get("description") or "").strip()
        instituicao_raw = str(inv.get("instituicao") or "").strip()
        instituicao = instituicao_raw.capitalize() if instituicao_raw else ""
        resultado = self._classify(tipo, descricao)
        nome = self._nome_ou_fallback(inv, tipo, resultado.classe, instituicao)
        return _Candidate(
            nome=nome,
            classe=resultado.classe,
            membro=member,
            instituicao=instituicao,
            valor=valor,
            tipo_origem="investimento",
            autoridade=resultado.autoridade.value,
        )

    def _collect_imoveis(
        self, member: str, bens: Mapping[str, Any], residencia_no_desconhecido: bool
    ) -> list[_Candidate]:
        out: list[_Candidate] = []
        overrides = self._config.classes_config.property_classification_overrides
        for imovel in bens.get("imoveis", []) or []:
            if not isinstance(imovel, Mapping):
                continue
            cand = self._build_imovel_candidate(
                member, imovel, overrides, residencia_no_desconhecido
            )
            if cand is not None:
                out.append(cand)
        return out

    def _build_imovel_candidate(
        self, member: str, imovel: Mapping[str, Any], overrides: Mapping[str, str], sem_peso: bool
    ) -> _Candidate | None:
        valor = _valor_declarado_do_imovel(imovel)
        classe = classe_do_imovel_na_carteira(
            imovel, overrides, residencia_no_desconhecido=sem_peso
        )
        if valor <= 0 or classe is None:
            return None
        return _candidato_imovel(member, imovel, valor, classe, overrides)

    def _classify(self, tipo: str, descricao: str):
        """Delega para :func:`classify_asset_outcome` — taxonomia ADR-193 unificada
        com :class:`InvestimentosClassesAnalyzer`; `instituicao` não entra (ADR-400)."""
        return classify_asset_outcome(
            tipo,
            descricao,
            keywords=self._config.classes_config.keywords_por_classe,
        )

    def _nome_ou_fallback(self, inv, tipo: str, classe: str, instituicao: str) -> str:
        return str(inv.get("nome") or "").strip() or self._fallback_nome(tipo, classe, instituicao)

    @staticmethod
    def _fallback_nome(tipo: str, classe: str, instituicao: str) -> str:
        # ADR-337: sem nome do produto, cai na classe (nunca "Investimento" pelado).
        base = (tipo if tipo.strip().lower() not in _TIPOS_SEM_INFORMACAO else "") or classe
        return (
            f"{base or 'Investimento'} ({instituicao})" if instituicao else base or "Investimento"
        )


def _imovel_display_label(classificacao: str) -> str:
    """ADR-337: rótulo classe-only — a descrição cartorial (matrícula, IPTU, CPF de
    terceiro, endereço) NUNCA entra em ``top_ativos[].nome``. Esse campo é lido pela
    UI E pelo prompt do parecer (`$.investimentos.top_ativos[*]`, egresso a LLM de
    terceiro), então PII de localização/documento fica fora da fonte E5. Granularidade
    estrita ([[ADR-332]]); enriquecimento de display (bairro/cidade) só downstream."""
    # [[ADR-444]] D4: o nome segue a CLASSIFICAÇÃO — "de investimento" sobre uso
    # desconhecido reafirmaria o qualificador que a [[ADR-420]] §D1 tirou da composição.
    if classificacao == CLASSIFICATION_DESCONHECIDO:
        return "Imóvel com uso não apurado"
    return "Imóvel de investimento"


def _pct_na_carteira(candidato: "_Candidate", total: Decimal) -> float | None:
    if candidato.classe in CLASSES_SEM_PESO:
        return None
    return float(candidato.valor / total) * 100 if total > 0 else 0.0


def _candidato_imovel(
    member: str,
    imovel: Mapping[str, Any],
    valor: Decimal,
    classe: str,
    overrides: Mapping[str, str],
) -> "_Candidate":
    classificacao = classificacao_do_imovel(imovel, overrides)
    return _Candidate(
        nome=_imovel_display_label(classificacao),
        classe=classe,
        membro=_membro_label(imovel, member),
        instituicao="",
        valor=valor,
        tipo_origem="imovel",
        autoridade=AssetAuthority.ORIGEM.value,
        property_id=imovel_property_id(imovel),
        classificacao_imovel=classificacao,
    )


def _membro_label(imovel: Mapping[str, Any], member: str) -> str:
    """ADR-246: 'Casal' quando E1.5c marcou proprietario=casal após dedup."""
    return "Casal" if (imovel.get("proprietario") or "").lower() == "casal" else member


def _dedup_by_property_id(candidates: list[_Candidate]) -> list[_Candidate]:
    """Safety net (ADR-246): se PR1 falhar e baseline ainda vier duplicado,
    dedup por property_id mantém o maior valor por imóvel."""
    by_pid: dict[str, _Candidate] = {}
    out: list[_Candidate] = []
    for c in candidates:
        if c.property_id is None:
            out.append(c)
            continue
        existing = by_pid.get(c.property_id)
        if existing is None or c.valor > existing.valor:
            by_pid[c.property_id] = c
    out.extend(by_pid.values())
    return out
