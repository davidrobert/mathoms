"""InstituicoesPorMembroAnalyzer — agrega instituições de investimento por membro + conta imóveis (companion de TopAtivosAnalyzer; mesmo bens_por_membro; substitui leitura de processed/E4_unified/*-4_unified.json em scripts/generate_narratives.py::_extract_top_institutions)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from pipeline.domain.services.investimentos_classes_analyzer import (
    InvestimentosClassesConfig,
)


@dataclass(frozen=True)
class InstituicoesPorMembroConfig:
    classes_config: InvestimentosClassesConfig

    @classmethod
    def from_configs(
        cls, *, residencia_property_ids: frozenset[str] = frozenset()
    ) -> "InstituicoesPorMembroConfig":
        return cls(
            classes_config=InvestimentosClassesConfig.from_configs(
                residencia_property_ids=residencia_property_ids
            )
        )


@dataclass(frozen=True)
class MembroInstituicoes:
    membro: str
    instituicoes: tuple[str, ...]

    def to_dict(self) -> dict:
        return {"membro": self.membro, "instituicoes": list(self.instituicoes)}


@dataclass(frozen=True)
class InstituicoesPorMembroResult:
    por_membro: tuple[MembroInstituicoes, ...]
    n_imoveis_total: int  # paridade com legado: residência + investimento

    def to_legacy_dict(self) -> dict:
        return {
            "instituicoes_por_membro": [m.to_dict() for m in self.por_membro],
            "n_imoveis_total": self.n_imoveis_total,
        }


class InstituicoesPorMembroAnalyzer:
    """Agrupa instituições por membro + conta imóveis a partir de bens_por_membro."""

    def __init__(self, config: InstituicoesPorMembroConfig | None = None) -> None:
        self._config = config or InstituicoesPorMembroConfig.from_configs()

    def analyze(
        self,
        bens_por_membro: list[tuple[str, Mapping[str, Any]]] | None,
    ) -> InstituicoesPorMembroResult:
        por_membro: list[MembroInstituicoes] = []
        n_imoveis = 0
        for member, bens in self._iter_entries(bens_por_membro or []):
            n_imoveis += self._count_imoveis(bens)
            if not member:
                # Workspace sem cônjuge → conjuge_key=""; pula da lista
                # (schema exige membro non-empty), mas n_imoveis fica.
                continue
            instituicoes = self._collect_instituicoes(bens)
            por_membro.append(MembroInstituicoes(membro=member, instituicoes=tuple(instituicoes)))
        por_membro.sort(key=lambda m: m.membro)
        return InstituicoesPorMembroResult(
            por_membro=tuple(por_membro),
            n_imoveis_total=n_imoveis,
        )

    @staticmethod
    def _iter_entries(entries):
        for entry in entries:
            if not isinstance(entry, tuple) or len(entry) != 2:
                continue
            member, bens = entry
            if isinstance(bens, Mapping):
                yield member, bens

    @staticmethod
    def _collect_instituicoes(bens: Mapping[str, Any]) -> list[str]:
        seen: set[str] = set()
        for inv in bens.get("investimentos", []) or []:
            if not isinstance(inv, Mapping):
                continue
            inst = str(inv.get("instituicao") or "").strip()
            if inst:
                seen.add(inst.capitalize())
        return sorted(seen)

    @staticmethod
    def _count_imoveis(bens: Mapping[str, Any]) -> int:
        # Paridade com _extract_top_institutions (legado): conta TODOS os imóveis,
        # incluindo residência. Filtros por classe ficam em TopAtivosAnalyzer/InvestimentosClassesAnalyzer.
        imoveis = bens.get("imoveis") or []
        if not isinstance(imoveis, list):
            return 0
        return sum(1 for i in imoveis if isinstance(i, Mapping))
