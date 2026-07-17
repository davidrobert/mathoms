"""Sanitiza PII do contexto do parecer antes do egresso ao LLM — CTO-03 / [[ADR-332]].

O parecer expõe o E5 ao provider por DOIS egressos que leem o mesmo ``e5_data``:
o distiller (``parecer_distiller``, paths do manifest) e a tool
``get_e5_section`` (``planner_drill_down``, devolve seções INTEIRAS sem truncar,
26 roots do whitelist). Sanitizar o objeto uma vez no boundary ``generate_parecer``,
ANTES de ``compute_cache_key``, cobre os dois por construção (um choke point).

Estratégia (co-design senior-cto + prompt-engineer, 2026-07-16): substituir nome
próprio de membro por PAPEL (Titular/Cônjuge/Dependente) — a análise patrimonial
opera sobre papéis, não nomes; o React (superfície do dono) mantém o nome real.
Scrub global word-boundary sobre toda string E chave-de-dict cobre os vetores
conhecidos (``top_ativos[].membro``, ``composicao[].categoria``,
``receita_datasets[].label``, chaves de ``por_fonte_detalhado``) E a cauda das
seções que a tool devolve inteiras. ``valor``/número nunca é tocado ([[ADR-090]]).
Identificadores (CPF/CNPJ) são redigidos como defesa em profundidade.
"""

from __future__ import annotations

import re
from typing import Any, Mapping

from pipeline.observability.pii_patterns import scrub_identifiers

# 2 pega nomes curtos reais (ex.: "Zé") sem vazá-los ao provider; 1 char é
# patológico e over-redigiria demais (CTO-03, finding da revisão adversarial).
_MIN_NAME_LEN = 2
_ROLE_LABEL = {"titular": "Titular", "conjuge": "Cônjuge"}


def _papel(key: str, info: Mapping[str, Any], titular_key: str) -> str:
    return str(info.get("papel") or ("titular" if key == titular_key else "dependente_outro"))


def _dep_label(key: str, deps: list[str], multi_dep: bool) -> str:
    """Ordinal estável (por ordem de key) só quando há 2+ dependentes."""
    return f"Dependente {deps.index(key) + 1}" if multi_dep else "Dependente"


def build_name_role_pairs(family_config: Mapping[str, Any] | None) -> tuple[tuple[str, str], ...]:
    """(nome_curto, papel) por membro do ``family_members`` — Titular/Cônjuge/Dependente[ N]."""
    fam = family_config or {}
    membros = fam.get("membros") or {}
    if not isinstance(membros, dict):
        return ()
    titular_key = str(fam.get("titular") or "")
    ordered = sorted((k, v) for k, v in membros.items() if isinstance(v, dict))
    deps = [k for k, v in ordered if _papel(k, v, titular_key) not in ("titular", "conjuge")]
    multi_dep = len(deps) > 1
    pairs = []
    for key, info in ordered:
        papel = _papel(key, info, titular_key)
        label = _ROLE_LABEL.get(papel) or _dep_label(key, deps, multi_dep)
        pairs.append((str(info.get("nome_curto") or key.title()), label))
    return tuple(pairs)


def _compile_name_subs(
    name_role_pairs: tuple[tuple[str, str], ...],
) -> list[tuple[re.Pattern, str]]:
    """Regex word-boundary case-insensitive por nome (maior primeiro) → papel."""
    subs = []
    for name, role in sorted(name_role_pairs, key=lambda p: -len(p[0])):
        if name and len(name) >= _MIN_NAME_LEN:
            subs.append((re.compile(rf"\b{re.escape(name)}\b", re.IGNORECASE), role))
    return subs


def _scrub_text(text: str, name_subs: list[tuple[re.Pattern, str]]) -> str:
    for pattern, role in name_subs:
        text = pattern.sub(role, text)
    return scrub_identifiers(text)


def _scrub_node(node: Any, name_subs: list[tuple[re.Pattern, str]]) -> Any:
    if isinstance(node, Mapping):
        return {_scrub_text(str(k), name_subs): _scrub_node(v, name_subs) for k, v in node.items()}
    if isinstance(node, list):
        return [_scrub_node(v, name_subs) for v in node]
    if isinstance(node, str):
        return _scrub_text(node, name_subs)
    return node


def sanitize_e5_for_parecer(
    e5_data: Mapping[str, Any], name_role_pairs: tuple[tuple[str, str], ...]
) -> dict[str, Any]:
    """Cópia de ``e5_data`` com nome de membro → papel + CPF/CNPJ redigidos; número
    nunca tocado ([[ADR-090]]). Roda antes de ``compute_cache_key`` (re-gen única de cache)."""
    return _scrub_node(dict(e5_data), _compile_name_subs(name_role_pairs))
