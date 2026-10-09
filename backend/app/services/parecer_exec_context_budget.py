"""O que o corpo do exec context pediu e o que coube nele ([[ADR-341]] §Emenda 2026-10-09)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# A eviction por seção ([[ADR-341]] D2) é a garantia do contrato, e era MUDA: o marcador
# só existia dentro do prompt. O parecer do dogfood deixou de ver investimentos em
# 2026-08-26 e independência financeira em 2026-08-29, e nada fora do modelo sabia
# ([[A40.l124]]). Este tipo é a forma publicada do plano de eviction: só inteiros e ids de
# seção (constantes do manifest), nunca valor. Granularidade de SEÇÃO de propósito: bloco
# de poucos campos revelaria, pelo tamanho, a ordem de grandeza do valor que ele carrega.


@dataclass(frozen=True)
class ExecContextBudget:
    """Bytes pedidos e entregues do corpo orçado + seções evictadas, na ordem de remoção."""

    cap_bytes: int
    demand_bytes: int
    body_bytes: int
    section_bytes: tuple[tuple[str, int], ...]
    evicted_section_ids: tuple[str, ...]
    hard_cut: bool
    # Fora do orçamento do corpo ([[ADR-341]] D4 e o catálogo da A26.l1): não competem
    # com dado, mas crescem sem teto que os vigie — os hints foram de 5,8 a 9,5 KB.
    hints_bytes: int
    catalog_bytes: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "cap_bytes": self.cap_bytes,
            "demand_bytes": self.demand_bytes,
            "body_bytes": self.body_bytes,
            "section_bytes": dict(self.section_bytes),
            "evicted_section_ids": list(self.evicted_section_ids),
            "hard_cut": self.hard_cut,
            "hints_bytes": self.hints_bytes,
            "catalog_bytes": self.catalog_bytes,
        }


@dataclass(frozen=True)
class EvictionPlan:
    """O plano de eviction JÁ executado: seções do manifest, corpos, evictadas e corte."""

    sections: list[dict]
    bodies: list[str]
    evicted: list[dict]
    cap: int
    hard_cut: bool


def _utf8_len(text: str) -> int:
    return len(text.encode("utf-8"))


def _section_ids(sections: list[dict]) -> tuple[str, ...]:
    return tuple(str(s.get("id", "")) for s in sections)


# Mede o plano JÁ executado e nunca re-planeja: ids e bytes saem da mesma chamada de
# `_evict_to_budget` que montou o corpo (lição da A40.l83 — instrumento e produção
# respondendo "o que o modelo vê?" por caminhos diferentes divergem calados).
def measure_exec_context_budget(
    plan: EvictionPlan, *, rendered: tuple[str, str, str]
) -> ExecContextBudget:
    """Orçamento do corpo que o modelo recebeu; ``rendered`` = (corpo, hints, catálogo)."""
    body, hints, catalog = rendered
    return ExecContextBudget(
        cap_bytes=plan.cap,
        demand_bytes=_utf8_len("\n".join(plan.bodies)),
        body_bytes=_utf8_len(body),
        section_bytes=tuple(zip(_section_ids(plan.sections), map(_utf8_len, plan.bodies))),
        evicted_section_ids=_section_ids(plan.evicted),
        hard_cut=plan.hard_cut,
        hints_bytes=_utf8_len(hints),
        catalog_bytes=_utf8_len(catalog),
    )
